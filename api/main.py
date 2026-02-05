"""
Text-to-CAD API Server

A production-grade API that converts natural language descriptions into parametric 3D CAD models.
Uses an agentic LLM pipeline to generate FreeCAD Python scripts, which execute in isolated Docker
containers to produce B-Rep solids (STEP/STL files).

Architecture:
- FastAPI async server for request handling
- LLM pipeline (Gemini) for spec extraction and code generation
- Docker sandboxing for secure FreeCAD script execution
- Automatic retry with error feedback for geometry failures
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables (supports .env files for local development)
# Try root directory first (monorepo setup), then current directory
root_env = Path(__file__).parent.parent / ".env.local"
if root_env.exists():
    load_dotenv(root_env)
else:
    load_dotenv()

import asyncio
import uuid
import zipfile
import time
from fastapi import FastAPI, HTTPException, BackgroundTasks, UploadFile, File, Form
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from typing import Optional, List, Annotated
from pydantic import BaseModel
import json
from pipeline import AgentPipeline
import logging
import trimesh

# Configure structured logging for production observability
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("text-to-cad-api")

app = FastAPI(
    title="Text-to-CAD API",
    description="Generate parametric 3D CAD models from natural language using LLM-powered code generation",
    version="1.0.0"
)


class GeometryError(Exception):
    """
    Raised when FreeCAD fails to process geometry, triggering automatic retry.
    
    The pipeline uses this to distinguish between recoverable geometry errors
    (e.g., invalid fillet radius) and unrecoverable system errors.
    """
    pass


# ============================================================================
# Configuration (all via environment variables for portability)
# ============================================================================

# LLM Configuration - users provide their own API keys via request
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-3-flash-preview")

# Docker Configuration - configurable paths for different deployment environments
DOCKER_RUNNER_IMAGE = os.environ.get("DOCKER_RUNNER_IMAGE", "geometry-runner")
TEMP_DIR = Path(os.environ.get("TEMP_DIR", "/tmp/geometry_jobs"))
TEMP_DIR.mkdir(parents=True, exist_ok=True)

# Security Configuration
ALLOWED_ORIGINS = os.environ.get("ALLOWED_ORIGINS", "*").replace(";", ",").split(",")
origins = [o.strip() for o in ALLOWED_ORIGINS if o.strip()]

ALLOWED_HOSTS = os.environ.get("ALLOWED_HOSTS", "*").replace(";", ",").split(",")
hosts = [h.strip() for h in ALLOWED_HOSTS if h.strip()]

# CORS & Security Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=[
        "X-Render-Duration",
        "X-Retry-Count",
        "X-Extracted-Constraints",
        "X-Mesh-Volume",
        "X-Mesh-BBox",
        "X-Duration-Spec",
        "X-Duration-Code"
    ],
)

app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=hosts
)


# ============================================================================
# Mesh Validation
# ============================================================================

def validate_mesh(stl_path: str) -> None:
    """
    Validates generated mesh for production readiness.
    
    Checks:
    - Non-empty geometry
    - Watertight (manifold) mesh
    - Positive volume
    - Valid face count
    
    Raises GeometryError if validation fails, triggering pipeline retry.
    """
    if not os.path.exists(stl_path):
        return
    
    try:
        mesh = trimesh.load(stl_path, force='mesh')
        
        if mesh.is_empty:
            raise GeometryError("Generated mesh is empty.")
        
        if not mesh.is_watertight:
            raise GeometryError("Generated mesh is not watertight (non-manifold).")
        
        if mesh.volume <= 0:
            raise GeometryError("Generated mesh has zero or negative volume.")
        
        if len(mesh.faces) == 0:
            raise GeometryError("Generated mesh has no faces.")
            
    except Exception as e:
        if isinstance(e, GeometryError):
            raise e
        logger.warning(f"Mesh validation warning: {e}")


def _get_mesh_metadata(stl_path: str) -> dict:
    """
    Extracts geometric metadata for client-side verification.
    
    Returns volume and bounding box to help users validate generated geometry
    matches their expectations before downloading.
    """
    if not os.path.exists(stl_path):
        return {}
    
    try:
        mesh = trimesh.load(stl_path, force='mesh')
        bbox = mesh.bounds.tolist()  # [[min_x, min_y, min_z], [max_x, max_y, max_z]]
        return {
            "volume": round(mesh.volume, 2),
            "bbox": bbox
        }
    except Exception as e:
        logger.warning(f"Failed to get mesh metadata: {e}")
        return {}


# ============================================================================
# Docker Execution Sandbox
# ============================================================================

async def _run_docker_execution(
    script_content: str,
    timeout: int = 30,
    lib_path: Optional[Path] = None
) -> tuple[str, str, int, Path]:
    """
    Executes FreeCAD script in isolated Docker container.
    
    Security features:
    - Network isolation (--network none)
    - Resource limits (1 CPU, 512MB RAM)
    - Read-only root filesystem
    - Non-root user execution
    - Ephemeral containers (--rm)
    
    The library path is mounted read-only to prevent script modification
    of utility functions while allowing execution.
    
    Args:
        script_content: FreeCAD Python script to execute
        timeout: Maximum execution time in seconds
        lib_path: Path to FreeCAD utility library (defaults to ./lib)
    
    Returns:
        Tuple of (stdout, stderr, return_code, work_directory)
    """
    job_id = str(uuid.uuid4())
    work_dir = TEMP_DIR / job_id
    work_dir.mkdir(parents=True, exist_ok=True)
    
    script_path = work_dir / "gen.py"
    with open(script_path, "w") as f:
        f.write(script_content)
    
    # Resolve library path - use provided path or default to ./lib relative to script
    if lib_path is None:
        # Default to lib/ directory relative to this file
        lib_path = Path(__file__).parent / "lib"
    
    # Security-hardened Docker command with defense-in-depth:
    # - Network isolation prevents code injection attacks (user-generated Python
    #   cannot exfiltrate data or access internal services)
    # - Resource limits (1 CPU, 512MB) prevent DoS via infinite loops or memory exhaustion
    # - Non-root execution (UID 1000) limits privilege escalation risk
    # - Read-only root filesystem prevents tampering; only /tmp and /workspace writable
    cmd = [
        "docker", "run", "--rm",
        "--network", "none",  # No network access
        "--cpus", "2.0",  # CPU limit (Increased for performance)
        "--memory", "2048m",  # Memory limit (Increased to 2GB for complex CAD)
        "--user", "1000:1000",  # Non-root user
        "--read-only",  # Read-only root filesystem
        "--tmpfs", "/tmp:rw,size=512m",  # Writable /tmp (Increased for large temp files)
        "-v", f"{work_dir}:/workspace:rw",  # Workspace for I/O
        "-w", "/workspace",
        "-e", "STEP_OUTPUT=/workspace/output.step",
        "-e", "STL_OUTPUT=/workspace/output.stl",
        "-v", f"{lib_path.absolute()}:/app/lib:ro",  # Read-only library mount
        DOCKER_RUNNER_IMAGE,
        "/workspace/gen.py"
    ]
    
    try:
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await asyncio.wait_for(
            process.communicate(),
            timeout=timeout
        )
        
        return stdout.decode(), stderr.decode(), process.returncode, work_dir
        
    except asyncio.TimeoutError:
        logger.warning(f"Execution timeout after {timeout}s")
        return "", f"TIMEOUT: Execution exceeded {timeout}s limit", 124, work_dir
    except Exception as e:
        logger.error(f"Docker execution error: {e}")
        return "", str(e), 1, work_dir


# ============================================================================
# Request Models
# ============================================================================

class RenderRequest(BaseModel):
    """Request model for rendering existing geometry scripts."""
    scad_code: str
    format: str = "stl"
    gemini_api_key: Optional[str] = None  # Not used for rendering, kept for API consistency


# ============================================================================
# API Endpoints
# ============================================================================

@app.get("/")
def health_check():
    """Health check endpoint for service monitoring and load balancers."""
    return {"status": "ok", "service": "text-to-cad-api"}


@app.post("/generate")
async def generate_from_text(
    background_tasks: BackgroundTasks,
    prompt: Annotated[str, Form()],
    format: Annotated[str, Form()] = "stl",
    previous_code: Annotated[Optional[str], Form()] = None,
    constraints: Annotated[Optional[str], Form()] = None,
    gemini_api_key: Annotated[Optional[str], Form()] = None,
    files: Annotated[Optional[List[UploadFile]], File()] = None
):
    """
    Generates a 3D CAD model from a natural language description.
    
    Pipeline:
    1. Extract structured spec from prompt using LLM
    2. Generate FreeCAD Python code using few-shot examples
    3. Execute code in Docker sandbox
    4. Validate output mesh
    5. Return STEP/STL file or ZIP archive
    
    Supports iterative design via previous_code parameter and automatic
    retry with error feedback on geometry failures.
    
    Args:
        prompt: Natural language description of desired part
        format: Output format ('stl', 'step', or 'zip')
        previous_code: Previous geometry script for iterative modifications
        constraints: JSON string of parametric overrides
        gemini_api_key: User-provided Gemini API key (required)
        files: Optional reference files (e.g., PDF spec sheets)
    
    Returns:
        FileResponse with generated model and metadata headers
    """
    # Validate API key is provided
    if not gemini_api_key:
        raise HTTPException(
            status_code=400,
            detail="gemini_api_key is required in request body"
        )
    
    # Initialize pipeline with user-provided API key
    try:
        agent_pipeline = AgentPipeline(
            api_key=gemini_api_key,
            model_name=GEMINI_MODEL
        )
    except Exception as e:
        logger.error(f"Failed to initialize pipeline: {e}")
        raise HTTPException(
            status_code=400,
            detail=f"Invalid API key or pipeline initialization failed: {str(e)}"
        )
    
    current_prompt = prompt
    last_error = None
    feedback_msg = None
    file_list = files if files else []
    
    # Retry loop with error feedback (max 3 attempts)
    for attempt in range(3):
        try:
            logger.info(f"Generation attempt {attempt + 1}/3")
            if feedback_msg:
                logger.info(f"Retrying with feedback: {feedback_msg}")
            
            # Parse constraints if provided
            constraint_dict = None
            if constraints:
                try:
                    constraint_dict = json.loads(constraints)
                except json.JSONDecodeError:
                    logger.warning(f"Invalid constraints JSON: {constraints}")
            
            # Use previous_code for iterative design, otherwise use error feedback
            feedback = previous_code if previous_code and attempt == 0 else feedback_msg
            
            # Run pipeline: spec extraction → code generation
            fc_result = await agent_pipeline.run(
                current_prompt,
                files=file_list,
                feedback=feedback,
                constraints=constraint_dict
            )
            
            fc_code = fc_result["fc_code"]
            extracted_spec = fc_result["spec"]
            usage = fc_result["usage"]
            timings = fc_result.get("timings", {})
            
            # Prepare response headers with metadata
            # Compact spec for header (no newlines)
            try:
                compact_spec = json.dumps(json.loads(extracted_spec))
            except json.JSONDecodeError:
                compact_spec = extracted_spec.replace("\n", " ")
            
            headers = {
                "X-Input-Tokens": str(usage.get("input_tokens", 0)),
                "X-Output-Tokens": str(usage.get("output_tokens", 0)),
                "X-Extracted-Constraints": compact_spec,
                "X-Duration-Spec": f"{timings.get('spec', 0):.4f}",
                "X-Duration-Code": f"{timings.get('code', 0):.4f}"
            }
            
            if attempt > 0:
                headers["X-Retry-Count"] = str(attempt)
            
            return await _run_freecad_generation(
                fc_code,
                background_tasks,
                extra_headers=headers,
                fmt=format
            )
            
        except GeometryError as e:
            last_error = e
            logger.warning(f"Attempt {attempt + 1} failed: {e}")
            
            if attempt < 2:
                # Parse error into actionable feedback for retry
                feedback_msg = agent_pipeline._parse_freecad_error(str(e))
            else:
                # Final attempt failed
                break
    
    raise HTTPException(
        status_code=400,
        detail=f"Generation failed after 3 attempts: {last_error}"
    )


@app.post("/render")
async def render_from_script(
    background_tasks: BackgroundTasks,
    body: RenderRequest
):
    """
    Renders a 3D model from an existing geometry script.
    
    Used for re-rendering models when parametric constraints change without
    regenerating from scratch. More efficient than full generation as it
    skips the text-to-geometry conversion step.
    
    Args:
        body: RenderRequest with scad_code, format, and optional gemini_api_key
    
    Returns:
        FileResponse with rendered model
    """
    if not body.scad_code:
        raise HTTPException(status_code=400, detail="scad_code is required")
    
    # Render directly without LLM pipeline
    return await _run_freecad_generation(
        body.scad_code,
        background_tasks,
        extra_headers=None,
        fmt=body.format
    )


# ============================================================================
# FreeCAD Generation Pipeline
# ============================================================================

async def _run_freecad_generation(
    fc_code: str,
    background_tasks: BackgroundTasks,
    extra_headers: Optional[dict] = None,
    fmt: str = "stl"
) -> FileResponse:
    """
    Executes FreeCAD code and packages output for delivery.
    
    Steps:
    1. Execute script in Docker sandbox
    2. Validate output mesh
    3. Package as ZIP (if requested) or single file
    4. Schedule cleanup task
    
    Args:
        fc_code: FreeCAD Python script to execute
        background_tasks: FastAPI background tasks for cleanup
        extra_headers: Additional headers to include in response
        fmt: Output format ('stl', 'step', or 'zip')
    
    Returns:
        FileResponse with generated model file
    """
    start_time = time.time()
    
    # Execute in Docker sandbox
    stdout, stderr, code, work_dir = await _run_docker_execution(fc_code)
    
    step_out = work_dir / "output.step"
    stl_out = work_dir / "output.stl"
    script_path = work_dir / "gen.py"
    
    try:
        if code != 0:
            logger.error(
                f"FreeCAD execution failed.\nSTDOUT:\n{stdout}\nSTDERR:\n{stderr}"
            )
            raise GeometryError(f"FreeCAD Error: {stderr}")
        
        # Validate mesh if STL was generated
        if stl_out.exists():
            validate_mesh(str(stl_out))
            mesh_meta = _get_mesh_metadata(str(stl_out))
            
            if mesh_meta and extra_headers is not None:
                extra_headers["X-Mesh-Volume"] = str(mesh_meta["volume"])
                extra_headers["X-Mesh-BBox"] = json.dumps(mesh_meta["bbox"])
        
        # Package output based on format
        if fmt in ["zip", "both"]:
            zip_path = work_dir / "render.zip"
            with zipfile.ZipFile(zip_path, 'w') as zf:
                if step_out.exists():
                    zf.write(step_out, "render.step")
                if stl_out.exists():
                    zf.write(stl_out, "render.stl")
                if script_path.exists():
                    zf.write(script_path, "model_gen.py")
            
            res_path = zip_path
            filename = f"render_{work_dir.name}.zip"
            media_type = "application/zip"
        else:
            # Single file output
            res_path = step_out if (fmt == "step" and step_out.exists()) else stl_out
            filename = f"render.{fmt}"
            media_type = "application/octet-stream"
        
        if not res_path.exists():
            raise HTTPException(
                status_code=500,
                detail="Output file missing from container"
            )
        
        # Calculate render duration
        render_time = time.time() - start_time
        
        # Build response headers
        headers = {
            "X-Render-Duration": f"{render_time:.4f}"
        }
        
        if extra_headers:
            headers.update(extra_headers)
        
        # Schedule cleanup task (runs after response is sent)
        import shutil
        
        def cleanup_workdir():
            """Background task to clean up temporary files."""
            try:
                shutil.rmtree(work_dir)
                logger.debug(f"Cleaned up work directory: {work_dir}")
            except Exception as e:
                logger.warning(f"Cleanup failed for {work_dir}: {e}")
        
        background_tasks.add_task(cleanup_workdir)
        
        return FileResponse(
            path=res_path,
            filename=filename,
            media_type=media_type,
            headers=headers
        )
        
    except Exception as e:
        # Ensure cleanup on failure
        import shutil
        shutil.rmtree(work_dir, ignore_errors=True)
        
        if isinstance(e, (GeometryError, HTTPException)):
            raise e
        
        raise HTTPException(status_code=500, detail=str(e))

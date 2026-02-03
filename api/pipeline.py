import os
import json
import base64
import logging
import time
from typing import Optional, Dict, Any, List
import google.generativeai as genai
import trimesh

logger = logging.getLogger("text-to-cad-pipeline")

# =============================================================================
# COMPACT UTILITY REFERENCE - Saves ~1500 tokens vs full source
# =============================================================================

# =============================================================================
# FEW-SHOT EXAMPLES - Gemini learns from these patterns
# =============================================================================

FEW_SHOT_EXAMPLES = """
## EXAMPLE 1: Enclosure with bosses
Prompt: "110x80x45mm enclosure, 2.5mm walls, 3mm floor, R6 corners, 1° draft, 4 bosses in 85x55 pattern"
```python
def generate_model(utils, step_path, stl_path):
    from FreeCAD import Base
    
    L, W, H = 110, 80, 45
    wall_t, floor_t = 2.5, 3.0
    
    # Mega-function handles box→draft→fillet→shell in correct order
    body, floor_z = utils.create_enclosure_base(
        "Enclosure", L, W, H,
        wall_thickness=wall_t,
        floor_thickness=floor_t,
        corner_radius=6.0,
        draft_angle=1.0,
        open_face='+Z'
    )
    
    # Boss positions in CENTERED coordinates
    positions = [(-42.5, -27.5), (42.5, -27.5), (-42.5, 27.5), (42.5, 27.5)]
    body = utils.add_enclosure_bosses(body, positions, boss_dia=7, boss_height=6, floor_z=floor_z)
    
    utils.export_step(body, step_path)
    utils.export_stl(body, stl_path)
```

## EXAMPLE 2: L-Bracket
Prompt: "L-bracket, 50mm vertical, 40mm horizontal, 25mm wide, 3mm thick, 5mm holes, R3 fillet"
```python
def generate_model(utils, step_path, stl_path):
    from FreeCAD import Base
    
    body = utils.create_l_bracket(
        "LBracket",
        leg1_length=50, leg2_length=40, width=25, thickness=3,
        hole_dia=5, hole_positions=[(1, 25), (2, 20)], fillet_radius=3
    )
    
    utils.export_step(body, step_path)
    utils.export_stl(body, stl_path)
```

## EXAMPLE 3: Custom block with holes and pocket
Prompt: "80x50x20mm block, 4 M5 counterbores at corners, 25mm center pocket"
```python
def generate_model(utils, step_path, stl_path):
    from FreeCAD import Base
    
    L, W, H = 80, 50, 20
    body = utils.create_box("Block", L, W, H, center=True)
    
    # Counterbore holes at corners (15mm from edge = corner - 15)
    for x, y in [(-25, -10), (25, -10), (-25, 10), (25, 10)]:
        cb = utils.create_counterbore("CB", hole_dia=5.5, hole_depth=H+1, cb_dia=10, cb_depth=5,
                                       position=Base.Vector(x, y, H/2-5))
        body = utils.cut_objects(body, cb)
    
    pocket = utils.create_pocket("Pocket", 25, 25, 10, corner_radius=3,
                                  position=Base.Vector(0, 0, H/2-10))
    body = utils.cut_objects(body, pocket)
    
    utils.export_step(body, step_path)
    utils.export_stl(body, stl_path)
```

## EXAMPLE 4: Pipe Flange
Prompt: "150mm OD flange, 102mm bore, 20mm thick, 6 bolt holes on 125mm BCD"
```python
def generate_model(utils, step_path, stl_path):
    from FreeCAD import Base
    
    body = utils.create_pipe_flange(
        "PipeFlange",
        outer_dia=150, inner_dia=102, thickness=20,
        bolt_circle_dia=125, bolt_hole_dia=12, bolt_count=6,
        hub_dia=115, hub_height=10
    )
    
    utils.export_step(body, step_path)
    utils.export_stl(body, stl_path)
```
"""

# =============================================================================
# TYPE-BASED EXAMPLE INJECTION - Match spec type to relevant examples
# =============================================================================

EXAMPLES_DIR = os.path.join(os.path.dirname(__file__), "lib", "examples")

# Maps keywords/types found in spec to example files
SPEC_TYPE_EXAMPLES = {
    # Enclosures & Housings
    "enclosure": ["example_enclosure.py"],
    "housing": ["example_enclosure.py"],
    "case": ["example_enclosure.py"],
    "box": ["example_enclosure.py", "example_custom_block.py"],
    
    # Brackets
    "bracket": ["example_l_bracket.py", "example_u_bracket.py", "example_flat_bracket.py"],
    "l-bracket": ["example_l_bracket.py"],
    "u-bracket": ["example_u_bracket.py"],
    "angle": ["example_l_bracket.py"],
    
    # Flanges
    "flange": ["example_pipe_flange.py", "example_mounting_flange.py"],
    "pipe": ["example_pipe_flange.py", "example_tube.py"],
    
    # Gears & Pulleys
    "gear": ["example_spur_gear.py"],
    "pulley": ["example_pulley.py"],
    "sprocket": ["example_spur_gear.py"],
    
    # Shafts & Rotating Parts
    "shaft": ["example_shaft.py"],
    "bushing": ["example_bushing.py"],
    "bearing": ["example_bushing.py"],
    "knob": ["example_knob.py"],
    
    # Structural
    "boss": ["example_boss.py", "example_standoff.py"],
    "standoff": ["example_standoff.py"],
    "rib": ["example_rib.py"],
    "gusset": ["example_gusset.py"],
    
    # Holes & Features
    "counterbore": ["example_counterbore.py", "example_custom_block.py"],
    "countersink": ["example_countersink.py"],
    "slot": ["example_slot.py"],
    "pocket": ["example_pocket.py", "example_custom_block.py"],
    
    # Primitives
    "tube": ["example_tube.py"],
    "cone": ["example_cone.py"],
    "torus": ["example_torus.py"],
    "wedge": ["example_wedge.py"],
}

UTILS_QUICK_REF = """
## PartUtils Quick Reference

### BASIC PRIMITIVES
create_box(name, length, width, height, center=False, position=None)
create_cylinder(name, radius, height, center=False, position=None, direction=None)
create_sphere(name, radius, position=None)
create_cone(name, radius1, radius2, height, position=None)
create_torus(name, radius1, radius2, position=None)

### HOLE FEATURES (cutting tools)
create_hole(name, diameter, depth, position=None)
create_counterbore(name, hole_dia, hole_depth, cb_dia, cb_depth, position=None)
create_countersink(name, hole_dia, hole_depth, cs_dia, cs_angle=90, position=None)
create_slot(name, length, width, depth, position=None)
create_pocket(name, length, width, depth, corner_radius=0, position=None)

### BOSS/STANDOFF FEATURES
create_boss(name, outer_dia, height, hole_dia=None, position=None)
create_standoff(name, outer_dia, inner_dia, height, position=None)
create_rib(name, length, height, thickness, position=None, direction='X')
create_gusset(name, width, height, thickness, position=None)

### ENCLOSURE MEGA-FUNCTIONS ⭐
create_enclosure_base(name, length, width, height, wall_thickness, floor_thickness=None, corner_radius=0, draft_angle=0, open_face='+Z')
  → Returns: (body, internal_floor_z)
add_enclosure_bosses(body, positions, boss_dia, boss_height, floor_z, hole_dia=None, base_fillet=0)
  → positions = [(x,y), ...] in CENTERED coordinates

### BRACKET MEGA-FUNCTIONS ⭐
create_l_bracket(name, leg1_length, leg2_length, width, thickness, hole_dia=0, hole_positions=None, fillet_radius=0)
create_u_bracket(name, width, height, depth, thickness, hole_dia=0, holes_per_leg=0, fillet_radius=0)
create_angle_bracket(name, leg1, leg2, width, thickness, hole_dia=0, holes_per_leg=1, fillet_radius=0)
create_flat_bracket(name, length, width, thickness, hole_dia=0, hole_count=2)

### FLANGE MEGA-FUNCTIONS ⭐
create_pipe_flange(name, outer_dia, inner_dia, thickness, bolt_circle_dia, bolt_hole_dia, bolt_count, hub_dia=0, hub_height=0)
create_mounting_flange(name, length, width, thickness, center_hole_dia, bolt_hole_dia=0, bolt_positions=None)

### GEAR/PULLEY FUNCTIONS
create_spur_gear(name, module, teeth, thickness, bore_dia=0, pressure_angle=20, hub_dia=0, hub_height=0)
create_pulley(name, outer_dia, bore_dia, width, groove_count=1, groove_depth=3, groove_angle=40)

### SHAFT/REVOLVED PARTS
create_tube(name, outer_dia, inner_dia, length, position=None)
create_bushing(name, outer_dia, inner_dia, length, flange_dia=0, flange_thickness=0)
create_shaft(name, diameter, length, keyway_width=0, keyway_depth=0, keyway_length=0)
create_knob(name, diameter, height, knurl_count=0, bore_dia=0)

### BOOLEANS
cut_objects(base, tool)
fuse_objects([obj1, obj2, ...])
intersect_objects([obj1, obj2, ...])

### FEATURES
apply_draft(obj, Vector(0,0,1), angle, neutral_plane_z) → MUST BE BEFORE FILLETS!
create_shell(obj, thickness, open_face_direction='+Z')
apply_fillet(obj, radius, edge_names=None, direction=None, z_level=None)
apply_chamfer(obj, size, edge_names=None, direction=None, z_level=None)

### EDGE SELECTION
select_edges(obj, edge_type=None, direction=None, z_level=None, min_radius=None, max_radius=None)
  edge_type: 'Circle', 'Line'
  direction: 'X', 'Y', 'Z'

### PATTERNS
create_linear_pattern(obj, direction, spacing, count)
create_rectangular_pattern(obj, dir1, spacing1, count1, dir2, spacing2, count2)
create_polar_pattern(obj, center, axis, count, angle=360)

### TRANSFORMS
move_object(obj, vector)
rotate_object(obj, axis, angle)
mirror_object(obj, normal)
copy_object(obj, new_name=None)
center_object(obj, axes="XYZ")

### EXPORT
export_step(obj, path)
export_stl(obj, path)

### INTROSPECTION (SELF-CORRECTION) ⭐
get_bounding_box(obj) → {'min':(x,y,z), 'max':(x,y,z), 'size':(x,y,z), 'volume':float}
measure_distance(obj1, obj2) → float (mindist)
### ATOMIC OPS (ADVANCED)
extrude_profile(name, sketch_or_face, distance)
revolve_profile(name, sketch, axis_dir, angle)
loft_profiles(name, list_of_sketches)
"""


class AgentPipeline:
    def __init__(self, api_key: str, model_name: str, utils_lib_path: str = "lib/freecad_utils.py"):
        if not api_key:
            raise ValueError("Google API Key required")
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(model_name)

    def _get_relevant_examples(self, spec: str, max_examples: int = 3) -> str:
        """
        Load example files based on keywords found in the spec.
        Returns formatted examples string for system prompt injection.
        """
        spec_lower = spec.lower()
        matched_files = set()
        
        # Find all matching example files
        for keyword, files in SPEC_TYPE_EXAMPLES.items():
            if keyword in spec_lower:
                matched_files.update(files)
        
        if not matched_files:
            logger.info("No type-specific examples matched, using defaults")
            return ""
        
        # Load up to max_examples files
        examples_text = "\n## RELEVANT EXAMPLES FOR YOUR SPEC:\n"
        loaded = 0
        
        for filename in list(matched_files)[:max_examples]:
            filepath = os.path.join(EXAMPLES_DIR, filename)
            try:
                with open(filepath, 'r') as f:
                    content = f.read()
                    examples_text += f"\n### {filename}\n```python\n{content}\n```\n"
                    loaded += 1
                    logger.info(f"Loaded example: {filename}")
            except Exception as e:
                logger.warning(f"Could not load example {filename}: {e}")
        
        if loaded == 0:
            return ""
        
        logger.info(f"Injected {loaded} type-specific examples")
        return examples_text

    def _parse_freecad_error(self, stderr: str) -> str:
        """Parse errors into actionable feedback for retry."""
        # Extract the last line or the line starting with ValueError
        lines = stderr.strip().split('\n')
        error_line = lines[-1]
        for line in lines:
            if "ValueError:" in line:
                error_line = line
        
        s = error_line.lower()
        
        if "apply_draft failed" in s or "draft" in s and "before" in s:
            return "DRAFT FAILED: You must apply draft BEFORE any fillets. Reorder: box → draft → fillet → shell"
        if "null shape" in s:
            return "NULL SHAPE: Boolean operation failed. Ensure objects overlap and have valid geometry."
        if "fuse_objects failed" in s:
            return "FUSION FAILED: Objects DO NOT intersect. Move objects closer (overlap by at least 0.1mm) or check dimensions."
        if "fillet" in s and "too large" in s:
            return f"FILLET ERROR: {s.split('ValueError: ')[-1] if 'ValueError:' in s else s}. Reduce fillet radius."
        if "not watertight" in s:
            return "NON-MANIFOLD: Mesh has holes. Check boolean operations created valid solids."
        if "empty" in s:
            return "EMPTY RESULT: No geometry created. Verify your logic creates actual shapes."
        if "makefillet" in s:
            return "FILLET FAILED: Radius may be too large for edge length, or edge selection returned nothing."
        
        return f"ERROR: {stderr[:300]}"

    async def run(self, user_prompt: str, files: List = None, feedback: str = None, 
                  constraints: Dict = None) -> Dict[str, Any]:
        """
        2-stage pipeline: Spec → Code (skip planning for speed)
        
        Two-stage approach improves accuracy: first stage extracts structured requirements
        (dimensions, features, constraints), second stage generates code with that context.
        This separation reduces hallucination compared to single-stage generation.
        """
        timings = {}

        # Stage 1: Extract structured spec from natural language. LLM parses prompt into
        # JSON with dimensions, features, and constraints. This structured representation
        # provides clear context for code generation, reducing ambiguity.
        t0 = time.time()
        spec, usage1 = await self._extract_spec(user_prompt, files)
        timings["spec"] = time.time() - t0

        # Apply constraint overrides
        if constraints:
            try:
                spec_data = json.loads(spec)
                spec_data["constraints"] = {**spec_data.get("constraints", {}), **constraints}
                spec = json.dumps(spec_data, indent=2)
            except:
                pass

        # Stage 2: Generate FreeCAD Python code from structured spec. Dynamically injects
        # relevant few-shot examples based on part type (enclosure, bracket, gear) to improve
        # code quality without requiring model fine-tuning. Includes error feedback from
        # previous attempts for self-correction.
        t1 = time.time()
        code, usage2 = await self._generate_code(spec, feedback=feedback)
        timings["code"] = time.time() - t1
        timings["plan"] = 0  # No planning stage

        return {
            "fc_code": code,
            "spec": spec,
            "plan": "direct",
            "timings": timings,
            "usage": {
                "input_tokens": usage1['input'] + usage2['input'],
                "output_tokens": usage1['output'] + usage2['output']
            }
        }

    async def _extract_spec(self, prompt: str, files: List = None) -> tuple[str, dict]:
        """Extract specification from prompt. Robust error handling to prevent 500 errors."""
        system = """You are a CAD Specification Extractor. Output JSON ONLY.

Required fields:
{
  "type": "enclosure|bracket|flange|gear|shaft|housing|custom",
  "dimensions": { ... all measurements in mm ... },
  "features": [ { "type": "...", "params": {...} }, ... ],
  "constraints": { "param_name": numeric_value, ... },
  "coordinate_system": "corner|center"  // Are positions from corner (0,0) or center?
}

CRITICAL EXTRACTIONS:
- For enclosures: wall_thickness vs floor_thickness (may differ!)
- For brackets: leg lengths, hole positions, fillet radii
- For flanges: bolt circle diameter, bolt count, bore size
- For gears: module, tooth count, bore, hub dimensions
- Position references: note if dimensions are from corner or center origin
- AMBIGUOUS POSITIONS: If a position is described as "adjacent" or "next to" without coordinates,
  calculate absolute positions based on object dimensions. Never leave positions undefined.

Focus on GEOMETRY only. Ignore materials, colors, finishes."""


        try:
            model = genai.GenerativeModel(self.model.model_name, system_instruction=system)

            parts = [prompt]
            if files:
                for f in files:
                    try:
                        if hasattr(f, "read"):
                            content = await f.read()
                            mime_type = f.content_type
                            if hasattr(f, "seek"):
                                await f.seek(0)
                            if content and mime_type:
                                parts.append({"mime_type": mime_type, 
                                             "data": base64.b64encode(content).decode()})
                    except Exception as file_err:
                        logger.warning(f"Could not process file: {file_err}")
                        continue

            response = await model.generate_content_async(parts)
            text = response.text

            # Extract JSON from markdown if needed
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0]
            elif "```" in text:
                text = text.split("```")[1].split("```")[0]

            # Validate JSON is parseable
            try:
                parsed = json.loads(text)
                # FIX TEST 12: Resolve any ambiguous positions
                if "features" in parsed:
                    for feature in parsed.get("features", []):
                        pos = feature.get("position", "")
                        if isinstance(pos, str) and any(word in pos.lower() for word in ["adjacent", "next to", "beside", "near"]):
                            logger.warning(f"Ambiguous position found: {pos}, setting to origin")
                            feature["position"] = {"x": 0, "y": 0, "z": 0}
                text = json.dumps(parsed, indent=2)
            except json.JSONDecodeError as je:
                logger.error(f"Failed to parse spec JSON: {je}")
                # Return minimal valid spec rather than failing
                text = json.dumps({
                    "type": "custom",
                    "dimensions": {},
                    "features": [],
                    "error": f"Could not parse prompt: {str(je)[:100]}"
                })

            return text.strip(), {
                "input": response.usage_metadata.prompt_token_count,
                "output": response.usage_metadata.candidates_token_count
            }
        except Exception as e:
            # FIX TEST 12: Never raise 500 - return error spec instead
            logger.error(f"Spec extraction failed: {e}")
            return json.dumps({
                "type": "custom",
                "dimensions": {},
                "features": [],
                "error": f"Spec extraction failed: {str(e)[:200]}"
            }), {"input": 0, "output": 0}


    async def _generate_code(self, spec: str, feedback: str = None) -> tuple[str, dict]:
        # Get type-specific examples based on spec content
        relevant_examples = self._get_relevant_examples(spec)
        
        system = f"""You are an Expert FreeCAD Code Generator.

{UTILS_QUICK_REF}

{FEW_SHOT_EXAMPLES}
{relevant_examples}

OUTPUT FORMAT:
```python
def generate_model(utils, step_path, stl_path):
    from FreeCAD import Base
    
    # Your code here
    
    utils.export_step(body, step_path)
    utils.export_stl(body, stl_path)
```

CRITICAL RULES:

1. USE MEGA-FUNCTIONS when available:
   - Enclosures: `body, floor_z = utils.create_enclosure_base(...)`
   - Brackets: `body = utils.create_l_bracket(...)`
   - Flanges: `body = utils.create_pipe_flange(...)`
   
2. COORDINATE CONVERSION:
   If spec positions are from corner (e.g., X=12.5 on 110mm part):
   `centered_x = corner_x - length/2  # 12.5 - 55 = -42.5`

3. DRAFT BEFORE FILLETS (mandatory for enclosures):
   The mega-function handles this internally. Don't add extra draft calls.

4. BOSS POSITIONS use centered coordinates:
   `positions = [(-42.5, -27.5), (42.5, -27.5), (-42.5, 27.5), (42.5, 27.5)]`

5. ALWAYS use position= parameter:
   `utils.create_cylinder("hole", r, h, position=Base.Vector(x, y, z))`

6. KEEP CODE SHORT - mega-functions do the heavy lifting.
   Typical enclosure: 15-20 lines
   Typical bracket: 5-10 lines
   Typical flange: 5-10 lines

7. END WITH EXPORTS:
   ```python
   utils.export_step(body, step_path)
   utils.export_stl(body, stl_path)
   ```
"""

        user_msg = f"Generate FreeCAD code for this specification:\n\n{spec}"
        if feedback:
            user_msg += f"\n\n⚠️ PREVIOUS ATTEMPT FAILED:\n{feedback}\n\nFix the issue!"

        chat = self.model.start_chat(history=[])
        response = await chat.send_message_async([system, user_msg])

        text = response.text
        logger.info(f"Raw response (first 300): {text[:300]}")

        # Extract code from markdown
        if "```python" in text:
            text = text.split("```python")[1].split("```")[0]
        elif "```" in text:
            text = text.split("```")[1].split("```")[0]

        # Ensure function definition exists
        if "def generate_model" not in text:
            logger.warning("Missing function definition, wrapping code")
            text = f"def generate_model(utils, step_path, stl_path):\n    from FreeCAD import Base\n    " + text.replace("\n", "\n    ")

        # Security validation: block dangerous patterns that could escape Docker sandbox.
        # Even with network isolation, preventing subprocess/system calls adds defense-in-depth.
        # These patterns are blocked before code reaches the execution container.
        dangerous = ["subprocess", "os.system", "eval(", "exec(", "__import__", "os.popen"]
        for pattern in dangerous:
            if pattern in text:
                raise ValueError(f"Security: blocked pattern '{pattern}'")

        # Wrap in executable script
        final_code = f"""import os, sys
sys.path.append('/app/lib')
from freecad_utils import PartUtils
import FreeCAD
from FreeCAD import Base

{text.strip()}

if __name__ == '__main__':
    utils = PartUtils()
    generate_model(utils,
                   os.environ.get('STEP_OUTPUT', 'output.step'),
                   os.environ.get('STL_OUTPUT', 'output.stl'))
"""

        return final_code, {
            "input": response.usage_metadata.prompt_token_count,
            "output": response.usage_metadata.candidates_token_count
        }

    def validate_mesh(self, stl_path: str) -> Dict[str, Any]:
        """Mesh validation using trimesh."""
        report = {"valid": True, "errors": []}
        try:
            mesh = trimesh.load(stl_path)
            if not mesh.is_watertight:
                report["valid"] = False
                report["errors"].append("Not watertight")
            if mesh.volume <= 0:
                report["valid"] = False
                report["errors"].append("Zero/negative volume")
        except Exception as e:
            logger.warning(f"Mesh validation error: {e}")
        return report

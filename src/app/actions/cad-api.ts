'use server';

/**
 * Server Actions for CAD generation API integration.
 *
 * Uses Next.js Server Actions to securely communicate with the backend API
 * without exposing credentials to the client. User-provided Gemini API keys
 * are passed through to the backend for LLM processing.
 *
 * @requires NEXT_PUBLIC_API_BASE_URL - Base URL of the CAD generation API
 */

// Use local API if NEXT_PUBLIC_API_BASE_URL is not set (monorepo default)
const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8080';

export interface RenderResponse {
  url: string;
  duration: number;
  base64?: string;
  extractedConstraints?: Record<string, number> | null;
}

/**
 * Generates a 3D CAD model from a natural language description.
 *
 * Sends a text prompt to the backend API which processes it through
 * a generative geometry engine. Returns a ZIP archive containing STL
 * (for visualization), STEP (for CAD import), and the source geometry script.
 *
 * @param prompt - Natural language description of the desired part
 * @param format - Output format: 'stl', 'step', or 'zip' (default: 'stl')
 * @param previousScript - Optional geometry script from previous generation for iterative design
 * @param constraints - Optional parametric constraints to override extracted values
 * @param file - Optional reference file (e.g., PDF spec sheet)
 * @param geminiApiKey - User-provided Gemini API key for backend LLM processing
 * @returns Base64-encoded model data, processing duration, and extracted parametric constraints
 * @throws Error if API key is missing or API request fails
 */
export async function generateModelAction(
  prompt: string,
  format: 'stl' | 'step' | 'zip' = 'stl',
  previousScript?: string,
  constraints?: Record<string, number>,
  file?: File,
  geminiApiKey?: string, // User-provided Gemini API key
) {
  if (!API_BASE_URL) {
    throw new Error(
      'Server Misconfiguration: NEXT_PUBLIC_API_BASE_URL environment variable is required',
    );
  }

  if (!geminiApiKey) {
    throw new Error('Gemini API key is required. Please enter your Google Gemini API key.');
  }

  try {
    const formData = new FormData();
    formData.append('prompt', prompt);
    if (format) formData.append('format', format);
    if (previousScript) formData.append('previous_code', previousScript);
    formData.append('gemini_api_key', geminiApiKey); // Add user's Gemini API key

    if (constraints && Object.keys(constraints).length > 0) {
      formData.append('constraints', JSON.stringify(constraints));
    }

    if (file) {
      formData.append('file', file);
    }

    const response = await fetch(`${API_BASE_URL}/generate`, {
      method: 'POST',
      body: formData,
    });

    if (!response.ok) {
      const errorText = await response.text();
      const errorMessage = `API request failed: ${response.status} ${response.statusText} - ${errorText}`;
      throw new Error(errorMessage);
    }

    const duration = parseFloat(response.headers.get('X-Render-Duration') || '0');

    // Extract parametric constraints from response header for UI editing
    const constraintsHeader = response.headers.get('X-Extracted-Constraints');
    let extractedConstraints: Record<string, number> | null = null;
    if (constraintsHeader) {
      try {
        extractedConstraints = JSON.parse(constraintsHeader);
      } catch (e) {
        console.warn('Failed to parse extracted constraints header', e);
      }
    }

    const arrayBuffer = await response.arrayBuffer();
    const base64 = Buffer.from(arrayBuffer).toString('base64');

    return {
      base64,
      duration,
      extractedConstraints,
    };
  } catch (error: unknown) {
    throw error;
  }
}

/**
 * Renders a 3D model from an existing geometry script.
 *
 * Used for re-rendering models when parametric constraints change without
 * regenerating the entire geometry. More efficient than full generation
 * as it skips the text-to-geometry conversion step.
 *
 * @param modelScript - Source geometry script (e.g., OpenSCAD, Python, or custom format)
 * @param format - Output format: 'stl' or 'step' (default: 'stl')
 * @param geminiApiKey - User-provided Gemini API key for backend processing
 * @returns Base64-encoded model file and processing duration
 * @throws Error if API key is missing or rendering fails
 */
export async function renderModelAction(
  modelScript: string,
  format: 'stl' | 'step' = 'stl',
  geminiApiKey?: string,
) {
  if (!API_BASE_URL) {
    throw new Error(
      'Server Misconfiguration: NEXT_PUBLIC_API_BASE_URL environment variable is required',
    );
  }

  if (!geminiApiKey) {
    throw new Error('Gemini API key is required. Please enter your Google Gemini API key.');
  }

  try {
    const response = await fetch(`${API_BASE_URL}/render`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        scad_code: modelScript,
        format,
        gemini_api_key: geminiApiKey,
      }),
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`API Render Failed: ${errorText}`);
    }

    const duration = parseFloat(response.headers.get('X-Render-Duration') || '0');
    const arrayBuffer = await response.arrayBuffer();
    const base64 = Buffer.from(arrayBuffer).toString('base64');

    return {
      base64,
      duration,
    };
  } catch (error: unknown) {
    if (error instanceof Error) {
      throw error;
    }
    throw new Error('Failed to compute geometry logic.');
  }
}

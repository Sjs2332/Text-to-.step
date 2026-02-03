import JSZip from 'jszip';

// Extracts STL, STEP, and geometry script files from ZIP archive returned by API
export async function extractFilesFromZip(
  zipBlob: Blob,
): Promise<{ stlUrl: string; stepUrl: string | null; modelScript: string | null }> {
  try {
    if (!zipBlob || zipBlob.size === 0) {
      return { stlUrl: '', stepUrl: null, modelScript: null };
    }
    const zip = await JSZip.loadAsync(zipBlob);
    let stlUrl = '';
    let stepUrl: string | null = null;

    // Find files (looking for .stl and .step extensions)
    const stlFile = Object.values(zip.files).find((f) => f.name.toLowerCase().endsWith('.stl'));
    const stepFile = Object.values(zip.files).find((f) => f.name.toLowerCase().endsWith('.step'));

    if (stlFile) {
      const stlBlob = await stlFile.async('blob');
      // Create blob URL for Three.js STLLoader. Blob URLs are temporary and
      // must be revoked when no longer needed to prevent memory leaks.
      stlUrl = URL.createObjectURL(stlBlob);
    } else {
      throw new Error('No model mesh found in generated output');
    }

    if (stepFile) {
      const stepBlob = await stepFile.async('blob');
      // STEP file blob URL for download. Not loaded into viewer (Three.js
      // doesn't support STEP), but available for direct download.
      stepUrl = URL.createObjectURL(stepBlob);
    }

    // Extract model script (logic source)
    const scriptFile = Object.values(zip.files).find(
      (f) =>
        f.name.toLowerCase().endsWith('.scad') ||
        f.name.toLowerCase().endsWith('.py') ||
        f.name.toLowerCase().endsWith('.fge'),
    );
    let modelScript: string | null = null;
    if (scriptFile) {
      modelScript = await scriptFile.async('string');
    }

    return { stlUrl, stepUrl, modelScript };
  } catch (error) {
    throw error;
  }
}

// Converts base64-encoded model data to Blob for browser download/display
export function base64ToBlob(base64: string, mimeType: string): Blob {
  const binaryString = atob(base64);
  const bytes = new Uint8Array(binaryString.length);
  for (let i = 0; i < binaryString.length; i++) {
    bytes[i] = binaryString.charCodeAt(i);
  }
  return new Blob([bytes], { type: mimeType });
}

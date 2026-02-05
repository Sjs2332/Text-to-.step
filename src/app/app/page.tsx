'use client';

import { CADChat } from '@/components/app/ai-chat';
import { ActionBar, ViewPreset } from '@/components/app/action-bar';
import { ModelViewer } from '@/components/app/model-viewer';
import { ConstraintsPanel } from '@/components/app/constraints-panel';
import { useState, useCallback } from 'react';
import { Loader2 } from 'lucide-react';
import { generateModelAction, renderModelAction } from '@/app/actions/cad-api';

import { extractFilesFromZip, base64ToBlob } from '@/lib/file-utils';

export default function AppPage() {
  // State management for model generation workflow
  const [stlState, setStlState] = useState<{ path: string; version: number } | null>(null);
  const [stepState, setStepState] = useState<string | null>(null);
  const [modelScript, setModelScript] = useState<string | null>(null);
  const [zipState, setZipState] = useState<Blob | null>(null);
  const [viewPreset, setViewPreset] = useState<ViewPreset>('iso');
  const [previewStatus, setPreviewStatus] = useState('');
  const [isGenerating, setIsGenerating] = useState(false);
  const [currentPrompt, setCurrentPrompt] = useState<string>('');
  const [constraints, setConstraints] = useState<Record<string, number>>({});
  const [currentThreadId, setCurrentThreadId] = useState<string | null>(null);
  const [isMeasureMode, setIsMeasureMode] = useState(false);

  const handleModelGenerated = useCallback(
    async (
      stlUrl: string,
      stepUrl: string | null,
      prompt: string,
      zipBlob: Blob,
      extractedConstraints?: Record<string, number> | null,
      threadId?: string,
    ) => {
      // Revoke previous blob URLs to prevent memory leaks. Browser maintains blob URLs
      // in memory until explicitly revoked or page unloads. Without cleanup, switching
      // between models accumulates orphaned blob references.
      if (stlState?.path) URL.revokeObjectURL(stlState.path);
      if (stepState) URL.revokeObjectURL(stepState);

      setStlState({ path: stlUrl, version: Date.now() });
      setStepState(stepUrl);
      setZipState(zipBlob);

      extractFilesFromZip(zipBlob)
        .then(({ modelScript: newScript }) => {
          if (newScript) setModelScript(newScript);
        })
        .catch((e) => console.error('Script extraction failed:', e));

      setCurrentPrompt(prompt);
      if (extractedConstraints) {
        setConstraints(extractedConstraints);
      }
      setPreviewStatus('Generated');
      setIsGenerating(false);
    },
    [stlState, stepState],
  );

  const handleGenerationStart = useCallback(() => {
    setIsGenerating(true);
    setPreviewStatus('Generating...');
  }, []);

  const handleChatReset = useCallback(() => {
    if (stlState?.path) URL.revokeObjectURL(stlState.path);
    if (stepState) URL.revokeObjectURL(stepState);

    setStlState(null);
    setStepState(null);
    setModelScript(null);
    setZipState(null);
    setPreviewStatus('');
    setCurrentThreadId(null);
    setIsMeasureMode(false);

    setConstraints({});
  }, [stlState, stepState]);

  const handleThreadSelected = useCallback(async (data: { prompt: string; threadId?: string }) => {
    setCurrentPrompt(data.prompt);
    setCurrentThreadId(data.threadId || null);
    setPreviewStatus('No Model');
  }, []);

  const handleExport = useCallback(
    async (format: 'stl' | 'step' | 'script') => {
      if (format === 'stl' && stlState?.path) {
        const link = document.createElement('a');
        link.href = stlState.path;
        link.download = `model_${Date.now()}.stl`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
      } else if (format === 'step') {
        if (stepState) {
          const link = document.createElement('a');
          link.href = stepState;
          link.download = `model_${Date.now()}.step`;
          document.body.appendChild(link);
          link.click();
          document.body.removeChild(link);
        } else if (zipState) {
          try {
            setPreviewStatus('Extracting STEP...');
            const { stepUrl } = await extractFilesFromZip(zipState);
            if (stepUrl) {
              setStepState(stepUrl);
              const link = document.createElement('a');
              link.href = stepUrl;
              link.download = `model_${Date.now()}.step`;
              document.body.appendChild(link);
              link.click();
              document.body.removeChild(link);
              setPreviewStatus('Exported STEP');
            } else {
              if (!modelScript) {
                alert('Source geometry missing. Cannot export STEP.');
                return;
              }

              setPreviewStatus('Converting to STEP...');
              try {
                // Get Gemini API key from localStorage (set by user in chat component)
                const geminiApiKey =
                  typeof window !== 'undefined'
                    ? localStorage.getItem('gemini_api_key') || undefined
                    : undefined;

                if (!geminiApiKey) {
                  alert('Gemini API key is required. Please set it in the chat interface.');
                  setPreviewStatus('API Key Required');
                  return;
                }

                const { base64 } = await renderModelAction(modelScript, 'step', geminiApiKey);
                if (base64) {
                  const blob = base64ToBlob(base64, 'application/step');
                  const url = URL.createObjectURL(blob);

                  const link = document.createElement('a');
                  link.href = url;
                  link.download = `model_${Date.now()}.step`;
                  document.body.appendChild(link);
                  link.click();
                  document.body.removeChild(link);

                  setTimeout(() => URL.revokeObjectURL(url), 1000);
                  setPreviewStatus('Exported STEP');
                }
              } catch (error: unknown) {
                console.error('STEP export failed:', error);
                setPreviewStatus('Export Failed');
                alert('Export failed. Please try again.');
              }
            }
          } catch {
            setPreviewStatus('Extract Failed');
          }
        }
      } else if (format === 'script') {
        if (modelScript) {
          const blob = new Blob([modelScript], { type: 'text/x-python' });
          const url = URL.createObjectURL(blob);
          const link = document.createElement('a');
          link.href = url;
          link.download = `model_script_${Date.now()}.py`;
          document.body.appendChild(link);
          link.click();
          document.body.removeChild(link);
          setTimeout(() => URL.revokeObjectURL(url), 1000);
          setPreviewStatus('Exported Script');
        } else {
          alert('No source script available.');
        }
      } else {
        alert('No model data available to export.');
      }
    },
    [stlState, stepState, zipState, modelScript],
  );

  return (
    <main className="h-screen w-full overflow-hidden bg-background text-foreground">
      <div className="flex h-full min-h-0 w-full flex-col md:flex-row">
        <div className="flex-1 relative bg-muted/5 min-w-0">
          {stlState && (
            <aside className="hidden md:flex flex-col absolute left-0 top-0 bottom-0 w-[200px] border-r border-border bg-background/95 backdrop-blur-sm z-50 shadow-2xl animate-in slide-in-from-left duration-300">
              <ConstraintsPanel constraints={constraints} />
            </aside>
          )}

          <ActionBar
            onViewPresetChange={setViewPreset}
            isRendering={isGenerating}
            previewStatus={previewStatus || (stlState ? 'Model Ready' : '')}
            isSidebarOpen={!!stlState}
            isMeasureMode={isMeasureMode}
            onToggleMeasure={() => setIsMeasureMode(!isMeasureMode)}
          />

          <div className="absolute inset-0 z-0">
            <ModelViewer
              fileName="generated_model.stl"
              stlPath={stlState?.path}
              stlVersion={stlState?.version}
              viewPreset={viewPreset}
              onExport={handleExport}
              isMeasureMode={isMeasureMode}
              onMeasureModeChange={setIsMeasureMode}
            />

            {isGenerating && (
              <div className="absolute inset-0 bg-background/50 backdrop-blur-[1px] flex items-center justify-center z-10 transition-all duration-500">
                <div className="flex flex-col items-center gap-3">
                  <div className="rounded-full bg-background p-3 shadow-lg border border-border">
                    <Loader2 className="h-6 w-6 animate-spin text-primary" />
                  </div>
                  <div className="text-sm font-medium text-muted-foreground bg-background/80 px-3 py-1 rounded-full border border-border/50">
                    Constructing geometry...
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
        <aside className="flex min-h-0 h-[45vh] w-full flex-col border-t border-border md:h-auto md:w-[520px] md:border-l md:border-t-0 bg-background">
          <div className="flex-1 min-h-0">
            <CADChat
              onModelGenerated={handleModelGenerated}
              onGenerationStart={handleGenerationStart}
              onChatReset={handleChatReset}
              onThreadSelected={handleThreadSelected}
              currentThreadId={currentThreadId}
              onThreadIdChange={setCurrentThreadId}
              onExport={handleExport}
            />
          </div>
        </aside>
      </div>
    </main>
  );
}

'use client';

import { useEffect, useRef, useState } from 'react';
import {
  ArrowUp,
  Clock,
  SquarePen,
  Settings2,
  Check,
  Copy,
  TrendingUp,
  Loader2,
  Box,
  Download,
  Key,
} from 'lucide-react';
import { generateModelAction } from '@/app/actions/cad-api';
import { extractFilesFromZip, base64ToBlob } from '@/lib/file-utils';
import { cn } from '@/lib/utils';
import { HistorySidebar } from './history-sidebar';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';

// Chat threads stored in local component state (no persistence)
type ChatThread = {
  id: string;
  title: string;
  createdAt: Date;
};

type ChatMessage = {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  isGenerationCard?: boolean;
  generationState?: 'working' | 'done';
  genNum?: number;
  isDownloadPrompt?: boolean; // NEW: Flag for download prompt message
  fileData?: {
    stlUrl: string;
    stepUrl: string | null;
    modelScript: string | null;
  };
};

function CopyButton({ content }: { content: string }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    await navigator.clipboard.writeText(content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <button
      onClick={handleCopy}
      className="absolute bottom-2 right-2 p-1 rounded-full bg-primary-foreground/10 hover:bg-primary-foreground/20 text-primary-foreground opacity-70 hover:opacity-100 transition-opacity"
      title="Copy description"
    >
      {copied ? <Check className="h-3 w-3" /> : <Copy className="h-3 w-3" />}
    </button>
  );
}

const INITIAL_MESSAGES: ChatMessage[] = [
  {
    id: 'welcome',
    role: 'assistant',
    content:
      '**This system produces STEP files, not concept art.**\n**Include dimensions and constraints in your prompt.**\n\n**Good request:**\nHeat sink: 60x60mm base, 5mm thick, 20x vertical fins (25mm height, 1.5mm thickness)\n\n**Bad request:**\ngenerate a heat sink',
  },
];

function formatMessage(content: string) {
  const parts = content.split(/(\*\*.*?\*\*)/g);
  return parts.map((part, index) => {
    if (part.startsWith('**') && part.endsWith('**')) {
      return (
        <strong key={index} className="font-bold text-foreground">
          {part.slice(2, -2)}
        </strong>
      );
    }
    return <span key={index}>{part}</span>;
  });
}

const GENERATION_STEPS = [
  'Analyzing request…',
  'Synthesizing constraints',
  'Refining structure',
  'Stabilizing form',
  'Finalizing output',
];

function GenerationCard({
  state,
  generationNum,
}: {
  state: 'working' | 'done';
  generationNum: number;
}) {
  const [visibleSteps, setVisibleSteps] = useState<number>(() =>
    state === 'done' ? GENERATION_STEPS.length : 0,
  );

  useEffect(() => {
    if (state === 'done') {
      const timer = setTimeout(() => setVisibleSteps(GENERATION_STEPS.length), 0);
      return () => clearTimeout(timer);
    }

    if (visibleSteps >= GENERATION_STEPS.length) return;

    const interval = setInterval(() => {
      setVisibleSteps((prev) => {
        if (prev < GENERATION_STEPS.length) return prev + 1;
        clearInterval(interval);
        return prev;
      });
    }, 500);

    return () => clearInterval(interval);
  }, [state, visibleSteps]);

  return (
    <div className="w-full rounded-xl border bg-card text-card-foreground shadow-sm overflow-hidden">
      <div className="border-b bg-muted/30 px-4 py-3 flex justify-between items-center h-10">
        <span className="text-xs font-semibold uppercase tracking-wider text-muted-foreground/70">
          Generation Protocol
        </span>
        {state === 'done' && (
          <div className="flex items-center gap-1.5 rounded-full border border-green-500/20 bg-green-500/10 px-2.5 py-0.5 text-xs font-medium text-green-700 dark:text-green-400 shadow-sm">
            <div className="h-1.5 w-1.5 rounded-full bg-green-500 shadow-[0_0_8px_rgba(34,197,94,0.6)] animate-pulse" />
            Complete
          </div>
        )}
      </div>
      <div className="p-5 space-y-3">
        {GENERATION_STEPS.map((step, i) => {
          const isCurrent = i === visibleSteps - 1 && state === 'working';
          const isCompleted = i < visibleSteps - 1 || state === 'done';
          const isVisible = i < visibleSteps;
          const isLast = i === GENERATION_STEPS.length - 1;
          const isFinalizing = step === 'Finalizing output';

          return (
            <div
              key={step}
              className={`flex items-center justify-between transition-all duration-500 ease-out transform ${
                isVisible ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-2'
              }`}
            >
              <div className="flex items-center gap-3 text-sm">
                <span
                  className={`font-mono text-xs transition-colors duration-300 ${
                    isCurrent ? 'text-primary font-bold' : 'text-muted-foreground/40'
                  }`}
                >
                  {String(i + 1).padStart(2, '0')}
                </span>
                <span
                  className={`transition-all duration-300 ${
                    isCurrent
                      ? 'text-foreground font-bold scale-[1.02] origin-left'
                      : isCompleted
                        ? 'text-muted-foreground/70'
                        : 'text-muted-foreground'
                  } ${isFinalizing && isCurrent ? 'animate-text-shimmer' : ''}`}
                >
                  {step}
                </span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

interface CADChatProps {
  onModelGenerated: (
    stlUrl: string,
    stepUrl: string | null,
    prompt: string,
    zipBlob: Blob,
    constraints?: Record<string, number> | null,
    threadId?: string,
  ) => void;
  onGenerationStart?: () => void;
  onChatReset: () => void;
  onThreadSelected: (data: { prompt: string; threadId?: string }) => void;
  currentThreadId: string | null;
  onThreadIdChange: (id: string | null) => void;
  onExport?: (format: 'stl' | 'step') => void; // NEW: Export callback
}

// HistorySidebar moved to separate component

export function CADChat({
  onModelGenerated,
  onGenerationStart,
  onChatReset,
  onThreadSelected,
  currentThreadId,
  onThreadIdChange,
  onExport, // NEW: Export callback
}: CADChatProps) {
  // State for Gemini API key (stored in localStorage)
  // Initialize to empty string to avoid hydration mismatch (localStorage only available on client)
  const [geminiApiKey, setGeminiApiKey] = useState<string>('');
  // Show modal on mount if API key isn't set (blocking modal)
  const [showApiKeyModal, setShowApiKeyModal] = useState(true);
  const [apiKeyInput, setApiKeyInput] = useState('');

  // Load API key from localStorage after hydration (client-side only)
  useEffect(() => {
    const storedKey = localStorage.getItem('gemini_api_key') || '';
    setGeminiApiKey(storedKey);
    setShowApiKeyModal(!storedKey);
  }, []);
  const [messages, setMessages] = useState<ChatMessage[]>(INITIAL_MESSAGES);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [generationCount, setGenerationCount] = useState(0);
  const [error, setError] = useState<string | null>(null);

  // Chat history stored in local state (session-only, no persistence)
  const [threads, setThreads] = useState<ChatThread[]>([]);
  const [showHistory, setShowHistory] = useState(false);

  // In-memory thread state map: stores messages and model blobs per thread.
  // Uses ref to persist across re-renders without triggering React updates.
  // Blob URLs are recreated on restore since browser revokes them after navigation.
  const threadDataMapRef = useRef<
    Map<
      string,
      {
        messages: ChatMessage[];
        modelState?: {
          stlUrl: string;
          stepUrl: string | null;
          modelScript: string | null;
          zipBlob: Blob;
          constraints: Record<string, number>;
          prompt: string;
        };
      }
    >
  >(new Map());

  const bottomRef = useRef<HTMLDivElement | null>(null);
  const textareaRef = useRef<HTMLTextAreaElement | null>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Separate refs for blob and constraints: blob URLs expire, so we store the original
  // zipBlob to recreate URLs on history restore. Constraints stored separately to
  // avoid serializing Blob objects in the main thread map.
  const zipBlobRef = useRef<Map<string, Blob>>(new Map());
  const constraintsRef = useRef<Map<string, Record<string, number>>>(new Map());

  // Save current thread data to map before switching
  const saveCurrentThreadData = (threadId: string | null) => {
    if (!threadId) return;

    // Find the last generated model from messages
    const reversedMessages = [...messages].reverse();
    const lastModelMessage = reversedMessages.find((m) => m.fileData?.modelScript);

    const zipBlob = zipBlobRef.current.get(threadId);
    const constraints = constraintsRef.current.get(threadId) || {};

    const modelState =
      lastModelMessage?.fileData && zipBlob
        ? {
            stlUrl: lastModelMessage.fileData.stlUrl,
            stepUrl: lastModelMessage.fileData.stepUrl,
            modelScript: lastModelMessage.fileData.modelScript,
            zipBlob: zipBlob,
            constraints: constraints,
            prompt: messages.find((m) => m.role === 'user' && !m.isGenerationCard)?.content || '',
          }
        : undefined;

    threadDataMapRef.current.set(threadId, {
      messages: [...messages],
      modelState,
    });
  };

  const handleNewChat = async () => {
    // Save current thread data before clearing
    if (currentThreadId) {
      saveCurrentThreadData(currentThreadId);
    }

    // 1. Clear Viewer
    onChatReset();

    // 2. Clear Chat State
    onThreadIdChange(null);
    setMessages(INITIAL_MESSAGES);
    setInput('');
    setError(null);
    setIsLoading(false);
  };

  const handleDeleteThread = async (threadId: string) => {
    setThreads((prev) => prev.filter((t) => t.id !== threadId));
    threadDataMapRef.current.delete(threadId); // Remove thread data from map
    zipBlobRef.current.delete(threadId); // Remove zipBlob reference
    constraintsRef.current.delete(threadId); // Remove constraints reference
    if (currentThreadId === threadId) {
      handleNewChat();
    }
  };

  const sendMessage = async () => {
    const contentToSend = input.trim();
    if (!contentToSend || isLoading) return;

    // Create new thread if this is the first message in the conversation
    let activeThreadId = currentThreadId;
    if (!activeThreadId) {
      const title = contentToSend.length > 30 ? contentToSend.slice(0, 30) + '...' : contentToSend;
      activeThreadId = crypto.randomUUID();
      const newThread: ChatThread = {
        id: activeThreadId,
        title,
        createdAt: new Date(),
      };
      setThreads((prev) => [newThread, ...prev]);
      onThreadIdChange(activeThreadId);
    }

    // 1. User Message - add to local state (remove welcome message first)
    const userMessage: ChatMessage = {
      id: crypto.randomUUID(),
      role: 'user',
      content: contentToSend,
    };

    // 2. Generation Card (Working State)
    const cardId = crypto.randomUUID();
    const currentGenNum = generationCount + 1;
    setGenerationCount(currentGenNum);

    const generationCard: ChatMessage = {
      id: cardId,
      role: 'assistant',
      content: JSON.stringify({ genNum: currentGenNum }),
      isGenerationCard: true,
      generationState: 'working',
      genNum: currentGenNum,
    } as ChatMessage & { genNum: number };

    // Remove welcome message and add user message + generation card
    setMessages((prev) =>
      prev.filter((m) => m.id !== 'welcome').concat([userMessage, generationCard]),
    );

    setInput('');
    setIsLoading(true);
    setError(null);
    onGenerationStart?.();

    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }

    try {
      // 3. Parallel Execution
      const startTime = Date.now();

      // Build conversation context from recent messages for iterative design
      const historyContext = messages
        .filter((m) => !m.isGenerationCard)
        .slice(-6)
        .map((m) => `${m.role === 'user' ? 'User' : 'Assistant'}: ${m.content}`)
        .join('\n');

      // Extract previous model script to enable incremental modifications
      const reversedMessages = [...messages].reverse();
      const lastScript =
        reversedMessages.find((m) => m.fileData?.modelScript)?.fileData?.modelScript || undefined;

      // Include previous script in prompt so AI can modify existing geometry
      const scriptInjection = lastScript
        ? `\n\nCURRENT MODEL SCRIPT:\n\`\`\`logic\n${lastScript}\n\`\`\`\n`
        : '';

      // Use iterative prompt template when modifying existing designs, otherwise use direct prompt
      const finalPrompt =
        lastScript || messages.length > 2
          ? `The user wants to modify the previous design. Context of previous conversation:\n${historyContext}\n${scriptInjection}\n\nCurrent Request:\n${contentToSend}\n\nIMPORTANT: Output the complete, valid geometric logic for the entire object, incorporating the new changes. Do not output only the new feature.`
          : contentToSend;

      // Check if API key is set
      if (!geminiApiKey) {
        setShowApiKeyModal(true);
        setIsLoading(false);
        setMessages((prev) => prev.filter((m) => m.id !== cardId));
        return;
      }

      // Request ZIP containing STL, STEP, and geometry script from backend
      const { base64, extractedConstraints } = await generateModelAction(
        finalPrompt,
        'zip',
        lastScript,
        undefined,
        undefined,
        geminiApiKey,
      );

      const elapsed = Date.now() - startTime;
      // Minimum display duration ensures users see the generation process
      const minDuration = 3000;
      if (elapsed < minDuration) {
        await new Promise((resolve) => setTimeout(resolve, minDuration - elapsed));
      }

      if (!base64) throw new Error('No model generated.');

      const zipBlob = base64ToBlob(base64, 'application/zip');

      // Extract all component files
      const { stlUrl, stepUrl, modelScript } = await extractFilesFromZip(zipBlob);

      // If no model found (e.g. valid zip but missing file), throw
      if (!stlUrl) throw new Error('No model found in generated output.');

      onModelGenerated(
        stlUrl,
        stepUrl,
        contentToSend,
        zipBlob,
        extractedConstraints,
        activeThreadId,
      );

      const doneCard = {
        ...generationCard,
        generationState: 'done' as const,
        fileData: { stlUrl, stepUrl, modelScript },
      };

      const doneMessage = {
        id: crypto.randomUUID(),
        role: 'assistant' as const,
        content:
          'Your model is generated. Examine it in the viewer, then export via the top-right export button in the viewer or the files below.',
        isDownloadPrompt: true, // NEW: Flag to show download buttons
      };

      // Store zipBlob and constraints for this thread
      zipBlobRef.current.set(activeThreadId, zipBlob);
      if (extractedConstraints) {
        constraintsRef.current.set(activeThreadId, extractedConstraints);
      }

      // Update generation card to done and add done message ONCE (keep user message)
      setMessages((prev) => {
        const updated = prev.map((msg) => (msg.id === cardId ? doneCard : msg));
        const withDoneMessage = [...updated, doneMessage];

        // Save thread data with model state after generation
        threadDataMapRef.current.set(activeThreadId, {
          messages: withDoneMessage,
          modelState: {
            stlUrl,
            stepUrl,
            modelScript: modelScript || null,
            zipBlob,
            constraints: extractedConstraints || {},
            prompt: contentToSend,
          },
        });

        return withDoneMessage;
      });
    } catch (err: unknown) {
      const errorMessage = err instanceof Error ? err.message : 'Unknown error';
      console.error('Design Generation Error:', err);
      setError('We encountered an issue generating your design. Please try again.');
      setMessages((prev) => prev.filter((m) => m.id !== cardId));
    } finally {
      setIsLoading(false);
    }
  };

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    await sendMessage();
  };

  const handleApiKeySubmit = () => {
    if (apiKeyInput.trim()) {
      setGeminiApiKey(apiKeyInput.trim());
      if (typeof window !== 'undefined') {
        localStorage.setItem('gemini_api_key', apiKeyInput.trim());
      }
      setShowApiKeyModal(false);
      setApiKeyInput('');
    }
  };

  const handleApiKeyChange = () => {
    setShowApiKeyModal(true);
    setApiKeyInput(geminiApiKey);
  };

  const handleTextareaKeyDown = async (event: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      await sendMessage();
    }
  };

  return (
    <div className="flex h-full min-h-0 flex-col relative overflow-hidden">
      {/* Blocking API Key Modal */}
      <Dialog
        open={showApiKeyModal}
        onOpenChange={(open) => {
          // Prevent closing if API key isn't set
          if (!geminiApiKey && !open) return;
          setShowApiKeyModal(open);
        }}
      >
        <DialogContent
          className="sm:max-w-[500px]"
          onInteractOutside={(e) => {
            // Prevent closing by clicking outside if API key isn't set
            if (!geminiApiKey) {
              e.preventDefault();
            }
          }}
          onEscapeKeyDown={(e) => {
            // Prevent closing with Escape if API key isn't set
            if (!geminiApiKey) {
              e.preventDefault();
            }
          }}
        >
          <DialogHeader>
            <DialogTitle>Set Gemini API Key</DialogTitle>
            <DialogDescription>
              Enter your Google Gemini API key to generate CAD models. Your key is stored locally in
              your browser and never sent to a server.
            </DialogDescription>
          </DialogHeader>
          <div className="py-4">
            <input
              type="password"
              value={apiKeyInput}
              onChange={(e) => setApiKeyInput(e.target.value)}
              placeholder="Enter your Gemini API key"
              className="w-full px-3 py-2 rounded-md border border-input bg-background text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
              onKeyDown={(e) => {
                if (e.key === 'Enter' && apiKeyInput.trim()) {
                  handleApiKeySubmit();
                }
              }}
              autoFocus
            />
            <p className="mt-2 text-xs text-muted-foreground">
              Get your API key from{' '}
              <a
                href="https://aistudio.google.com/app/apikey"
                target="_blank"
                rel="noopener noreferrer"
                className="text-primary hover:underline"
              >
                Google AI Studio
              </a>
            </p>
          </div>
          <DialogFooter>
            <button
              onClick={handleApiKeySubmit}
              disabled={!apiKeyInput.trim()}
              className={cn(
                'px-4 py-2 rounded-md text-sm font-medium transition-colors',
                apiKeyInput.trim()
                  ? 'bg-primary text-primary-foreground hover:bg-primary/90'
                  : 'bg-muted text-muted-foreground cursor-not-allowed',
              )}
            >
              Save API Key
            </button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* History Sidebar Overlay */}
      <HistorySidebar
        isOpen={showHistory}
        threads={threads}
        activeThreadId={currentThreadId}
        onThreadSelect={async (id) => {
          // Save current thread data before switching
          if (currentThreadId) {
            saveCurrentThreadData(currentThreadId);
          }

          // Load thread data from map
          const threadData = threadDataMapRef.current.get(id);

          if (threadData) {
            // Restore messages (without welcome message)
            setMessages(threadData.messages.filter((m) => m.id !== 'welcome'));

            // Restore model state if it exists
            if (threadData.modelState) {
              // First clear the viewer
              onChatReset();

              // Recreate blob URLs from stored zipBlob: browser revokes blob URLs
              // after navigation or page reload. Extracting from the original zipBlob
              // ensures the viewer can display the model even after browser state changes.
              const { stlUrl: newStlUrl, stepUrl: newStepUrl } = await extractFilesFromZip(
                threadData.modelState.zipBlob,
              );

              // Then restore the model with fresh blob URLs
              onModelGenerated(
                newStlUrl,
                newStepUrl,
                threadData.modelState.prompt,
                threadData.modelState.zipBlob,
                threadData.modelState.constraints,
                id,
              );

              onThreadSelected({
                prompt: threadData.modelState.prompt,
                threadId: id,
              });
            } else {
              // No model state, just restore messages
              onChatReset();
              onThreadSelected({
                prompt:
                  threadData.messages.find((m) => m.role === 'user' && !m.isGenerationCard)
                    ?.content || '',
                threadId: id,
              });
            }
          } else {
            // Thread exists but no data yet (new thread), just set ID
            setMessages(INITIAL_MESSAGES);
            onChatReset();
            onThreadSelected({
              prompt: '',
              threadId: id,
            });
          }

          onThreadIdChange(id);
          setShowHistory(false);
        }}
        onDeleteThread={handleDeleteThread}
        onClose={() => setShowHistory(false)}
      />

      <div className="flex items-center justify-between border-b bg-background/50 px-3 pt-3.5 pb-4.5">
        <div className="flex-1" />
        <div className="flex items-center gap-1">
          <button
            onClick={() => setShowHistory(!showHistory)}
            className={cn(
              'h-8 w-8 inline-flex items-center justify-center rounded-md transition-colors',
              showHistory
                ? 'bg-accent text-accent-foreground'
                : 'text-muted-foreground hover:bg-accent hover:text-accent-foreground',
            )}
            title="History"
          >
            <Clock size={16} />
          </button>
          <button
            onClick={handleNewChat}
            className="h-8 w-8 inline-flex items-center justify-center rounded-md text-muted-foreground hover:bg-accent hover:text-accent-foreground transition-colors"
            title="New Chat"
          >
            <SquarePen size={16} />
          </button>
          <button
            onClick={handleApiKeyChange}
            className="h-8 w-8 inline-flex items-center justify-center rounded-md text-muted-foreground hover:bg-accent hover:text-accent-foreground transition-colors"
            title={geminiApiKey ? 'Change API Key' : 'Set API Key'}
          >
            <Key size={16} />
          </button>
        </div>
      </div>
      <div className="flex-1 min-h-0 overflow-y-auto px-4 pb-4 pt-6">
        <div className="mx-auto flex w-full max-w-3xl flex-col gap-6">
          {messages.map((msg) => {
            if (msg.isGenerationCard) {
              return (
                <div key={msg.id} className="flex w-full justify-start">
                  <div className="w-full max-w-[85%]">
                    <GenerationCard
                      state={msg.generationState || 'working'}
                      generationNum={msg.genNum || 1}
                    />
                  </div>
                </div>
              );
            }

            const isUser = msg.role === 'user';
            const content = msg.content; // Define content here
            return (
              <div
                key={msg.id}
                className={`flex w-full gap-3 ${isUser ? 'justify-end' : 'justify-start'}`}
              >
                <div
                  className={`relative rounded-2xl px-5 py-3.5 shadow-sm text-sm leading-relaxed whitespace-pre-wrap ${
                    isUser
                      ? 'bg-primary text-primary-foreground rounded-tr-none pr-10'
                      : 'bg-muted/50 border border-border/50 text-foreground rounded-tl-none'
                  }`}
                >
                  {formatMessage(content)}

                  {isUser && <CopyButton content={content} />}

                  {/* Download Buttons for completion message */}
                  {!isUser && msg.isDownloadPrompt && onExport && (
                    <div className="mt-3 pt-3 border-t border-border/40 flex flex-col gap-2">
                      {/* STEP File Attachment Card */}
                      <button
                        onClick={() => onExport('step')}
                        className="flex items-center justify-between w-full p-2.5 rounded-md border border-border/50 bg-background/40 hover:bg-background hover:border-border transition-all group text-left shadow-sm"
                      >
                        <div className="flex items-center gap-3">
                          <div className="flex items-center justify-center w-8 h-8 rounded bg-blue-500/10 text-blue-600 border border-blue-500/20">
                            <Box size={14} />
                          </div>
                          <div className="flex flex-col gap-0.5">
                            <span className="text-xs font-semibold text-foreground">
                              Model Geometry
                            </span>
                            <span className="text-[9px] text-muted-foreground font-mono uppercase tracking-wider">
                              .STEP &bull; CAD Format
                            </span>
                          </div>
                        </div>
                        <div className="p-1.5 rounded-full text-muted-foreground/70 group-hover:text-foreground group-hover:bg-muted transition-colors">
                          <Download size={14} />
                        </div>
                      </button>

                      {/* STL File Attachment Card */}
                      <button
                        onClick={() => onExport('stl')}
                        className="flex items-center justify-between w-full p-2.5 rounded-md border border-border/50 bg-background/40 hover:bg-background hover:border-border transition-all group text-left shadow-sm"
                      >
                        <div className="flex items-center gap-3">
                          <div className="flex items-center justify-center w-8 h-8 rounded bg-orange-500/10 text-orange-600 border border-orange-500/20">
                            <Box size={14} />
                          </div>
                          <div className="flex flex-col gap-0.5">
                            <span className="text-xs font-semibold text-foreground">
                              3D Print Mesh
                            </span>
                            <span className="text-[9px] text-muted-foreground font-mono uppercase tracking-wider">
                              .STL &bull; Triangles
                            </span>
                          </div>
                        </div>
                        <div className="p-1.5 rounded-full text-muted-foreground/70 group-hover:text-foreground group-hover:bg-muted transition-colors">
                          <Download size={14} />
                        </div>
                      </button>
                    </div>
                  )}
                </div>
              </div>
            );
          })}

          {error && (
            <div className="rounded-md bg-destructive/10 p-3 text-center text-sm text-destructive">
              {error}
            </div>
          )}

          <div ref={bottomRef} />
        </div>
      </div>

      <div className="w-full border-t bg-background px-4 pb-6 pt-4">
        <div className="mx-auto w-full max-w-3xl">
          {/* Starter Prompts - Only show if we just have the welcome message */}
          {messages.length === 1 && messages[0].id === 'welcome' && (
            <div className="mb-4 space-y-3 animate-in fade-in slide-in-from-bottom-4 duration-500">
              <div className="flex items-center gap-2 text-xs font-medium text-muted-foreground ml-1">
                <TrendingUp className="h-3.5 w-3.5" />
                <span>Don&apos;t know what to generate? Try these options:</span>
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                <button
                  onClick={() =>
                    setInput(
                      'NEMA 17 L-Bracket: 45mm base, 50mm height, 3mm thick, standard 31mm bolt pattern, 22mm pilot hole clearance.',
                    )
                  }
                  disabled={!geminiApiKey}
                  className="flex flex-col items-start gap-2 p-3 rounded-xl bg-muted/40 hover:bg-muted border border-border/40 hover:border-primary/20 transition-all text-left group disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <div className="flex items-center gap-2 w-full">
                    <div className="p-1.5 rounded-md bg-background shadow-sm group-hover:shadow-md transition-shadow">
                      <Settings2 size={14} className="text-primary" />
                    </div>
                    <span className="text-xs font-semibold">NEMA 17 Mount</span>
                  </div>
                  <div className="text-[10px] text-muted-foreground line-clamp-1">
                    Stepper bracket (45mm)
                  </div>
                </button>

                <button
                  onClick={() =>
                    setInput(
                      'Heat Sink: 60x60mm base, 5mm thick, 20x vertical fins (25mm height, 1.5mm thickness), Aluminum-ready geometry.',
                    )
                  }
                  disabled={!geminiApiKey}
                  className="flex flex-col items-start gap-2 p-3 rounded-xl bg-muted/40 hover:bg-muted border border-border/40 hover:border-primary/20 transition-all text-left group disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <div className="flex items-center gap-2 w-full">
                    <div className="p-1.5 rounded-md bg-background shadow-sm group-hover:shadow-md transition-shadow">
                      <TrendingUp size={14} className="text-blue-500" />
                    </div>
                    <span className="text-xs font-semibold">Heat Sink</span>
                  </div>
                  <div className="text-[10px] text-muted-foreground line-clamp-1">
                    60x60mm Aluminum
                  </div>
                </button>

                <button
                  onClick={() =>
                    setInput(
                      'PCB Enclosure: 85x55x30mm external, 2.0mm wall thickness, 4x M2.5 screw bosses for 75x45mm PCB, USB-C side-cutout.',
                    )
                  }
                  disabled={!geminiApiKey}
                  className="flex flex-col items-start gap-2 p-3 rounded-xl bg-muted/40 hover:bg-muted border border-border/40 hover:border-primary/20 transition-all text-left group disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <div className="flex items-center gap-2 w-full">
                    <div className="p-1.5 rounded-md bg-background shadow-sm group-hover:shadow-md transition-shadow">
                      <Box size={14} className="text-emerald-500" />
                    </div>
                    <span className="text-xs font-semibold">PCB Enclosure</span>
                  </div>
                  <div className="text-[10px] text-muted-foreground line-clamp-1">85x55mm Box</div>
                </button>
              </div>
            </div>
          )}

          <form
            onSubmit={handleSubmit}
            className="relative flex items-end gap-3 rounded-[32px] border border-input bg-muted/40 p-2 pr-2 pl-4 focus-within:ring-1 focus-within:ring-ring"
          >
            <textarea
              ref={textareaRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleTextareaKeyDown}
              placeholder={
                geminiApiKey
                  ? 'Describe the object (dimensions, constraints, purpose).'
                  : 'Set API key to continue...'
              }
              disabled={!geminiApiKey}
              className="min-h-[48px] py-3.5 flex-1 resize-none border-0 bg-transparent p-0 text-sm shadow-none focus-visible:ring-0 placeholder:text-muted-foreground focus-visible:outline-none disabled:cursor-not-allowed disabled:opacity-50"
            />

            <button
              type="submit"
              className={cn(
                'mb-1 h-9 w-9 inline-flex shrink-0 items-center justify-center rounded-full transition-all duration-200',
                input.trim() && !isLoading && geminiApiKey
                  ? 'bg-primary text-primary-foreground hover:bg-primary/90 shadow-sm'
                  : 'bg-muted text-muted-foreground cursor-not-allowed opacity-50',
              )}
              disabled={!input.trim() || isLoading || !geminiApiKey}
            >
              <ArrowUp size={18} strokeWidth={2.5} />
            </button>
          </form>
          <p className="mt-2 text-center text-xs text-muted-foreground">
            One request = one generation. Be specific.
          </p>
        </div>
      </div>
    </div>
  );
}

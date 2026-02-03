'use client';

import { useState, useMemo } from 'react';
import {
  AlertDialog,
  AlertDialogContent,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogCancel,
  AlertDialogAction,
} from '@/components/ui/alert-dialog';

import { ScrollArea } from '@/components/ui/scroll-area';
import { Trash2, Search } from 'lucide-react';
// Chat thread type for local state management
type ChatThread = {
  id: string;
  title: string;
  createdAt: Date;
  lastMessage?: string;
};
import { cn } from '@/lib/utils';

interface HistorySidebarProps {
  threads: ChatThread[];
  activeThreadId: string | null;
  onThreadSelect: (threadId: string) => void;
  onDeleteThread: (threadId: string) => void;
  isOpen: boolean;
  onClose: () => void;
}

export function HistorySidebar({
  threads,
  activeThreadId,
  onThreadSelect,
  onDeleteThread,
  isOpen,
  onClose,
}: HistorySidebarProps) {
  const [searchQuery, setSearchQuery] = useState('');
  const [threadToDelete, setThreadToDelete] = useState<string | null>(null);

  const filteredThreads = useMemo(() => {
    if (!searchQuery.trim()) return threads;
    const query = searchQuery.toLowerCase();
    return threads.filter(
      (t) =>
        (t.title || 'Untitled Generation').toLowerCase().includes(query) ||
        t.lastMessage?.toLowerCase().includes(query),
    );
  }, [threads, searchQuery]);

  // Group threads by date
  const groupedThreads = useMemo(() => {
    const groups: Record<string, ChatThread[]> = {
      Today: [],
      Yesterday: [],
      'Past Week': [],
      Older: [],
    };

    const now = new Date();
    const yesterday = new Date(now);
    yesterday.setDate(yesterday.getDate() - 1);
    const lastWeek = new Date(now);
    lastWeek.setDate(lastWeek.getDate() - 7);

    filteredThreads.forEach((thread) => {
      const date = thread.createdAt;

      if (date.toDateString() === now.toDateString()) {
        groups['Today'].push(thread);
      } else if (date.toDateString() === yesterday.toDateString()) {
        groups['Yesterday'].push(thread);
      } else if (date > lastWeek) {
        groups['Past Week'].push(thread);
      } else {
        groups['Older'].push(thread);
      }
    });

    return Object.entries(groups).filter(([, items]) => items.length > 0);
  }, [filteredThreads]);

  return (
    <>
      {/* Backdrop for outside click */}
      {isOpen && (
        <div className="fixed inset-0 z-40 bg-background/5 backdrop-blur-[2px]" onClick={onClose} />
      )}

      <aside
        className={cn(
          'fixed left-0 top-0 bottom-0 w-80 border-r border-border bg-background z-50 flex flex-col transition-transform duration-300 ease-in-out shadow-2xl',
          isOpen ? 'translate-x-0' : '-translate-x-full',
        )}
      >
        <div className="p-6 border-b border-border/50">
          <div className="relative group">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground/40 h-3.5 w-3.5 group-focus-within:text-foreground transition-colors" />
            <input
              type="text"
              placeholder="Search history..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full bg-muted/30 border-none rounded-xl py-2.5 pl-9 pr-4 text-xs focus:outline-none focus:ring-1 focus:ring-border transition-all placeholder:text-muted-foreground/30 font-medium"
            />
          </div>
        </div>

        <ScrollArea className="flex-1 px-2 py-6">
          <div className="space-y-10">
            {groupedThreads.map(([group, items]) => (
              <div key={group} className="space-y-2">
                <h3 className="px-4 text-[11px] font-bold uppercase tracking-[0.25em] text-foreground/80 mb-4">
                  {group}
                </h3>
                {items.map((thread) => (
                  <div
                    key={thread.id}
                    className={cn(
                      'group relative flex items-center justify-between gap-2 px-3.5 py-3.5 rounded-2xl transition-all cursor-pointer border border-transparent',
                      activeThreadId === thread.id
                        ? 'bg-muted/80 border-border/50 shadow-sm'
                        : 'hover:bg-muted/40',
                    )}
                    onClick={() => {
                      onThreadSelect(thread.id);
                      onClose();
                    }}
                  >
                    <div className="flex-1 min-w-0">
                      <span
                        className={cn(
                          'text-xs font-bold truncate block',
                          activeThreadId === thread.id
                            ? 'text-foreground'
                            : 'text-foreground/70 group-hover:text-foreground',
                        )}
                      >
                        {thread.title || 'Untitled Part'}
                      </span>
                    </div>

                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        setThreadToDelete(thread.id);
                      }}
                      className="p-2 text-muted-foreground/30 hover:bg-destructive/10 hover:text-destructive rounded-xl transition-all duration-200 shrink-0"
                      title="Delete thread"
                    >
                      <Trash2 size={16} />
                    </button>
                  </div>
                ))}
              </div>
            ))}
          </div>
        </ScrollArea>

        <AlertDialog open={!!threadToDelete} onOpenChange={() => setThreadToDelete(null)}>
          <AlertDialogContent className="bg-background border-border">
            <AlertDialogHeader>
              <AlertDialogTitle>Delete Chat Thread?</AlertDialogTitle>
              <AlertDialogDescription>
                This will permanently remove this generation history and all associated messages.
                This action cannot be undone.
              </AlertDialogDescription>
            </AlertDialogHeader>
            <AlertDialogFooter>
              <AlertDialogCancel className="bg-muted">Cancel</AlertDialogCancel>
              <AlertDialogAction
                onClick={() => {
                  if (threadToDelete) {
                    onDeleteThread(threadToDelete);
                    setThreadToDelete(null);
                  }
                }}
                className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
              >
                Delete Thread
              </AlertDialogAction>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialog>
      </aside>
    </>
  );
}

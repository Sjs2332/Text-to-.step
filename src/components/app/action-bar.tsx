'use client';

import { Box, Loader2, CheckCircle2, Grid3X3, Cuboid, ArrowUpFromLine, Ruler } from 'lucide-react';
import { ViewPreset } from './model-viewer';
export type { ViewPreset };

export interface ActionBarProps {
  onViewPresetChange: (preset: ViewPreset) => void;
  isRendering?: boolean;
  previewStatus?: string;
  isSidebarOpen?: boolean;
  isMeasureMode?: boolean;
  onToggleMeasure?: () => void;
}

export function ActionBar({
  onViewPresetChange,
  isRendering = false,
  previewStatus = '',
  isSidebarOpen = false,
  isMeasureMode = false,
  onToggleMeasure,
}: ActionBarProps) {
  return (
    <div
      className={`absolute top-0 left-0 right-0 z-40 h-[60px] flex items-center justify-between p-2 pr-4 transition-all duration-300 bg-background border-b border-border ${
        isSidebarOpen ? 'md:pl-[216px]' : 'pl-2'
      }`}
    >
      {/* Left Status Area */}
      <div className="flex items-center gap-4 shrink-0">
        <div className="flex items-center text-xs font-medium min-w-[140px]">
          {isRendering ? (
            <div className="flex items-center gap-2 text-blue-500 px-3 py-1 bg-blue-500/10 rounded-full animate-pulse">
              <Loader2 size={12} className="animate-spin" />
              <span>Updating...</span>
            </div>
          ) : previewStatus ? (
            <div className="flex items-center gap-2 text-emerald-600 px-3 py-1 bg-emerald-500/10 rounded-full">
              <CheckCircle2 size={12} />
              <span>{previewStatus}</span>
            </div>
          ) : (
            <span className="text-muted-foreground/50 px-3 py-1">Ready</span>
          )}
        </div>
      </div>

      {/* Right: View Controls */}
      <div className="flex items-center gap-3 shrink-0">
        <button
          onClick={onToggleMeasure}
          className={`h-7 px-3 gap-2 inline-flex items-center justify-center rounded-md text-xs font-medium transition-colors border ${
            isMeasureMode
              ? 'bg-emerald-500/10 text-emerald-600 border-emerald-500/20 hover:bg-emerald-500/20'
              : 'bg-background text-muted-foreground border-border/50 hover:bg-accent hover:text-accent-foreground'
          }`}
        >
          <Ruler size={14} />
          <span>{isMeasureMode ? 'Measuring...' : 'Measure'}</span>
        </button>

        <div className="flex items-center gap-1 bg-muted/50 p-0.5 rounded-lg">
          <button
            type="button"
            className="h-7 w-7 inline-flex items-center justify-center rounded-md text-muted-foreground hover:bg-accent hover:text-accent-foreground transition-colors"
            onClick={() => onViewPresetChange('iso')}
            title="Isometric"
          >
            <Box size={14} />
          </button>
          <button
            type="button"
            className="h-7 w-7 inline-flex items-center justify-center rounded-md text-muted-foreground hover:bg-accent hover:text-accent-foreground transition-colors"
            onClick={() => onViewPresetChange('top')}
            title="Top"
          >
            <Grid3X3 size={14} />
          </button>
          <button
            type="button"
            className="h-7 w-7 inline-flex items-center justify-center rounded-md text-muted-foreground hover:bg-accent hover:text-accent-foreground transition-colors"
            onClick={() => onViewPresetChange('front')}
            title="Front"
          >
            <Cuboid size={14} />
          </button>
          <button
            type="button"
            className="h-7 w-7 inline-flex items-center justify-center rounded-md text-muted-foreground hover:bg-accent hover:text-accent-foreground transition-colors"
            onClick={() => onViewPresetChange('right')}
            title="Right"
          >
            <ArrowUpFromLine size={14} className="rotate-90" />
          </button>
        </div>
      </div>
    </div>
  );
}

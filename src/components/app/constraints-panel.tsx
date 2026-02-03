'use client';

import { useState, useEffect } from 'react';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { cn } from '@/lib/utils';

interface ConstraintsPanelProps {
  constraints: Record<string, number>;
}

// Displays extracted parametric dimensions from generated models
// Currently read-only; users modify values via chat prompts
export function ConstraintsPanel({ constraints }: ConstraintsPanelProps) {
  // Determine the actual constraints object (handle nested vs flat)
  const getEffectiveConstraints = (data: Record<string, unknown>): Record<string, number> => {
    if (!data) return {};

    const filtered: Record<string, number> = {};

    // Helper to extract numbers from an object
    const extractNumbers = (source: Record<string, unknown>, prefix?: string) => {
      for (const [key, val] of Object.entries(source)) {
        if (typeof val === 'number') {
          const displayKey = prefix ? `${prefix}: ${key}` : key;
          filtered[displayKey] = val;
        }
      }
    };

    // Extract from 'constraints' sub-object
    if (
      data.constraints &&
      typeof data.constraints === 'object' &&
      !Array.isArray(data.constraints)
    ) {
      extractNumbers(data.constraints as Record<string, unknown>);
    }

    // Extract from 'dimensions' sub-object
    if (data.dimensions && typeof data.dimensions === 'object' && !Array.isArray(data.dimensions)) {
      extractNumbers(data.dimensions as Record<string, unknown>);
    }

    // Fallback: extract top-level numbers if no nested objects found
    if (Object.keys(filtered).length === 0) {
      extractNumbers(data);
    }

    return filtered;
  };

  const effectiveConstraints = getEffectiveConstraints(constraints);

  const [localConstraints, setLocalConstraints] =
    useState<Record<string, number>>(effectiveConstraints);
  const [unit, setUnit] = useState<'mm' | 'in'>('mm');

  // Helper to format display value
  const toDisplay = (valMm: number): string => {
    if (unit === 'mm') return valMm.toString();
    // Convert to inches, max 4 decimal places to avoid floating point mess
    return (valMm / 25.4).toFixed(4).replace(/\.?0+$/, '');
  };

  // Sync local state when prop updates (e.g. new generation)
  useEffect(() => {
    const nextConstraints = getEffectiveConstraints(constraints);
    if (JSON.stringify(nextConstraints) !== JSON.stringify(localConstraints)) {
      const timer = setTimeout(() => {
        setLocalConstraints(nextConstraints);
      }, 0);
      return () => clearTimeout(timer);
    }
  }, [constraints, localConstraints]);

  const isEmpty = !effectiveConstraints || Object.keys(effectiveConstraints).length === 0;

  // Check if the API returned an error for spec extraction
  const hasError = constraints && 'error' in constraints;

  const displayConstraints = localConstraints;

  // Show message if there's an error from the API
  if (hasError) {
    return (
      <div className="flex flex-col h-full w-full bg-muted/5 border-r border-border">
        <div className="flex items-center justify-between p-4 border-b border-white/10 shrink-0 h-[60px]">
          <span className="text-xs font-bold uppercase tracking-[0.2em] text-muted-foreground">
            Specs
          </span>
        </div>
        <div className="flex-1 flex items-center justify-center p-4">
          <p className="text-xs text-muted-foreground/60 text-center">
            Spec extraction unavailable for this model
          </p>
        </div>
      </div>
    );
  }

  if (isEmpty) return null;

  return (
    <div className="flex flex-col h-full w-full bg-muted/5 border-r border-border">
      {/* Header / Metric Toggle */}
      <div className="flex items-center justify-between p-4 border-b border-white/10 shrink-0 h-[60px]">
        <div className="flex items-center gap-2">
          <span className="text-xs font-bold uppercase tracking-[0.2em] text-muted-foreground">
            Specs
          </span>
        </div>
        <div className="flex bg-muted/40 p-0.5 rounded-lg border border-white/5">
          <button
            onClick={() => setUnit('mm')}
            className={cn(
              'px-2 py-0.5 text-[9px] font-mono transition-all rounded-md uppercase min-w-[32px]',
              unit === 'mm'
                ? 'bg-background text-foreground font-bold shadow-sm'
                : 'text-muted-foreground/50 hover:text-muted-foreground',
            )}
          >
            MM
          </button>
          <button
            onClick={() => setUnit('in')}
            className={cn(
              'px-2 py-0.5 text-[9px] font-mono transition-all rounded-md uppercase min-w-[32px]',
              unit === 'in'
                ? 'bg-background text-foreground font-bold shadow-sm'
                : 'text-muted-foreground/50 hover:text-muted-foreground',
            )}
          >
            IN
          </button>
        </div>
      </div>

      {/* Tech-styled Inputs (Vertical Scroll) */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4 min-h-0 mask-linear-fade-bottom">
        {Object.entries(displayConstraints).map(([key, value]) => (
          <div key={key} className="flex flex-col gap-1 group relative">
            {/* Label */}
            <Label
              htmlFor={key}
              className="text-[9px] font-medium uppercase text-muted-foreground/80 tracking-tight truncate cursor-help transition-colors group-hover:text-emerald-500/90"
              title={key}
            >
              {key.replace(/_/g, ' ')}
            </Label>

            {/* Value Display */}
            <div className="relative flex items-center border-b border-white/10 group-hover:border-white/30 transition-colors pb-1">
              <Input
                id={key}
                type="number"
                step={unit === 'mm' ? '0.1' : '0.001'}
                value={toDisplay(value)}
                readOnly={true}
                tabIndex={-1}
                className={cn(
                  'h-auto p-0 border-none rounded-none bg-transparent shadow-none focus-visible:ring-0',
                  'text-sm font-mono tracking-tight w-full',
                  '[appearance:textfield] [&::-webkit-outer-spin-button]:appearance-none [&::-webkit-inner-spin-button]:appearance-none cursor-default',
                  isEmpty ? 'text-muted-foreground/20 italic' : 'text-foreground font-semibold',
                )}
              />
              <span className="text-[10px] text-muted-foreground font-mono ml-2">{unit}</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

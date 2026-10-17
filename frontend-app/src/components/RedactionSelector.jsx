import React from 'react';
import {
  ShieldAlert,
  CheckCircle2,
  EyeOff,
  Eye,
  Sliders,
  RotateCcw,
  Sparkles,
  Info,
  Check,
} from 'lucide-react';

const POLICY_FLOOR_CATEGORIES = new Set(['government_id', 'account_identifier']);

export default function RedactionSelector({
  plan = {},
  detectedFields = [],
  onToggleCategory,
  onSetAll,
  onResetPlan,
}) {
  // Aggregate occurrences count per category
  const categoryCounts = React.useMemo(() => {
    const counts = {};
    for (const f of detectedFields) {
      if (f.category) {
        counts[f.category] = (counts[f.category] || 0) + 1;
      }
    }
    return counts;
  }, [detectedFields]);

  // Categories present in the plan or detected fields
  const categories = Object.keys(plan);

  if (categories.length === 0) return null;

  return (
    <div className="p-4 sm:p-5 rounded-2xl bg-white dark:bg-[#090e17] border border-slate-200 dark:border-slate-800 shadow-sm space-y-4 animate-fade-in-up">
      {/* Header & Quick Controls */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-slate-100 dark:border-slate-800">
        <div className="space-y-0.5">
          <div className="flex items-center gap-2">
            <Sliders className="w-4 h-4 text-blue-600 dark:text-blue-400" />
            <h3 className="text-sm font-bold text-slate-900 dark:text-white">
              Select or Deselect Redacted Information
            </h3>
          </div>
          <p className="text-xs text-slate-500 dark:text-slate-400">
            Customize which fields are blocked from AI upload vs. kept for prompt answering. Changes update the Diff instantly.
          </p>
        </div>

        {/* Quick Batch Buttons */}
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => onSetAll('DROP')}
            className="text-xs font-semibold px-2.5 py-1.5 rounded-lg border border-rose-200 dark:border-rose-900/60 bg-rose-50 dark:bg-rose-950/30 text-rose-700 dark:text-rose-300 hover:bg-rose-100 transition-all active:scale-95 flex items-center gap-1 cursor-pointer"
            title="Redact all detected sensitive categories"
          >
            <EyeOff className="w-3.5 h-3.5" />
            <span>Redact All</span>
          </button>
          <button
            type="button"
            onClick={() => onSetAll('KEEP')}
            className="text-xs font-semibold px-2.5 py-1.5 rounded-lg border border-emerald-200 dark:border-emerald-900/60 bg-emerald-50 dark:bg-emerald-950/30 text-emerald-700 dark:text-emerald-300 hover:bg-emerald-100 transition-all active:scale-95 flex items-center gap-1 cursor-pointer"
            title="Keep all detected categories for AI"
          >
            <Eye className="w-3.5 h-3.5" />
            <span>Keep All</span>
          </button>
          {onResetPlan && (
            <button
              type="button"
              onClick={onResetPlan}
              className="text-xs font-semibold px-2.5 py-1.5 rounded-lg border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-[#0d1522] text-slate-700 dark:text-slate-300 hover:bg-slate-100 transition-all active:scale-95 flex items-center gap-1 cursor-pointer"
              title="Reset to Gemini planner's original task recommendation"
            >
              <RotateCcw className="w-3.5 h-3.5" />
              <span className="hidden sm:inline">Reset</span>
            </button>
          )}
        </div>
      </div>

      {/* Grid of Interactive Redaction Checkboxes */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-2.5">
        {categories.map((cat) => {
          const decision = plan[cat] || { action: 'DROP', reason: '' };
          const action = decision.action || 'DROP';
          const isRedacted = action !== 'KEEP';
          const isPolicyFloor = POLICY_FLOOR_CATEGORIES.has(cat);
          const count = categoryCounts[cat] || 0;

          return (
            <div
              key={cat}
              onClick={() => onToggleCategory(cat, isRedacted ? 'KEEP' : 'DROP')}
              className={`p-3 rounded-xl border transition-all duration-150 cursor-pointer select-none flex items-start justify-between gap-3 ${
                isRedacted
                  ? 'border-rose-200 dark:border-rose-900/50 bg-rose-50/40 dark:bg-rose-950/20 hover:border-rose-300'
                  : 'border-emerald-200 dark:border-emerald-900/50 bg-emerald-50/40 dark:bg-emerald-950/20 hover:border-emerald-300'
              }`}
            >
              <div className="flex items-start gap-2.5 min-w-0">
                {/* Styled Checkbox */}
                <div
                  className={`w-4 h-4 rounded mt-0.5 flex items-center justify-center transition-all ${
                    isRedacted
                      ? 'bg-rose-600 text-white shadow-xs'
                      : 'bg-emerald-600 text-white shadow-xs'
                  }`}
                >
                  <Check className="w-3 h-3 stroke-[3]" />
                </div>

                <div className="space-y-0.5 min-w-0">
                  <div className="flex items-center gap-1.5 flex-wrap">
                    <span className="font-mono font-bold text-xs text-slate-900 dark:text-white truncate">
                      {cat}
                    </span>
                    {count > 0 && (
                      <span className="text-[10px] font-mono px-1.5 py-0.2 rounded-full bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400 font-semibold">
                        {count}×
                      </span>
                    )}
                  </div>

                  <p className="text-[11px] text-slate-500 dark:text-slate-400 line-clamp-1">
                    {decision.reason || (isRedacted ? 'Blocked from upload' : 'Retained for answer')}
                  </p>

                  {isPolicyFloor && (
                    <span className="inline-flex items-center gap-1 text-[9px] font-bold text-amber-700 dark:text-amber-400 bg-amber-50 dark:bg-amber-950/40 px-1.5 py-0.2 rounded border border-amber-200 dark:border-amber-800">
                      <ShieldAlert className="w-2.5 h-2.5" /> Policy Floor
                    </span>
                  )}
                </div>
              </div>

              {/* Status Action Pill */}
              <div className="shrink-0 text-right">
                <span
                  className={`text-[10px] font-bold px-2 py-0.5 rounded-full border ${
                    isRedacted
                      ? 'bg-rose-100 dark:bg-rose-900/40 text-rose-800 dark:text-rose-300 border-rose-300 dark:border-rose-800'
                      : 'bg-emerald-100 dark:bg-emerald-900/40 text-emerald-800 dark:text-emerald-300 border-emerald-300 dark:border-emerald-800'
                  }`}
                >
                  {isRedacted ? 'REDACTED' : 'KEPT'}
                </span>
                <span className="block text-[9px] text-slate-400 mt-1">
                  Click to {isRedacted ? 'Keep' : 'Redact'}
                </span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

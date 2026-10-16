import React, { useState } from 'react';
import { AlertTriangle, CheckCircle2, HelpCircle, ChevronRight } from 'lucide-react';

const ACTION_COLORS = {
  KEEP: 'bg-emerald-100 text-emerald-800 border-emerald-300',
  DROP: 'bg-slate-100 text-slate-700 border-slate-300',
};

export default function UnsureReview({ unsureCategories, plan, onOverride }) {
  const [overrides, setOverrides] = useState({});

  if (!unsureCategories || unsureCategories.length === 0) return null;

  const handleOverride = (cat, action) => {
    const newOverrides = { ...overrides, [cat]: action };
    setOverrides(newOverrides);
    if (onOverride) onOverride(newOverrides);
  };

  return (
    <div className="p-4 rounded-xl bg-amber-50 border border-amber-300 space-y-3 animate-fade-in-up">
      {/* Header */}
      <div className="flex items-center gap-2">
        <HelpCircle className="w-4 h-4 text-amber-600 shrink-0" />
        <div>
          <h4 className="text-xs font-bold text-amber-900">
            {unsureCategories.length} Ambiguous {unsureCategories.length === 1 ? 'Category' : 'Categories'} — Your Review Needed
          </h4>
          <p className="text-[10px] text-amber-700 font-medium mt-0.5">
            The AI planner was not confident about these fields. Override the decision or accept the default.
          </p>
        </div>
      </div>

      {/* Cards */}
      <div className="space-y-2">
        {unsureCategories.map((cat) => {
          const decision = plan?.[cat];
          const override = overrides[cat];
          const currentAction = override || decision?.action || 'DROP';
          const isOverridden = !!override;

          return (
            <div
              key={cat}
              className={`flex items-center justify-between gap-3 p-3 rounded-lg border bg-white transition-all duration-200 ${
                isOverridden ? 'border-blue-300 shadow-sm shadow-blue-100' : 'border-amber-200'
              }`}
            >
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <span className="text-xs font-bold text-slate-800 font-mono">{cat}</span>
                  {isOverridden && (
                    <span className="text-[10px] font-semibold text-blue-600 bg-blue-50 border border-blue-200 rounded-full px-2 py-0.5">
                      Overridden
                    </span>
                  )}
                </div>
                {decision?.reason && (
                  <p className="text-[11px] text-slate-500 mt-0.5 line-clamp-1">
                    {decision.reason}
                  </p>
                )}
              </div>

              {/* Current action chip */}
              <span
                className={`text-[10px] font-bold px-2 py-0.5 rounded-full border shrink-0 ${
                  ACTION_COLORS[currentAction] || 'bg-slate-100 text-slate-700 border-slate-300'
                }`}
              >
                {currentAction}
              </span>

              {/* Override buttons */}
              <div className="flex gap-1 shrink-0">
                <button
                  id={`override-keep-${cat}`}
                  onClick={() => handleOverride(cat, 'KEEP')}
                  className={`flex items-center gap-1 px-2.5 py-1 rounded-lg text-[10px] font-bold border transition-all duration-150 active:scale-95 ${
                    currentAction === 'KEEP'
                      ? 'bg-emerald-600 text-white border-emerald-600'
                      : 'bg-white text-emerald-700 border-emerald-300 hover:bg-emerald-50'
                  }`}
                >
                  <CheckCircle2 className="w-3 h-3" /> Keep
                </button>
                <button
                  id={`override-drop-${cat}`}
                  onClick={() => handleOverride(cat, 'DROP')}
                  className={`flex items-center gap-1 px-2.5 py-1 rounded-lg text-[10px] font-bold border transition-all duration-150 active:scale-95 ${
                    currentAction === 'DROP'
                      ? 'bg-slate-600 text-white border-slate-600'
                      : 'bg-white text-slate-600 border-slate-300 hover:bg-slate-50'
                  }`}
                >
                  <ChevronRight className="w-3 h-3" /> Drop
                </button>
              </div>
            </div>
          );
        })}
      </div>

      {Object.keys(overrides).length > 0 && (
        <p className="text-[10px] text-amber-700 font-medium flex items-center gap-1">
          <AlertTriangle className="w-3 h-3" />
          {Object.keys(overrides).length} override(s) recorded. These will be reflected in the Decisions Table display only — re-run to apply changes to the minimized output.
        </p>
      )}
    </div>
  );
}

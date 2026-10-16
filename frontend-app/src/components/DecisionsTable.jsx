import React, { useState } from 'react';
import { Filter, Check, X, ShieldAlert } from 'lucide-react';

const ACTION_STYLES = {
  DROP: 'bg-rose-50 text-rose-700 border-rose-200 font-bold',
  KEEP: 'bg-emerald-50 text-emerald-700 border-emerald-200 font-bold',
  MASK_PARTIAL: 'bg-amber-50 text-amber-800 border-amber-200 font-bold',
  GENERALIZE: 'bg-blue-50 text-blue-700 border-blue-200 font-bold',
  PSEUDONYMIZE: 'bg-indigo-50 text-indigo-700 border-indigo-200 font-bold',
  AGGREGATE: 'bg-teal-50 text-teal-700 border-teal-200 font-bold',
};

export default function DecisionsTable({ plan = {}, policyViolations = [] }) {
  const [filter, setFilter] = useState('ALL');

  const categories = Object.keys(plan);
  const violationCategories = new Set(policyViolations.map((v) => v.category));

  const filteredCategories = categories.filter((cat) => {
    if (filter === 'ALL') return true;
    return plan[cat]?.action === filter;
  });

  return (
    <div className="space-y-3 animate-fade-in-up">
      {/* Filters */}
      <div className="flex flex-wrap items-center justify-between gap-2 pb-2">
        <div className="flex items-center gap-1.5 text-xs text-slate-500 font-medium">
          <Filter className="w-3.5 h-3.5" />
          <span>Filter Action:</span>
        </div>
        <div className="flex flex-wrap gap-1">
          {['ALL', 'DROP', 'KEEP', 'MASK_PARTIAL'].map((act) => (
            <button
              key={act}
              type="button"
              onClick={() => setFilter(act)}
              className={`px-2.5 py-1 rounded-md text-xs font-semibold transition-all duration-150 active:scale-95 ${
                filter === act
                  ? 'bg-blue-50 text-blue-700 border border-blue-200 shadow-xs'
                  : 'bg-white hover:bg-slate-100 text-slate-600 border border-slate-200'
              }`}
            >
              {act}
            </button>
          ))}
        </div>
      </div>

      {/* Table Container */}
      <div className="overflow-x-auto rounded-xl border border-slate-200 bg-white shadow-xs">
        <table className="w-full text-left text-xs min-w-[580px]">
          <thead className="bg-slate-50 text-slate-600 uppercase tracking-wider border-b border-slate-200">
            <tr>
              <th className="py-3 px-4 font-bold">Category</th>
              <th className="py-3 px-4 font-bold">Action</th>
              <th className="py-3 px-4 font-bold">Confidence</th>
              <th className="py-3 px-4 font-bold">Justification / Reason</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {filteredCategories.length === 0 ? (
              <tr>
                <td colSpan={4} className="py-6 text-center text-slate-400">
                  No categories match the filter "{filter}".
                </td>
              </tr>
            ) : (
              filteredCategories.map((category) => {
                const decision = plan[category];
                const action = decision.action || 'DROP';
                const style = ACTION_STYLES[action] || 'bg-slate-100 text-slate-700';
                const isViolation = violationCategories.has(category);
                const confPct = Math.round((decision.confidence || 0) * 100);

                return (
                  <tr key={category} className="hover:bg-slate-50/70 transition-colors">
                    {/* Category Name */}
                    <td className="py-3 px-4 font-mono font-semibold text-slate-800">
                      <div className="flex items-center gap-2">
                        <span>{category}</span>
                        {isViolation && (
                          <span
                            title="Clamped by Deterministic Policy Floor"
                            className="px-1.5 py-0.5 text-[10px] rounded bg-amber-50 text-amber-800 border border-amber-200 flex items-center gap-1 font-sans font-semibold"
                          >
                            <ShieldAlert className="w-3 h-3 text-amber-600" /> Policy Floor
                          </span>
                        )}
                      </div>
                    </td>

                    {/* Action Badge */}
                    <td className="py-3 px-4 whitespace-nowrap">
                      <span
                        className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-bold border ${style}`}
                      >
                        {action === 'KEEP' ? (
                          <Check className="w-3 h-3" />
                        ) : (
                          <X className="w-3 h-3" />
                        )}
                        {action}
                      </span>
                    </td>

                    {/* Confidence bar */}
                    <td className="py-3 px-4 whitespace-nowrap">
                      <div className="flex items-center gap-2">
                        <div className="w-16 h-1.5 rounded-full bg-slate-200 overflow-hidden">
                          <div
                            className={`h-full rounded-full ${
                              confPct >= 80 ? 'bg-emerald-500' : 'bg-blue-600'
                            }`}
                            style={{ width: `${confPct}%` }}
                          />
                        </div>
                        <span className="font-mono text-slate-600 font-semibold">{confPct}%</span>
                      </div>
                    </td>

                    {/* Reason */}
                    <td className="py-3 px-4 text-slate-600 max-w-md leading-relaxed font-medium">
                      {decision.reason || 'Evaluated for task relevance.'}
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

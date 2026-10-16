import React, { useState } from 'react';
import { Search, Tag, Table as TableIcon, LayoutGrid, CheckCircle2, Shield } from 'lucide-react';

function cleanFieldId(id = '') {
  const parts = id.split('-');
  if (parts.length >= 2) {
    return `${parts[parts.length - 2]}-${parts[parts.length - 1]}`;
  }
  return id;
}

function cleanDetectorName(detector = '') {
  if (detector.toLowerCase().startsWith('custom_pattern:')) {
    return detector.replace(/^custom_pattern:\s*/i, 'Regex: ');
  }
  return detector;
}

export default function DetectedFieldsGrid({ fields = [] }) {
  const [query, setQuery] = useState('');
  const [viewMode, setViewMode] = useState('table');

  const filtered = fields.filter((f) => {
    const q = query.toLowerCase();
    return (
      (f.id && f.id.toLowerCase().includes(q)) ||
      (f.category && f.category.toLowerCase().includes(q)) ||
      (f.placeholder && f.placeholder.toLowerCase().includes(q)) ||
      (f.detector && f.detector.toLowerCase().includes(q))
    );
  });

  return (
    <div className="space-y-3.5 animate-fade-in-up">
      {/* Control Bar: Search + View Toggle */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div className="relative flex-1 max-w-sm">
          <Search className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search by category, tag, or detector..."
            className="w-full bg-slate-50 border border-slate-200 rounded-lg pl-8 pr-3 py-1.5 text-xs text-slate-800 placeholder-slate-400 focus:outline-none focus:border-blue-500 focus:bg-white"
          />
        </div>

        <div className="flex items-center gap-3">
          <span className="text-xs text-slate-500 font-medium">
            <span className="font-bold text-slate-900">{filtered.length}</span> of {fields.length} detected
          </span>

          <div className="flex items-center rounded-lg bg-slate-100 border border-slate-200 p-0.5">
            <button
              type="button"
              onClick={() => setViewMode('table')}
              className={`p-1.5 rounded-md text-xs transition-all duration-150 active:scale-95 flex items-center gap-1 font-medium ${
                viewMode === 'table'
                  ? 'bg-white text-blue-700 shadow-xs border border-slate-200 font-bold'
                  : 'text-slate-500 hover:text-slate-800'
              }`}
              title="Table view"
            >
              <TableIcon className="w-3.5 h-3.5" />
              <span className="hidden sm:inline">Table</span>
            </button>
            <button
              type="button"
              onClick={() => setViewMode('cards')}
              className={`p-1.5 rounded-md text-xs transition-all duration-150 active:scale-95 flex items-center gap-1 font-medium ${
                viewMode === 'cards'
                  ? 'bg-white text-blue-700 shadow-xs border border-slate-200 font-bold'
                  : 'text-slate-500 hover:text-slate-800'
              }`}
              title="Cards view"
            >
              <LayoutGrid className="w-3.5 h-3.5" />
              <span className="hidden sm:inline">Cards</span>
            </button>
          </div>
        </div>
      </div>

      {/* 1. TABLE VIEW */}
      {viewMode === 'table' && (
        <div className="overflow-x-auto rounded-xl border border-slate-200 bg-white shadow-xs">
          <table className="w-full text-left text-xs min-w-[620px]">
            <thead className="bg-slate-50 text-slate-600 uppercase tracking-wider border-b border-slate-200">
              <tr>
                <th className="py-2.5 px-3.5 font-bold">Field ID</th>
                <th className="py-2.5 px-3.5 font-bold">Category</th>
                <th className="py-2.5 px-3.5 font-bold">Skeleton Tag</th>
                <th className="py-2.5 px-3.5 font-bold">Detector Engine</th>
                <th className="py-2.5 px-3.5 font-bold">Location</th>
                <th className="py-2.5 px-3.5 font-bold text-right">Confidence</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 font-mono">
              {filtered.length === 0 ? (
                <tr>
                  <td colSpan={6} className="py-8 text-center text-slate-400 font-sans">
                    No detected fields match your search.
                  </td>
                </tr>
              ) : (
                filtered.map((field) => {
                  const line = field.location?.line ?? '-';
                  const startChar = field.location?.start_char ?? field.location?.start ?? 0;
                  const endChar = field.location?.end_char ?? field.location?.end ?? 0;
                  const confPct = Math.round((field.confidence || 0) * 100);

                  return (
                    <tr key={field.id} className="hover:bg-slate-50/70 transition-colors">
                      {/* ID Badge */}
                      <td className="py-2.5 px-3.5 whitespace-nowrap">
                        <span
                          className="px-2 py-0.5 rounded bg-blue-50 text-blue-700 border border-blue-200 text-[11px] font-bold"
                          title={field.id}
                        >
                          {cleanFieldId(field.id)}
                        </span>
                      </td>

                      {/* Category */}
                      <td className="py-2.5 px-3.5 font-sans font-semibold text-slate-900 whitespace-nowrap">
                        <div className="flex items-center gap-1.5">
                          <Tag className="w-3 h-3 text-blue-600" />
                          <span>{field.category}</span>
                        </div>
                      </td>

                      {/* Placeholder Tag */}
                      <td className="py-2.5 px-3.5 whitespace-nowrap">
                        <span className="px-2 py-0.5 rounded bg-slate-100 text-slate-800 border border-slate-200 text-[11px] font-bold">
                          {field.placeholder}
                        </span>
                      </td>

                      {/* Detector Engine */}
                      <td className="py-2.5 px-3.5 font-sans text-slate-600 text-[11px] font-medium">
                        <span className="inline-block max-w-[200px] truncate" title={field.detector}>
                          {cleanDetectorName(field.detector)}
                        </span>
                      </td>

                      {/* Location */}
                      <td className="py-2.5 px-3.5 text-slate-500 text-[11px] whitespace-nowrap font-medium">
                        Line {line} <span className="opacity-75 font-semibold">[{startChar}..{endChar}]</span>
                      </td>

                      {/* Confidence */}
                      <td className="py-2.5 px-3.5 text-right font-sans whitespace-nowrap">
                        <span
                          className={`font-bold text-xs ${
                            confPct >= 90 ? 'text-emerald-700' : 'text-blue-700'
                          }`}
                        >
                          {confPct}%
                        </span>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      )}

      {/* 2. CARDS VIEW */}
      {viewMode === 'cards' && (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          {filtered.length === 0 ? (
            <div className="col-span-full py-8 text-center text-slate-400 text-xs">
              No detected fields match your search.
            </div>
          ) : (
            filtered.map((field) => {
              const line = field.location?.line ?? '-';
              const startChar = field.location?.start_char ?? field.location?.start ?? 0;
              const endChar = field.location?.end_char ?? field.location?.end ?? 0;
              const confPct = Math.round((field.confidence || 0) * 100);

              return (
                <div
                  key={field.id}
                  className="p-3.5 rounded-xl bg-white border border-slate-200 hover:border-slate-300 transition-all flex flex-col justify-between gap-2.5 shadow-xs"
                >
                  {/* Top Header */}
                  <div className="flex items-start justify-between gap-2 border-b border-slate-100 pb-2">
                    <span
                      className="font-mono text-[11px] font-bold text-blue-700 bg-blue-50 px-2 py-0.5 rounded border border-blue-200 shrink-0"
                      title={field.id}
                    >
                      {cleanFieldId(field.id)}
                    </span>
                    <span
                      className="text-[10px] text-slate-600 bg-slate-50 px-2 py-0.5 rounded border border-slate-200 truncate text-right max-w-[150px] font-medium"
                      title={field.detector}
                    >
                      {cleanDetectorName(field.detector)}
                    </span>
                  </div>

                  {/* Middle: Category & Placeholder */}
                  <div className="space-y-1.5">
                    <div className="flex items-center gap-1.5 text-xs font-bold text-slate-900">
                      <Tag className="w-3.5 h-3.5 text-blue-600 shrink-0" />
                      <span className="truncate">{field.category}</span>
                    </div>
                    <div>
                      <span className="inline-block font-mono text-xs font-bold text-slate-800 bg-slate-100 px-2.5 py-1 rounded-md border border-slate-200">
                        {field.placeholder}
                      </span>
                    </div>
                  </div>

                  {/* Bottom: Location & Confidence */}
                  <div className="pt-2 border-t border-slate-100 flex items-center justify-between text-[11px] text-slate-500 font-medium">
                    <span>
                      Line {line} <span className="opacity-75 font-mono">[{startChar}..{endChar}]</span>
                    </span>
                    <span
                      className={`font-bold ${
                        confPct >= 90 ? 'text-emerald-700' : 'text-blue-700'
                      }`}
                    >
                      {confPct}% Conf
                    </span>
                  </div>
                </div>
              );
            })
          )}
        </div>
      )}
    </div>
  );
}

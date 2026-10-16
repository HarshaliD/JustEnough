import React, { useState } from 'react';
import { Columns, Eye, Copy, Check, ShieldCheck, AlertCircle } from 'lucide-react';

export default function DiffView({ originalText = '', minimizedText = '', plan = {}, detectedFields = [] }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(minimizedText);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="space-y-3 animate-fade-in-up">
      <div className="flex items-center justify-between">
        <p className="text-xs text-slate-500 font-medium">
          Compare original document content against the task-minimized version:
        </p>
        <button
          type="button"
          onClick={handleCopy}
          className={`text-xs font-semibold px-2.5 py-1 rounded-md border transition-all duration-150 flex items-center gap-1.5 active:scale-95 ${
            copied
              ? 'bg-emerald-50 text-emerald-700 border-emerald-300 shadow-xs'
              : 'bg-slate-100 hover:bg-slate-200 text-slate-700 hover:text-slate-900 border-slate-200'
          }`}
        >
          {copied ? (
            <Check className="w-3.5 h-3.5 text-emerald-600 animate-spring-bounce" />
          ) : (
            <Copy className="w-3.5 h-3.5 text-slate-500" />
          )}
          <span>{copied ? 'Copied to Clipboard!' : 'Copy Minimized Text'}</span>
        </button>
      </div>

      {/* Side by Side Split */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Left: Original Document */}
        <div className="rounded-xl border border-rose-200 bg-white overflow-hidden flex flex-col min-w-0 shadow-xs interactive-card">
          <div className="px-4 py-2.5 bg-rose-50/60 border-b border-rose-100 flex items-center justify-between text-xs">
            <span className="font-bold text-slate-800 flex items-center gap-1.5">
              <AlertCircle className="w-3.5 h-3.5 text-rose-500" /> Original Document
            </span>
            <span className="text-[10px] text-rose-700 bg-rose-100 px-2 py-0.5 rounded font-mono font-bold">
              Contains Raw PII
            </span>
          </div>
          <div className="p-4 font-mono text-xs text-slate-700 bg-slate-50/40 whitespace-pre-wrap break-all overflow-y-auto max-h-[460px] leading-relaxed selection:bg-rose-100">
            {originalText || '(No original text available)'}
          </div>
        </div>

        {/* Right: Minimized Document */}
        <div className="rounded-xl border border-emerald-300 bg-white overflow-hidden flex flex-col min-w-0 shadow-xs interactive-card">
          <div className="px-4 py-2.5 bg-emerald-50/70 border-b border-emerald-100 flex items-center justify-between text-xs">
            <span className="font-bold text-emerald-800 flex items-center gap-1.5">
              <ShieldCheck className="w-3.5 h-3.5 text-emerald-600" />
              Task-Minimized Safe Version
            </span>
            <span className="text-[10px] text-emerald-800 bg-emerald-100 px-2 py-0.5 rounded font-mono font-bold">
              Safe for LLM Upload
            </span>
          </div>
          <div className="p-4 font-mono text-xs text-slate-900 bg-emerald-50/15 whitespace-pre-wrap break-all overflow-y-auto max-h-[460px] leading-relaxed selection:bg-emerald-100">
            {minimizedText || '(No minimized text available)'}
          </div>
        </div>
      </div>
    </div>
  );
}

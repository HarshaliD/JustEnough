import React, { useState } from 'react';
import { Copy, Download, Check, Sparkles, Shield } from 'lucide-react';

export default function MinimizedViewer({ minimizedText = '', task = '' }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(minimizedText);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleDownload = () => {
    const blob = new Blob([minimizedText], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = 'minimized_safe_document.txt';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  const charCount = minimizedText.length;
  const wordCount = minimizedText.trim() ? minimizedText.trim().split(/\s+/).length : 0;

  return (
    <div className="space-y-4 animate-fade-in-up">
      {/* Ready Banner */}
      <div className="p-3.5 rounded-xl bg-blue-50 border border-blue-200 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 shadow-xs interactive-card">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-blue-100 text-blue-700 flex items-center justify-center shrink-0">
            <Sparkles className="w-4 h-4 text-blue-600" />
          </div>
          <div>
            <p className="text-xs font-bold text-slate-900">
              Clean, Anonymized Text Ready for AI Prompting
            </p>
            <p className="text-[11px] text-slate-600">
              Contains only the fields required for: <span className="text-blue-700 font-semibold italic">"{task}"</span>
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2 shrink-0">
          <button
            type="button"
            onClick={handleCopy}
            className={`text-xs font-semibold px-3 py-1.5 rounded-lg border transition-all duration-150 flex items-center gap-1.5 shadow-xs active:scale-95 ${
              copied
                ? 'bg-emerald-50 text-emerald-700 border-emerald-300'
                : 'bg-white hover:bg-slate-50 text-slate-700 border-slate-300'
            }`}
          >
            {copied ? (
              <Check className="w-3.5 h-3.5 text-emerald-600 animate-spring-bounce" />
            ) : (
              <Copy className="w-3.5 h-3.5 text-slate-500" />
            )}
            <span>{copied ? 'Copied!' : 'Copy Text'}</span>
          </button>
          <button
            type="button"
            onClick={handleDownload}
            className="text-xs font-semibold px-3 py-1.5 rounded-lg bg-blue-600 hover:bg-blue-700 active:scale-95 text-white transition-all duration-150 flex items-center gap-1.5 shadow-xs group"
          >
            <Download className="w-3.5 h-3.5 transition-transform duration-200 group-hover:translate-y-0.5" />
            <span>Download</span>
          </button>
        </div>
      </div>

      {/* Text Container */}
      <div className="rounded-xl border border-slate-200 bg-white overflow-hidden shadow-xs">
        <div className="px-4 py-2 bg-slate-50 border-b border-slate-200 flex items-center justify-between text-[11px] text-slate-500 font-medium">
          <span>Format: Structured Plaintext</span>
          <span>{charCount} characters • {wordCount} words</span>
        </div>
        <div className="p-4 font-mono text-xs text-slate-800 bg-slate-50/30 whitespace-pre-wrap break-all overflow-y-auto max-h-[500px] leading-relaxed selection:bg-blue-100">
          {minimizedText}
        </div>
      </div>
    </div>
  );
}

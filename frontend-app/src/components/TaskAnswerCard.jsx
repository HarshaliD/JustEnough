import React, { useState } from 'react';
import {
  Sparkles,
  Check,
  Copy,
  RotateCcw,
  ShieldCheck,
  Zap,
  Bot,
  HelpCircle,
  Loader2,
} from 'lucide-react';

export default function TaskAnswerCard({ answer, task, isLoading, onRegenerate, liveMode }) {
  const [copied, setCopied] = useState(false);

  if (!answer && !isLoading) return null;

  const handleCopy = () => {
    if (!answer?.reply) return;
    navigator.clipboard.writeText(answer.reply);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div
      id="task-answer-card"
      className="p-5 sm:p-6 rounded-2xl bg-gradient-to-br from-emerald-50/50 via-white to-blue-50/40 dark:from-emerald-950/20 dark:via-[#090e17] dark:to-blue-950/20 border-2 border-emerald-400/80 dark:border-emerald-500/50 shadow-lg shadow-emerald-500/5 space-y-4 animate-fade-in-up"
    >
      {/* Card Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-emerald-100 dark:border-emerald-900/40">
        <div className="flex items-center gap-2.5">
          <div className="w-9 h-9 rounded-xl bg-emerald-600 text-white flex items-center justify-center shadow-sm shadow-emerald-500/20">
            <Sparkles className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h3 className="text-sm font-bold text-slate-900 dark:text-white">
                AI Task Answer
              </h3>
              <span className="text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 rounded-full bg-emerald-100 dark:bg-emerald-900/50 text-emerald-800 dark:text-emerald-300 border border-emerald-300 dark:border-emerald-700">
                Safe Inference
              </span>
            </div>
            <p className="text-xs text-slate-500 dark:text-slate-400">
              Answered using <strong>only the task-minimized document</strong> — no raw PII sent
            </p>
          </div>
        </div>

        {/* Model & Latency Badges */}
        <div className="flex items-center gap-2">
          {answer?.model && (
            <span className="text-[11px] font-mono font-semibold px-2 py-1 rounded-lg bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 border border-slate-200 dark:border-slate-700">
              {liveMode ? '🟢 Live Gemini' : '🔵 Mock Mode'} • {answer.model}
            </span>
          )}
          {answer?.latency_ms && (
            <span className="text-[11px] font-mono text-emerald-700 dark:text-emerald-400 font-bold flex items-center gap-1">
              <Zap className="w-3 h-3 text-emerald-600" />
              {Math.round(answer.latency_ms)}ms
            </span>
          )}
        </div>
      </div>

      {/* Task Prompt Reference */}
      <div className="p-3 rounded-xl bg-white/80 dark:bg-[#0d1522]/80 border border-slate-200/80 dark:border-slate-800 text-xs">
        <span className="text-slate-500 dark:text-slate-400 font-semibold block text-[11px]">
          Target Question / Task:
        </span>
        <p className="font-bold text-slate-800 dark:text-slate-100 mt-0.5 italic">
          "{task}"
        </p>
      </div>

      {/* Answer Body */}
      {isLoading ? (
        <div className="p-8 rounded-xl bg-white dark:bg-[#070b14] border border-slate-200 dark:border-slate-800 flex flex-col items-center justify-center gap-3 text-center">
          <Loader2 className="w-7 h-7 text-emerald-600 animate-spin" />
          <div className="space-y-0.5">
            <p className="text-xs font-bold text-slate-800 dark:text-slate-200">
              Prompting AI with Safe Minimized Document…
            </p>
            <p className="text-[11px] text-slate-500 dark:text-slate-400">
              Computing answer with zero raw PII exposure
            </p>
          </div>
        </div>
      ) : (
        <div className="p-4 sm:p-5 rounded-xl bg-white dark:bg-[#070b14] border border-emerald-200/60 dark:border-emerald-900/50 shadow-inner">
          <p className="text-sm text-slate-900 dark:text-slate-100 font-medium leading-relaxed whitespace-pre-wrap selection:bg-emerald-100 dark:selection:bg-emerald-900">
            {answer?.reply}
          </p>
        </div>
      )}

      {/* Footer Guarantee & Action Buttons */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pt-2 text-xs">
        <div className="flex items-center gap-1.5 text-emerald-800 dark:text-emerald-300 font-semibold">
          <ShieldCheck className="w-4 h-4 text-emerald-600 shrink-0" />
          <span className="text-[11px]">
            Zero-Leak Proof: Account number, PAN, and contacts were 100% blocked from the prompt.
          </span>
        </div>

        <div className="flex items-center gap-2 self-end sm:self-auto">
          {answer && (
            <button
              type="button"
              onClick={handleCopy}
              className={`text-xs font-semibold px-3 py-1.5 rounded-lg border transition-all duration-150 flex items-center gap-1.5 shadow-xs active:scale-95 cursor-pointer ${
                copied
                  ? 'bg-emerald-50 text-emerald-700 border-emerald-300 shadow-xs'
                  : 'bg-white hover:bg-slate-50 dark:bg-[#0d1522] dark:hover:bg-slate-800 text-slate-700 dark:text-slate-200 border-slate-300 dark:border-slate-700'
              }`}
            >
              {copied ? (
                <Check className="w-3.5 h-3.5 text-emerald-600 animate-spring-bounce" />
              ) : (
                <Copy className="w-3.5 h-3.5 text-slate-500" />
              )}
              <span>{copied ? 'Copied!' : 'Copy Answer'}</span>
            </button>
          )}

          {onRegenerate && (
            <button
              type="button"
              onClick={onRegenerate}
              disabled={isLoading}
              className="text-xs font-semibold px-3 py-1.5 rounded-lg border border-slate-300 dark:border-slate-700 bg-white hover:bg-slate-50 dark:bg-[#0d1522] dark:hover:bg-slate-800 text-slate-700 dark:text-slate-200 transition-all active:scale-95 flex items-center gap-1.5 disabled:opacity-40 cursor-pointer"
              title="Re-run answer inference on current minimized text"
            >
              <RotateCcw className="w-3.5 h-3.5 text-slate-500" />
              <span>Re-run Answer</span>
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

import React, { useState } from 'react';
import { CheckCircle2, AlertTriangle, Loader2, ChevronDown, ChevronUp, Zap, FileText, Target } from 'lucide-react';
import { verifyAnswers } from '../api';

const METHOD_LABELS = {
  numeric_tolerance_2pct: 'Numeric (≤2% tolerance)',
  set_jaccard_80pct: 'Set matching (≥80% overlap)',
  keyword_overlap_60pct: 'Keyword overlap (≥60%)',
  exact_match: 'Exact text match',
};

export default function VerifierPanel({ task, originalText, minimizedText, liveMode, taskOutputSchema }) {
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [expanded, setExpanded] = useState(false);

  const handleVerify = async () => {
    setLoading(true);
    setError(null);
    console.log(`[VERIFIER] Starting verification | Live: ${liveMode} | Model: gemini-3.6-flash`);
    try {
      const data = await verifyAnswers({
        task,
        originalText,
        minimizedText,
        live: liveMode,
        taskOutputSchema,
      });
      console.log('[VERIFIER SUCCESS] Result:', data);
      setResult(data);
      setExpanded(true);
    } catch (err) {
      console.error('[VERIFIER ERROR]:', err);
      setError(err.message || 'Verification failed. Please check backend logs.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-4 animate-fade-in-up">
      {/* Header + Run Button */}
      <div className="flex items-center justify-between">
        <div className="space-y-0.5">
          <h3 className="text-sm font-bold text-slate-800 flex items-center gap-2">
            <Target className="w-4 h-4 text-blue-600" />
            Answer Verification (A vs B)
          </h3>
          <p className="text-[11px] text-slate-500 font-medium">
            Runs your task on both versions. Proves the minimized document preserves the answer.
          </p>
        </div>
        <button
          id="verify-run-btn"
          onClick={handleVerify}
          disabled={loading || !originalText || !minimizedText}
          className="flex items-center gap-2 px-4 py-2 rounded-lg bg-blue-600 hover:bg-blue-700 text-white text-xs font-bold transition-all duration-150 active:scale-95 disabled:opacity-40 disabled:cursor-not-allowed shadow-sm"
        >
          {loading ? (
            <><Loader2 className="w-3.5 h-3.5 animate-spin" /> Verifying…</>
          ) : (
            <><Zap className="w-3.5 h-3.5" /> Run Verification</>
          )}
        </button>
      </div>

      {error && (
        <div className="p-3 rounded-lg bg-rose-50 border border-rose-200 text-rose-800 text-xs font-medium flex items-center gap-2">
          <AlertTriangle className="w-4 h-4 shrink-0" />
          {error}
        </div>
      )}

      {result && (
        <div className="space-y-3">
          {/* Verdict Banner */}
          <div
            className={`flex items-center gap-3 p-3.5 rounded-xl border ${
              result.preserved
                ? 'bg-emerald-50 border-emerald-200 text-emerald-800'
                : 'bg-amber-50 border-amber-200 text-amber-800'
            }`}
          >
            {result.preserved ? (
              <CheckCircle2 className="w-5 h-5 text-emerald-600 shrink-0" />
            ) : (
              <AlertTriangle className="w-5 h-5 text-amber-600 shrink-0" />
            )}
            <div className="flex-1">
              <p className="text-xs font-bold">
                {result.preserved
                  ? '✅ Answer Preserved — Minimization is safe for this task'
                  : `⚠️ Answer Deviation Detected — ${result.deviation_pct}% deviation`}
              </p>
              <p className="text-[11px] mt-0.5 opacity-80">
                Comparison method: {METHOD_LABELS[result.method] || result.method} •{' '}
                Mode: {result.mode === 'live' ? '🟢 Live Gemini' : '🔵 Mock'}
              </p>
            </div>
            <div
              className={`text-lg font-black tabular-nums ${
                result.preserved ? 'text-emerald-600' : 'text-amber-600'
              }`}
            >
              {result.deviation_pct}%
            </div>
          </div>

          {/* Toggle answer comparison */}
          <button
            id="verify-expand-btn"
            onClick={() => setExpanded(!expanded)}
            className="flex items-center gap-1.5 text-[11px] text-slate-500 font-semibold hover:text-slate-700 transition-colors"
          >
            {expanded ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
            {expanded ? 'Hide' : 'Show'} answer comparison
          </button>

          {expanded && (
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 animate-fade-in-up">
              <div className="space-y-1.5">
                <div className="flex items-center gap-1.5 text-[11px] font-bold text-slate-600">
                  <FileText className="w-3 h-3" />
                  A-Arm: Original Document
                </div>
                <div className="p-3 rounded-lg bg-slate-50 border border-slate-200 text-xs text-slate-700 leading-relaxed font-mono whitespace-pre-wrap min-h-[60px]">
                  {result.answer_original}
                </div>
              </div>
              <div className="space-y-1.5">
                <div className="flex items-center gap-1.5 text-[11px] font-bold text-emerald-700">
                  <FileText className="w-3 h-3" />
                  B-Arm: Minimized Document
                </div>
                <div className="p-3 rounded-lg bg-emerald-50 border border-emerald-200 text-xs text-emerald-900 leading-relaxed font-mono whitespace-pre-wrap min-h-[60px]">
                  {result.answer_minimized}
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {!result && !loading && !error && (
        <div className="p-4 rounded-xl bg-slate-50 border border-slate-200 text-center">
          <p className="text-[11px] text-slate-400 font-medium">
            Click <strong>Run Verification</strong> to compare task answers on original vs minimized text.
          </p>
        </div>
      )}
    </div>
  );
}

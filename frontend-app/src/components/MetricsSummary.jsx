import React from 'react';
import {
  ShieldCheck,
  EyeOff,
  CheckCircle,
  AlertTriangle,
  Lock,
  Zap,
} from 'lucide-react';

export default function MetricsSummary({ metrics, policyViolations }) {
  if (!metrics) return null;

  const pct = Math.round(metrics.sensitive_field_reduction_pct || 0);

  // SVG Gauge calculations
  const radius = 34;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset = circumference - (pct / 100) * circumference;

  return (
    <div className="space-y-3.5 animate-fade-in-up">
      {/* Policy Floor Alert Banner */}
      {policyViolations && policyViolations.length > 0 && (
        <div className="p-3.5 rounded-xl bg-amber-50 border border-amber-200 text-amber-800 text-xs flex items-start gap-3 shadow-xs animate-fade-in-up">
          <AlertTriangle className="w-4 h-4 text-amber-600 shrink-0 mt-0.5" />
          <div className="space-y-1 min-w-0">
            <p className="font-bold text-amber-900">
              Deterministic Policy Floor Enforced ({policyViolations.length}{' '}
              rule{policyViolations.length > 1 ? 's' : ''})
            </p>
            {policyViolations.map((v, i) => (
              <p key={i} className="text-amber-800 leading-relaxed text-[11px]">
                • Category <code className="font-mono bg-amber-100 px-1 rounded text-amber-900 font-semibold">{v.category}</code>: Model proposed <span className="font-bold">{v.model_action}</span>, clamped to <span className="font-bold underline">{v.clamped_action}</span> ({v.reason})
              </p>
            ))}
          </div>
        </div>
      )}

      {/* Hero Card: Privacy Reduction Gauge Banner */}
      <div className="glass-card-sm interactive-card p-4 sm:p-5 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        {/* Left: Text & Numbers */}
        <div className="space-y-1 min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <span className="text-[11px] font-bold text-blue-700 uppercase tracking-wider bg-blue-50 px-2 py-0.5 rounded border border-blue-200">
              Privacy Reduction
            </span>
            <span className="text-xs text-emerald-700 font-bold flex items-center gap-1">
              <Zap className="w-3 h-3 text-emerald-600 animate-pulse" /> {metrics.latency_ms ? `${metrics.latency_ms}ms` : '< 20ms'} latency
            </span>
          </div>

          <div className="flex items-baseline gap-2.5 pt-1">
            <span className="text-3xl sm:text-4xl font-black text-slate-900 tracking-tight">
              {pct}%
            </span>
            <span className="text-sm font-bold text-slate-700">
              Less Sensitive Data Sent to AI
            </span>
          </div>

          <p className="text-xs text-slate-500">
            <span className="text-slate-800 font-semibold">
              {metrics.fields_dropped_or_masked} of {metrics.total_fields_detected}
            </span>{' '}
            sensitive fields removed or masked before model inference
          </p>
        </div>

        {/* Right: Circular SVG Gauge */}
        <div className="relative w-20 h-20 shrink-0 self-center sm:self-auto flex items-center justify-center group cursor-pointer">
          <svg className="w-full h-full -rotate-90" viewBox="0 0 90 90">
            <circle
              cx="45"
              cy="45"
              r={radius}
              className="stroke-slate-200"
              strokeWidth="8"
              fill="none"
            />
            <circle
              cx="45"
              cy="45"
              r={radius}
              className="stroke-blue-600 transition-all duration-1000 ease-out"
              strokeWidth="8"
              strokeDasharray={circumference}
              strokeDashoffset={strokeDashoffset}
              strokeLinecap="round"
              fill="none"
            />
          </svg>
          <div className="absolute inset-0 flex items-center justify-center transition-transform duration-300 group-hover:scale-125">
            <Lock className="w-4 h-4 text-blue-600" />
          </div>
        </div>
      </div>

      {/* Row of 3 Equal-Width Metric Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        {/* Metric 1: Detected */}
        <div className="glass-card-sm interactive-card p-4 flex flex-col justify-between min-w-0 group cursor-default">
          <div className="flex items-center justify-between text-slate-500 text-xs">
            <span className="font-semibold text-slate-700">Fields Detected</span>
            <ShieldCheck className="w-4 h-4 text-blue-600 shrink-0 ml-1 transition-transform duration-200 group-hover:scale-115" />
          </div>
          <div className="mt-3">
            <span className="text-2xl sm:text-3xl font-black text-slate-900">
              {metrics.total_fields_detected}
            </span>
            <span className="text-[11px] text-slate-500 block mt-0.5 font-medium">
              Presidio + Indian Regex
            </span>
          </div>
        </div>

        {/* Metric 2: Protected */}
        <div className="glass-card-sm interactive-card p-4 flex flex-col justify-between min-w-0 group cursor-default">
          <div className="flex items-center justify-between text-slate-500 text-xs">
            <span className="font-semibold text-slate-700">Protected / Masked</span>
            <EyeOff className="w-4 h-4 text-rose-600 shrink-0 ml-1 transition-transform duration-200 group-hover:scale-115" />
          </div>
          <div className="mt-3">
            <span className="text-2xl sm:text-3xl font-black text-rose-600">
              {metrics.fields_dropped_or_masked}
            </span>
            <span className="text-[11px] text-slate-500 block mt-0.5 font-medium">
              Blocked from AI upload
            </span>
          </div>
        </div>

        {/* Metric 3: Kept */}
        <div className="glass-card-sm interactive-card p-4 flex flex-col justify-between min-w-0 group cursor-default">
          <div className="flex items-center justify-between text-slate-500 text-xs">
            <span className="font-semibold text-slate-700">Task-Essential Kept</span>
            <CheckCircle className="w-4 h-4 text-emerald-600 shrink-0 ml-1 transition-transform duration-200 group-hover:scale-115" />
          </div>
          <div className="mt-3">
            <span className="text-2xl sm:text-3xl font-black text-emerald-600">
              {metrics.fields_kept}
            </span>
            <span className="text-[11px] text-slate-500 block mt-0.5 font-medium">
              Required for answer
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}

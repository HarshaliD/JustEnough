import React from 'react';
import {
  Search,
  FileCode,
  BrainCircuit,
  ShieldCheck,
  Cpu,
  Check,
} from 'lucide-react';

const STEPS = [
  { id: 'detect', label: '1. Sensitive Detection', icon: Search, desc: 'Presidio + Indian Regex' },
  { id: 'skeleton', label: '2. Zero-Leak Skeleton', icon: FileCode, desc: 'Typed Placeholders' },
  { id: 'plan', label: '3. Task Planner', icon: BrainCircuit, desc: 'Gemini Proposes Needs' },
  { id: 'policy', label: '4. Policy Floor', icon: ShieldCheck, desc: 'Deterministic Clamping' },
  { id: 'transform', label: '5. Deterministic Min', icon: Cpu, desc: 'Rule-Based Transform' },
];

export default function PipelineStepper({ currentStep, isDone }) {
  return (
    <div className="glass-card-sm interactive-card p-4">
      <div className="flex items-center justify-between gap-1 overflow-x-auto pb-1 sm:pb-0">
        {STEPS.map((step, idx) => {
          const Icon = step.icon;
          const isCurrent = currentStep === idx;
          const isFinished = isDone || currentStep > idx;

          return (
            <div
              key={step.id}
              className={`flex items-center gap-2 px-2.5 py-1.5 rounded-lg border text-xs whitespace-nowrap transition-all duration-300 ${
                isFinished
                  ? 'bg-emerald-50 border-emerald-200 text-emerald-700 font-semibold'
                  : isCurrent
                  ? 'bg-blue-50 border-blue-400 text-blue-700 font-bold shadow-sm scale-[1.02]'
                  : 'bg-slate-50 border-slate-200 text-slate-400 font-medium'
              }`}
            >
              <div
                className={`w-5 h-5 rounded-full flex items-center justify-center shrink-0 transition-all duration-300 ${
                  isFinished
                    ? 'bg-emerald-600 text-white font-bold animate-spring-bounce shadow-xs'
                    : isCurrent
                    ? 'bg-blue-600 text-white font-bold animate-pulse shadow-sm shadow-blue-500/30'
                    : 'bg-slate-200 text-slate-500'
                }`}
              >
                {isFinished ? (
                  <Check className="w-3 h-3 stroke-[3]" />
                ) : (
                  <Icon className="w-3 h-3" />
                )}
              </div>
              <div className="leading-tight">
                <span className="font-semibold block">{step.label}</span>
                <span className="text-[10px] opacity-75 hidden md:block">
                  {step.desc}
                </span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

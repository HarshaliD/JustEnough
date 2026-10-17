import React, { useState } from 'react';
import {
  X,
  Shield,
  Sparkles,
  Sliders,
  CheckCircle2,
  Lock,
  Cpu,
  FileSearch,
  FileCheck,
  AlertTriangle,
  ArrowRight,
  HelpCircle,
  BookOpen,
  Info,
} from 'lucide-react';

export default function AboutHelpModal({ isOpen, onClose }) {
  const [activeTab, setActiveTab] = useState('pipeline');

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 sm:p-6 overflow-y-auto bg-black/60 backdrop-blur-sm animate-fade-in">
      <div
        className="relative w-full max-w-3xl rounded-2xl bg-white dark:bg-[#090e17] border border-slate-200 dark:border-slate-800 shadow-2xl overflow-hidden flex flex-col max-h-[90vh] animate-slide-up"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-200 dark:border-slate-800 bg-slate-50/80 dark:bg-[#0d1522]">
          <div className="flex items-center gap-2.5">
            <div className="w-9 h-9 rounded-xl bg-blue-600 text-white flex items-center justify-center shadow-sm">
              <Shield className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-base font-bold text-slate-900 dark:text-white flex items-center gap-2">
                About JustEnough
                <span className="text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 rounded-full bg-blue-50 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 border border-blue-200 dark:border-blue-700">
                  Help Guide
                </span>
              </h2>
              <p className="text-xs text-slate-500 dark:text-slate-400">
                Task-Aware Data Minimization Layer for BFSI AI Uploads
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-slate-700 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
            title="Close"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Modal Subnav */}
        <div className="flex items-center gap-2 px-6 pt-3 border-b border-slate-100 dark:border-slate-800 bg-white dark:bg-[#090e17]">
          <button
            type="button"
            onClick={() => setActiveTab('pipeline')}
            className={`flex items-center gap-2 pb-2.5 px-3 text-xs font-bold border-b-2 transition-all ${
              activeTab === 'pipeline'
                ? 'border-blue-600 text-blue-600 dark:text-blue-400'
                : 'border-transparent text-slate-500 hover:text-slate-800 dark:hover:text-slate-300'
            }`}
          >
            <Cpu className="w-3.5 h-3.5" />
            <span>How the Pipeline Works (6 Steps)</span>
          </button>
          <button
            type="button"
            onClick={() => setActiveTab('guide')}
            className={`flex items-center gap-2 pb-2.5 px-3 text-xs font-bold border-b-2 transition-all ${
              activeTab === 'guide'
                ? 'border-blue-600 text-blue-600 dark:text-blue-400'
                : 'border-transparent text-slate-500 hover:text-slate-800 dark:hover:text-slate-300'
            }`}
          >
            <BookOpen className="w-3.5 h-3.5" />
            <span>How to Use the App (5 Steps)</span>
          </button>
        </div>

        {/* Content Body */}
        <div className="p-6 overflow-y-auto space-y-6 text-xs text-slate-700 dark:text-slate-300 leading-relaxed">
          {activeTab === 'pipeline' && (
            <div className="space-y-4">
              <div className="p-3.5 rounded-xl bg-blue-50/70 dark:bg-blue-950/30 border border-blue-200/80 dark:border-blue-800/50 space-y-1">
                <p className="font-bold text-blue-900 dark:text-blue-200">
                  Core Claim: "Same task answer, using fewer sensitive fields."
                </p>
                <p className="text-slate-600 dark:text-slate-400 leading-normal">
                  Traditional redaction removes everything, breaking the AI's ability to answer. JustEnough asks: <em>What does this specific task actually require?</em> and deterministically removes the rest.
                </p>
              </div>

              {/* Step by step cards */}
              <div className="grid grid-cols-1 gap-3">
                {/* Step 1 */}
                <div className="p-3.5 rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-50/60 dark:bg-[#0d1522] space-y-1">
                  <div className="flex items-center gap-2 text-slate-900 dark:text-white font-bold">
                    <span className="w-5 h-5 rounded-full bg-blue-100 dark:bg-blue-900/40 text-blue-700 dark:text-blue-300 flex items-center justify-center text-[10px]">1</span>
                    <span>Sensitive Entity Detection</span>
                  </div>
                  <p className="text-slate-600 dark:text-slate-400 pl-7 text-[11px]">
                    Presidio + custom Indian BFSI regex detect 16 categories: PAN cards, account numbers, IFSC codes, customer IDs, phone numbers, addresses, salaries, and transactions. Detectors <strong>never</strong> decide necessity.
                  </p>
                </div>

                {/* Step 2 */}
                <div className="p-3.5 rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-50/60 dark:bg-[#0d1522] space-y-1">
                  <div className="flex items-center gap-2 text-slate-900 dark:text-white font-bold">
                    <span className="w-5 h-5 rounded-full bg-blue-100 dark:bg-blue-900/40 text-blue-700 dark:text-blue-300 flex items-center justify-center text-[10px]">2</span>
                    <span>Zero-Leak Skeleton Generation</span>
                  </div>
                  <p className="text-slate-600 dark:text-slate-400 pl-7 text-[11px]">
                    Detected values are replaced by typed placeholders (<code className="font-mono bg-blue-100 dark:bg-blue-900/50 text-blue-800 dark:text-blue-300 px-1 rounded">[PAN]</code>, <code className="font-mono bg-blue-100 dark:bg-blue-900/50 text-blue-800 dark:text-blue-300 px-1 rounded">[ACCT]</code>) before the AI planner sees any text. The planner model <strong>never</strong> sees raw sensitive values.
                  </p>
                </div>

                {/* Step 3 */}
                <div className="p-3.5 rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-50/60 dark:bg-[#0d1522] space-y-1">
                  <div className="flex items-center gap-2 text-slate-900 dark:text-white font-bold">
                    <span className="w-5 h-5 rounded-full bg-blue-100 dark:bg-blue-900/40 text-blue-700 dark:text-blue-300 flex items-center justify-center text-[10px]">3</span>
                    <span>Task-Aware Planning (Gemini)</span>
                  </div>
                  <p className="text-slate-600 dark:text-slate-400 pl-7 text-[11px]">
                    Google Gemini proposes a structured JSON plan: for each category, whether the user's specific prompt needs it (<code className="font-mono text-emerald-600 font-bold">KEEP</code>) or not (<code className="font-mono text-rose-600 font-bold">DROP</code>, <code className="font-mono text-amber-600 font-bold">MASK_PARTIAL</code>, <code className="font-mono text-blue-600 font-bold">GENERALIZE</code>).
                  </p>
                </div>

                {/* Step 4 */}
                <div className="p-3.5 rounded-xl border border-indigo-200 dark:border-indigo-900/50 bg-indigo-50/50 dark:bg-indigo-950/20 space-y-1">
                  <div className="flex items-center gap-2 text-indigo-900 dark:text-indigo-300 font-bold">
                    <span className="w-5 h-5 rounded-full bg-indigo-100 dark:bg-indigo-900/50 text-indigo-700 dark:text-indigo-300 flex items-center justify-center text-[10px]">4</span>
                    <Sliders className="w-3.5 h-3.5 text-indigo-600" />
                    <span>Deterministic Policy Floor (Immutable Security)</span>
                  </div>
                  <p className="text-slate-600 dark:text-slate-400 pl-7 text-[11px]">
                    High-risk entities (Government IDs and Full Account Numbers) are strictly clamped to <code className="font-mono font-bold">DROP</code> or <code className="font-mono font-bold">MASK_PARTIAL</code> by deterministic Python code. AI models cannot relax this floor.
                  </p>
                </div>

                {/* Step 5 */}
                <div className="p-3.5 rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-50/60 dark:bg-[#0d1522] space-y-1">
                  <div className="flex items-center gap-2 text-slate-900 dark:text-white font-bold">
                    <span className="w-5 h-5 rounded-full bg-blue-100 dark:bg-blue-900/40 text-blue-700 dark:text-blue-300 flex items-center justify-center text-[10px]">5</span>
                    <span>Deterministic Transformation</span>
                  </div>
                  <p className="text-slate-600 dark:text-slate-400 pl-7 text-[11px]">
                    Our code replaces exact character spans in memory without LLM rewriting. Zero hallucinated numbers or altered transaction descriptions.
                  </p>
                </div>

                {/* Step 6 */}
                <div className="p-3.5 rounded-xl border border-emerald-200 dark:border-emerald-900/50 bg-emerald-50/50 dark:bg-emerald-950/20 space-y-1">
                  <div className="flex items-center gap-2 text-emerald-900 dark:text-emerald-300 font-bold">
                    <span className="w-5 h-5 rounded-full bg-emerald-100 dark:bg-emerald-900/50 text-emerald-700 dark:text-emerald-300 flex items-center justify-center text-[10px]">6</span>
                    <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
                    <span>Answer Verification Engine</span>
                  </div>
                  <p className="text-slate-600 dark:text-slate-400 pl-7 text-[11px]">
                    Executes the prompt on both original (A) and minimized data (B) to verify numerical answers within 2% tolerance, proving zero data loss for the task.
                  </p>
                </div>
              </div>
            </div>
          )}

          {activeTab === 'guide' && (
            <div className="space-y-4">
              <div className="space-y-3">
                <div className="flex items-start gap-3 p-3.5 rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-50/60 dark:bg-[#0d1522]">
                  <div className="w-6 h-6 rounded-lg bg-blue-600 text-white flex items-center justify-center font-bold text-xs shrink-0 mt-0.5">1</div>
                  <div className="space-y-0.5">
                    <p className="font-bold text-slate-900 dark:text-white">Provide Document & Task</p>
                    <p className="text-slate-600 dark:text-slate-400 text-[11px]">
                      Upload your PDF or text document (or click <strong>Load Demo Sample</strong> for an instant HDFC statement test). Choose or write the specific question you want answered.
                    </p>
                  </div>
                </div>

                <div className="flex items-start gap-3 p-3.5 rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-50/60 dark:bg-[#0d1522]">
                  <div className="w-6 h-6 rounded-lg bg-blue-600 text-white flex items-center justify-center font-bold text-xs shrink-0 mt-0.5">2</div>
                  <div className="space-y-0.5">
                    <p className="font-bold text-slate-900 dark:text-white">Run Minimization</p>
                    <p className="text-slate-600 dark:text-slate-400 text-[11px]">
                      Click <strong>Run Task Minimization</strong>. JustEnough detects sensitive values, generates the safe skeleton, plans minimal needs with Gemini, and outputs the redacted text.
                    </p>
                  </div>
                </div>

                <div className="flex items-start gap-3 p-3.5 rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-50/60 dark:bg-[#0d1522]">
                  <div className="w-6 h-6 rounded-lg bg-blue-600 text-white flex items-center justify-center font-bold text-xs shrink-0 mt-0.5">3</div>
                  <div className="space-y-0.5">
                    <p className="font-bold text-slate-900 dark:text-white">Inspect Side-by-Side Diff</p>
                    <p className="text-slate-600 dark:text-slate-400 text-[11px]">
                      Review the clean split-screen comparison: Original document with raw PII on the left, vs. safe task-minimized text on the right ready for AI upload.
                    </p>
                  </div>
                </div>

                <div className="flex items-start gap-3 p-3.5 rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-50/60 dark:bg-[#0d1522]">
                  <div className="w-6 h-6 rounded-lg bg-blue-600 text-white flex items-center justify-center font-bold text-xs shrink-0 mt-0.5">4</div>
                  <div className="space-y-0.5">
                    <p className="font-bold text-slate-900 dark:text-white">Customize Redactions Anytime (Optional)</p>
                    <p className="text-slate-600 dark:text-slate-400 text-[11px]">
                      Click <strong>Customize Redactions & Deep Dive</strong> to manually select/deselect any sensitive category. Changes update the diff in real-time!
                    </p>
                  </div>
                </div>

                <div className="flex items-start gap-3 p-3.5 rounded-xl border border-emerald-200 dark:border-emerald-900/60 bg-emerald-50/50 dark:bg-emerald-950/20">
                  <div className="w-6 h-6 rounded-lg bg-emerald-600 text-white flex items-center justify-center font-bold text-xs shrink-0 mt-0.5">5</div>
                  <div className="space-y-0.5">
                    <div className="flex items-center gap-1.5 flex-wrap">
                      <p className="font-bold text-slate-900 dark:text-white">Accept Redacted Version & Get AI Answer</p>
                      <span className="text-[10px] uppercase font-bold px-1.5 py-0.2 rounded bg-emerald-100 dark:bg-emerald-900/50 text-emerald-800 dark:text-emerald-300">Final Step</span>
                    </div>
                    <p className="text-slate-600 dark:text-slate-400 text-[11px]">
                      Once satisfied with the sanitized document, click <strong>Accept Redacted Version & Get AI Answer</strong>. The model generates your answer strictly from the sanitized document — zero PAN cards, account numbers, or personal contacts are ever exposed to the AI.
                    </p>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-3.5 border-t border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-[#0d1522] flex items-center justify-between text-xs text-slate-500 dark:text-slate-400">
          <div className="flex items-center gap-1.5 font-medium">
            <Lock className="w-3.5 h-3.5 text-blue-600" />
            <span>Honest Privacy Guarantee: Zero Raw PII Sent to LLM Planner</span>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-1.5 rounded-lg bg-blue-600 text-white font-bold hover:bg-blue-700 transition-colors cursor-pointer"
          >
            Got it
          </button>
        </div>
      </div>
    </div>
  );
}

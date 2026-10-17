import React, { useState, useEffect } from 'react';
import Navbar from './components/Navbar';
import UploadCard from './components/UploadCard';
import PipelineStepper from './components/PipelineStepper';
import MetricsSummary from './components/MetricsSummary';
import DecisionsTable from './components/DecisionsTable';
import DetectedFieldsGrid from './components/DetectedFieldsGrid';
import DiffView from './components/DiffView';
import MinimizedViewer from './components/MinimizedViewer';
import CursorEffects from './components/CursorEffects';
import SensitivityHeatmap from './components/SensitivityHeatmap';
import VerifierPanel from './components/VerifierPanel';
import UnsureReview from './components/UnsureReview';
import AboutHelpModal from './components/AboutHelpModal';
import RedactionSelector from './components/RedactionSelector';
import TaskAnswerCard from './components/TaskAnswerCard';
import { checkHealth, analyzeDocument, getTaskAnswer } from './api';
import {
  ShieldCheck,
  Cpu,
  Lock,
  Sparkles,
  FileSearch,
  Sliders,
  CheckCircle2,
  FileCheck,
  AlertCircle,
  Eye,
  ChevronDown,
  ChevronUp,
  HelpCircle,
  Loader2,
} from 'lucide-react';

const DEMO_STATEMENT_CONTENT = `================================================================================
                       HDFC BANK - ACCOUNT STATEMENT                  
================================================================================
Account Holder Name: Priya Nair
Permanent Acct No:   ABCDE1234F (PAN)
Account Number:      50100234891024
Customer ID:         CUST992014
Registered Mobile:   +91-9876543210
Registered Email:    priya.nair@example.com
Communication Addr:  Flat 301, Palm Meadows, Whitefield, Bengaluru 560066
Branch:              Whitefield Branch | IFSC: HDFC0001234
Statement Period:    01-Oct-2026 to 15-Oct-2026
--------------------------------------------------------------------------------
Date         Description                        Debit (INR)   Credit (INR)    Balance (INR)
--------------------------------------------------------------------------------
2026-10-01   Salary Credit - Infosys Ltd                  -      125000.00       145000.00
2026-10-03   UPI/Swiggy Bangalore/dinner             680.00              -       144320.00
             Merchant: Swiggy Bangalore
2026-10-05   UPI/Zomato Online/lunch                 420.00              -       143900.00
             Merchant: Zomato
2026-10-07   Transfer to Rohan Verma                2500.00              -       141400.00
             Narration: Rent Split
2026-10-10   Apollo Pharmacy Indiranagar             850.00              -       140550.00
             Merchant: Apollo Pharmacy
2026-10-12   Uber India Systems Pvt Ltd              340.00              -       140210.00
             Merchant: Uber
--------------------------------------------------------------------------------
Closing Balance:                                                         140210.00
================================================================================
END OF STATEMENT - Synthetic test document generated for JustEnough demo.`;

// Client-side real-time deterministic transformation
function computeMinimizedText(rawText, detectedFields, plan) {
  if (!rawText || !detectedFields || detectedFields.length === 0 || !plan) return rawText || '';

  // Extract valid field spans and sort descending by start position to preserve offsets
  const sorted = [...detectedFields]
    .map((f) => {
      const start = f.location?.start_char ?? f.location?.start;
      const end = f.location?.end_char ?? f.location?.end;
      return {
        ...f,
        start,
        end,
      };
    })
    .filter((f) => typeof f.start === 'number' && typeof f.end === 'number' && f.start >= 0 && f.end <= rawText.length && f.end > f.start)
    .sort((a, b) => b.start - a.start);

  let transformed = rawText;
  let lastStart = Infinity;

  for (const field of sorted) {
    const action = plan[field.category]?.action || 'DROP';
    const start = field.start;
    const end = field.end;

    if (end > lastStart) continue; // skip overlapping spans
    lastStart = start;

    let replacement = '';
    if (action === 'KEEP') {
      replacement = rawText.slice(start, end);
    } else if (action === 'DROP') {
      replacement = `[REDACTED:${(field.category || 'PII').toUpperCase()}]`;
    } else if (action === 'MASK_PARTIAL') {
      const slice = rawText.slice(start, end);
      const clean = slice.replace(/[\s-]/g, '');
      const trailer = clean.length >= 4 ? clean.slice(-4) : clean;
      replacement = `XXXX-XXXX-${trailer}`;
    } else if (action === 'GENERALIZE') {
      replacement = `[GENERALIZED:${(field.category || 'PII').toUpperCase()}]`;
    } else if (action === 'PSEUDONYMIZE') {
      replacement = `[${(field.category || 'PII').toUpperCase()}_PSEUDO]`;
    } else {
      replacement = `[REDACTED:${(field.category || 'PII').toUpperCase()}]`;
    }

    transformed = transformed.slice(0, start) + replacement + transformed.slice(end);
  }

  return transformed;
}

export default function App() {
  const [backendStatus, setBackendStatus] = useState('checking');
  const [liveMode, setLiveMode] = useState(false);
  const [file, setFile] = useState(null);
  const [task, setTask] = useState('Calculate my total dining and food expenses');
  const [originalText, setOriginalText] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [pipelineStep, setPipelineStep] = useState(0);
  const [isDone, setIsDone] = useState(false);
  const [result, setResult] = useState(null);
  const [initialPlan, setInitialPlan] = useState(null);
  const [taskAnswer, setTaskAnswer] = useState(null);
  const [isAnswering, setIsAnswering] = useState(false);
  const [activeTab, setActiveTab] = useState('decisions');
  const [toast, setToast] = useState(null);
  const [showHelpModal, setShowHelpModal] = useState(false);
  const [showAdvancedInspector, setShowAdvancedInspector] = useState(false);
  const [theme, setTheme] = useState(() => {
    return localStorage.getItem('justenough_theme') || 'light';
  });

  // Sync theme with HTML root class for Tailwind & CSS dark mode
  useEffect(() => {
    const root = document.documentElement;
    if (theme === 'dark') {
      root.classList.add('dark');
    } else {
      root.classList.remove('dark');
    }
    localStorage.setItem('justenough_theme', theme);
  }, [theme]);

  const toggleTheme = () => {
    setTheme((prev) => (prev === 'dark' ? 'light' : 'dark'));
  };

  // Check backend health on mount
  useEffect(() => {
    checkHealth().then((res) => {
      if (res && res.status === 'ok') {
        setBackendStatus('online');
      } else {
        setBackendStatus('offline');
      }
    });
  }, []);

  // Update originalText when file changes
  useEffect(() => {
    if (!file) {
      setOriginalText('');
      return;
    }
    const reader = new FileReader();
    reader.onload = (e) => {
      setOriginalText(e.target.result || '');
    };
    reader.readAsText(file);
  }, [file]);

  // Keyboard shortcut: Ctrl + Enter to run
  useEffect(() => {
    const handleKeyDown = (e) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
        if (file && task.trim().length >= 3 && !isLoading) {
          handleRun();
        }
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [file, task, isLoading, liveMode]);

  const showToast = (message, type = 'info') => {
    setToast({ message, type });
    setTimeout(() => setToast(null), 4000);
  };

  const handleLoadDemo = () => {
    const demoBlob = new Blob([DEMO_STATEMENT_CONTENT], { type: 'text/plain' });
    const demoFile = new File([demoBlob], 'demo_sample_statement.txt', {
      type: 'text/plain',
    });
    setFile(demoFile);
    setOriginalText(DEMO_STATEMENT_CONTENT);
    setTask('Calculate my total dining and food expenses');
    setTaskAnswer(null);
    showToast('Loaded synthetic demo bank statement', 'success');
  };

  const handleRun = async () => {
    if (!file || !task.trim()) return;

    setIsLoading(true);
    setIsDone(false);
    setPipelineStep(0);

    const interval = setInterval(() => {
      setPipelineStep((prev) => (prev < 4 ? prev + 1 : prev));
    }, 280);

    try {
      const data = await analyzeDocument({ file, task, live: liveMode });
      clearInterval(interval);
      setPipelineStep(4);
      setIsDone(true);
      setResult(data);
      setInitialPlan(data.plan ? JSON.parse(JSON.stringify(data.plan)) : null);
      setTaskAnswer(null);
      setIsAnswering(false);
      setShowAdvancedInspector(false); // primary focus is Side-by-Side Diff

      setTimeout(() => {
        document.getElementById('results-dashboard')?.scrollIntoView({ behavior: 'smooth' });
      }, 120);
      showToast(
        `Minimization complete! ${Math.round(data.metrics.sensitive_field_reduction_pct)}% privacy reduction`,
        'success'
      );
    } catch (err) {
      clearInterval(interval);
      showToast(`Error: ${err.message}`, 'error');
    } finally {
      setIsLoading(false);
    }
  };

  // Toggle single category between REDACTED (DROP) and KEPT (KEEP) with instant client-side update
  const handleToggleCategory = (cat, newAction) => {
    if (!result) return;
    const newPlan = {
      ...result.plan,
      [cat]: {
        ...result.plan[cat],
        action: newAction,
        reason: newAction === 'KEEP' ? 'User override: marked to keep for task' : 'User override: marked to redact',
      },
    };

    const newMinimized = computeMinimizedText(originalText, result.detected_fields, newPlan);

    let kept = 0;
    let dropped = 0;
    for (const f of result.detected_fields || []) {
      const act = newPlan[f.category]?.action || 'DROP';
      if (act === 'KEEP') kept++;
      else dropped++;
    }
    const total = (result.detected_fields || []).length || 1;
    const pct = Math.round((dropped / total) * 100);

    setResult({
      ...result,
      plan: newPlan,
      minimized_text: newMinimized,
      metrics: {
        ...result.metrics,
        fields_kept: kept,
        fields_dropped_or_masked: dropped,
        sensitive_field_reduction_pct: pct,
      },
    });
    setTaskAnswer(null); // reset answer if redaction plan changed
    showToast(`${cat} is now ${newAction === 'KEEP' ? 'KEPT' : 'REDACTED'}`, 'info');
  };

  // Get AI Answer strictly on the accepted minimized text
  const handleGetAnswer = async () => {
    if (!result || !result.minimized_text) return;
    setIsAnswering(true);
    try {
      const answerData = await getTaskAnswer({
        task,
        minimizedText: result.minimized_text,
        live: liveMode,
      });
      setTaskAnswer(answerData);
      setTimeout(() => {
        document.getElementById('task-answer-card')?.scrollIntoView({ behavior: 'smooth' });
      }, 120);
      showToast('AI answer generated using minimized data only', 'success');
    } catch (err) {
      showToast(`Answer query failed: ${err.message}`, 'error');
    } finally {
      setIsAnswering(false);
    }
  };

  // Batch set all categories
  const handleSetAll = (action) => {
    if (!result) return;
    const newPlan = {};
    for (const [cat, val] of Object.entries(result.plan)) {
      newPlan[cat] = {
        ...val,
        action,
        reason: `User set all to ${action}`,
      };
    }
    const newMinimized = computeMinimizedText(originalText, result.detected_fields, newPlan);
    const total = (result.detected_fields || []).length || 1;
    const dropped = action === 'KEEP' ? 0 : total;
    const kept = action === 'KEEP' ? total : 0;
    const pct = action === 'KEEP' ? 0 : 100;

    setResult({
      ...result,
      plan: newPlan,
      minimized_text: newMinimized,
      metrics: {
        ...result.metrics,
        fields_kept: kept,
        fields_dropped_or_masked: dropped,
        sensitive_field_reduction_pct: pct,
      },
    });

    showToast(`All categories set to ${action === 'KEEP' ? 'KEPT' : 'REDACTED'}`, 'info');
  };

  // Reset to original Gemini plan
  const handleResetPlan = () => {
    if (!result || !initialPlan) return;
    const restoredPlan = JSON.parse(JSON.stringify(initialPlan));
    const newMinimized = computeMinimizedText(originalText, result.detected_fields, restoredPlan);
    let kept = 0;
    let dropped = 0;
    for (const f of result.detected_fields || []) {
      const act = restoredPlan[f.category]?.action || 'DROP';
      if (act === 'KEEP') kept++;
      else dropped++;
    }
    const total = (result.detected_fields || []).length || 1;
    const pct = Math.round((dropped / total) * 100);

    setResult({
      ...result,
      plan: restoredPlan,
      minimized_text: newMinimized,
      metrics: {
        ...result.metrics,
        fields_kept: kept,
        fields_dropped_or_masked: dropped,
        sensitive_field_reduction_pct: pct,
      },
    });
    showToast('Restored Gemini recommended plan', 'info');
  };

  const handlePlanOverride = (newOverrides) => {
    if (!result) return;
    const updatedPlan = { ...result.plan };
    for (const [cat, action] of Object.entries(newOverrides)) {
      if (updatedPlan[cat]) {
        updatedPlan[cat] = {
          ...updatedPlan[cat],
          action,
          reason: `Human review override: set to ${action}`,
        };
      }
    }
    const newMinimized = computeMinimizedText(originalText, result.detected_fields, updatedPlan);
    setResult({
      ...result,
      plan: updatedPlan,
      minimized_text: newMinimized,
    });
    showToast(`Decision updated for ${Object.keys(newOverrides).join(', ')}`, 'info');
  };

  return (
    <div className="app-container min-h-screen bg-slate-50 text-slate-900 flex flex-col font-inter bg-grid antialiased relative">
      {/* Interactive Cursor Spotlight & Click Ripple Shockwaves */}
      <CursorEffects />

      {/* Navigation */}
      <Navbar
        backendStatus={backendStatus}
        liveMode={liveMode}
        setLiveMode={setLiveMode}
        theme={theme}
        toggleTheme={toggleTheme}
        onOpenHelp={() => setShowHelpModal(true)}
      />

      {/* About & Help Modal */}
      <AboutHelpModal
        isOpen={showHelpModal}
        onClose={() => setShowHelpModal(false)}
      />

      {/* Main Content Area */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8 relative z-10">
        {/* Hero Section */}
        <div className="text-center space-y-3 max-w-3xl mx-auto">
          <button
            type="button"
            onClick={() => setShowHelpModal(true)}
            className="inline-flex items-center gap-2 px-3.5 py-1 rounded-full bg-blue-50 dark:bg-blue-900/30 border border-blue-200 dark:border-blue-800 text-blue-700 dark:text-blue-300 text-xs font-bold shadow-xs transition-transform duration-200 hover:scale-105 cursor-pointer"
          >
            <Sparkles className="w-3.5 h-3.5 text-blue-600 dark:text-blue-400 animate-pulse" />
            <span>Task-Aware Data Minimization Layer • How It Works</span>
          </button>
          <h1 className="text-3xl sm:text-4xl lg:text-5xl font-black text-slate-900 dark:text-white tracking-tight">
            Same Task Answer.{' '}
            <span className="gradient-text">Fewer Sensitive Fields.</span>
          </h1>
          <p className="text-sm sm:text-base text-slate-600 dark:text-slate-400 max-w-2xl mx-auto leading-relaxed font-medium">
            Upload sensitive documents to AI without leaking identities. JustEnough
            detects PII, plans minimal task requirements, and enforces hard policy floors.
          </p>
        </div>

        {/* Top Configuration & Pipeline Section */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
          {/* Left Column: Upload & Task Card */}
          <div className="lg:col-span-7 space-y-5">
            <UploadCard
              file={file}
              setFile={setFile}
              task={task}
              setTask={setTask}
              onRun={handleRun}
              isLoading={isLoading}
              onLoadDemo={handleLoadDemo}
            />
          </div>

          {/* Right Column: Interactive Pipeline Stepper & Architecture Guarantee */}
          <div className="lg:col-span-5 space-y-5">
            <PipelineStepper
              currentStep={pipelineStep}
              isDone={isDone}
              isLoading={isLoading}
            />

            {/* Architecture Guarantees Card */}
            <div className="glass-card interactive-card p-5 space-y-3.5">
              <div className="flex items-center justify-between pb-2 border-b border-slate-100 dark:border-slate-800">
                <div className="flex items-center gap-2 text-slate-800 dark:text-slate-200 text-xs font-bold">
                  <Lock className="w-3.5 h-3.5 text-blue-600 dark:text-blue-400" />
                  <span>Zero-Raw-Leakage Architecture</span>
                </div>
                <button
                  type="button"
                  onClick={() => setShowHelpModal(true)}
                  className="text-[11px] text-blue-600 dark:text-blue-400 hover:underline font-semibold flex items-center gap-1 cursor-pointer"
                >
                  <HelpCircle className="w-3 h-3" />
                  <span>Learn more</span>
                </button>
              </div>

              <div className="space-y-2.5">
                <div className="p-3 rounded-xl bg-blue-50/70 dark:bg-blue-950/20 border border-blue-200/80 dark:border-blue-900/50 space-y-1 interactive-card group cursor-default">
                  <div className="flex items-center gap-1.5 text-blue-800 dark:text-blue-300 text-xs font-bold">
                    <ShieldCheck className="w-3.5 h-3.5 text-blue-600 dark:text-blue-400 transition-transform duration-200 group-hover:scale-115" />
                    <span>Zero Raw Sensitive Values to AI</span>
                  </div>
                  <p className="text-[11px] text-slate-600 dark:text-slate-400 leading-relaxed font-medium">
                    The Gemini planner receives typed skeleton placeholders (<code className="font-mono bg-blue-100 dark:bg-blue-900/40 text-blue-900 dark:text-blue-200 px-1 rounded">[PAN]</code>, <code className="font-mono bg-blue-100 dark:bg-blue-900/40 text-blue-900 dark:text-blue-200 px-1 rounded">[PHONE]</code>), never raw PII.
                  </p>
                </div>

                <div className="p-3 rounded-xl bg-indigo-50/70 dark:bg-indigo-950/20 border border-indigo-200/80 dark:border-indigo-900/50 space-y-1 interactive-card group cursor-default">
                  <div className="flex items-center gap-1.5 text-indigo-800 dark:text-indigo-300 text-xs font-bold">
                    <Sliders className="w-3.5 h-3.5 text-indigo-600 dark:text-indigo-400 transition-transform duration-200 group-hover:scale-115" />
                    <span>Deterministic Policy Floor</span>
                  </div>
                  <p className="text-[11px] text-slate-600 dark:text-slate-400 leading-relaxed font-medium">
                    Govt IDs (PAN) and account numbers default to DROP/MASK by hard code — models cannot relax it.
                  </p>
                </div>

                <div className="p-3 rounded-xl bg-emerald-50/70 dark:bg-emerald-950/20 border border-emerald-200/80 dark:border-emerald-900/50 space-y-1 interactive-card group cursor-default">
                  <div className="flex items-center gap-1.5 text-emerald-800 dark:text-emerald-300 text-xs font-bold">
                    <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600 dark:text-emerald-400 transition-transform duration-200 group-hover:scale-115" />
                    <span>Answer Verification Engine</span>
                  </div>
                  <p className="text-[11px] text-slate-600 dark:text-slate-400 leading-relaxed font-medium">
                    Runs the task on both original and minimized data to verify answer preservation within 2% tolerance.
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Results Area: Diff First + Customization Option */}
        {result && (
          <div id="results-dashboard" className="glass-card interactive-card p-5 sm:p-7 space-y-6 animate-fade-in-up">
            {/* Top Preservation Summary Bar */}
            <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 p-4 rounded-xl bg-blue-50/60 dark:bg-blue-950/20 border border-blue-200/80 dark:border-blue-900/50">
              <div className="space-y-1">
                <div className="flex items-center gap-2">
                  <span className="text-xs font-bold text-blue-700 dark:text-blue-300 uppercase tracking-wider bg-blue-100 dark:bg-blue-900/50 px-2.5 py-0.5 rounded-full">
                    Minimization Complete
                  </span>
                  <span className="text-xs font-semibold text-emerald-700 dark:text-emerald-400 flex items-center gap-1">
                    <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
                    Preserved for AI
                  </span>
                </div>
                <h3 className="text-lg font-black text-slate-900 dark:text-white tracking-tight">
                  {Math.round(result.metrics?.sensitive_field_reduction_pct || 0)}% of Sensitive Fields Removed
                </h3>
                <p className="text-xs text-slate-600 dark:text-slate-400">
                  {result.metrics?.fields_dropped_or_masked} of {result.metrics?.total_fields_detected} fields redacted • {result.metrics?.fields_kept} task-essential fields kept
                </p>
              </div>

              {/* Action: Customize Redactions Button */}
              <button
                type="button"
                onClick={() => setShowAdvancedInspector(!showAdvancedInspector)}
                className={`flex items-center gap-2 px-4 py-2.5 rounded-xl font-bold text-xs transition-all active:scale-95 cursor-pointer shadow-sm ${
                  showAdvancedInspector
                    ? 'bg-blue-600 text-white shadow-blue-500/20'
                    : 'bg-white dark:bg-[#0d1522] hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-800 dark:text-slate-200 border border-slate-300 dark:border-slate-700'
                }`}
              >
                <Sliders className="w-3.5 h-3.5 text-blue-500" />
                <span>
                  {showAdvancedInspector
                    ? 'Hide Redaction Controls'
                    : 'Customize Redactions (Select / Deselect Fields)'}
                </span>
                {showAdvancedInspector ? (
                  <ChevronUp className="w-3.5 h-3.5" />
                ) : (
                  <ChevronDown className="w-3.5 h-3.5" />
                )}
              </button>
            </div>

            {/* PRIMARY VIEW: Side-by-Side Diff */}
            <DiffView
              originalText={originalText}
              minimizedText={result.minimized_text}
              plan={result.plan}
              detectedFields={result.detected_fields}
            />

            {/* Accept Redacted Version & Get AI Answer Action Bar */}
            <div className="p-4 sm:p-5 rounded-2xl bg-gradient-to-r from-blue-50/90 via-indigo-50/70 to-emerald-50/80 dark:from-blue-950/40 dark:via-indigo-950/30 dark:to-emerald-950/30 border border-blue-200 dark:border-blue-800/80 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 shadow-sm animate-fade-in-up">
              <div className="space-y-1">
                <div className="flex items-center gap-2">
                  <span className="text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 rounded-full bg-blue-100 dark:bg-blue-900/50 text-blue-700 dark:text-blue-300 border border-blue-200 dark:border-blue-700">
                    Next Step
                  </span>
                  <span className="text-xs font-bold text-slate-800 dark:text-slate-200">
                    Satisfied with the sanitized document?
                  </span>
                </div>
                <p className="text-xs text-slate-600 dark:text-slate-400">
                  Accept this redacted version to query the AI with zero raw PII exposure.
                </p>
              </div>

              <button
                type="button"
                id="accept-and-answer-btn"
                onClick={handleGetAnswer}
                disabled={isAnswering}
                className="w-full sm:w-auto px-6 py-3 rounded-xl bg-blue-600 hover:bg-blue-700 active:scale-95 text-white font-bold text-xs shadow-md shadow-blue-500/20 hover:shadow-blue-500/35 transition-all flex items-center justify-center gap-2 cursor-pointer disabled:opacity-50"
              >
                {isAnswering ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin text-white" />
                    <span>Querying AI Model…</span>
                  </>
                ) : (
                  <>
                    <CheckCircle2 className="w-4 h-4 text-white" />
                    <span>Accept Redacted Version & Get AI Answer</span>
                  </>
                )}
              </button>
            </div>

            {/* AI Task Answer Display Card */}
            <TaskAnswerCard
              answer={taskAnswer}
              task={task}
              isLoading={isAnswering}
              onRegenerate={handleGetAnswer}
              liveMode={liveMode}
            />

            {/* EXPANDABLE INSPECTOR: Redaction Customizer + All Audit Tabs */}
            {showAdvancedInspector && (
              <div className="pt-4 border-t border-slate-200 dark:border-slate-800 space-y-6 animate-fade-in-up">
                {/* 1. Interactive Redaction Selector */}
                <RedactionSelector
                  plan={result.plan}
                  detectedFields={result.detected_fields}
                  onToggleCategory={handleToggleCategory}
                  onSetAll={handleSetAll}
                  onResetPlan={handleResetPlan}
                />

                {/* 2. Scorecard Gauge & Core Metrics */}
                <MetricsSummary
                  metrics={result.metrics}
                  policyViolations={result.policy_violations}
                />

                {/* Human-in-the-Loop Review for Ambiguous Categories */}
                {result.unsure_categories && result.unsure_categories.length > 0 && (
                  <UnsureReview
                    unsureCategories={result.unsure_categories}
                    plan={result.plan}
                    onOverride={handlePlanOverride}
                  />
                )}

                {/* 3. Detailed Audit Tabs */}
                <div className="border-b border-slate-200 dark:border-slate-800 pb-3">
                  <div className="flex items-center gap-2 sm:gap-3 overflow-x-auto no-scrollbar">
                    {[
                      { id: 'decisions', label: '1. Decisions Table', badge: Object.keys(result.plan || {}).length, icon: Sliders },
                      { id: 'fields', label: '2. Detected Fields', badge: result.detected_fields?.length || 0, icon: FileSearch },
                      { id: 'heatmap', label: '3. Sensitivity Heatmap', icon: Eye },
                      { id: 'minimized', label: '4. Minimized Document', icon: FileCheck },
                      { id: 'verifier', label: '5. Answer Verifier', badge: 'A vs B', icon: Sparkles },
                    ].map((tab) => {
                      const Icon = tab.icon;
                      const isActive = activeTab === tab.id;
                      return (
                        <button
                          key={tab.id}
                          type="button"
                          onClick={() => setActiveTab(tab.id)}
                          className={`flex items-center gap-2 whitespace-nowrap px-4 py-2.5 rounded-xl font-bold text-xs transition-all duration-150 active:scale-95 cursor-pointer ${
                            isActive
                              ? 'bg-blue-600 text-white shadow-sm shadow-blue-500/25 active'
                              : 'bg-white dark:bg-[#0d1522] hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-700 dark:text-slate-300 border border-slate-200 dark:border-slate-800'
                          }`}
                        >
                          <Icon className="w-3.5 h-3.5 shrink-0" />
                          <span>{tab.label}</span>
                          {tab.badge !== undefined && (
                            <span
                              className={`text-[10px] font-mono px-2 py-0.5 rounded-full font-bold ${
                                isActive
                                  ? 'bg-blue-500/80 text-white'
                                  : 'bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 border border-slate-200 dark:border-slate-700'
                              }`}
                            >
                              {tab.badge}
                            </span>
                          )}
                        </button>
                      );
                    })}
                  </div>
                </div>

                {/* Tab Content Panels */}
                <div className="pt-2 animate-fade-in-up" key={activeTab}>
                  {activeTab === 'decisions' && (
                    <DecisionsTable
                      plan={result.plan}
                      policyViolations={result.policy_violations}
                    />
                  )}

                  {activeTab === 'fields' && (
                    <DetectedFieldsGrid fields={result.detected_fields} />
                  )}

                  {activeTab === 'heatmap' && (
                    <SensitivityHeatmap
                      originalText={originalText}
                      detectedFields={result.detected_fields}
                    />
                  )}

                  {activeTab === 'minimized' && (
                    <MinimizedViewer
                      minimizedText={result.minimized_text}
                      task={result.task}
                    />
                  )}

                  {activeTab === 'verifier' && (
                    <VerifierPanel
                      task={result.task}
                      originalText={originalText}
                      minimizedText={result.minimized_text}
                      liveMode={liveMode}
                      taskOutputSchema={result.task_output_schema}
                    />
                  )}
                </div>
              </div>
            )}
          </div>
        )}
      </main>

      {/* Toast Notification */}
      {toast && (
        <div className="fixed bottom-6 right-6 z-50 animate-slide-up">
          <div
            className={`px-4 py-3 rounded-xl shadow-lg text-xs font-semibold flex items-center gap-2.5 border ${
              toast.type === 'success'
                ? 'bg-white text-emerald-800 border-emerald-300 shadow-emerald-500/10'
                : toast.type === 'error'
                ? 'bg-white text-rose-800 border-rose-300 shadow-rose-500/10'
                : 'bg-white text-slate-800 border-slate-300'
            }`}
          >
            {toast.type === 'success' ? (
              <CheckCircle2 className="w-4 h-4 text-emerald-600" />
            ) : (
              <AlertCircle className="w-4 h-4 text-rose-600" />
            )}
            <span>{toast.message}</span>
          </div>
        </div>
      )}

      {/* Footer */}
      <footer className="border-t border-slate-200 dark:border-slate-800 bg-white dark:bg-black py-6 mt-12">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col sm:flex-row items-center justify-between gap-3 text-xs text-slate-500 dark:text-slate-400">
          <div className="flex items-center gap-2">
            <span className="font-bold text-slate-800 dark:text-slate-200">JustEnough</span>
            <span>•</span>
            <span>Task-Aware Data Minimization for AI Uploads</span>
            <span>•</span>
            <button
              type="button"
              onClick={() => setShowHelpModal(true)}
              className="text-blue-600 dark:text-blue-400 hover:underline font-semibold cursor-pointer"
            >
              How It Works & Help
            </button>
          </div>
          <div className="font-medium">
            BFSI Intelligent Privacy & Compliance Layer • Powered by Google Gemini
          </div>
        </div>
      </footer>
    </div>
  );
}

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
import ChatPanel from './components/ChatPanel';
import { checkHealth, analyzeDocument } from './api';
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
  const [activeTab, setActiveTab] = useState('decisions');
  const [toast, setToast] = useState(null);

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
    setResult({
      ...result,
      plan: updatedPlan,
    });
    showToast(`Decision updated for ${Object.keys(newOverrides).join(', ')}`, 'info');
  };

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900 flex flex-col font-inter bg-grid antialiased relative">
      {/* Interactive Cursor Spotlight & Click Ripple Shockwaves */}
      <CursorEffects />

      {/* Navigation */}
      <Navbar
        backendStatus={backendStatus}
        liveMode={liveMode}
        setLiveMode={setLiveMode}
      />

      {/* Main Content Area */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8 relative z-10">
        {/* Hero Section */}
        <div className="text-center space-y-3 max-w-3xl mx-auto">
          <div className="inline-flex items-center gap-2 px-3.5 py-1 rounded-full bg-blue-50 border border-blue-200 text-blue-700 text-xs font-bold shadow-xs transition-transform duration-200 hover:scale-105 cursor-default">
            <Sparkles className="w-3.5 h-3.5 text-blue-600 animate-pulse" />
            <span>Task-Aware Data Minimization Layer</span>
          </div>
          <h1 className="text-3xl sm:text-4xl lg:text-5xl font-black text-slate-900 tracking-tight">
            Same Task Answer.{' '}
            <span className="gradient-text">Fewer Sensitive Fields.</span>
          </h1>
          <p className="text-sm sm:text-base text-slate-600 max-w-2xl mx-auto leading-relaxed font-medium">
            Upload sensitive documents to AI without leaking identities. JustEnough
            detects PII, plans minimal task requirements, and enforces hard policy floors.
          </p>
        </div>

        {/* Top Configuration & Pipeline Section */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
          {/* Left / Main Column: Upload & Task Card (7 cols) */}
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

          {/* Right Column: Pipeline Stepper & Privacy Engine Architecture (5 cols) */}
          <div className="lg:col-span-5 space-y-4">
            <PipelineStepper currentStep={pipelineStep} isDone={isDone} />

            {/* 3 Privacy Engine Architecture Highlights */}
            <div className="glass-card interactive-card p-5 space-y-3">
              <div className="flex items-center gap-2 text-xs font-bold text-slate-900 pb-1 border-b border-slate-100">
                <ShieldCheck className="w-4 h-4 text-blue-600" />
                <span>Zero-Raw-Leakage Architecture</span>
              </div>

              <div className="space-y-2.5">
                <div className="p-3 rounded-xl bg-blue-50/70 border border-blue-200/80 space-y-1 interactive-card group cursor-default">
                  <div className="flex items-center gap-1.5 text-blue-800 text-xs font-bold">
                    <Lock className="w-3.5 h-3.5 text-blue-600 transition-transform duration-200 group-hover:scale-115" />
                    <span>Zero Raw Sensitive Values to AI</span>
                  </div>
                  <p className="text-[11px] text-slate-600 leading-relaxed font-medium">
                    The Gemini planner receives typed skeleton placeholders (<code className="font-mono bg-blue-100 text-blue-900 px-1 rounded">[PAN]</code>, <code className="font-mono bg-blue-100 text-blue-900 px-1 rounded">[PHONE]</code>), never raw PII.
                  </p>
                </div>

                <div className="p-3 rounded-xl bg-indigo-50/70 border border-indigo-200/80 space-y-1 interactive-card group cursor-default">
                  <div className="flex items-center gap-1.5 text-indigo-800 text-xs font-bold">
                    <Sliders className="w-3.5 h-3.5 text-indigo-600 transition-transform duration-200 group-hover:scale-115" />
                    <span>Deterministic Policy Floor</span>
                  </div>
                  <p className="text-[11px] text-slate-600 leading-relaxed font-medium">
                    Govt IDs (PAN) and account numbers default to DROP/MASK by hard code — models cannot relax it.
                  </p>
                </div>

                <div className="p-3 rounded-xl bg-emerald-50/70 border border-emerald-200/80 space-y-1 interactive-card group cursor-default">
                  <div className="flex items-center gap-1.5 text-emerald-800 text-xs font-bold">
                    <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600 transition-transform duration-200 group-hover:scale-115" />
                    <span>Answer Verification Engine</span>
                  </div>
                  <p className="text-[11px] text-slate-600 leading-relaxed font-medium">
                    Runs the task on both original and minimized data to verify answer preservation within 2% tolerance.
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Full-Width Results & Intelligence Dashboard (Shifted Down for Clarity) */}
        {result && (
          <div id="results-dashboard" className="glass-card interactive-card p-6 sm:p-8 space-y-6 animate-fade-in-up">
            {/* Scorecard Gauge & Core Metrics */}
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

            {/* Spacious Full-Width 6-Tabs Navigation */}
            <div className="border-b border-slate-200 pb-3">
              <div className="flex items-center gap-2 sm:gap-3 overflow-x-auto no-scrollbar">
                {[
                  { id: 'decisions', label: '1. Decisions Table', badge: Object.keys(result.plan || {}).length, icon: Sliders },
                  { id: 'fields', label: '2. Detected Fields', badge: result.detected_fields?.length || 0, icon: FileSearch },
                  { id: 'heatmap', label: '3. Sensitivity Heatmap', icon: Eye },
                  { id: 'diff', label: '4. Side-by-Side Diff', icon: Cpu },
                  { id: 'minimized', label: '5. Minimized Document', icon: FileCheck },
                  { id: 'verifier', label: '6. Answer Verifier', badge: 'A vs B', icon: Sparkles },
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
                          : 'bg-white hover:bg-slate-100 text-slate-700 border border-slate-200'
                      }`}
                    >
                      <Icon className="w-3.5 h-3.5 shrink-0" />
                      <span>{tab.label}</span>
                      {tab.badge !== undefined && (
                        <span
                          className={`text-[10px] font-mono px-2 py-0.5 rounded-full font-bold ${
                            isActive
                              ? 'bg-blue-500/80 text-white'
                              : 'bg-slate-100 text-slate-700 border border-slate-200'
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

            {/* Tab Content Panels (Full Width, Spacious & Readable) */}
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

              {activeTab === 'diff' && (
                <DiffView
                  originalText={originalText}
                  minimizedText={result.minimized_text}
                  plan={result.plan}
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
      <footer className="border-t border-slate-200 bg-white py-6 mt-12">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col sm:flex-row items-center justify-between gap-3 text-xs text-slate-500">
          <div className="flex items-center gap-2">
            <span className="font-bold text-slate-800">JustEnough</span>
            <span>•</span>
            <span>Task-Aware Data Minimization for AI Uploads</span>
          </div>
          <div className="font-medium">
            BFSI Intelligent Privacy & Compliance Layer • Powered by Google Gemini
          </div>
        </div>
      </footer>
      {/* Floating Chat Assistant (Queries Minimized Document Only) */}
      {result && result.minimized_text && (
        <ChatPanel
          minimizedText={result.minimized_text}
          liveMode={liveMode}
        />
      )}
    </div>
  );
}

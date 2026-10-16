import React, { useRef, useState } from 'react';
import {
  UploadCloud,
  FileText,
  X,
  Sparkles,
  ArrowRight,
  ShieldAlert,
  FileCode2,
  CheckCircle2,
} from 'lucide-react';

const SUGGESTIONS = [
  { label: 'Food & Dining Expenses', text: 'Calculate my total dining and food expenses' },
  { label: 'Salary & Closing Balance', text: 'Verify if my monthly salary was credited and check my closing balance' },
  { label: 'UPI P2P Transfers', text: 'List all UPI money transfers made to individual friends' },
  { label: 'Pharmacy & Medical', text: 'Summarize all medical and pharmacy transactions' },
];

export default function UploadCard({
  file,
  setFile,
  task,
  setTask,
  onRun,
  isLoading,
  onLoadDemo,
}) {
  const [isDragging, setIsDragging] = useState(false);
  const fileInputRef = useRef(null);

  const handleDragOver = (e) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = () => {
    setIsDragging(false);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      setFile(e.dataTransfer.files[0]);
    }
  };

  const handleFileChange = (e) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0]);
    }
  };

  const formatFileSize = (bytes) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  const canSubmit = Boolean(file && task.trim().length >= 3 && !isLoading);

  return (
    <div className="glass-card interactive-card p-5 sm:p-6 space-y-6">
      {/* Card Header */}
      <div className="flex items-center justify-between pb-3 border-b border-slate-100">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-blue-50 border border-blue-200 flex items-center justify-center text-blue-600">
            <UploadCloud className="w-4 h-4" />
          </div>
          <div>
            <h2 className="text-sm font-bold text-slate-900 uppercase tracking-wider">
              Input Document & Task
            </h2>
            <p className="text-xs text-slate-500">
              Deterministic detection & task-specific minimization
            </p>
          </div>
        </div>

        {/* 1-click Demo Button */}
        <button
          type="button"
          onClick={onLoadDemo}
          className="text-xs font-semibold px-3 py-1.5 rounded-lg bg-blue-50 hover:bg-blue-100 text-blue-700 border border-blue-200 transition-all flex items-center gap-1.5 shadow-xs active:scale-95 group hover:-translate-y-0.5"
          title="Load synthetic HDFC statement demo file"
        >
          <Sparkles className="w-3.5 h-3.5 text-blue-600 transition-transform duration-300 group-hover:rotate-12 group-hover:scale-110" />
          <span>Load Demo Sample</span>
        </button>
      </div>

      {/* 1. Document Upload Dropzone */}
      <div className="space-y-2">
        <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider">
          1. Upload Document (PDF or TXT)
        </label>

        {!file ? (
          <div
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
            onClick={() => fileInputRef.current?.click()}
            className={`border-2 border-dashed rounded-xl p-6 text-center cursor-pointer transition-all duration-200 ${
              isDragging
                ? 'border-blue-500 bg-blue-50/70 scale-[0.99] shadow-sm'
                : 'border-slate-300 hover:border-blue-400 bg-slate-50/50 hover:bg-slate-50 hover:-translate-y-0.5'
            }`}
          >
            <input
              ref={fileInputRef}
              type="file"
              accept=".txt,.pdf,.csv,.json"
              className="hidden"
              onChange={handleFileChange}
            />
            <div className="flex flex-col items-center gap-2">
              <div className="w-12 h-12 rounded-full bg-blue-50 flex items-center justify-center text-blue-600 transition-transform duration-200 group-hover:scale-110">
                <UploadCloud className="w-6 h-6" />
              </div>
              <p className="text-sm font-medium text-slate-800">
                Drag and drop your file here, or{' '}
                <span className="text-blue-600 font-semibold underline underline-offset-2">
                  browse
                </span>
              </p>
              <p className="text-xs text-slate-500">
                Supports Bank Statements, Payslips, Invoices (.txt, .pdf)
              </p>
            </div>
          </div>
        ) : (
          <div className="flex items-center justify-between p-3.5 rounded-xl bg-slate-50 border border-slate-200 animate-fade-in-up">
            <div className="flex items-center gap-3 overflow-hidden">
              <div className="w-10 h-10 rounded-lg bg-blue-100 text-blue-700 flex items-center justify-center shrink-0">
                <FileText className="w-5 h-5" />
              </div>
              <div className="min-w-0">
                <p className="text-sm font-semibold text-slate-900 truncate">
                  {file.name}
                </p>
                <div className="flex items-center gap-2 text-xs text-slate-500">
                  <span>{formatFileSize(file.size)}</span>
                  <span>•</span>
                  <span className="text-emerald-700 font-medium flex items-center gap-1">
                    <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" /> Ready for analysis
                  </span>
                </div>
              </div>
            </div>
            <button
              type="button"
              onClick={() => setFile(null)}
              className="p-1.5 rounded-lg hover:bg-slate-200 text-slate-400 hover:text-slate-700 transition-all active:scale-90"
              title="Remove file"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        )}
      </div>

      {/* 2. Task Description Input */}
      <div className="space-y-2">
        <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider">
          2. Specific AI Task or Question
        </label>
        <textarea
          value={task}
          onChange={(e) => setTask(e.target.value)}
          placeholder="e.g. Calculate my total dining expenses, or summarize salary credits..."
          rows={3}
          className="field-input resize-none"
        />

        {/* Suggestion Pills */}
        <div className="space-y-1.5 pt-1">
          <p className="text-[11px] font-semibold text-slate-500">
            Quick Preset Prompts:
          </p>
          <div className="flex flex-wrap gap-1.5">
            {SUGGESTIONS.map((item, idx) => (
              <button
                key={idx}
                type="button"
                onClick={() => setTask(item.text)}
                className="preset-chip text-left font-medium"
              >
                {item.label}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* 3. Run Button */}
      <div>
        <button
          type="button"
          onClick={onRun}
          disabled={!canSubmit}
          className="w-full btn-primary btn-shimmer flex items-center justify-center gap-2 group active:scale-[0.98]"
        >
          {isLoading ? (
            <>
              <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
              <span>Minimizing Sensitive Data...</span>
            </>
          ) : (
            <>
              <span>Run Task-Aware Minimization</span>
              <ArrowRight className="w-4 h-4 transition-transform duration-200 group-hover:translate-x-1" />
            </>
          )}
        </button>

        <p className="text-[11px] text-center text-slate-500 mt-2">
          Strict policy floor applied: Govt IDs and full accounts are never exposed.
        </p>
      </div>
    </div>
  );
}

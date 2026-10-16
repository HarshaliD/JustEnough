import React from 'react';
import { Shield, Sparkles, Server, Zap, ExternalLink } from 'lucide-react';

export default function Navbar({ backendStatus, liveMode, setLiveMode }) {
  return (
    <header className="sticky top-0 z-50 backdrop-blur-md bg-white/95 border-b border-slate-200/90 shadow-xs">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        {/* Brand */}
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-blue-600 shadow-sm shadow-blue-500/20 flex items-center justify-center text-white">
            <Shield className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-extrabold text-lg tracking-tight text-slate-900">
                Just<span className="text-blue-600">Enough</span>
              </span>
              <span className="text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 rounded-full bg-blue-50 text-blue-700 border border-blue-200">
                v1.0
              </span>
            </div>
            <p className="text-xs text-slate-500 hidden sm:block">
              Task-Aware Data Minimization for AI
            </p>
          </div>
        </div>

        {/* Status & Controls */}
        <div className="flex items-center gap-3 sm:gap-4">
          {/* Backend Status indicator */}
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-slate-50 border border-slate-200 text-xs">
            <span
              className={`w-2 h-2 rounded-full ${
                backendStatus === 'online'
                  ? 'bg-emerald-500 shadow-sm shadow-emerald-500/50 animate-pulse'
                  : 'bg-rose-500 shadow-sm shadow-rose-500/50'
              }`}
            />
            <span className="text-slate-600 font-medium hidden md:inline">
              Backend:
            </span>
            <span
              className={`font-semibold ${
                backendStatus === 'online' ? 'text-emerald-700' : 'text-rose-600'
              }`}
            >
              {backendStatus === 'online' ? 'FastAPI Connected' : 'Offline'}
            </span>
          </div>

          {/* Live / Mock Mode Switch */}
          <div className="flex items-center gap-1 p-1 rounded-lg bg-slate-100 border border-slate-200">
            <button
              type="button"
              onClick={() => setLiveMode(false)}
              className={`px-2.5 py-1 rounded-md text-xs font-semibold transition-all ${
                !liveMode
                  ? 'bg-white text-slate-900 shadow-xs'
                  : 'text-slate-500 hover:text-slate-800'
              }`}
            >
              Mock Mode
            </button>
            <button
              type="button"
              onClick={() => setLiveMode(true)}
              className={`px-2.5 py-1 rounded-md text-xs font-semibold flex items-center gap-1.5 transition-all ${
                liveMode
                  ? 'bg-blue-600 text-white shadow-xs'
                  : 'text-slate-500 hover:text-slate-800'
              }`}
            >
              <Zap className="w-3 h-3" />
              Live Gemini
            </button>
          </div>

          {/* Swagger docs link */}
          <a
            href="http://localhost:8000/docs"
            target="_blank"
            rel="noreferrer"
            className="hidden lg:flex items-center gap-1 text-xs text-slate-500 hover:text-blue-600 font-medium transition-colors px-2 py-1"
          >
            <span>API Docs</span>
            <ExternalLink className="w-3 h-3" />
          </a>
        </div>
      </div>
    </header>
  );
}

import React, { useMemo, useState } from 'react';
import { Eye, Info, Sparkles, Shield, AlertCircle, CheckCircle, Tag, Filter } from 'lucide-react';

// Color coding by category sensitivity tier (refined, high-contrast pastel styling)
const TIER_STYLES = {
  // Tier 1: Policy floor — always dropped (government IDs, full account numbers)
  government_id: {
    bg: 'bg-rose-100/90 hover:bg-rose-200',
    text: 'text-rose-950 font-semibold',
    border: 'border-rose-400',
    ring: 'ring-rose-400',
    label: '🔴 Policy Floor: Govt ID',
    shortLabel: 'Govt ID',
    tier: 1,
    tierName: 'Tier 1 Policy Floor',
    policyNote: 'Strictly dropped by deterministic policy floor',
  },
  account_identifier: {
    bg: 'bg-rose-100/90 hover:bg-rose-200',
    text: 'text-rose-950 font-semibold',
    border: 'border-rose-400',
    ring: 'ring-rose-400',
    label: '🔴 Policy Floor: Account #',
    shortLabel: 'Account ID',
    tier: 1,
    tierName: 'Tier 1 Policy Floor',
    policyNote: 'Strictly dropped or masked by deterministic policy floor',
  },

  // Tier 2: High sensitivity (names, contacts, address, etc.)
  person_name: {
    bg: 'bg-orange-100/90 hover:bg-orange-200',
    text: 'text-orange-950 font-semibold',
    border: 'border-orange-400',
    ring: 'ring-orange-400',
    label: '🟠 High: Person Name',
    shortLabel: 'Person Name',
    tier: 2,
    tierName: 'Tier 2 High Sensitivity',
    policyNote: 'Masked/Dropped to protect individual identity',
  },
  contact: {
    bg: 'bg-orange-100/90 hover:bg-orange-200',
    text: 'text-orange-950 font-semibold',
    border: 'border-orange-400',
    ring: 'ring-orange-400',
    label: '🟠 High: Contact / Phone',
    shortLabel: 'Contact',
    tier: 2,
    tierName: 'Tier 2 High Sensitivity',
    policyNote: 'Phone / Email addresses stripped to prevent contact harvesting',
  },
  address: {
    bg: 'bg-orange-100/90 hover:bg-orange-200',
    text: 'text-orange-950 font-semibold',
    border: 'border-orange-400',
    ring: 'ring-orange-400',
    label: '🟠 High: Physical Address',
    shortLabel: 'Address',
    tier: 2,
    tierName: 'Tier 2 High Sensitivity',
    policyNote: 'Street addresses dropped to prevent geolocation profiling',
  },
  date_of_birth: {
    bg: 'bg-orange-100/90 hover:bg-orange-200',
    text: 'text-orange-950 font-semibold',
    border: 'border-orange-400',
    ring: 'ring-orange-400',
    label: '🟠 High: Date of Birth',
    shortLabel: 'DOB',
    tier: 2,
    tierName: 'Tier 2 High Sensitivity',
    policyNote: 'Generalized or dropped to prevent identity theft',
  },
  internal_id: {
    bg: 'bg-purple-100/90 hover:bg-purple-200',
    text: 'text-purple-950 font-semibold',
    border: 'border-purple-400',
    ring: 'ring-purple-400',
    label: '🟣 High: Internal ID / IFSC',
    shortLabel: 'Internal ID',
    tier: 2,
    tierName: 'Tier 2 High Sensitivity',
    policyNote: 'Customer IDs and branch codes removed',
  },
  employer: {
    bg: 'bg-orange-100/90 hover:bg-orange-200',
    text: 'text-orange-950 font-semibold',
    border: 'border-orange-400',
    ring: 'ring-orange-400',
    label: '🟠 High: Employer Name',
    shortLabel: 'Employer',
    tier: 2,
    tierName: 'Tier 2 High Sensitivity',
    policyNote: 'Workplace information dropped when not required',
  },
  medical_value: {
    bg: 'bg-purple-100/90 hover:bg-purple-200',
    text: 'text-purple-950 font-semibold',
    border: 'border-purple-400',
    ring: 'ring-purple-400',
    label: '🟣 High: Medical Record',
    shortLabel: 'Medical',
    tier: 2,
    tierName: 'Tier 2 High Sensitivity',
    policyNote: 'Protected health information',
  },

  // Tier 3: Contextual (merchants, counterparty, dates)
  counterparty_name: {
    bg: 'bg-amber-100/90 hover:bg-amber-200',
    text: 'text-amber-950 font-semibold',
    border: 'border-amber-400',
    ring: 'ring-amber-400',
    label: '🟡 Contextual: Counterparty',
    shortLabel: 'Counterparty',
    tier: 3,
    tierName: 'Tier 3 Contextual',
    policyNote: 'Kept only if specific recipient is needed for task',
  },
  merchant: {
    bg: 'bg-amber-100/90 hover:bg-amber-200',
    text: 'text-amber-950 font-semibold',
    border: 'border-amber-400',
    ring: 'ring-amber-400',
    label: '🟡 Contextual: Merchant',
    shortLabel: 'Merchant',
    tier: 3,
    tierName: 'Tier 3 Contextual',
    policyNote: 'Kept for expense categorisation (e.g. food, travel)',
  },
  transaction_date: {
    bg: 'bg-amber-100/90 hover:bg-amber-200',
    text: 'text-amber-950 font-semibold',
    border: 'border-amber-400',
    ring: 'ring-amber-400',
    label: '🟡 Contextual: Date',
    shortLabel: 'Date',
    tier: 3,
    tierName: 'Tier 3 Contextual',
    policyNote: 'Kept for chronological aggregation',
  },
  clause_text: {
    bg: 'bg-amber-100/90 hover:bg-amber-200',
    text: 'text-amber-950 font-semibold',
    border: 'border-amber-400',
    ring: 'ring-amber-400',
    label: '🟡 Contextual: Clause',
    shortLabel: 'Clause',
    tier: 3,
    tierName: 'Tier 3 Contextual',
    policyNote: 'Kept if contract interpretation requires it',
  },

  // Tier 4: Task-essential (amounts, balance, etc.)
  amount: {
    bg: 'bg-emerald-100/90 hover:bg-emerald-200',
    text: 'text-emerald-950 font-semibold',
    border: 'border-emerald-400',
    ring: 'ring-emerald-400',
    label: '🟢 Essential: Amount',
    shortLabel: 'Amount',
    tier: 4,
    tierName: 'Tier 4 Task-Essential',
    policyNote: 'Preserved to calculate mathematical result',
  },
  balance: {
    bg: 'bg-emerald-100/90 hover:bg-emerald-200',
    text: 'text-emerald-950 font-semibold',
    border: 'border-emerald-400',
    ring: 'ring-emerald-400',
    label: '🟢 Essential: Balance',
    shortLabel: 'Balance',
    tier: 4,
    tierName: 'Tier 4 Task-Essential',
    policyNote: 'Preserved if closing/running balance is requested',
  },
  salary_component: {
    bg: 'bg-emerald-100/90 hover:bg-emerald-200',
    text: 'text-emerald-950 font-semibold',
    border: 'border-emerald-400',
    ring: 'ring-emerald-400',
    label: '🟢 Essential: Salary',
    shortLabel: 'Salary Item',
    tier: 4,
    tierName: 'Tier 4 Task-Essential',
    policyNote: 'Preserved for payslip computation',
  },
};

const DEFAULT_STYLE = {
  bg: 'bg-slate-100 hover:bg-slate-200',
  text: 'text-slate-800 font-semibold',
  border: 'border-slate-300',
  ring: 'ring-slate-400',
  label: '⚪ Generic Field',
  shortLabel: 'Field',
  tier: 5,
  tierName: 'Other Field',
  policyNote: 'Subject to LLM minimization plan',
};

function buildSpans(text, fields) {
  if (!text) return [];
  if (!fields || fields.length === 0) return [{ type: 'text', content: text }];

  // Extract intervals checking start_char / end_char (from detector) or start / end
  const intervals = [];
  for (const f of fields) {
    const start = f.location?.start_char ?? f.location?.start;
    const end = f.location?.end_char ?? f.location?.end;
    if (typeof start === 'number' && typeof end === 'number' && end > start && end <= text.length) {
      intervals.push({
        id: f.id,
        start,
        end,
        category: f.category,
        placeholder: f.placeholder,
        rule: f.detection_rule,
        detector: f.detector,
        confidence: f.confidence,
        rawText: text.slice(start, end),
      });
    }
  }

  // Sort by start position
  intervals.sort((a, b) => a.start - b.start);

  // Deduplicate overlaps — keep higher sensitivity (lower tier number)
  const merged = [];
  for (const iv of intervals) {
    if (merged.length > 0 && iv.start < merged[merged.length - 1].end) {
      const last = merged[merged.length - 1];
      const lastTier = (TIER_STYLES[last.category] || DEFAULT_STYLE).tier;
      const ivTier = (TIER_STYLES[iv.category] || DEFAULT_STYLE).tier;
      if (ivTier < lastTier) {
        merged[merged.length - 1] = iv;
      }
    } else {
      merged.push(iv);
    }
  }

  // Build sequential spans
  const spans = [];
  let cursor = 0;
  for (const iv of merged) {
    if (iv.start > cursor) {
      spans.push({ type: 'text', content: text.slice(cursor, iv.start) });
    }
    spans.push({
      type: 'field',
      content: text.slice(iv.start, iv.end),
      id: iv.id,
      category: iv.category,
      placeholder: iv.placeholder,
      rule: iv.rule,
      detector: iv.detector,
      confidence: iv.confidence,
    });
    cursor = iv.end;
  }
  if (cursor < text.length) {
    spans.push({ type: 'text', content: text.slice(cursor) });
  }
  return spans;
}

export default function SensitivityHeatmap({ originalText, detectedFields }) {
  const [hoveredField, setHoveredField] = useState(null);
  const [filterTier, setFilterTier] = useState(null);

  const spans = useMemo(() => buildSpans(originalText, detectedFields), [originalText, detectedFields]);

  // Aggregate tier statistics
  const tierStats = useMemo(() => {
    const counts = { 1: 0, 2: 0, 3: 0, 4: 0 };
    for (const f of detectedFields || []) {
      const tier = (TIER_STYLES[f.category] || DEFAULT_STYLE).tier;
      if (tier <= 4) counts[tier]++;
    }
    return counts;
  }, [detectedFields]);

  return (
    <div className="space-y-4 animate-fade-in-up">
      {/* Legend & Filter Controls */}
      <div className="flex flex-wrap gap-2 items-center justify-between pb-1 border-b border-slate-100">
        <div className="flex flex-wrap gap-2 items-center">
          <Eye className="w-4 h-4 text-blue-600 shrink-0" />
          <span className="text-xs font-bold text-slate-800 mr-1">PII Sensitivity Classification:</span>
          {[
            { tier: 1, label: '🔴 Policy Floor (Govt ID / Acct)', bg: 'bg-rose-50 hover:bg-rose-100', border: 'border-rose-300 text-rose-800', count: tierStats[1] },
            { tier: 2, label: '🟠 High (Names, Contacts, Org)', bg: 'bg-orange-50 hover:bg-orange-100', border: 'border-orange-300 text-orange-800', count: tierStats[2] },
            { tier: 3, label: '🟡 Contextual (Merchants, Dates)', bg: 'bg-amber-50 hover:bg-amber-100', border: 'border-amber-300 text-amber-800', count: tierStats[3] },
            { tier: 4, label: '🟢 Task-Essential (Amounts, Balance)', bg: 'bg-emerald-50 hover:bg-emerald-100', border: 'border-emerald-300 text-emerald-800', count: tierStats[4] },
          ].map((item) => {
            const isSelected = filterTier === item.tier;
            return (
              <button
                key={item.tier}
                type="button"
                onClick={() => setFilterTier(isSelected ? null : item.tier)}
                className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-semibold border transition-all duration-150 active:scale-95 cursor-pointer ${
                  item.bg
                } ${item.border} ${
                  isSelected ? 'ring-2 ring-blue-500 shadow-xs font-bold' : 'opacity-85 hover:opacity-100'
                }`}
              >
                <span>{item.label}</span>
                <span className="font-mono text-[10px] px-1.5 py-0.2 rounded-full bg-white/80 border border-slate-200">
                  {item.count}
                </span>
              </button>
            );
          })}
        </div>

        {filterTier !== null && (
          <button
            type="button"
            onClick={() => setFilterTier(null)}
            className="text-xs font-semibold text-blue-600 hover:text-blue-800 underline"
          >
            Clear Filter
          </button>
        )}
      </div>

      {/* Interactive Document Viewer with Highlight Spans */}
      <div className="relative">
        <div className="p-4 sm:p-5 rounded-xl bg-slate-900 text-slate-100 border border-slate-800 overflow-auto max-h-[380px] font-mono text-xs leading-7 whitespace-pre-wrap select-text shadow-inner">
          {spans.map((span, i) => {
            if (span.type === 'text') {
              return <span key={i} className="text-slate-300">{span.content}</span>;
            }

            const style = TIER_STYLES[span.category] || DEFAULT_STYLE;
            const isHovered = hoveredField && hoveredField.id === span.id;
            const isDimmed = filterTier !== null && style.tier !== filterTier;

            return (
              <span
                key={i}
                onMouseEnter={() => setHoveredField(span)}
                onMouseLeave={() => setHoveredField(null)}
                className={`relative inline-block mx-0.5 px-1.5 py-0.5 rounded border transition-all duration-150 cursor-pointer ${
                  style.bg
                } ${style.text} ${style.border} ${
                  isHovered
                    ? `ring-2 ring-offset-1 ring-offset-slate-900 ${style.ring} scale-105 shadow-lg z-30 font-bold underline`
                    : ''
                } ${isDimmed ? 'opacity-25 filter blur-[0.4px]' : 'opacity-100'}`}
              >
                {span.content}
                {/* Floating pill badge showing category */}
                <span className="ml-1 text-[9px] font-mono opacity-70 uppercase tracking-wider">
                  [{style.shortLabel}]
                </span>
              </span>
            );
          })}
        </div>
      </div>

      {/* Live Field Inspector Bar (Hover Information) */}
      <div
        className={`p-3.5 sm:p-4 rounded-xl border transition-all duration-200 ${
          hoveredField
            ? 'bg-blue-50/90 border-blue-300 shadow-sm'
            : 'bg-slate-50 border-slate-200'
        }`}
      >
        {hoveredField ? (
          <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 text-xs">
            <div className="space-y-1">
              <div className="flex items-center gap-2">
                <span className="font-bold text-slate-900 text-sm">
                  Detected Field: <span className="font-mono bg-white px-2 py-0.5 rounded border border-slate-300 text-blue-700">"{hoveredField.content}"</span>
                </span>
                <span className="text-[11px] font-semibold text-slate-600 bg-white px-2 py-0.5 rounded-full border border-slate-200">
                  {(TIER_STYLES[hoveredField.category] || DEFAULT_STYLE).tierName}
                </span>
              </div>
              <p className="text-[11px] text-slate-600 font-medium">
                <strong>Detection Pattern:</strong> {hoveredField.rule || `Matched ${hoveredField.category} pattern`}
              </p>
            </div>

            <div className="flex flex-wrap sm:flex-nowrap items-center gap-2.5 shrink-0">
              <div className="text-right">
                <div className="text-[10px] text-slate-500 uppercase font-semibold">Skeleton Placeholder</div>
                <div className="font-mono text-xs font-bold text-slate-800 bg-white px-2 py-0.5 rounded border border-slate-300">
                  {hoveredField.placeholder || `[${hoveredField.category.toUpperCase()}]`}
                </div>
              </div>
              {hoveredField.confidence && (
                <div className="text-right">
                  <div className="text-[10px] text-slate-500 uppercase font-semibold">Confidence</div>
                  <div className="text-xs font-bold text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded border border-emerald-200">
                    {Math.round(hoveredField.confidence * 100)}%
                  </div>
                </div>
              )}
            </div>
          </div>
        ) : (
          <div className="flex items-center gap-2 text-xs text-slate-500">
            <Info className="w-4 h-4 text-blue-600 shrink-0" />
            <span>
              <strong>Live Heatmap Inspector:</strong> Hover your cursor over any highlighted text above to inspect its classification tier, pattern rule, and skeleton placeholder.
            </span>
          </div>
        )}
      </div>
    </div>
  );
}

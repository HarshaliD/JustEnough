/**
 * JustEnough — app.js
 * Production-grade vanilla JS for the JustEnough frontend.
 */

const API_BASE = 'http://localhost:8000';

// ── State ────────────────────────────────────────────────────────────────────
let state = {
  file: null,
  task: '',
  live: false,
  result: null,
  loading: false,
};

// ── Element refs ─────────────────────────────────────────────────────────────
const $  = id => document.getElementById(id);
const dropzone       = $('dropzone');
const fileInput      = $('fileInput');
const browseBtn      = $('browseBtn');
const dropzoneIdle   = $('dropzoneIdle');
const dropzoneActive = $('dropzoneActive');
const fileName       = $('fileName');
const fileSize       = $('fileSize');
const removeFile     = $('removeFile');
const taskInput      = $('taskInput');
const analyzeBtn     = $('analyzeBtn');
const btnText        = analyzeBtn.querySelector('.btn-text');
const btnSpinner     = analyzeBtn.querySelector('.btn-spinner');
const modeToggle     = $('modeToggle');
const modeTrack      = modeToggle.querySelector('.mode-toggle-track');
const modeLabel      = $('modeLabel');
const pipelineSteps  = $('pipelineSteps');
const emptyState     = $('emptyState');
const resultsContent = $('resultsContent');

// ── Mode toggle ──────────────────────────────────────────────────────────────
modeToggle.addEventListener('click', () => {
  state.live = !state.live;
  modeTrack.classList.toggle('live', state.live);
  modeLabel.textContent = state.live ? 'Live Mode' : 'Mock Mode';
  modeLabel.classList.toggle('live', state.live);
  toast(state.live
    ? 'Live Mode enabled — calls will use Gemini API.'
    : 'Mock mode — no API calls.',
    'info'
  );
});

// ── File handling ─────────────────────────────────────────────────────────────
browseBtn.addEventListener('click', e => { e.stopPropagation(); fileInput.click(); });
dropzone.addEventListener('click', () => { if (!state.file) fileInput.click(); });

fileInput.addEventListener('change', e => {
  const f = e.target.files[0];
  if (f) setFile(f);
});

dropzone.addEventListener('dragover', e => {
  e.preventDefault();
  dropzone.classList.add('drag-over');
});
dropzone.addEventListener('dragleave', () => dropzone.classList.remove('drag-over'));
dropzone.addEventListener('drop', e => {
  e.preventDefault();
  dropzone.classList.remove('drag-over');
  const f = e.dataTransfer.files[0];
  if (f) setFile(f);
});

removeFile.addEventListener('click', e => {
  e.stopPropagation();
  clearFile();
});

function setFile(f) {
  if (!f.name.match(/\.(txt|pdf)$/i)) {
    toast('Unsupported file type. Please upload a .txt or .pdf file.', 'error');
    return;
  }
  state.file = f;
  fileName.textContent = f.name;
  fileSize.textContent = formatBytes(f.size);
  dropzoneIdle.hidden = true;
  dropzoneActive.hidden = false;
  updateAnalyzeBtn();
}

function clearFile() {
  state.file = null;
  fileInput.value = '';
  dropzoneIdle.hidden = false;
  dropzoneActive.hidden = true;
  updateAnalyzeBtn();
}

function formatBytes(bytes) {
  if (bytes < 1024) return bytes + ' B';
  if (bytes < 1048576) return (bytes / 1024).toFixed(1) + ' KB';
  return (bytes / 1048576).toFixed(1) + ' MB';
}

// ── Task suggestions ─────────────────────────────────────────────────────────
document.querySelectorAll('.suggestion-pill').forEach(btn => {
  btn.addEventListener('click', () => {
    taskInput.value = btn.dataset.task;
    state.task = btn.dataset.task;
    updateAnalyzeBtn();
  });
});

taskInput.addEventListener('input', () => {
  state.task = taskInput.value.trim();
  updateAnalyzeBtn();
});

function updateAnalyzeBtn() {
  analyzeBtn.disabled = !(state.file && state.task.length > 3);
}

// ── Tabs ─────────────────────────────────────────────────────────────────────
document.querySelectorAll('.tab-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('tab-active'));
    document.querySelectorAll('.tab-panel').forEach(p => {
      p.classList.remove('tab-panel-active');
      p.hidden = true;
    });
    btn.classList.add('tab-active');
    const panel = document.getElementById('panel' + capitalize(btn.dataset.tab));
    panel.hidden = false;
    panel.classList.add('tab-panel-active');
  });
});
function capitalize(s) { return s.charAt(0).toUpperCase() + s.slice(1); }

// ── Pipeline step animation ───────────────────────────────────────────────────
const STEPS = ['detect', 'skeleton', 'plan', 'policy', 'transform'];
let stepTimer = null;

function startPipelineAnim() {
  pipelineSteps.hidden = false;
  STEPS.forEach(s => {
    const el = $('step-' + s);
    el.classList.remove('active', 'done');
  });
  let i = 0;
  function next() {
    if (i > 0) $('step-' + STEPS[i - 1]).classList.replace('active', 'done');
    if (i >= STEPS.length) return;
    $('step-' + STEPS[i]).classList.add('active');
    i++;
    stepTimer = setTimeout(next, 650);
  }
  next();
}

function finishPipelineAnim() {
  clearTimeout(stepTimer);
  STEPS.forEach(s => {
    const el = $('step-' + s);
    el.classList.remove('active');
    el.classList.add('done');
  });
  setTimeout(() => { pipelineSteps.hidden = true; }, 1200);
}

// ── Analyze ───────────────────────────────────────────────────────────────────
analyzeBtn.addEventListener('click', runAnalysis);

async function runAnalysis() {
  if (!state.file || !state.task || state.loading) return;
  state.loading = true;

  // UI: loading
  btnText.hidden = true;
  btnSpinner.hidden = false;
  analyzeBtn.disabled = true;
  startPipelineAnim();

  const form = new FormData();
  form.append('file', state.file, state.file.name);
  form.append('task', state.task);

  const url = `${API_BASE}/analyze?live=${state.live}&case_id=upload`;

  try {
    const res = await fetch(url, { method: 'POST', body: form });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(err.detail || `HTTP ${res.status}`);
    }
    const data = await res.json();
    state.result = data;
    finishPipelineAnim();
    renderResults(data);
    toast(`Analysis complete — ${data.metrics.sensitive_field_reduction_pct}% privacy reduction`, 'success');
  } catch (e) {
    finishPipelineAnim();
    toast('Analysis failed: ' + e.message, 'error');
    console.error(e);
  } finally {
    state.loading = false;
    btnText.hidden = false;
    btnSpinner.hidden = true;
    analyzeBtn.disabled = false;
  }
}

// ── Render results ────────────────────────────────────────────────────────────
function renderResults(data) {
  emptyState.hidden = true;
  resultsContent.hidden = false;

  renderMetrics(data.metrics);
  renderViolations(data.policy_violations);
  renderDecisions(data.plan, data.policy_violations);
  renderFields(data.detected_fields);
  renderDiff(data);
  renderMinimized(data.minimized_text);

  // Reset to first tab
  document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('tab-active'));
  document.querySelectorAll('.tab-panel').forEach(p => { p.classList.remove('tab-panel-active'); p.hidden = true; });
  $('tabDecisions').classList.add('tab-active');
  $('panelDecisions').hidden = false;
  $('panelDecisions').classList.add('tab-panel-active');
}

// Metrics
function renderMetrics(m) {
  // Gauge
  const pct = m.sensitive_field_reduction_pct;
  const circumference = 2 * Math.PI * 32; // 201.06
  const offset = circumference * (1 - pct / 100);
  $('gaugeFill').style.strokeDashoffset = offset;
  $('gaugeFill').style.stroke = pct >= 70 ? 'var(--green-500)' : pct >= 40 ? 'var(--orange-500)' : 'var(--red-500)';
  $('gaugeText').textContent = pct + '%';
  $('reductionSub').textContent = `${m.fields_dropped_or_masked} of ${m.total_fields_detected} protected`;

  animateCount($('metricDetected'), 0, m.total_fields_detected, 700);
  animateCount($('metricKept'),     0, m.fields_kept,            700);
  animateCount($('metricRedacted'), 0, m.fields_dropped_or_masked, 700);
  $('metricLatency').textContent = m.latency_ms + 'ms';
}

function animateCount(el, from, to, dur) {
  const start = performance.now();
  function frame(now) {
    const t = Math.min((now - start) / dur, 1);
    el.textContent = Math.round(from + (to - from) * easeOut(t));
    if (t < 1) requestAnimationFrame(frame);
  }
  requestAnimationFrame(frame);
}
function easeOut(t) { return 1 - Math.pow(1 - t, 3); }

// Violations
function renderViolations(violations) {
  const banner = $('violationsBanner');
  if (violations.length === 0) { banner.hidden = true; return; }
  banner.hidden = false;
  $('violationsText').textContent =
    `Policy floor clamped ${violations.length} categor${violations.length > 1 ? 'ies' : 'y'}: ` +
    violations.map(v => `${v.category} (${v.model_action} → ${v.clamped_action})`).join(', ') + '.';
}

// Decisions table
const ACTION_CLASS = {
  KEEP: 'action-keep', DROP: 'action-drop',
  MASK_PARTIAL: 'action-mask', GENERALIZE: 'action-generalize',
  PSEUDONYMIZE: 'action-pseudo', AGGREGATE: 'action-aggregate',
};
const ACTION_LABEL = {
  KEEP: 'KEEP', DROP: 'DROP', MASK_PARTIAL: 'MASK', GENERALIZE: 'GEN',
  PSEUDONYMIZE: 'PSEUDO', AGGREGATE: 'AGG',
};

function renderDecisions(plan, violations) {
  const tbody = $('decisionsBody');
  tbody.innerHTML = '';
  const enforcedCats = new Set(violations.map(v => v.category));

  Object.entries(plan).forEach(([cat, dec]) => {
    const tr = document.createElement('tr');
    const conf = Math.round(dec.confidence * 100);
    const enforced = enforcedCats.has(cat);
    tr.innerHTML = `
      <td class="td-category">${cat}</td>
      <td><span class="action-badge ${ACTION_CLASS[dec.action] || ''}">${ACTION_LABEL[dec.action] || dec.action}</span></td>
      <td>
        <div class="confidence-bar-wrap">
          <div class="confidence-bar"><div class="confidence-fill" style="width:0%" data-target="${conf}"></div></div>
          <span class="confidence-val">${conf}%</span>
        </div>
      </td>
      <td class="td-reason">${dec.reason}</td>
      <td>${enforced
        ? '<span class="policy-badge policy-enforced">Clamped</span>'
        : '<span class="policy-badge policy-ok">—</span>'
      }</td>
    `;
    tbody.appendChild(tr);
  });

  // Animate confidence bars
  setTimeout(() => {
    tbody.querySelectorAll('.confidence-fill').forEach(bar => {
      bar.style.transition = 'width .8s cubic-bezier(.4,0,.2,1)';
      bar.style.width = bar.dataset.target + '%';
    });
  }, 50);
}

// Detected fields
function renderFields(fields) {
  const grid = $('fieldsGrid');
  grid.innerHTML = '';
  if (fields.length === 0) {
    grid.innerHTML = '<p style="color:var(--navy-400);font-size:13px">No sensitive fields detected.</p>';
    return;
  }
  fields.forEach(f => {
    const card = document.createElement('div');
    card.className = 'field-card';
    card.innerHTML = `
      <div class="field-card-top">
        <span class="fc-category">${f.category}</span>
        <span class="fc-id">${f.id}</span>
      </div>
      <span class="fc-placeholder">${f.placeholder}</span>
      <div class="field-card-meta">
        <span class="fc-meta">line ${f.location.line ?? '?'}</span>
        <span class="fc-meta">${f.detector}</span>
        <span class="fc-meta">conf ${Math.round(f.confidence * 100)}%</span>
      </div>
    `;
    grid.appendChild(card);
  });
}

// Diff view — show original text alongside minimized with REDACTED spans highlighted
function renderDiff(data) {
  const orig = data.minimized_text; // we'll reconstruct from original via the file
  // Since we don't re-send the original, we show what we have
  // Original: read from state.file
  const reader = new FileReader();
  reader.onload = e => {
    $('diffOriginal').textContent = e.target.result;
  };
  if (state.file) reader.readAsText(state.file);

  // Minimized with highlighted redactions
  const minimized = data.minimized_text;
  const highlighted = minimized.replace(/\[REDACTED:[^\]]+\]|\[AGGREGATED:[^\]]+\]/g,
    m => `<span class="redacted-span">${m}</span>`);
  $('diffMinimized').innerHTML = highlighted;
}

// Minimized doc tab
function renderMinimized(text) {
  $('minimizedDoc').textContent = text;
}

// Copy & Download
$('copyMinimized').addEventListener('click', () => {
  if (!state.result) return;
  navigator.clipboard.writeText(state.result.minimized_text).then(() => {
    toast('Minimized document copied to clipboard!', 'success');
  });
});

$('downloadMinimized').addEventListener('click', () => {
  if (!state.result) return;
  const blob = new Blob([state.result.minimized_text], { type: 'text/plain' });
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = (state.file?.name?.replace(/\.[^.]+$/, '') || 'document') + '_minimized.txt';
  a.click();
  URL.revokeObjectURL(a.href);
  toast('Minimized document downloaded.', 'success');
});

// ── Toast ─────────────────────────────────────────────────────────────────────
const TOAST_ICONS = {
  success: `<svg width="18" height="18" viewBox="0 0 24 24" fill="none"><path d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>`,
  error:   `<svg width="18" height="18" viewBox="0 0 24 24" fill="none"><path d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>`,
  info:    `<svg width="18" height="18" viewBox="0 0 24 24" fill="none"><path d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>`,
};

function toast(msg, type = 'info', duration = 4000) {
  const container = $('toastContainer');
  const el = document.createElement('div');
  el.className = `toast toast-${type}`;

  const [title, detail] = msg.split(' — ');
  el.innerHTML = `
    <span class="toast-icon-${type}">${TOAST_ICONS[type]}</span>
    <div class="toast-body">
      <div class="toast-title">${title}</div>
      ${detail ? `<div class="toast-msg">${detail}</div>` : ''}
    </div>
  `;
  container.appendChild(el);

  setTimeout(() => {
    el.classList.add('toast-exit');
    setTimeout(() => el.remove(), 350);
  }, duration);
}

// ── Sticky header shadow on scroll ───────────────────────────────────────────
window.addEventListener('scroll', () => {
  $('header').style.boxShadow = window.scrollY > 10
    ? '0 2px 16px rgba(0,0,0,.4)'
    : 'none';
}, { passive: true });

// ── Init: check API health ────────────────────────────────────────────────────
(async () => {
  try {
    const res = await fetch(`${API_BASE}/health`);
    if (res.ok) {
      const data = await res.json();
      toast(`Connected to JustEnough API — model: ${data.model}`, 'success', 3000);
    }
  } catch {
    toast('Cannot reach API at localhost:8000 — start the backend first.', 'error', 6000);
  }
})();

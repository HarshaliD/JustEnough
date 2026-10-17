const API_BASE = 'http://localhost:8000';

export async function checkHealth() {
  try {
    const res = await fetch(`${API_BASE}/health`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } catch (err) {
    console.error('Health check failed:', err);
    return null;
  }
}

export async function getSchemas() {
  try {
    const res = await fetch(`${API_BASE}/schemas`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } catch (err) {
    console.error('Failed to fetch schemas:', err);
    return null;
  }
}

export async function analyzeDocument({ file, task, live = false }) {
  const formData = new FormData();
  formData.append('file', file, file.name);
  formData.append('task', task);

  const url = `${API_BASE}/analyze?live=${Boolean(live)}&case_id=upload`;
  const res = await fetch(url, {
    method: 'POST',
    body: formData,
  });

  if (!res.ok) {
    let errorDetail = `HTTP ${res.status}`;
    try {
      const errorJson = await res.json();
      errorDetail = errorJson.detail || errorDetail;
    } catch (_) {}
    throw new Error(errorDetail);
  }

  return await res.json();
}

export async function verifyAnswers({ task, originalText, minimizedText, live = false, taskOutputSchema = null }) {
  const body = {
    task,
    original_text: originalText,
    minimized_text: minimizedText,
    live: Boolean(live),
    task_output_schema: taskOutputSchema,
  };

  const res = await fetch(`${API_BASE}/verify`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });

  if (!res.ok) {
    let errorDetail = `HTTP ${res.status}`;
    try {
      const errorJson = await res.json();
      errorDetail = errorJson.detail || errorDetail;
    } catch (_) {}
    throw new Error(errorDetail);
  }

  return await res.json();
}

export async function sendChatMessage({ minimizedText, history = [], message, live = false }) {
  const body = {
    minimized_text: minimizedText,
    history,
    message,
    live: Boolean(live),
  };

  const res = await fetch(`${API_BASE}/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });

  if (!res.ok) {
    let errorDetail = `HTTP ${res.status}`;
    try {
      const errorJson = await res.json();
      errorDetail = errorJson.detail || errorDetail;
    } catch (_) {}
    throw new Error(errorDetail);
  }

  return await res.json();
}

export async function getAuditLog() {
  try {
    const res = await fetch(`${API_BASE}/audit-log`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } catch (err) {
    console.error('Failed to fetch audit log:', err);
    return { count: 0, entries: [] };
  }
}

export async function getTaskAnswer({ task, minimizedText, live = false }) {
  const body = {
    minimized_text: minimizedText,
    history: [],
    message: task,
    live: Boolean(live),
  };

  const res = await fetch(`${API_BASE}/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });

  if (!res.ok) {
    let errorDetail = `HTTP ${res.status}`;
    try {
      const errorJson = await res.json();
      errorDetail = errorJson.detail || errorDetail;
    } catch (_) {}
    throw new Error(errorDetail);
  }

  return await res.json();
}

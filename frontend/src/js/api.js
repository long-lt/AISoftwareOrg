export function getToken() {
  return localStorage.getItem('dashboard_token') || '';
}

export function saveToken(tokenValue) {
  const cleanToken = tokenValue ? tokenValue.trim() : '';
  if (cleanToken) {
    localStorage.setItem('dashboard_token', cleanToken);
  } else {
    localStorage.removeItem('dashboard_token');
  }
  return cleanToken;
}

export async function fetchJSON(url) {
  const headers = {};
  const token = getToken();
  if (token) headers['Authorization'] = 'Bearer ' + token;
  const resp = await fetch(url, { headers });
  if (!resp.ok) {
    throw new Error(`Truy cập ${url} thất bại: ${resp.status}`);
  }
  return resp.json();
}

// ---------------------------------------------------------
// CÁC HÀM GET DỮ LIỆU ĐỘNG TỪ BACKEND
// ---------------------------------------------------------

export async function getTasks() {
  return fetchJSON('/api/tasks');
}

export async function getExperiences() {
  return fetchJSON('/api/experiences');
}

export async function getCheckpoints() {
  return fetchJSON('/api/checkpoints');
}

export async function getPermissions() {
  return fetchJSON('/api/permissions');
}

export async function getAgents() {
  return fetchJSON('/api/agents');
}

export async function getCosts() {
  return fetchJSON('/api/costs');
}

export async function getProviders() {
  return fetchJSON('/api/providers');
}

export async function getModels(provider = '', key = '', baseUrl = '') {
  let url = '/api/models';
  const params = [];
  if (provider) params.push(`provider=${encodeURIComponent(provider)}`);
  if (key) params.push(`key=${encodeURIComponent(key)}`);
  if (baseUrl) params.push(`base_url=${encodeURIComponent(baseUrl)}`);
  if (params.length > 0) {
    url += '?' + params.join('&');
  }
  return fetchJSON(url);
}

export async function getJobs() {
  return fetchJSON('/api/jobs');
}

export async function getJob(slug) {
  return fetchJSON(`/api/jobs/${encodeURIComponent(slug)}`);
}

export async function getJobPhases(slug) {
  return fetchJSON(`/api/jobs/${encodeURIComponent(slug)}/phases`);
}

export async function getJobCodeTree(slug) {
  return fetchJSON(`/api/jobs/${encodeURIComponent(slug)}/code/tree`);
}

export async function getJobCodeFile(slug, path) {
  return fetchJSON(`/api/jobs/${encodeURIComponent(slug)}/code/file?path=${encodeURIComponent(path)}`);
}


// ---------------------------------------------------------
// CÁC HÀM POST THAO TÁC LÊN BACKEND
// ---------------------------------------------------------

export async function changeActiveProvider(name) {
  if (!name) return;
  const resp = await fetch('/api/providers/' + encodeURIComponent(name) + '/use', { method: 'POST' });
  if (!resp.ok) {
    throw new Error(`Không thể kích hoạt provider ${name}`);
  }
}

export async function createJob(jobData) {
  const resp = await fetch('/api/jobs', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(jobData)
  });
  if (!resp.ok) {
    throw new Error(`Sinh ứng dụng thất bại với mã ${resp.status}`);
  }
  return resp.json();
}

export async function handleObservabilityAction(type, action, id) {
  const endpoint = `/api/${type}s/${encodeURIComponent(id)}/${action}`;
  const resp = await fetch(endpoint, { method: 'POST' });
  if (!resp.ok) {
    throw new Error(`Thao tác ${action} trên ${type} ${id} thất bại: ${resp.status}`);
  }
}

// ---------------------------------------------------------
// ĐỒNG BỘ HÓA SÁNG KIẾN DOANH NGHIỆP, KPIS, CONFIGS VÀ SETTINGS
// ---------------------------------------------------------

export async function getKPIs() {
  return fetchJSON('/api/kpis');
}

export async function getProjects() {
  return fetchJSON('/api/projects');
}

export async function getProject(slug) {
  return fetchJSON(`/api/projects/${encodeURIComponent(slug)}`);
}

export async function createProject(projectData) {
  const resp = await fetch('/api/projects', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(projectData)
  });
  if (!resp.ok) {
    throw new Error(`Tạo sáng kiến thất bại: ${resp.status}`);
  }
  return resp.json();
}

export async function deleteProject(slug) {
  const resp = await fetch(`/api/projects/${encodeURIComponent(slug)}`, {
    method: 'DELETE'
  });
  if (!resp.ok) {
    throw new Error(`Xoá sáng kiến thất bại: ${resp.status}`);
  }
  return resp.json();
}

export async function deleteJob(slug, purge = false) {
  const url = `/api/jobs/${encodeURIComponent(slug)}${purge ? '?purge=true' : ''}`;
  const resp = await fetch(url, { method: 'DELETE' });
  if (!resp.ok) {
    throw new Error(`Xoá job thất bại: ${resp.status}`);
  }
  return resp.json();
}

export async function cancelJob(slug) {
  const resp = await fetch(`/api/jobs/${encodeURIComponent(slug)}/cancel`, {
    method: 'POST'
  });
  if (!resp.ok) {
    throw new Error(`Huỷ job thất bại: ${resp.status}`);
  }
  return resp.json();
}

export async function getDailyCosts(days = 7) {
  return fetchJSON(`/api/costs/daily?days=${days}`);
}

export async function getAgentConfigs() {
  return fetchJSON('/api/agents/config');
}

export async function saveAgentConfig(agentId, config) {
  const resp = await fetch(`/api/agents/config/${encodeURIComponent(agentId)}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(config)
  });
  if (!resp.ok) {
    throw new Error(`Lưu cấu hình agent thất bại: ${resp.status}`);
  }
  return resp.json();
}

export async function getSystemSettings() {
  return fetchJSON('/api/settings');
}

export async function saveSystemSettings(settingsData) {
  const resp = await fetch('/api/settings', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(settingsData)
  });
  if (!resp.ok) {
    throw new Error(`Lưu cài đặt hệ thống thất bại: ${resp.status}`);
  }
  return resp.json();
}

export async function wipeSystemData() {
  const resp = await fetch('/api/settings/wipe', {
    method: 'POST'
  });
  if (!resp.ok) {
    throw new Error(`Xoá dữ liệu hệ thống thất bại: ${resp.status}`);
  }
  return resp.json();
}


import BaseView from './BaseView.js';
import template from '../../views/pipelines.html?raw';
import * as api from '../api.js';

export default class PipelinesView extends BaseView {
  constructor(router) {
    super('pipelines', template);
    this.router = router;
    this.refreshInterval = null;
  }

  onMount() {
    // 1. Nút Click xem chi tiết Pipeline Run
    const pipeRow = this.container.querySelector('#pipe-row-cs-agent');
    if (pipeRow) {
      pipeRow.addEventListener('click', () => {
        this.router.showView('view-pipeline-detail');
      });
    }

    // 2. Khởi tạo Token JWT đầu vào
    const tokenInput = this.container.querySelector('#team-token');
    if (tokenInput) {
      tokenInput.value = api.getToken();
    }

    // 3. Gán sự kiện lưu token
    const saveTokenBtn = this.container.querySelector('#btn-save-token');
    if (saveTokenBtn && tokenInput) {
      saveTokenBtn.addEventListener('click', () => {
        const tokenVal = tokenInput.value;
        const clean = api.saveToken(tokenVal);
        const statusEl = this.container.querySelector('#token-status');
        if (statusEl) {
          statusEl.textContent = clean ? 'Đã lưu Token' : 'Đã xoá Token';
          setTimeout(() => { statusEl.textContent = ''; }, 2000);
        }
        this.onUpdate();
      });
    }

    // Nạp dữ liệu realtime
    this.onUpdate();

    // Thiết lập đồng bộ hóa
    this.refreshInterval = setInterval(() => this.onUpdate(), 5000);
  }

  onUnmount() {
    if (this.refreshInterval) {
      clearInterval(this.refreshInterval);
      this.refreshInterval = null;
    }
  }

  async onUpdate() {
    const pulseTime = this.container.querySelector('#last-update');
    if (pulseTime) {
      pulseTime.textContent = new Date().toLocaleTimeString();
    }

    // Gọi đồng thời tất cả các API nghiệp vụ liên quan
    await Promise.all([
      this.loadActivePipelines(),
      this.loadTasks(),
      this.loadExperiences(),
      this.loadCheckpoints(),
      this.loadAgentsActivity(),
      this.loadPermissions()
    ]);
  }

  async loadActivePipelines() {
    const target = this.container.querySelector('#pipelines-table-body');
    const totalEl = this.container.querySelector('#pipe-kpi-total');
    const runningEl = this.container.querySelector('#pipe-kpi-running');
    const successEl = this.container.querySelector('#pipe-kpi-success');
    const failedEl = this.container.querySelector('#pipe-kpi-failed');
    const durationEl = this.container.querySelector('#pipe-kpi-duration');

    try {
      const [projects, jobs] = await Promise.all([
        api.getProjects(),
        api.getJobs()
      ]);

      const runningCount = jobs.filter(j => j.status === 'running' || j.status === 'queued').length;
      const successCount = jobs.filter(j => j.status === 'succeeded' || j.status === 'success' || j.status === 'active').length;
      const failedCount = jobs.filter(j => j.status === 'failed' || j.status === 'error').length;
      
      if (totalEl) totalEl.textContent = jobs.length;
      if (runningEl) runningEl.textContent = runningCount;
      if (successEl) successEl.textContent = successCount;
      if (failedEl) failedEl.textContent = failedCount;
      if (durationEl) durationEl.textContent = jobs.length > 0 ? '4m 12s' : '0s';

      if (target) {
        if (jobs.length > 0) {
          target.innerHTML = jobs.map(j => {
            const isDone = j.status === 'succeeded' || j.status === 'success' || j.status === 'active';
            const isFail = j.status === 'failed' || j.status === 'error';
            
            let stageText = 'create Stage';
            const phases = j.phases || {};
            if (phases.ba === 'done') stageText = 'ba Spec Stage';
            if (phases.architect === 'done') stageText = 'architect Architecture Stage';
            if (phases.uiux === 'done') stageText = 'uiux Style Stage';
            if (phases.dev === 'done') stageText = 'dev Coding Stage';
            if (phases.qa === 'done') stageText = 'qa Quality Gate';
            if (phases.export === 'done') stageText = 'export Archive';

            let badgeClass = 'badge-running';
            let statusText = j.status;
            if (isDone) {
              badgeClass = 'badge-success';
              statusText = 'Success';
            } else if (isFail) {
              badgeClass = 'badge-error';
              statusText = 'Failed';
            }

            return `
              <tr style="cursor:pointer;" class="pipeline-run-row" data-slug="${this.escapeHTML(j.slug)}">
                <td><strong>${this.escapeHTML(j.slug)}</strong></td>
                <td>${this.escapeHTML(j.name)}</td>
                <td>API Trigger</td>
                <td><span style="color:var(--accent-blue);">${this.escapeHTML(stageText)}</span></td>
                <td><span class="badge ${badgeClass}">${statusText.toUpperCase()}</span></td>
                <td>3m 15s</td>
                <td>${isFail ? '0%' : '100%'}</td>
                <td class="actions">
                  <a class="btn-text" style="cursor:pointer; font-weight:700; color:var(--accent-blue);">View Logs</a>
                </td>
              </tr>
            `;
          }).join('');

          // Gán sự kiện click động đi tới trang chi tiết
          target.querySelectorAll('.pipeline-run-row').forEach(row => {
            row.addEventListener('click', () => {
              const slug = row.getAttribute('data-slug');
              this.router.showView('view-pipeline-detail', { slug });
            });
          });
        } else {
          target.innerHTML = `<tr><td colspan="8" style="text-align:center; color:var(--text-secondary); padding:20px;">Không có delivery pipeline nào đang hoạt động.</td></tr>`;
        }
      }
    } catch (err) {
      console.warn('Lỗi tải active pipelines:', err);
    }
  }

  // -------------------------------------------------------------
  // XỬ LÝ NẠP DỮ LIỆU TỪ MÔ-ĐUN API
  // -------------------------------------------------------------

  async loadTasks() {
    const target = this.container.querySelector('#task-summary');
    if (!target) return;
    try {
      const data = await api.getTasks();
      const tasks = data.logs || [];
      
      target.innerHTML = `
        <div class="stat-row" style="display:flex; justify-content:space-between; margin-bottom:10px;">
          <div class="stat"><span class="stat-value" style="font-size:18px; font-weight:800;">${data.total}</span><div class="stat-label" style="font-size:10px; color:var(--text-secondary);">Tổng số</div></div>
          <div class="stat"><span class="stat-value" style="font-size:18px; font-weight:800; color:var(--accent-green);">${data.success}</span><div class="stat-label" style="font-size:10px; color:var(--text-secondary);">Thành công</div></div>
          <div class="stat"><span class="stat-value" style="font-size:18px; font-weight:800; color:var(--accent-rose);">${data.failed}</span><div class="stat-label" style="font-size:10px; color:var(--text-secondary);">Thất bại</div></div>
        </div>
        ${tasks.length ? `
        <table>
          <thead>
            <tr><th>Task ID</th><th>Status</th><th>Fixes</th></tr>
          </thead>
          <tbody>
            ${tasks.slice(-4).reverse().map(l => `
            <tr>
              <td><code style="font-size:10px;">${this.escapeHTML(l.task_id)}</code></td>
              <td>${this.badgeHTML(l.status)}</td>
              <td>${l.details?.fix_attempts ?? '-'}</td>
            </tr>`).join('')}
          </tbody>
        </table>` : '<p style="font-size:12px; color:var(--text-muted);">Chưa có tác vụ nào</p>'}
      `;
    } catch (err) {
      target.innerHTML = `<p style="color:var(--accent-rose); font-size:11px;">Không thể tải tác vụ: ${err.message}</p>`;
    }
  }

  async loadExperiences() {
    const target = this.container.querySelector('#experience-queue');
    if (!target) return;
    try {
      const data = await api.getExperiences();
      const counts = data.counts || {};
      
      target.innerHTML = `
        <div class="stat-row" style="display:flex; justify-content:space-between; margin-bottom:10px;">
          <div class="stat"><span class="stat-value" style="font-size:18px; font-weight:800; color:var(--accent-amber);">${counts.pending_review || 0}</span><div class="stat-label" style="font-size:10px; color:var(--text-secondary);">Chờ duyệt</div></div>
          <div class="stat"><span class="stat-value" style="font-size:18px; font-weight:800; color:var(--accent-green);">${counts.approved || 0}</span><div class="stat-label" style="font-size:10px; color:var(--text-secondary);">Đã duyệt</div></div>
          <div class="stat"><span class="stat-value" style="font-size:18px; font-weight:800; color:var(--accent-rose);">${counts.rejected || 0}</span><div class="stat-label" style="font-size:10px; color:var(--text-secondary);">Từ chối</div></div>
        </div>
        ${data.pending && data.pending.length ? `
        <table>
          <thead>
            <tr><th>ID</th><th>Task</th><th>Thao tác</th></tr>
          </thead>
          <tbody>
            ${data.pending.slice(0, 3).map(e => `
            <tr>
              <td><code style="font-size:10px;">${this.escapeHTML(e.id)}</code></td>
              <td title="${this.escapeHTML(e.task_id)}">${this.escapeHTML(e.task_id.slice(0,12))}...</td>
              <td class="actions">
                <a class="btn-action-trigger" data-action="approve" data-type="experience" data-id="${this.escapeHTML(e.id)}" style="color:var(--accent-green); font-weight:bold; cursor:pointer;">Duyệt</a>
                <a class="btn-action-trigger" data-action="reject" data-type="experience" data-id="${this.escapeHTML(e.id)}" style="color:var(--accent-rose); font-weight:bold; cursor:pointer; margin-left:6px;">Bỏ</a>
              </td>
            </tr>`).join('')}
          </tbody>
        </table>` : '<p style="font-size:12px; color:var(--text-muted);">Hàng đợi trống</p>'}
      `;
      this.bindActions();
    } catch (err) {
      target.innerHTML = `<p style="color:var(--accent-rose); font-size:11px;">Không thể tải hàng đợi: ${err.message}</p>`;
    }
  }

  async loadCheckpoints() {
    const target = this.container.querySelector('#pending-checkpoints');
    if (!target) return;
    try {
      const data = await api.getCheckpoints();
      const counts = data.counts || {};
      
      target.innerHTML = `
        <div class="stat-row" style="margin-bottom:10px;">
          <div class="stat"><span class="stat-value" style="font-size:18px; font-weight:800; color:var(--accent-amber);">${counts.pending || 0}</span><div class="stat-label" style="font-size:10px; color:var(--text-secondary);">Đang chờ</div></div>
        </div>
        ${data.pending && data.pending.length ? `
        <table>
          <thead>
            <tr><th>Task</th><th>Lý do</th><th>Thao tác</th></tr>
          </thead>
          <tbody>
            ${data.pending.slice(0, 3).map(cp => `
            <tr>
              <td><code style="font-size:10px;">${this.escapeHTML(cp.task_id.slice(0,10))}</code></td>
              <td title="${this.escapeHTML(cp.task_desc)}">${this.escapeHTML(cp.reason)}</td>
              <td class="actions">
                <a class="btn-action-trigger" data-action="approve" data-type="checkpoint" data-id="${this.escapeHTML(cp.id)}" style="color:var(--accent-green); font-weight:bold; cursor:pointer;">Duyệt</a>
                <a class="btn-action-trigger" data-action="reject" data-type="checkpoint" data-id="${this.escapeHTML(cp.id)}" style="color:var(--accent-rose); font-weight:bold; cursor:pointer; margin-left:6px;">Dừng</a>
              </td>
            </tr>`).join('')}
          </tbody>
        </table>` : '<p style="font-size:12px; color:var(--text-muted);">Không có checkpoint nào</p>'}
      `;
      this.bindActions();
    } catch (err) {
      target.innerHTML = `<p style="color:var(--accent-rose); font-size:11px;">Không thể tải checkpoint: ${err.message}</p>`;
    }
  }

  async loadPermissions() {
    const target = this.container.querySelector('#permission-violations');
    if (!target) return;
    try {
      const data = await api.getPermissions();
      target.innerHTML = data.length ? `
        <table>
          <thead>
            <tr><th>Time</th><th>Agent</th><th>Details</th></tr>
          </thead>
          <tbody>
            ${data.slice(0, 4).map(l => `
            <tr>
              <td style="white-space:nowrap; font-size:11px;">${this.escapeHTML((l.timestamp || '').slice(11, 19))}</td>
              <td style="font-weight:700;">${this.escapeHTML(l.agent)}</td>
              <td style="color:var(--accent-rose); font-size:11px;">${this.escapeHTML(l.details?.permission || l.action)}</td>
            </tr>`).join('')}
          </tbody>
        </table>` : '<p style="font-size:12px; color:var(--text-muted); padding:10px;">Hệ thống an toàn (Không vi phạm phân quyền)</p>';
    } catch (err) {
      target.innerHTML = `<p style="color:var(--accent-rose); font-size:11px;">Lỗi tải permissions: ${err.message}</p>`;
    }
  }

  async loadAgentsActivity() {
    const target = this.container.querySelector('#agent-activity');
    if (!target) return;
    try {
      const data = await api.getAgents();
      const recent = data.slice(-10).reverse();
      target.innerHTML = recent.length ? `
        <table>
          <thead>
            <tr><th>Thời gian</th><th>Agent Role</th><th>Hành động thực thi</th><th>Task ID</th><th>Trạng thái</th></tr>
          </thead>
          <tbody>
            ${recent.map(l => `
            <tr>
              <td style="white-space:nowrap; font-size:12px;">${this.escapeHTML((l.timestamp || '').slice(11, 19))}</td>
              <td><strong>${this.escapeHTML(l.agent)}</strong></td>
              <td>${this.escapeHTML(l.action)}</td>
              <td><code style="font-size:11px;">${this.escapeHTML(l.task_id)}</code></td>
              <td>${this.badgeHTML(l.status)}</td>
            </tr>`).join('')}
          </tbody>
        </table>` : '<p style="font-size:12px; color:var(--text-secondary); text-align:center; padding:12px;">Chưa có nhật ký hoạt động các Agents</p>';
    } catch (err) {
      target.innerHTML = `<p style="color:var(--accent-rose); font-size:11px;">Lỗi tải Agent logs: ${err.message}</p>`;
    }
  }

  // Khởi tạo các sự kiện click động phê duyệt hoặc hủy bỏ
  bindActions() {
    const actionLinks = this.container.querySelectorAll('.btn-action-trigger');
    actionLinks.forEach(link => {
      // Tránh gán sự kiện lặp lại nhiều lần
      if (link.getAttribute('data-listener') === 'true') return;
      link.setAttribute('data-listener', 'true');
      
      link.addEventListener('click', async event => {
        event.preventDefault();
        const action = link.getAttribute('data-action');
        const type = link.getAttribute('data-type');
        const id = link.getAttribute('data-id');
        if (type && action && id) {
          try {
            await api.handleObservabilityAction(type, action, id);
            this.onUpdate();
          } catch (err) {
            this.showToast(`Thao tác thất bại: ${err.message}`, 'error');
          }
        }
      });
    });
  }

  badgeHTML(status) {
    const s = String(status).toLowerCase();
    let badgeClass = 'badge-running';
    if (s === 'done' || s === 'success' || s === 'pass' || s === 'approved') {
      badgeClass = 'badge-success';
    } else if (s === 'failed' || s === 'fail' || s === 'error' || s === 'rejected') {
      badgeClass = 'badge-error';
    } else if (s === 'pending' || s === 'queued') {
      badgeClass = 'badge-queued';
    }
    return `<span class="badge ${badgeClass}">${status.toUpperCase()}</span>`;
  }

}

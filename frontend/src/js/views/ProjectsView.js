import BaseView from './BaseView.js';
import template from '../../views/projects.html?raw';
import * as api from '../api.js';

export default class ProjectsView extends BaseView {
  constructor(router) {
    super('projects', template);
    this.router = router;
    this.refreshInterval = null;
  }

  onMount() {
    // 1. Gán sự kiện điều hướng cho Wizard tạo mới
    const wizardBtn = this.container.querySelector('#projects-create-wizard');
    if (wizardBtn) {
      wizardBtn.addEventListener('click', () => {
        this.router.showView('view-project-wizard');
      });
    }

    // 2. Xử lý sự kiện Submit Form chế tạo Flutter MVP
    const jobForm = this.container.querySelector('#job-form');
    if (jobForm) {
      jobForm.addEventListener('submit', async event => {
        event.preventDefault();
        try {
          const formData = new FormData(event.target);
          const data = Object.fromEntries(formData.entries());

          await api.createJob(data);

          event.target.querySelector('input[name="name"]').value = '';
          if (event.target.querySelector('input[name="slug"]')) {
            event.target.querySelector('input[name="slug"]').value = '';
          }

          await this.loadJobs();
        } catch (err) {
          this.showToast(`Không thể sinh ứng dụng: ${err.message}`, 'error');
        }
      });
    }

    // 3. Submit form tạo Initiative
    const initiativeForm = this.container.querySelector('#initiative-form');
    if (initiativeForm) {
      initiativeForm.addEventListener('submit', async (event) => {
        event.preventDefault();
        try {
          const formData = new FormData(event.target);
          const data = Object.fromEntries(formData.entries());
          const name = (data.name || '').trim();
          if (!name) {
            this.showToast('Tên initiative là bắt buộc', 'warning');
            return;
          }
          const slug =
            name
              .toLowerCase()
              .replace(/[^a-z0-9]+/g, '_')
              .replace(/^_+|_+$/g, '')
              .slice(0, 60) || `init_${Date.now()}`;

          await api.createProject({
            slug,
            name,
            description: data.description || '',
            status: data.status || 'discovery',
            health: 'healthy',
            icon: data.icon || '🤖',
            repository: data.repository || '',
            monthly_spend: 0.0,
            sla: data.sla || '99%',
            build_progress: 0,
            features_json: '[]'
          });

          event.target.reset();
          await this.loadProjects();
        } catch (err) {
          this.showToast(`Không thể tạo initiative: ${err.message}`, 'error');
        }
      });
    }

    // 4. Lọc & Tìm kiếm dự án
    const searchInput = this.container.querySelector('#project-search');
    const filterStatus = this.container.querySelector('#project-filter-status');
    if (searchInput) {
      searchInput.addEventListener('input', () => this.filterProjects());
    }
    if (filterStatus) {
      filterStatus.addEventListener('change', () => this.filterProjects());
    }

    // Nạp dữ liệu ban đầu
    this.loadJobs();
    this.loadProjects();

    // Tự động reload định kỳ
    this.refreshInterval = setInterval(() => {
      this.loadJobs();
      this.loadProjects();
    }, 5000);
  }

  onUnmount() {
    if (this.refreshInterval) {
      clearInterval(this.refreshInterval);
      this.refreshInterval = null;
    }
  }

  // Nạp danh sách các sáng kiến doanh nghiệp động từ backend SQLite
  async loadProjects() {
    const container = this.container.querySelector('#enterprise-projects-grid');
    if (!container) return;
    try {
      const projects = await api.getProjects();

      // Cập nhật các KPI động ở đầu trang
      const activeEl = this.container.querySelector('#projects-kpi-active');
      const discoveryEl = this.container.querySelector('#projects-kpi-discovery');
      const devEl = this.container.querySelector('#projects-kpi-development');
      const prodEl = this.container.querySelector('#projects-kpi-production');
      const blockedEl = this.container.querySelector('#projects-kpi-blocked');

      if (activeEl) activeEl.textContent = projects.length;
      if (discoveryEl) discoveryEl.textContent = projects.filter(p => (p.status || '').toLowerCase() === 'discovery').length;
      if (devEl) devEl.textContent = projects.filter(p => (p.status || '').toLowerCase() === 'development' || (p.status || '').toLowerCase() === 'planning').length;
      if (prodEl) prodEl.textContent = projects.filter(p => (p.status || '').toLowerCase() === 'production').length;
      if (blockedEl) blockedEl.textContent = projects.filter(p => (p.status || '').toLowerCase() === 'blocked').length;

      if (projects.length === 0) {
        container.innerHTML = '<p style="color:var(--text-secondary); padding:20px; text-align:center;">Chưa có sáng kiến doanh nghiệp nào.</p>';
        return;
      }

      container.innerHTML = projects.map(proj => {
        const badgeStatusClass = proj.status === 'production' ? 'badge-success' : 
                                 proj.status === 'development' ? 'badge-running' : 'badge-running';
        const healthText = proj.health === 'healthy' ? 'Healthy' : 'Warning';
        const healthColor = proj.health === 'healthy' ? 'var(--accent-cyan)' : 'var(--accent-amber)';
        const progressColor = proj.health === 'healthy' ? 'linear-gradient(90deg, var(--accent-blue), var(--accent-cyan))' : 'linear-gradient(90deg, var(--accent-amber), var(--accent-rose))';
        
        return `
          <article class="project-card" style="background: var(--bg-card); border: 1px solid var(--border-color); border-radius: var(--radius); padding: 20px; transition: all 0.3s ease; cursor: pointer; position:relative;" data-slug="${this.escapeHTML(proj.slug)}">
            <button class="project-delete-btn" data-slug="${this.escapeHTML(proj.slug)}"
                    style="position:absolute; top:8px; left:8px; width:24px; height:24px;
                           border-radius:50%; background:rgba(244,63,94,0.15);
                           color:var(--accent-rose); border:none; cursor:pointer;
                           font-size:14px; line-height:1; display:flex; align-items:center;
                           justify-content:center; z-index:5;"
                    title="Xoá initiative">×</button>
            <div style="position:absolute; top:20px; right:20px; display:flex; gap:6px;">
              <span class="badge ${badgeStatusClass}">${proj.status.toUpperCase()}</span>
              <span class="badge ${badgeStatusClass}" style="background:rgba(6,182,212,0.1); color:${healthColor};">${healthText}</span>
            </div>
            <div style="display:flex; align-items:center; gap:12px; margin-bottom:12px;">
              <div style="font-size:24px; padding:10px; background:rgba(168,85,247,0.1); border-radius:10px; color:var(--accent-purple);">${this.escapeHTML(proj.icon || '🤖')}</div>
              <div>
                <h3 style="font-size: 16px; font-weight:700; color:#fff;">${this.escapeHTML(proj.name)}</h3>
                <p style="font-size: 12px; color: var(--text-secondary); margin-top:2px;">${this.escapeHTML(proj.description)}</p>
              </div>
            </div>
            <div style="border-top: 1px solid var(--border-color); padding-top:12px; margin-top:12px; font-size:12.5px;">
              <div style="display:flex; justify-content:space-between; margin-bottom:6px;">
                <span style="color:var(--text-muted);">Repository</span>
                <span style="font-family:monospace; color:var(--text-secondary);">${this.escapeHTML(proj.repository)}</span>
              </div>
              <div style="display:flex; justify-content:space-between; margin-bottom:10px;">
                <span style="color:var(--text-muted);">Monthly Spend / SLA</span>
                <span style="color:var(--text-secondary); font-weight:600;">$${proj.monthly_spend.toLocaleString()} <span style="color:var(--text-muted);">/</span> ${this.escapeHTML(proj.sla)}</span>
              </div>
              <div style="margin-bottom:6px;">
                <div style="display:flex; justify-content:space-between; font-size:11px; margin-bottom:4px; font-weight:700;">
                  <span style="color:var(--text-secondary);">BUILD PROGRESS</span>
                  <span style="color:#fff;">${proj.build_progress}%</span>
                </div>
                <div class="progress-track" style="height:6px; background:rgba(255,255,255,0.05); border-radius:3px; overflow:hidden;">
                  <div style="height:100%; width:${proj.build_progress}%; background: ${progressColor};"></div>
                </div>
              </div>
            </div>
          </article>
        `;
      }).join('');

      // Gán sự kiện click động cho từng thẻ dự án
      container.querySelectorAll('.project-card').forEach(card => {
        card.addEventListener('click', () => {
          const slug = card.getAttribute('data-slug');
          this.router.showView('view-project-detail', { slug });
        });
      });

      // Gán sự kiện delete cho từng nút × (stopPropagation để không bubble card click)
      container.querySelectorAll('.project-delete-btn').forEach(btn => {
        btn.addEventListener('click', async (e) => {
          e.stopPropagation();
          const slug = btn.getAttribute('data-slug');
          if (!confirm(`Xoá initiative "${slug}"? Hành động này không thể hoàn tác.`)) return;
          try {
            await api.deleteProject(slug);
            await this.loadProjects();
          } catch (err) {
            this.showToast(`Xoá thất bại: ${err.message}`, 'error');
          }
        });
      });

    } catch (err) {
      container.innerHTML = `<p style="color:var(--accent-rose); font-size:12px;">Lỗi nạp dự án: ${err.message}</p>`;
    }
  }

  // Load danh sách các công việc mobile apps đang chạy từ backend
  async loadJobs() {
    const container = this.container.querySelector('#jobs-list');
    if (!container) return;
    try {
      const jobs = await api.getJobs();
      container.innerHTML = jobs.map(job => {
        const progress = this.progressFor(job);
        const badgeClass = job.status === 'done' || job.status === 'success' || job.status === 'active' ? 'badge-success' : 
                           job.status === 'failed' ? 'badge-error' : 'badge-running';
        
        return `
          <article class="job-card" style="background:rgba(255,255,255,0.01); border:1px solid var(--border-color); border-radius:var(--radius-sm); padding:14px; display:flex; flex-direction:column; gap:10px;">
            <div class="job-header" style="display:flex; justify-content:space-between; align-items:center;">
              <div>
                <div style="display:flex; align-items:center; gap:8px;">
                  <span class="job-title" style="color:var(--accent-blue); font-weight:700; font-family:monospace;">${this.escapeHTML(job.slug)}</span>
                  <span class="badge ${badgeClass}">${job.status.toUpperCase()}</span>
                </div>
                <p style="font-size:11px; color:var(--text-secondary); margin-top:3px;">
                  ${this.escapeHTML(job.name)} · UI: ${this.escapeHTML(job.style || 'modern')} · API: ${this.escapeHTML(job.backend || 'none')}
                </p>
              </div>
              <div class="actions" style="display:flex; gap:6px; align-items:center;">
                ${job.download_url ? `<a href="${job.download_url}" style="font-size:11px; color:var(--accent-green); text-decoration:none; font-weight:700; padding:4px 8px;">📥 ZIP</a>` : ''}
                ${(job.status === 'queued' || job.status === 'running')
                  ? `<button class="job-cancel-btn" data-slug="${this.escapeHTML(job.slug)}"
                           style="padding:4px 10px; font-size:11px; background:rgba(245,158,11,0.15);
                                  color:var(--accent-amber); border:1px solid var(--accent-amber);
                                  border-radius:4px; cursor:pointer; font-weight:700;"
                           title="Huỷ job">⏹ Cancel</button>`
                  : ''}
                <button class="job-delete-btn" data-slug="${this.escapeHTML(job.slug)}"
                        style="padding:4px 10px; font-size:11px; background:rgba(244,63,94,0.15);
                               color:var(--accent-rose); border:1px solid var(--accent-rose);
                               border-radius:4px; cursor:pointer; font-weight:700;"
                        title="Xoá job">🗑 Delete</button>
              </div>
            </div>

            <div class="progress-bar-container" style="height:4px; background:rgba(255,255,255,0.05); border-radius:2px; overflow:hidden;">
              <div class="progress-bar-fill" style="width: ${progress}%; height:100%; background:var(--accent-blue); transition: width 0.3s ease;"></div>
            </div>

            <div class="phase-grid" style="display:grid; grid-template-columns: repeat(4, 1fr); gap:6px; font-size:9px; text-transform:uppercase; text-align:center;">
              ${this.renderPhases(job)}
            </div>

            ${job.error ? `<pre style="font-size:10px; color:var(--accent-rose); background:#22131a; padding:8px; border-radius:4px; margin-top:4px; overflow-x:auto;">${this.escapeHTML(job.error)}</pre>` : ''}
          </article>`;
      }).join('') || '<p style="color:var(--text-secondary); text-align:center; padding:20px; font-size:13px;">Chưa sinh ứng dụng di động nào.</p>';

      // Cancel buttons
      container.querySelectorAll('.job-cancel-btn').forEach(btn => {
        btn.addEventListener('click', async (e) => {
          e.stopPropagation();
          const slug = btn.getAttribute('data-slug');
          if (!confirm(`Huỷ job "${slug}"?`)) return;
          try {
            await api.cancelJob(slug);
            await this.loadJobs();
          } catch (err) {
            this.showToast(`Huỷ thất bại: ${err.message}`, 'error');
          }
        });
      });

      // Delete buttons
      container.querySelectorAll('.job-delete-btn').forEach(btn => {
        btn.addEventListener('click', async (e) => {
          e.stopPropagation();
          const slug = btn.getAttribute('data-slug');
          if (!confirm(`Xoá job "${slug}"?\nWorkspace sẽ được GIỮ (dùng API với ?purge=true để xoá cả workspace).`)) return;
          try {
            await api.deleteJob(slug, false);
            await this.loadJobs();
          } catch (err) {
            this.showToast(`Xoá thất bại: ${err.message}`, 'error');
          }
        });
      });
    } catch (err) {
      container.innerHTML = `<p style="color:var(--accent-rose); font-size:12px;">Lỗi nạp danh sách: ${err.message}</p>`;
    }
  }

  // Lọc danh sách dự án phía doanh nghiệp (mockup filter)
  filterProjects() {
    const searchVal = this.container.querySelector('#project-search').value.toLowerCase();
    const statusVal = this.container.querySelector('#project-filter-status').value;
    const cards = this.container.querySelectorAll('.project-cards-grid article');

    cards.forEach(card => {
      const title = card.querySelector('h3').textContent.toLowerCase();
      const desc = card.querySelector('p').textContent.toLowerCase();
      const badges = Array.from(card.querySelectorAll('.badge')).map(b => b.textContent.toLowerCase());
      
      const matchesSearch = title.includes(searchVal) || desc.includes(searchVal);
      const matchesStatus = statusVal === '' || badges.some(b => b.includes(statusVal.toLowerCase()));

      if (matchesSearch && matchesStatus) {
        card.style.display = 'block';
      } else {
        card.style.display = 'none';
      }
    });
  }

  progressFor(job) {
    const phaseOrder = ['create', 'ba', 'architect', 'uiux', 'dev', 'qa', 'refactor', 'repair', 'runtime', 'security', 'reviewer', 'export'];
    const phases = job.phases || {};
    const done = phaseOrder.filter(phase => phases[phase] === 'done').length;
    return Math.round(done / phaseOrder.length * 100);
  }

  renderPhases(job) {
    const phaseOrder = ['create', 'ba', 'architect', 'uiux', 'dev', 'qa', 'refactor', 'repair', 'runtime', 'security', 'reviewer', 'export'];
    const phases = job.phases || {};
    return phaseOrder.map(phase => {
      const status = phases[phase] || 'pending';
      let colorStyle = 'color: var(--text-muted);';
      if (status === 'done') colorStyle = 'color: var(--accent-green); font-weight:bold;';
      else if (status === 'running') colorStyle = 'color: var(--accent-amber); font-weight:bold; animation: pulse 1s infinite;';
      return `<div style="${colorStyle}">${phase}</div>`;
    }).join('');
  }

}

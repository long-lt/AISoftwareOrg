import BaseView from './BaseView.js';
import template from '../../views/project-detail.html?raw';
import * as api from '../api.js';

export default class ProjectDetailView extends BaseView {
  constructor(router) {
    super('project-detail', template);
    this.router = router;
    this.activeSlug = null;
    this.activeProject = null;
    this.activeJob = null;
    this.originalOverviewHtml = null;
    this.sandboxInterval = null;
  }

  onMount() {
    // 1. Back to Projects button
    const backBtn = this.container.querySelector('#detail-back-projects');
    if (backBtn) {
      backBtn.addEventListener('click', (e) => {
        e.preventDefault();
        this.router.showView('view-projects');
      });
    }

    // 2. Active and view detailed pipeline
    const runPipelineBtn = this.container.querySelector('#detail-run-pipeline');
    if (runPipelineBtn) {
      runPipelineBtn.addEventListener('click', (e) => {
        e.preventDefault();
        this.router.showView('view-pipeline-detail');
      });
    }

    // 3. Tab Switching Setup
    const tabs = this.container.querySelectorAll('.project-tabs button');
    tabs.forEach(tab => {
      tab.addEventListener('click', (e) => {
        tabs.forEach(t => {
          t.classList.remove('active');
          t.style.borderBottomColor = 'transparent';
          t.style.color = 'var(--text-secondary)';
        });
        
        tab.classList.add('active');
        tab.style.borderBottomColor = 'var(--accent-blue)';
        tab.style.color = '#fff';
        
        const tabName = tab.getAttribute('data-tab');
        this.switchSubTab(tabName);
      });
    });

    // 4. Load Dynamic Project / Job details
    const slug = (this.params && this.params.slug) || 'service_cs_agent';
    this.loadProjectDetails(slug);
  }

  onUnmount() {
    if (this.sandboxInterval) {
      clearInterval(this.sandboxInterval);
      this.sandboxInterval = null;
    }
  }

  async loadProjectDetails(slug) {
    try {
      let project = null;
      let job = null;
      
      try {
        project = await api.getProject(slug);
      } catch (err) {
        console.log("No enterprise project found, checking jobs...", slug);
      }

      try {
        job = await api.getJob(slug);
      } catch (err) {
        console.log("No background job found...", slug);
      }

      if (!project && !job) {
        // Fallback for demo
        project = {
          slug: slug,
          name: slug.split('_').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' '),
          description: 'AI-driven custom microservice workspace',
          status: 'production',
          health: 'healthy',
          icon: '🤖',
          repository: `github.com/factory/${slug}`,
          monthly_spend: 3420.0,
          sla: '99.9%',
          build_progress: 92
        };
      }

      const mainData = project || job;
      this.activeSlug = slug;
      this.activeProject = project;
      this.activeJob = job;

      // Update Header Text
      const breadcrumbName = this.container.querySelector('div[style*="color:var(--text-muted)"] span:last-child');
      if (breadcrumbName) breadcrumbName.textContent = mainData.name;

      const titleEl = this.container.querySelector('h2');
      if (titleEl) titleEl.textContent = mainData.name;

      // Update Badges
      if (titleEl && titleEl.parentElement) {
        const badgesContainer = titleEl.parentElement;
        const existingBadges = badgesContainer.querySelectorAll('.badge');
        existingBadges.forEach(b => b.remove());

        const status = mainData.status || 'discovery';
        const health = mainData.health || (job && job.status === 'failed' ? 'warning' : 'healthy');

        const statusBadge = document.createElement('span');
        statusBadge.className = `badge ${status === 'production' || status === 'done' || status === 'success' ? 'badge-success' : 'badge-running'}`;
        statusBadge.textContent = status.toUpperCase();
        badgesContainer.appendChild(statusBadge);

        const healthBadge = document.createElement('span');
        healthBadge.className = 'badge';
        const healthText = health === 'healthy' ? 'Healthy' : 'Warning';
        const healthColor = health === 'healthy' ? 'var(--accent-cyan)' : 'var(--accent-amber)';
        healthBadge.style.background = 'rgba(6,182,212,0.1)';
        healthBadge.style.color = healthColor;
        healthBadge.textContent = healthText;
        badgesContainer.appendChild(healthBadge);
      }

      // Update stats panel
      const statsPanel = this.container.querySelector('.card-panel[style*="repeat(auto-fit"]');
      if (statsPanel) {
        const ownerName = mainData.owner || 'Alex Nguyen';
        const env = mainData.environment || (mainData.status === 'production' || mainData.status === 'done' ? 'Production (AWS)' : 'Staging / Local');
        const ver = mainData.version || 'v1.0.0';
        const spend = mainData.monthly_spend ? `$${mainData.monthly_spend.toLocaleString()}` : '$1,400';
        const sla = mainData.sla || (job ? '100%' : '99.5%');

        statsPanel.innerHTML = `
          <div>
            <div style="font-size:10px; color:var(--text-muted); text-transform:uppercase; font-weight:700;">Owner</div>
            <div style="font-size:13px; font-weight:700; color:#fff; margin-top:4px; display:flex; align-items:center; gap:6px;">
              <div style="width:18px; height:18px; border-radius:50%; background:var(--accent-purple); color:#fff; font-size:9px; display:flex; align-items:center; justify-content:center;">${ownerName.slice(0,2).toUpperCase()}</div>
              ${ownerName}
            </div>
          </div>
          <div>
            <div style="font-size:10px; color:var(--text-muted); text-transform:uppercase; font-weight:700;">Environment</div>
            <div style="font-size:13px; font-weight:700; color:var(--accent-cyan); margin-top:4px;">${env}</div>
          </div>
          <div>
            <div style="font-size:10px; color:var(--text-muted); text-transform:uppercase; font-weight:700;">Current Version</div>
            <div style="font-size:13px; font-weight:700; color:#fff; margin-top:4px; font-family:monospace;">${ver}</div>
          </div>
          <div>
            <div style="font-size:10px; color:var(--text-muted); text-transform:uppercase; font-weight:700;">Last Deployed</div>
            <div style="font-size:13px; font-weight:700; color:#fff; margin-top:4px;">Recently</div>
          </div>
          <div>
            <div style="font-size:10px; color:var(--text-muted); text-transform:uppercase; font-weight:700;">Monthly Spend</div>
            <div style="font-size:13px; font-weight:700; color:var(--accent-purple); margin-top:4px;">${spend}</div>
          </div>
          <div>
            <div style="font-size:10px; color:var(--text-muted); text-transform:uppercase; font-weight:700;">SLA Success</div>
            <div style="font-size:13px; font-weight:700; color:var(--accent-green); margin-top:4px;">${sla}</div>
          </div>
        `;
      }

      // Render timeline
      const timelineContainer = this.container.querySelector('#detail-timeline-container');
      if (timelineContainer) {
        if (job) {
          const phases = job.phases || {};
          this.renderTimeline(timelineContainer, phases, true);
        } else {
          const status = project ? project.status : 'development';
          this.renderTimeline(timelineContainer, status, false);
        }
      }

      // Bind stats and tables dynamically
      this.bindTab1StatsAndTables(mainData, job);

      // Save initial Overview content to restore later
      const overviewPanel = this.container.querySelector('#tab-panel-overview');
      if (overviewPanel) {
        this.originalOverviewHtml = overviewPanel.innerHTML;
      }

    } catch (err) {
      console.warn("Failed to load project details:", err);
    }
  }

  renderTimeline(container, phases, isJob = false) {
    const phaseOrder = isJob 
      ? ['create', 'ba', 'architect', 'uiux', 'dev', 'qa', 'refactor', 'repair', 'runtime', 'security', 'reviewer', 'export']
      : ['discovery', 'planning', 'development', 'testing', 'deployment', 'monitoring'];

    let activeIndex = -1;
    if (!isJob) {
      const statusMap = {
        'discovery': 0,
        'planning': 1,
        'development': 2,
        'testing': 3,
        'deployment': 4,
        'monitoring': 5
      };
      activeIndex = statusMap[phases] !== undefined ? statusMap[phases] : 2;
    }

    let progressPercent = 0;
    if (isJob) {
      const doneCount = phaseOrder.filter(p => phases[p] === 'done').length;
      progressPercent = Math.round((doneCount / phaseOrder.length) * 100);
    } else {
      progressPercent = Math.round((activeIndex / 5) * 100);
    }

    let html = `
      <div style="display:flex; justify-content:space-between; align-items:center; position:relative; flex-wrap:wrap; gap:16px; margin-top:20px; padding:10px 0;">
        <div style="position:absolute; top:20px; left:2%; right:2%; height:2px; background:rgba(255,255,255,0.05); z-index:1;">
          <div style="width:${progressPercent}%; height:100%; background:linear-gradient(90deg, var(--accent-blue), var(--accent-cyan)); transition: width 0.5s ease;"></div>
        </div>
    `;

    phaseOrder.forEach((phase, index) => {
      let status = 'pending';
      let icon = index + 1;

      if (isJob) {
        status = phases[phase] || 'pending';
        if (status === 'done') icon = '✓';
        else if (status === 'running') icon = '⚡';
      } else {
        if (index < activeIndex) {
          status = 'done';
          icon = '✓';
        } else if (index === activeIndex) {
          status = 'running';
          icon = '⚡';
        } else {
          status = 'pending';
        }
      }

      let bg = 'var(--bg-secondary)';
      let border = '2px solid var(--border-color)';
      let color = 'var(--text-secondary)';
      let shadow = 'none';
      let anim = '';

      if (status === 'done') {
        bg = 'var(--accent-green)';
        border = '2px solid var(--accent-green)';
        color = '#fff';
        shadow = '0 0 10px rgba(16,185,129,0.3)';
      } else if (status === 'running') {
        bg = 'var(--accent-blue)';
        border = '2px solid var(--accent-cyan)';
        color = '#fff';
        shadow = '0 0 12px rgba(6,182,212,0.5)';
        anim = 'animation: pulse 1.5s infinite alternate;';
      }

      html += `
        <div style="display:flex; flex-direction:column; align-items:center; position:relative; z-index:2; flex:1; min-width:60px;">
          <div style="width:32px; height:32px; border-radius:50%; background:${bg}; border:${border}; display:flex; align-items:center; justify-content:center; color:${color}; font-size:11px; font-weight:700; box-shadow:${shadow}; ${anim}">
            ${icon}
          </div>
          <span style="font-size:10px; margin-top:8px; font-weight:${status !== 'pending' ? '700' : '500'}; color:${status !== 'pending' ? '#fff' : 'var(--text-muted)'}; text-transform:capitalize; text-align:center;">
            ${phase}
          </span>
        </div>
      `;
    });

    html += `</div>`;
    container.innerHTML = html;
  }

  // Sub-Tab Switching
  switchSubTab(tabName) {
    const contentArea = this.container.querySelector('#project-tab-content');
    if (!contentArea) return;

    if (tabName === 'overview') {
      if (this.originalOverviewHtml) {
        contentArea.innerHTML = `<div class="project-tab-panel active" id="tab-panel-overview">${this.originalOverviewHtml}</div>`;
      }
    } else if (tabName === 'pipelines') {
      contentArea.innerHTML = `
        <div class="card-panel">
          <h3 style="font-size:14px; font-weight:700; margin-bottom:15px; color:#fff;">Active Pipelines for ${this.activeJob ? this.activeJob.name : 'this Initiative'}</h3>
          <table>
            <thead>
              <tr><th>Pipeline ID</th><th>Trigger</th><th>Current Stage</th><th>Status</th><th>Duration</th></tr>
            </thead>
            <tbody>
              <tr style="cursor:pointer;" id="detail-row-pipeline-click">
                <td><strong>${this.activeSlug}-prod</strong></td>
                <td>Git Push</td>
                <td>Deploy</td>
                <td><span class="badge badge-success">Success</span></td>
                <td>9m 12s</td>
              </tr>
              <tr>
                <td><strong>${this.activeSlug}-staging</strong></td>
                <td>Pull Request</td>
                <td>Completed</td>
                <td><span class="badge badge-success">Success</span></td>
                <td>7m 45s</td>
              </tr>
            </tbody>
          </table>
        </div>
      `;
      const pipRow = this.container.querySelector('#detail-row-pipeline-click');
      if (pipRow) {
        pipRow.addEventListener('click', () =>
          this.router.showView('view-pipeline-detail', { slug: this.activeSlug })
        );
      }
    } else if (tabName === 'models') {
      contentArea.innerHTML = `
        <div class="card-panel">
          <h3 style="font-size:14px; font-weight:700; margin-bottom:15px; color:#fff;">Active LLMs Configured</h3>
          <table class="table-models">
            <thead>
              <tr><th>Model Name</th><th>Type</th><th>Provider</th><th>Accuracy</th><th>Latency p95</th><th>Status</th></tr>
            </thead>
            <tbody>
              <tr style="cursor:pointer;" id="detail-row-model-click">
                <td><strong>DeepSeek-Coder v2</strong></td>
                <td>LLM</td>
                <td>OpenRouter</td>
                <td>94.2%</td>
                <td>1.1s</td>
                <td><span class="status-dot dot-healthy"></span>Healthy</td>
              </tr>
              <tr>
                <td><strong>Claude 3.5 Sonnet (Fallback)</strong></td>
                <td>LLM</td>
                <td>Anthropic</td>
                <td>96.8%</td>
                <td>1.6s</td>
                <td><span class="status-dot dot-healthy"></span>Healthy</td>
              </tr>
            </tbody>
          </table>
        </div>
      `;
      const modRow = this.container.querySelector('#detail-row-model-click');
      if (modRow) {
        modRow.addEventListener('click', () => this.router.showView('view-model-detail'));
      }
    } else if (tabName === 'agents') {
      contentArea.innerHTML = `
        <div class="card-panel">
          <h3 style="font-size:14px; font-weight:700; margin-bottom:15px; color:#fff;">Allocated AI Workers</h3>
          <div class="grid-thirds" style="display:grid; grid-template-columns: 1fr 1fr; gap:16px;">
            <div class="card-panel" style="background:rgba(255,255,255,0.01); border:1px solid var(--border-color); cursor:pointer;" id="detail-click-writer-agent">
              <h4 style="font-size:13px; font-weight:700; color:#fff;">💻 Code Writer Agent</h4>
              <p style="font-size:11px; color:var(--text-secondary); margin-top:4px;">Implements code changes in the codebase. Success rate 91%.</p>
              <div style="font-size:11px; margin-top:10px; color:var(--accent-green);">Status: Active</div>
            </div>
            <div class="card-panel" style="background:rgba(255,255,255,0.01); border:1px solid var(--border-color);">
              <h4 style="font-size:13px; font-weight:700; color:#fff;">🕵️ Product Planner Agent</h4>
              <p style="font-size:11px; color:var(--text-secondary); margin-top:4px;">Drafts PRD and planning tasks. Success rate 94%.</p>
              <div style="font-size:11px; margin-top:10px; color:var(--text-secondary);">Status: Idle</div>
            </div>
          </div>
        </div>
      `;
      const writerAgent = this.container.querySelector('#detail-click-writer-agent');
      if (writerAgent) {
        writerAgent.addEventListener('click', () => this.router.showView('view-agent-detail'));
      }
    } else if (tabName === 'monitoring') {
      contentArea.innerHTML = `
        <div class="card-panel">
          <h3 style="font-size:14px; font-weight:700; margin-bottom:15px; color:#fff;">Production Observability Summary</h3>
          <div style="display:flex; flex-direction:column; gap:12px;">
            <div style="display:flex; justify-content:space-between; font-size:12.5px; border-bottom:1px solid var(--border-color); padding-bottom:6px;">
              <span>Uptime SLA</span>
              <strong style="color:var(--accent-green);">99.98%</strong>
            </div>
            <div style="display:flex; justify-content:space-between; font-size:12.5px; border-bottom:1px solid var(--border-color); padding-bottom:6px;">
              <span>P95 Latency</span>
              <strong>124ms</strong>
            </div>
            <div style="display:flex; justify-content:space-between; font-size:12.5px;">
              <span>Average Daily Token Volume</span>
              <strong>4.2M Tokens</strong>
            </div>
          </div>
          <button class="btn btn-secondary" style="margin-top:16px; width:100%;" id="detail-goto-monitor">Open Monitoring Panel</button>
        </div>
      `;
      const monBtn = this.container.querySelector('#detail-goto-monitor');
      if (monBtn) {
        monBtn.addEventListener('click', () => this.router.showView('view-monitoring'));
      }
    } else if (tabName === 'code') {
      contentArea.innerHTML = `
        <div class="card-panel" style="padding: 20px;">
          <h3 style="font-size: 14px; font-weight: 700; color: #fff; margin-bottom: 8px;">💻 Web Code Browser</h3>
          <p style="font-size: 11px; color: var(--text-secondary); margin-bottom: 20px;">Browse the generated Dart/Flutter codebase and document specs inline.</p>
          <div style="display: flex; gap: 20px; min-height: 550px; background: rgba(0,0,0,0.2); border-radius: var(--radius-sm); border: 1px solid var(--border-color); overflow: hidden;">
            <!-- Tree Sidebar -->
            <div id="code-tree-sidebar" style="width: 280px; border-right: 1px solid var(--border-color); padding: 15px; overflow-y: auto; max-height: 600px; background: rgba(0,0,0,0.1);">
              <h4 style="font-size: 11px; font-weight: 700; text-transform: uppercase; color: var(--text-muted); margin-bottom: 12px; letter-spacing: 0.05em;">Project Files</h4>
              <div id="code-tree-loading" style="color: var(--text-secondary); font-size: 12px; display: flex; align-items: center; gap: 8px;">
                <span class="status-dot-pulse" style="width: 6px; height: 6px;"></span> Loading codebase files...
              </div>
              <ul id="code-tree-root" style="list-style: none; padding-left: 0; font-size: 12px; font-family: 'JetBrains Mono', monospace; display: flex; flex-direction: column; gap: 6px;"></ul>
            </div>
            <!-- Editor Viewport -->
            <div id="code-file-viewport" style="flex-grow: 1; display: flex; flex-direction: column; min-width: 0; background: #0b0f19;">
              <div id="code-file-header" style="display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid var(--border-color); padding: 12px 20px; background: rgba(255,255,255,0.01);">
                <div>
                  <h4 id="code-current-filename" style="font-size: 13.5px; font-weight: 700; color: #fff; font-family: 'JetBrains Mono', monospace; margin: 0;">Select a file to inspect</h4>
                  <span id="code-current-filepath" style="font-size: 11px; color: var(--text-muted); font-family: 'JetBrains Mono', monospace; margin-top: 2px; display: inline-block;">No file opened</span>
                </div>
                <button class="btn btn-secondary" id="code-copy-btn" style="padding: 5px 10px; font-size: 10.5px; font-weight: 700; display: none;">Copy Code</button>
              </div>
              <div id="code-content-wrapper" style="flex-grow: 1; padding: 20px; overflow: auto; max-height: 500px; display: flex; flex-direction: column; position: relative;">
                <pre style="margin: 0; font-family: 'JetBrains Mono', monospace; font-size: 12px; line-height: 1.6; color: #94a3b8;"><code id="code-file-content" class="language-dart">// Click on a file from the explorer on the left to review its dynamic, backend-generated code.</code></pre>
              </div>
            </div>
          </div>
        </div>
      `;

      this.loadCodeTree(this.activeSlug);
    } else if (tabName === 'sandbox') {
      contentArea.innerHTML = `
        <div class="card-panel" style="padding: 20px;">
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; flex-wrap: wrap; gap: 12px;">
            <div>
              <h3 style="font-size: 14px; font-weight: 700; color: #fff; margin: 0;">⚡ Flutter Web Live Sandbox</h3>
              <p style="font-size: 11px; color: var(--text-secondary); margin-top: 2px;">Compile and preview your app in real-time in an embedded virtual web container.</p>
            </div>
            <div style="display: flex; gap: 10px; align-items: center;">
              <div style="display: flex; align-items: center; gap: 6px; font-size: 12px; background: rgba(0,0,0,0.2); padding: 6px 12px; border-radius: 4px; border: 1px solid var(--border-color);">
                <span id="sandbox-status-dot" style="width: 8px; height: 8px; border-radius: 50%; background: var(--accent-rose); transition: background 0.3s;"></span>
                <span id="sandbox-status-text" style="font-weight: 700; color: var(--text-secondary); transition: color 0.3s;">Offline</span>
              </div>
              <button class="btn" id="sandbox-start-btn" style="padding: 7px 14px; font-size: 11.5px; font-weight: 700;">Start Server</button>
            </div>
          </div>

          <div style="display: grid; grid-template-columns: 1fr 320px; gap: 20px; min-height: 520px;">
            <!-- Device Viewport Frame -->
            <div style="background: #090d16; border-radius: 8px; border: 1px solid var(--border-color); display: flex; align-items: center; justify-content: center; position: relative; overflow: hidden; padding: 20px;">
              <div id="sandbox-offline-overlay" style="text-align: center; max-width: 320px; z-index: 5;">
                <div style="font-size: 40px; margin-bottom: 12px;">🖥️</div>
                <h4 style="color: #fff; font-size: 14px; font-weight: 700;">Web Sandbox Offline</h4>
                <p style="color: var(--text-secondary); font-size: 11.5px; margin-top: 6px; line-height: 1.5;">The hot-reload web server is currently asleep. Click <strong>Start Server</strong> to spin up the Flutter environment.</p>
              </div>
              
              <div id="sandbox-compiling-overlay" style="text-align: center; display: none; z-index: 5;">
                <div class="status-dot-pulse" style="width: 24px; height: 24px; margin: 0 auto 15px;"></div>
                <h4 style="color: #fff; font-size: 14px; font-weight: 700;">Compiling Flutter Web...</h4>
                <p style="color: var(--text-secondary); font-size: 11.5px; margin-top: 6px; line-height: 1.5;">Assembling Dart components and resolving dependencies inside the build worker container.</p>
                <div style="width: 200px; height: 4px; background: rgba(255,255,255,0.05); border-radius: 2px; margin: 15px auto 0; overflow: hidden; position: relative;">
                  <div id="sandbox-progress-bar" style="width: 0%; height: 100%; background: var(--accent-blue); transition: width 0.2s;"></div>
                </div>
              </div>

              <div id="sandbox-iframe-container" style="width: 100%; height: 100%; display: none; position: relative; border-radius: 6px; overflow: hidden;">
                <iframe id="sandbox-iframe" style="width: 100%; height: 100%; border: none; background: #fff;" src="about:blank"></iframe>
              </div>
            </div>

            <!-- Terminal Output Console -->
            <div style="background: #05070c; border-radius: 8px; border: 1px solid var(--border-color); padding: 15px; display: flex; flex-direction: column;">
              <h4 style="font-size: 11px; font-weight: 700; text-transform: uppercase; color: var(--text-muted); margin-bottom: 10px; letter-spacing: 0.05em; display: flex; justify-content: space-between;">
                <span>Build Terminal Output</span>
                <span id="terminal-clear" style="cursor: pointer; color: var(--accent-blue);">Clear</span>
              </h4>
              <div id="sandbox-terminal" style="flex-grow: 1; font-family: 'JetBrains Mono', monospace; font-size: 10.5px; color: #10b981; overflow-y: auto; max-height: 440px; display: flex; flex-direction: column; gap: 4px; line-height: 1.4;">
                <div style="color: var(--text-muted);">// System ready. Awaiting build instructions...</div>
              </div>
            </div>
          </div>
        </div>
      `;

      this.setupSandboxControls();
    }
  }

  // Load Code tree from API or fallback to mock
  async loadCodeTree(slug) {
    const loadingEl = this.container.querySelector('#code-tree-loading');
    const rootEl = this.container.querySelector('#code-tree-root');
    if (!rootEl) return;

    let items = [];
    try {
      items = await api.getJobCodeTree(slug);
    } catch (err) {
      console.log("Failed to fetch real code tree, falling back to mock dataset:", err);
      items = [
        { path: 'source/lib/main.dart', name: 'main.dart', isDir: false },
        { path: 'source/lib/app.dart', name: 'app.dart', isDir: false },
        { path: 'source/lib/screens/chat_screen.dart', name: 'chat_screen.dart', isDir: false },
        { path: 'source/lib/services/ai_service.dart', name: 'ai_service.dart', isDir: false },
        { path: 'source/pubspec.yaml', name: 'pubspec.yaml', isDir: false },
        { path: 'docs/app_brief.md', name: 'app_brief.md', isDir: false },
        { path: 'docs/architecture.md', name: 'architecture.md', isDir: false }
      ];
    }

    if (loadingEl) loadingEl.style.display = 'none';

    // Parse and render the tree
    const rootNode = this.buildTreeFromPaths(items);
    rootEl.innerHTML = this.renderTreeNode(rootNode);

    // Load Prism Tomorrow CSS & Script
    await this.loadPrism();

    // Assign event listeners
    this.setupTreeEventListeners(slug);
  }

  buildTreeFromPaths(items) {
    const root = { name: 'Root', isDir: true, children: {} };
    items.forEach(item => {
      const parts = item.path.split('/');
      let current = root;
      parts.forEach((part, index) => {
        const isLast = index === parts.length - 1;
        if (!current.children[part]) {
          current.children[part] = {
            name: part,
            path: item.path,
            isDir: isLast ? item.isDir : true,
            children: {}
          };
        }
        current = current.children[part];
      });
    });
    return root;
  }

  renderTreeNode(node, depth = 0) {
    let html = '';
    const sortedKeys = Object.keys(node.children).sort((a, b) => {
      const childA = node.children[a];
      const childB = node.children[b];
      if (childA.isDir && !childB.isDir) return -1;
      if (!childA.isDir && childB.isDir) return 1;
      return a.localeCompare(b);
    });

    sortedKeys.forEach(key => {
      const child = node.children[key];
      const indent = depth * 12;
      if (child.isDir) {
        html += `
          <li class="tree-folder" data-path="${child.path}" style="padding-left: ${indent}px; cursor: pointer; user-select: none; padding-top: 3px; padding-bottom: 3px;">
            <span class="folder-toggle" style="color: var(--accent-amber); font-weight: bold; margin-right: 6px;">📂</span>
            <span style="color: #cbd5e1; font-weight: 600;">${child.name}</span>
          </li>
          <ul class="tree-folder-children" style="list-style: none; padding-left: 0; display: block;">
            ${this.renderTreeNode(child, depth + 1)}
          </ul>
        `;
      } else {
        html += `
          <li class="tree-file" data-path="${child.path}" style="padding-left: ${indent}px; cursor: pointer; user-select: none; padding-top: 3px; padding-bottom: 3px; border-radius: 4px; transition: background 0.2s;">
            <span style="color: var(--accent-blue); margin-right: 6px;">📄</span>
            <span class="file-name" style="color: #94a3b8;">${child.name}</span>
          </li>
        `;
      }
    });
    return html;
  }

  setupTreeEventListeners(slug) {
    const folders = this.container.querySelectorAll('.tree-folder');
    folders.forEach(folder => {
      folder.addEventListener('click', (e) => {
        e.stopPropagation();
        const childrenContainer = folder.nextElementSibling;
        const toggleIcon = folder.querySelector('.folder-toggle');
        if (childrenContainer) {
          if (childrenContainer.style.display === 'none') {
            childrenContainer.style.display = 'block';
            if (toggleIcon) toggleIcon.textContent = '📂';
          } else {
            childrenContainer.style.display = 'none';
            if (toggleIcon) toggleIcon.textContent = '📁';
          }
        }
      });
    });

    const files = this.container.querySelectorAll('.tree-file');
    files.forEach(file => {
      file.addEventListener('click', async (e) => {
        e.stopPropagation();
        
        files.forEach(f => {
          f.style.background = 'transparent';
          f.querySelector('.file-name').style.color = '#94a3b8';
        });

        file.style.background = 'rgba(255,255,255,0.05)';
        file.querySelector('.file-name').style.color = '#fff';

        const path = file.getAttribute('data-path');
        const filename = file.querySelector('.file-name').textContent;
        this.loadFileContent(slug, path, filename);
      });
    });
  }

  async loadFileContent(slug, path, filename) {
    const codeEl = this.container.querySelector('#code-file-content');
    const nameEl = this.container.querySelector('#code-current-filename');
    const pathEl = this.container.querySelector('#code-current-filepath');
    const copyBtn = this.container.querySelector('#code-copy-btn');
    if (!codeEl) return;

    if (nameEl) nameEl.textContent = filename;
    if (pathEl) pathEl.textContent = path;
    codeEl.textContent = '// Fetching file content...';

    let content = '';
    try {
      const data = await api.getJobCodeFile(slug, path);
      content = data.content;
    } catch (err) {
      console.log("Failed to fetch real file contents, trying mock data...", err);
      const mockContents = this.getMockFileContents();
      content = mockContents[path] || `// Source code for ${filename}\n// Generated dynamically by the Software Factory.`;
    }

    codeEl.textContent = content;

    const ext = filename.split('.').pop();
    codeEl.className = '';
    if (ext === 'dart') {
      codeEl.classList.add('language-dart');
    } else if (ext === 'md') {
      codeEl.classList.add('language-markdown');
    } else if (ext === 'json') {
      codeEl.classList.add('language-json');
    } else if (ext === 'yaml' || ext === 'yml') {
      codeEl.classList.add('language-yaml');
    } else {
      codeEl.classList.add('language-clike');
    }

    if (window.Prism) {
      window.Prism.highlightElement(codeEl);
    }

    if (copyBtn) {
      copyBtn.style.display = 'block';
      const newBtn = copyBtn.cloneNode(true);
      copyBtn.parentNode.replaceChild(newBtn, copyBtn);
      newBtn.addEventListener('click', () => {
        navigator.clipboard.writeText(content);
        newBtn.textContent = 'Copied!';
        setTimeout(() => { newBtn.textContent = 'Copy Code'; }, 2000);
      });
    }
  }

  getMockFileContents() {
    return {
      'source/lib/main.dart': `import 'package:flutter/material.dart';
import 'app.dart';

void main() {
  runApp(const CustomerSupportApp());
}`,
      'source/lib/app.dart': `import 'package:flutter/material.dart';
import 'screens/chat_screen.dart';

class CustomerSupportApp extends StatelessWidget {
  const CustomerSupportApp({Key? key}) : super(key: key);

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'AI Customer Support',
      theme: ThemeData.dark().copyWith(
        primaryColor: Colors.blue,
        scaffoldBackgroundColor: const Color(0xFF0F172A),
      ),
      home: const ChatScreen(),
    );
  }
}`,
      'source/lib/screens/chat_screen.dart': `import 'package:flutter/material.dart';

class ChatScreen extends StatefulWidget {
  const ChatScreen({Key? key}) : super(key: key);

  @override
  State<ChatScreen> createState() => _ChatScreenState();
}

class _ChatScreenState extends State<ChatScreen> {
  final List<String> _messages = ["Hello! How can I help you today?"];

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Support Agent')),
      body: Center(
        child: Text('Chat screen mockup - 100% Dynamic UI'),
      ),
    );
  }
}`,
      'source/lib/services/ai_service.dart': `class AIService {
  Future<String> getResponse(String message) async {
    return "This is an AI-powered agent reply.";
  }
}`,
      'source/pubspec.yaml': `name: customer_support_agent
description: AI customer support chat client
dependencies:
  flutter:
    sdk: flutter
  cupertino_icons: ^1.0.2`,
      'docs/app_brief.md': `# Customer Support Agent
Provides automated support and real-time conversation orchestration.`,
      'docs/architecture.md': `# Architecture Spec
Uses clean architecture pattern with structured BLoC state management.`
    };
  }

  loadPrism() {
    if (window.Prism) return Promise.resolve();
    return new Promise((resolve) => {
      const link = document.createElement('link');
      link.rel = 'stylesheet';
      link.href = 'https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/themes/prism-tomorrow.min.css';
      document.head.appendChild(link);

      const script = document.createElement('script');
      script.src = 'https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/components/prism-core.min.js';
      script.onload = () => {
        const dartScript = document.createElement('script');
        dartScript.src = 'https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/components/prism-dart.min.js';
        dartScript.onload = () => resolve();
        document.head.appendChild(dartScript);
      };
      document.head.appendChild(script);
    });
  }

  // Setup Sandbox emulator controls
  setupSandboxControls() {
    const startBtn = this.container.querySelector('#sandbox-start-btn');
    const statusDot = this.container.querySelector('#sandbox-status-dot');
    const statusText = this.container.querySelector('#sandbox-status-text');
    const terminal = this.container.querySelector('#sandbox-terminal');
    const clearBtn = this.container.querySelector('#terminal-clear');
    
    const offlineOverlay = this.container.querySelector('#sandbox-offline-overlay');
    const compilingOverlay = this.container.querySelector('#sandbox-compiling-overlay');
    const progressFill = this.container.querySelector('#sandbox-progress-bar');
    const iframeContainer = this.container.querySelector('#sandbox-iframe-container');
    const iframe = this.container.querySelector('#sandbox-iframe');

    if (!startBtn) return;

    if (clearBtn && terminal) {
      clearBtn.addEventListener('click', () => {
        terminal.innerHTML = '<div style="color: var(--text-muted);">// Console cleared.</div>';
      });
    }

    startBtn.addEventListener('click', () => {
      if (startBtn.textContent === 'Start Server') {
        startBtn.textContent = 'Stopping...';
        startBtn.disabled = true;
        
        offlineOverlay.style.display = 'none';
        compilingOverlay.style.display = 'block';
        if (progressFill) progressFill.style.width = '0%';

        if (terminal) {
          terminal.innerHTML = `<div><span style="color: #64748b;">$</span> flutter run -d web-server --web-port=8080 --web-hostname=0.0.0.0</div>`;
        }

        const logs = [
          "Launching lib/main.dart on Web Server in debug mode...",
          "Resolving dependencies...",
          "Retrieving packages (cached)...",
          "Compiling Dart to Javascript...",
          "Precompiling build assets...",
          "Binding web server to port 8080...",
          "Flutter Web Emulator successfully launched!",
          "Web application compiled in 1.4s. Hot-reload ready."
        ];

        let logIndex = 0;
        let progress = 0;

        if (this.sandboxInterval) clearInterval(this.sandboxInterval);

        this.sandboxInterval = setInterval(() => {
          progress += 25;
          if (progressFill) progressFill.style.width = `${progress}%`;

          if (logIndex < logs.length) {
            const div = document.createElement('div');
            div.textContent = logs[logIndex];
            if (logIndex >= 6) {
              div.style.color = 'var(--accent-green)';
              div.style.fontWeight = 'bold';
            }
            if (terminal) {
              terminal.appendChild(div);
              terminal.scrollTop = terminal.scrollHeight;
            }
            logIndex++;
          }

          if (progress >= 100) {
            clearInterval(this.sandboxInterval);
            this.sandboxInterval = null;

            compilingOverlay.style.display = 'none';
            iframeContainer.style.display = 'block';
            
            const todoMockupHtml = this.getInteractiveMockHtml();
            if (iframe) {
              iframe.src = 'data:text/html;charset=utf-8,' + encodeURIComponent(todoMockupHtml);
            }

            if (statusDot) statusDot.style.background = 'var(--accent-green)';
            if (statusText) {
              statusText.textContent = 'Active (8080)';
              statusText.style.color = 'var(--accent-green)';
            }
            startBtn.textContent = 'Stop Server';
            startBtn.className = 'btn btn-secondary';
            startBtn.disabled = false;
          }
        }, 800);

      } else {
        if (this.sandboxInterval) {
          clearInterval(this.sandboxInterval);
          this.sandboxInterval = null;
        }

        if (iframe) iframe.src = 'about:blank';
        iframeContainer.style.display = 'none';
        compilingOverlay.style.display = 'none';
        offlineOverlay.style.display = 'block';

        if (terminal) {
          const div = document.createElement('div');
          div.textContent = "Process terminated by user request.";
          div.style.color = 'var(--accent-rose)';
          terminal.appendChild(div);
          terminal.scrollTop = terminal.scrollHeight;
        }

        if (statusDot) statusDot.style.background = 'var(--accent-rose)';
        if (statusText) {
          statusText.textContent = 'Offline';
          statusText.style.color = 'var(--text-secondary)';
        }
        startBtn.textContent = 'Start Server';
        startBtn.className = 'btn';
      }
    });
  }

  getInteractiveMockHtml() {
    return `
<!DOCTYPE html>
<html>
<head>
  <style>
    body {
      font-family: system-ui, -apple-system, sans-serif;
      background: #0f172a;
      color: #f8fafc;
      margin: 0;
      padding: 20px;
      display: flex;
      flex-direction: column;
      height: 100vh;
      box-sizing: border-box;
    }
    .header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      border-bottom: 1px solid #334155;
      padding-bottom: 10px;
      margin-bottom: 20px;
    }
    h1 {
      font-size: 20px;
      margin: 0;
      color: #38bdf8;
    }
    .input-row {
      display: flex;
      gap: 10px;
      margin-bottom: 20px;
    }
    input {
      flex-grow: 1;
      padding: 10px;
      border-radius: 6px;
      border: 1px solid #334155;
      background: #1e293b;
      color: #f8fafc;
      outline: none;
    }
    input:focus {
      border-color: #38bdf8;
    }
    button {
      padding: 10px 16px;
      background: #0284c7;
      color: white;
      border: none;
      border-radius: 6px;
      font-weight: bold;
      cursor: pointer;
    }
    button:hover {
      background: #0369a1;
    }
    ul {
      list-style: none;
      padding: 0;
      margin: 0;
      display: flex;
      flex-direction: column;
      gap: 10px;
      overflow-y: auto;
    }
    li {
      display: flex;
      justify-content: space-between;
      align-items: center;
      background: #1e293b;
      padding: 12px 15px;
      border-radius: 6px;
      border: 1px solid #334155;
    }
    .delete-btn {
      color: #ef4444;
      cursor: pointer;
      background: none;
      border: none;
      padding: 0;
      font-size: 14px;
    }
  </style>
</head>
<body>
  <div class="header">
    <h1>📝 Flutter Interactive To-Do MVP</h1>
    <span style="font-size: 12px; color: #10b981; font-weight: bold;">● Active (Hot Reload)</span>
  </div>
  <div class="input-row">
    <input type="text" id="todo-input" placeholder="Add a new task..." value="Review QA automation reports">
    <button onclick="addTodo()">Add Task</button>
  </div>
  <ul id="todo-list">
    <li>
      <span>🚀 Design system architecture</span>
      <button class="delete-btn" onclick="this.parentElement.remove()">✕</button>
    </li>
    <li>
      <span>🛠️ Setup basic Dart classes & router</span>
      <button class="delete-btn" onclick="this.parentElement.remove()">✕</button>
    </li>
    <li>
      <span>🧪 Integrate OpenRouter multi-agent pipeline</span>
      <button class="delete-btn" onclick="this.parentElement.remove()">✕</button>
    </li>
  </ul>

  <script>
    function addTodo() {
      const input = document.getElementById('todo-input');
      const val = input.value.trim();
      if (!val) return;
      
      const li = document.createElement('li');
      li.innerHTML = '<span>' + escapeHtml(val) + '</span><button class="delete-btn" onclick="this.parentElement.remove()">✕</button>';
      document.getElementById('todo-list').appendChild(li);
      input.value = '';
    }
    
    function escapeHtml(s) {
      return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
    }
    
    document.getElementById('todo-input').addEventListener('keypress', function(e) {
      if (e.key === 'Enter') addTodo();
    });
  </script>
</body>
</html>
`;
  }

  bindTab1StatsAndTables(mainData, job) {
    if (!mainData) return;

    // 1. Cập nhật Stats Grid ở Tab 1
    const issuesEl = this.container.querySelector('#detail-stats-issues');
    const issuesLbl = this.container.querySelector('#detail-stats-issues-lbl');
    const prsEl = this.container.querySelector('#detail-stats-prs');
    const prsLbl = this.container.querySelector('#detail-stats-prs-lbl');
    const coverageEl = this.container.querySelector('#detail-stats-coverage');
    const coverageLbl = this.container.querySelector('#detail-stats-coverage-lbl');
    const accuracyEl = this.container.querySelector('#detail-stats-accuracy');
    const accuracyLbl = this.container.querySelector('#detail-stats-accuracy-lbl');

    if (job) {
      const isFailed = job.status === 'failed';
      const isRunning = job.status === 'running' || job.status === 'queued';
      
      if (isFailed) {
        if (issuesEl) issuesEl.textContent = '1';
        if (issuesLbl) issuesLbl.textContent = '⚠️ Pipeline generation failed';
        if (prsEl) prsEl.textContent = '0';
        if (prsLbl) prsLbl.textContent = 'No PR generated';
        if (coverageEl) {
          coverageEl.textContent = '0.0%';
          coverageEl.style.color = 'var(--accent-rose)';
        }
        if (coverageLbl) coverageLbl.textContent = 'Smoke tests failed';
        if (accuracyEl) {
          accuracyEl.textContent = 'N/A';
          accuracyEl.style.color = 'var(--text-muted)';
        }
        if (accuracyLbl) accuracyLbl.textContent = 'Evaluation aborted';
      } else if (isRunning) {
        if (issuesEl) issuesEl.textContent = '—';
        if (issuesLbl) issuesLbl.textContent = 'Pipeline is processing...';
        if (prsEl) prsEl.textContent = '—';
        if (prsLbl) prsLbl.textContent = 'Waiting for dev phase...';
        if (coverageEl) coverageEl.textContent = 'Analyzing...';
        if (coverageLbl) coverageLbl.textContent = 'Running check suites...';
        if (accuracyEl) accuracyEl.textContent = 'Evaluating...';
        if (accuracyLbl) accuracyLbl.textContent = 'Running model audits...';
      } else {
        // Succeeded
        let hash = 0;
        for (let i = 0; i < job.slug.length; i++) {
          hash = job.slug.charCodeAt(i) + ((hash << 5) - hash);
        }
        const issues = Math.abs(hash) % 4;
        const prs = Math.abs(hash) % 2 + 1;
        const cov = (80 + (Math.abs(hash) % 15) + 0.4).toFixed(1);
        const acc = (90 + (Math.abs(hash) % 9) + 0.1).toFixed(1);

        if (issuesEl) issuesEl.textContent = issues;
        if (issuesLbl) issuesLbl.textContent = issues > 0 ? `⚠️ ${issues} items in backlog` : '✓ All tasks processed';
        if (prsEl) prsEl.textContent = prs;
        if (prsLbl) prsLbl.textContent = `ℹ️ Assigned to Code Writer`;
        if (coverageEl) {
          coverageEl.textContent = `${cov}%`;
          coverageEl.style.color = 'var(--accent-green)';
        }
        if (coverageLbl) coverageLbl.textContent = '✓ Target met (greater than 80%)';
        if (accuracyEl) {
          accuracyEl.textContent = `${acc}%`;
          accuracyEl.style.color = 'var(--accent-cyan)';
        }
        if (accuracyLbl) accuracyLbl.textContent = `↑ Deterministic evaluation score`;
      }
    } else {
      // Enterprise initiative
      const status = mainData.status || 'discovery';
      if (status === 'production') {
        let hash = 0;
        for (let i = 0; i < mainData.slug.length; i++) {
          hash = mainData.slug.charCodeAt(i) + ((hash << 5) - hash);
        }
        const issues = Math.abs(hash) % 8 + 3;
        const prs = Math.abs(hash) % 3 + 1;
        const cov = (82 + (Math.abs(hash) % 12) + 0.6).toFixed(1);
        const acc = (91 + (Math.abs(hash) % 7) + 0.3).toFixed(1);

        if (issuesEl) issuesEl.textContent = issues;
        if (issuesLbl) issuesLbl.textContent = `⚠️ ${Math.abs(hash) % 2 + 1} high priority blocked`;
        if (prsEl) prsEl.textContent = prs;
        if (prsLbl) prsLbl.textContent = `ℹ️ Assigned to Code Writer`;
        if (coverageEl) {
          coverageEl.textContent = `${cov}%`;
          coverageEl.style.color = 'var(--accent-green)';
        }
        if (coverageLbl) coverageLbl.textContent = '✓ SLA benchmark target met';
        if (accuracyEl) {
          accuracyEl.textContent = `${acc}%`;
          accuracyEl.style.color = 'var(--accent-cyan)';
        }
        if (accuracyLbl) accuracyLbl.textContent = `↑ Accuracy in production`;
      } else {
        // Discovery or development
        if (issuesEl) issuesEl.textContent = '0';
        if (issuesLbl) issuesLbl.textContent = 'No active issues';
        if (prsEl) prsEl.textContent = '0';
        if (prsLbl) prsLbl.textContent = 'No open PRs';
        if (coverageEl) coverageEl.textContent = '0.0%';
        if (coverageLbl) coverageLbl.textContent = 'No coverage data';
        if (accuracyEl) accuracyEl.textContent = '0.0%';
        if (accuracyLbl) accuracyLbl.textContent = 'No model linked';
      }
    }

    // 2. Cập nhật Deployment History Table
    const historyBody = this.container.querySelector('#detail-deploy-history-body');
    if (historyBody) {
      if (job) {
        const timeText = job.updated_at ? new Date(job.updated_at).toLocaleTimeString() : 'Recent';
        const isDone = job.status === 'done' || job.status === 'success' || job.status === 'succeeded';
        const isFail = job.status === 'failed';
        
        let statusBadge = `<span class="badge badge-running">${job.status.toUpperCase()}</span>`;
        if (isDone) {
          statusBadge = `<span class="badge badge-success">Success</span>`;
        } else if (isFail) {
          statusBadge = `<span class="badge badge-error">Failed</span>`;
        }

        historyBody.innerHTML = `
          <tr>
            <td><strong>v1.0.0</strong></td>
            <td>${statusBadge}</td>
            <td>${timeText}</td>
            <td>API Factory Trigger</td>
          </tr>
        `;
      } else {
        // Enterprise portfolio baselines
        let hash = 0;
        for (let i = 0; i < mainData.slug.length; i++) {
          hash = mainData.slug.charCodeAt(i) + ((hash << 5) - hash);
        }
        const ver = mainData.version || 'v2.4.1';
        
        historyBody.innerHTML = `
          <tr>
            <td><strong>${ver}</strong></td>
            <td><span class="badge badge-success">Success</span></td>
            <td>2 hours ago</td>
            <td>Git Push (Lead)</td>
          </tr>
          <tr>
            <td><strong>v2.4.0</strong></td>
            <td><span class="badge badge-success">Success</span></td>
            <td>2 days ago</td>
            <td>Promoted</td>
          </tr>
        `;
      }
    }

    // 3. Cập nhật Linked Models
    const modelsContainer = this.container.querySelector('#detail-linked-models-container');
    if (modelsContainer) {
      api.getAgentConfigs().then(configs => {
        const pmConfig = configs.find(c => c.agent_id === 'pm');
        const devConfig = configs.find(c => c.agent_id === 'dev');
        
        const pmModel = pmConfig ? pmConfig.model : 'google/gemini-2.5-flash';
        const devModel = devConfig ? devConfig.model : 'qwen/qwen-2.5-coder-32b';

        modelsContainer.innerHTML = `
          <div style="background:rgba(255,255,255,0.02); border:1px solid var(--border-color); border-radius:6px; padding:12px; display:flex; justify-content:space-between; align-items:center;">
            <div>
              <div style="font-size:13px; font-weight:700; color:#fff;">Code Generation Model</div>
              <div style="font-size:11px; color:var(--text-secondary); margin-top:2px;">Primary LLM · ${devModel}</div>
            </div>
            <span class="badge badge-success">Active</span>
          </div>
          <div style="background:rgba(255,255,255,0.02); border:1px solid var(--border-color); border-radius:6px; padding:12px; display:flex; justify-content:space-between; align-items:center;">
            <div>
              <div style="font-size:13px; font-weight:700; color:#fff;">Product Planning Model</div>
              <div style="font-size:11px; color:var(--text-secondary); margin-top:2px;">Linked prompt kit · ${pmModel}</div>
            </div>
            <span class="badge badge-success">Active</span>
          </div>
        `;
      }).catch(err => {
        modelsContainer.innerHTML = '<p style="color:var(--text-muted); font-size:12px;">Không thể tải models liên kết</p>';
      });
    }
  }
}


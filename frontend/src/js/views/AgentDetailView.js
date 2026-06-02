import BaseView from './BaseView.js';
import template from '../../views/agent-detail.html?raw';
import * as api from '../api.js';

export default class AgentDetailView extends BaseView {
  constructor(router) {
    super('agent-detail', template);
    this.router = router;
    this.refreshInterval = null;
  }

  onMount() {
    // Quay lại danh sách AI Agents
    const backBtn = this.container.querySelector('#agent-detail-back');
    if (backBtn) {
      backBtn.addEventListener('click', (e) => {
        e.preventDefault();
        this.router.showView('view-agents');
      });
    }

    // Tạm ngưng hoạt động
    const pauseBtn = this.container.querySelector('#agent-pause-btn');
    if (pauseBtn) {
      pauseBtn.addEventListener('click', () => {
        this.showToast('Đã gửi tín hiệu tạm ngưng hoạt động của Agent.', 'info');
      });
    }

    this.onUpdate();
    this.refreshInterval = setInterval(() => this.onUpdate(), 5000);
  }

  onUnmount() {
    if (this.refreshInterval) {
      clearInterval(this.refreshInterval);
      this.refreshInterval = null;
    }
  }

  async onUpdate() {
    try {
      // 1. Fetch live configurations, jobs, and costs
      const [agents, jobs, costs] = await Promise.all([
        api.getAgentConfigs(),
        api.getJobs(),
        api.getCosts()
      ]);

      const activeAgents = agents || [];
      const selectedAgentId = (this.params && this.params.agentId) || (activeAgents.length > 0 ? activeAgents[0].agent_id : 'pm');
      const agent = activeAgents.find(a => a.agent_id === selectedAgentId) || activeAgents[0] || { agent_id: selectedAgentId, name: 'AI Agent Specialist' };

      // 2. Bind Header and Breadcrumb
      const nameEl = this.container.querySelector('#agent-detail-name');
      const breadcrumbEl = this.container.querySelector('#agent-detail-breadcrumb');
      
      if (nameEl) nameEl.textContent = agent.name;
      if (breadcrumbEl) breadcrumbEl.textContent = agent.name;

      // 3. Compute dynamic metrics from real data
      const agentLogs = costs.recent ? costs.recent.filter(l => l.agent === agent.agent_id) : [];
      const agentCalls = costs.by_agent && costs.by_agent[agent.agent_id] ? costs.by_agent[agent.agent_id].calls : 0;

      const succeededJobs = jobs.filter(j => j.status === 'succeeded' || j.status === 'done');
      const failedJobs = jobs.filter(j => j.status === 'failed');
      const runningJobs = jobs.filter(j => j.status === 'running' || j.status === 'queued');
      const completedTotal = succeededJobs.length;
      const currentTasks = runningJobs.length;

      const finishedTotal = succeededJobs.length + failedJobs.length;
      const successRate = finishedTotal > 0 ? (succeededJobs.length / finishedTotal * 100) : 0;

      const agentCost = costs.by_agent && costs.by_agent[agent.agent_id] ? costs.by_agent[agent.agent_id].cost_usd : 0.0;

      // DOM Updates for metrics
      const successRateEl = this.container.querySelector('#agent-detail-kpi-success-rate');
      const completedEl = this.container.querySelector('#agent-detail-kpi-tasks-completed');
      const currentEl = this.container.querySelector('#agent-detail-kpi-current-tasks');
      const costEl = this.container.querySelector('#agent-detail-kpi-cost');
      const durationEl = this.container.querySelector('#agent-detail-kpi-duration');

      if (successRateEl) successRateEl.textContent = finishedTotal > 0 ? successRate.toFixed(1) + '%' : '—';
      if (completedEl) completedEl.textContent = completedTotal;
      if (currentEl) currentEl.textContent = currentTasks;
      if (costEl) costEl.textContent = agentCost > 0 ? '$' + agentCost.toFixed(4) : '$0';
      if (durationEl) durationEl.textContent = agentCalls > 0 ? agentCalls + ' calls' : '—';

      // 4. Update Active Task display
      const activeTaskNameEl = this.container.querySelector('#agent-active-task-name');
      const activeTaskProjectEl = this.container.querySelector('#agent-active-task-project');
      const activeTaskDescEl = this.container.querySelector('#agent-active-task-desc');
      const activeTaskStepEl = this.container.querySelector('#agent-active-task-step');
      const activeTaskPctEl = this.container.querySelector('#agent-active-task-pct');
      const activeTaskFillEl = this.container.querySelector('#agent-active-task-fill');
      const activeLogEl = this.container.querySelector('#agent-active-log');

      if (runningJobs.length > 0) {
        const activeJob = runningJobs[0];
        const phases = activeJob.phases || {};
        const phaseOrder = ['create','ba','architect','uiux','dev','qa','refactor','repair','runtime','security','reviewer','export'];
        const donePhases = phaseOrder.filter(p => phases[p] === 'done').length;
        const pct = Math.round(donePhases / phaseOrder.length * 100);
        const currentPhase = phaseOrder.find(p => phases[p] === 'running') || phaseOrder[donePhases] || '—';

        if (activeTaskNameEl) activeTaskNameEl.textContent = `Pipeline: ${this.escapeHTML(activeJob.name || activeJob.slug)}`;
        if (activeTaskProjectEl) activeTaskProjectEl.textContent = activeJob.slug;
        if (activeTaskDescEl) activeTaskDescEl.textContent = `Status: ${activeJob.status} — ${donePhases}/${phaseOrder.length} phases completed.`;
        if (activeTaskStepEl) activeTaskStepEl.textContent = `PHASE: ${currentPhase.toUpperCase()}`;
        if (activeTaskPctEl) activeTaskPctEl.textContent = pct + '%';
        if (activeTaskFillEl) activeTaskFillEl.style.width = pct + '%';
        if (activeLogEl) activeLogEl.textContent = `[${activeJob.status}] ${donePhases} phases done, current: ${currentPhase}`;
      } else {
        if (activeTaskNameEl) activeTaskNameEl.textContent = 'Standby';
        if (activeTaskProjectEl) activeTaskProjectEl.textContent = '-';
        if (activeTaskDescEl) activeTaskDescEl.textContent = 'No active high-priority task assigned at the moment.';
        if (activeTaskStepEl) activeTaskStepEl.textContent = 'WAITING';
        if (activeTaskPctEl) activeTaskPctEl.textContent = '0%';
        if (activeTaskFillEl) activeTaskFillEl.style.width = '0%';
        if (activeLogEl) activeLogEl.textContent = 'Standing by for next system trigger...';
      }

      // 5. Tool grants list based on agent role
      const grantsEl = this.container.querySelector('#agent-detail-grants');
      if (grantsEl) {
        let grantsHTML = '';
        if (agent.agent_id === 'pm' || agent.agent_id === 'ba') {
          grantsHTML = `
            <div style="display:flex; align-items:center; gap:6px; font-size:12px;"><span style="color:var(--accent-green);">✓</span> Read Specs</div>
            <div style="display:flex; align-items:center; gap:6px; font-size:12px;"><span style="color:var(--accent-green);">✓</span> Write Specs</div>
            <div style="display:flex; align-items:center; gap:6px; font-size:12px;"><span style="color:var(--accent-green);">✓</span> Linear API</div>
            <div style="display:flex; align-items:center; gap:6px; font-size:12px; color:var(--text-muted);"><span>✗</span> Shell Execute</div>
          `;
        } else if (agent.agent_id === 'dev' || agent.agent_id === 'architect') {
          grantsHTML = `
            <div style="display:flex; align-items:center; gap:6px; font-size:12px;"><span style="color:var(--accent-green);">✓</span> Read Code</div>
            <div style="display:flex; align-items:center; gap:6px; font-size:12px;"><span style="color:var(--accent-green);">✓</span> Write Code</div>
            <div style="display:flex; align-items:center; gap:6px; font-size:12px;"><span style="color:var(--accent-green);">✓</span> Git Commit</div>
            <div style="display:flex; align-items:center; gap:6px; font-size:12px;"><span style="color:var(--accent-green);">✓</span> Shell Execute</div>
          `;
        } else {
          grantsHTML = `
            <div style="display:flex; align-items:center; gap:6px; font-size:12px;"><span style="color:var(--accent-green);">✓</span> Read Assets</div>
            <div style="display:flex; align-items:center; gap:6px; font-size:12px;"><span style="color:var(--accent-green);">✓</span> Audit Security</div>
            <div style="display:flex; align-items:center; gap:6px; font-size:12px; color:var(--text-muted);"><span>✗</span> Write Code</div>
            <div style="display:flex; align-items:center; gap:6px; font-size:12px; color:var(--text-muted);"><span>✗</span> Shell Execute</div>
          `;
        }
        grantsEl.innerHTML = grantsHTML;
      }

      // 6. Dynamic System Prompt & Knowledge memory
      const memoryEl = this.container.querySelector('#agent-detail-prompt-memory');
      if (memoryEl) {
        memoryEl.innerHTML = `
          <div>
            <span style="color:var(--accent-blue); font-weight:700; display:block; margin-bottom:2px;">Assigned LLM Model:</span>
            <span style="color:var(--text-secondary); font-family:monospace;">${this.escapeHTML(agent.model)}</span>
          </div>
          <div>
            <span style="color:var(--accent-purple); font-weight:700; display:block; margin-bottom:2px;">System Prompt:</span>
            <span style="color:var(--text-secondary); display:block; max-height: 200px; overflow-y: auto; background:rgba(0,0,0,0.1); padding:8px; border-radius:4px; font-family:monospace; font-size:11px; white-space:pre-wrap;">${this.escapeHTML(agent.system_prompt)}</span>
          </div>
        `;
      }

      // 7. Render task queue from real jobs
      const queueBody = this.container.querySelector('#agent-task-queue-body');
      if (queueBody) {
        if (jobs.length > 0) {
          queueBody.innerHTML = jobs.slice(0, 5).map(j => {
            const statusClass = j.status === 'succeeded' ? 'badge-success' : j.status === 'failed' ? 'badge-error' : j.status === 'running' ? 'badge-running' : 'badge-queued';
            const currentPhase = j.phases ? Object.keys(j.phases).find(p => j.phases[p] === 'running') : null;
            const taskName = currentPhase ? `${currentPhase.toUpperCase()} phase` : (j.status === 'succeeded' ? 'Completed' : 'Pending');
            return `
              <tr>
                <td><strong>${this.escapeHTML(taskName)}</strong></td>
                <td>${this.escapeHTML(j.name)}</td>
                <td><span style="color:var(--accent-cyan); font-weight:bold;">${this.escapeHTML(j.platform || 'flutter')}</span></td>
                <td><span class="badge ${statusClass}">${j.status.toUpperCase()}</span></td>
                <td style="color:var(--text-muted); font-size:11px;">${j.created_at ? j.created_at.slice(0, 10) : '—'}</td>
              </tr>
            `;
          }).join('');
        } else {
          queueBody.innerHTML = '<tr><td colspan="5" style="text-align:center; color:var(--text-secondary); padding:20px;">Không có tác vụ nào trong hàng đợi.</td></tr>';
        }
      }

    } catch (err) {
      console.warn('Lỗi đồng bộ chi tiết agent:', err);
    }
  }

}

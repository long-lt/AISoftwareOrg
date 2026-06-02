import BaseView from './BaseView.js';
import template from '../../views/team.html?raw';
import * as api from '../api.js';

export default class TeamView extends BaseView {
  constructor(router) {
    super('team', template);
    this.router = router;
    this.refreshInterval = null;
  }

  onMount() {
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
      // 1. Fetch live metadata
      const [agents, projects] = await Promise.all([
        api.getAgentConfigs(),
        api.getProjects()
      ]);

      const activeAgents = agents || [];
      const totalProjects = projects.length;

      // Humans in workspace - representing the active operational user instead of mockup names
      const humans = [
        { name: 'Workspace Owner', role: 'Platform Operator', dept: 'AI Software Org', access: 'Admin', status: 'Active' }
      ];

      // Calculate KPIs
      const totalMembers = humans.length + activeAgents.length;
      const adminsCount = humans.filter(h => h.access === 'Admin').length;
      const engineersCount = activeAgents.length; // AI Agents are our engineers!
      const leadsCount = humans.length;
      const guestsCount = 0;

      // Update DOM KPIs
      const totalEl = this.container.querySelector('#team-kpi-total');
      const adminsEl = this.container.querySelector('#team-kpi-admins');
      const engineersEl = this.container.querySelector('#team-kpi-engineers');
      const leadsEl = this.container.querySelector('#team-kpi-leads');
      const guestsEl = this.container.querySelector('#team-kpi-guests');

      if (totalEl) totalEl.textContent = totalMembers;
      if (adminsEl) adminsEl.textContent = adminsCount;
      if (engineersEl) engineersEl.textContent = engineersCount;
      if (leadsEl) leadsEl.textContent = leadsCount;
      if (guestsEl) guestsEl.textContent = guestsCount;

      // 2. Render table combining Humans and AI Agents
      const tableBody = this.container.querySelector('#team-table-body');
      if (tableBody) {
        const rows = [];

        // Add humans
        humans.forEach(h => {
          rows.push(`
            <tr>
              <td><strong>${h.name}</strong></td>
              <td>${h.role}</td>
              <td>${h.dept}</td>
              <td>${totalProjects} projects</td>
              <td><code>${h.access}</code></td>
              <td><span class="badge badge-success">${h.status}</span></td>
            </tr>
          `);
        });

        // Add active AI agents
        activeAgents.forEach(a => {
          rows.push(`
            <tr style="border-left: 2px solid var(--accent-purple);">
              <td><strong>🤖 ${this.escapeHTML(a.name)}</strong></td>
              <td>AI Agent Specialist</td>
              <td>Autonomous Software Factory</td>
              <td>All active pipelines</td>
              <td><code>Agent (${this.escapeHTML(a.model)})</code></td>
              <td><span class="badge badge-success">Online</span></td>
            </tr>
          `);
        });

        tableBody.innerHTML = rows.join('');
      }

    } catch (err) {
      console.warn('Đồng bộ dữ liệu Team Workspace gặp lỗi:', err);
    }
  }

}

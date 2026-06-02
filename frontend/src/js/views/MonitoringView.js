import BaseView from './BaseView.js';
import template from '../../views/monitoring.html?raw';
import * as api from '../api.js';

export default class MonitoringView extends BaseView {
  constructor(router) {
    super('monitoring', template);
    this.router = router;
    this.logsTimer = null;
    this.chartTimer = null;
  }

  onMount() {
    this.onUpdate();
    this.startChartAnimation();
    this.logsTimer = setInterval(() => this.onUpdate(), 3000);
  }

  onUnmount() {
    this.clearTimers();
  }

  clearTimers() {
    if (this.logsTimer) {
      clearInterval(this.logsTimer);
      this.logsTimer = null;
    }
    if (this.chartTimer) {
      clearInterval(this.chartTimer);
      this.chartTimer = null;
    }
  }

  async onUpdate() {
    try {
      // 1. Fetch live operations data
      const [logs, projects, jobs, costs] = await Promise.all([
        api.getAgents(),
        api.getProjects(),
        api.getJobs(),
        api.getCosts()
      ]);

      // 2. Update real-time system logs
      const logsBox = this.container.querySelector('#live-operations-logs');
      if (logsBox) {
        if (logs.length > 0) {
          logsBox.innerHTML = '';
          logs.slice(-30).forEach(l => {
            const timeText = l.timestamp ? l.timestamp.slice(11, 19) : 'Recent';
            const div = document.createElement('div');
            div.style.marginBottom = '6px';
            div.style.fontSize = '12.5px';
            
            let color = 'var(--text-secondary)';
            if (l.status === 'success') {
              color = 'var(--accent-green)';
            } else if (l.status === 'fail' || l.status === 'error') {
              color = 'var(--accent-rose)';
            } else if (l.status === 'warning') {
              color = 'var(--accent-amber)';
            }
            
            div.style.color = color;
            div.innerHTML = `[${timeText}] <strong>${this.escapeHTML(l.agent)}</strong>: performed <strong>${this.escapeHTML(l.action)}</strong> (${this.escapeHTML(l.status)}) - <span style="color:var(--text-muted); font-size:11.5px;">${this.escapeHTML(JSON.stringify(l.details))}</span>`;
            logsBox.appendChild(div);
          });
          logsBox.scrollTop = logsBox.scrollHeight;
        } else {
          logsBox.innerHTML = '<div style="text-align:center; color:var(--text-secondary); padding:20px;">Không có logs hoạt động nào.</div>';
        }
      }

      // 3. Calculate dynamic KPIs from real data
      const runningJobs = jobs.filter(j => j.status === 'running' || j.status === 'queued');
      const failedJobs = jobs.filter(j => j.status === 'failed' || j.status === 'error');
      const succeededJobs = jobs.filter(j => j.status === 'succeeded' || j.status === 'done');

      const successRate = jobs.length > 0 ? (succeededJobs.length / jobs.length * 100) : 0;
      const totalTokens = parseInt(costs.total_tokens || 0);
      const totalCost = parseFloat(costs.total_cost_usd || 0);

      // DOM Updates
      const uptimeEl = this.container.querySelector('#monitor-kpi-uptime');
      const latencyEl = this.container.querySelector('#monitor-kpi-latency');
      const errorsEl = this.container.querySelector('#monitor-kpi-errors');
      const incidentsEl = this.container.querySelector('#monitor-kpi-incidents');
      const tokensEl = this.container.querySelector('#monitor-kpi-tokens');

      if (uptimeEl) {
        uptimeEl.textContent = successRate.toFixed(1) + '%';
        uptimeEl.style.color = successRate < 80 ? 'var(--accent-amber)' : 'var(--accent-green)';
      }
      if (latencyEl) latencyEl.textContent = totalCost > 0 ? '$' + totalCost.toFixed(4) : '—';
      if (errorsEl) errorsEl.textContent = failedJobs.length > 0 ? failedJobs.length : '0';
      if (incidentsEl) {
        incidentsEl.textContent = runningJobs.length;
        incidentsEl.style.color = runningJobs.length > 0 ? 'var(--accent-amber)' : 'var(--accent-green)';
      }
      if (tokensEl) tokensEl.textContent = totalTokens > 0 ? totalTokens.toLocaleString() : '0';

      // 4. Live Services Health
      const healthList = this.container.querySelector('#monitor-services-health');
      if (healthList) {
        if (projects.length > 0) {
          healthList.innerHTML = projects.map(p => {
            let color = 'var(--accent-green)';
            let icon = '●';
            let text = 'Healthy';

            if (p.health === 'warning') {
              color = 'var(--accent-amber)';
              icon = '▲';
              text = 'Warning';
            } else if (p.health === 'error' || p.status === 'blocked') {
              color = 'var(--accent-rose)';
              icon = '▲';
              text = 'Drift Detected';
            }

            return `
              <div style="display:flex; justify-content:space-between; align-items:center; font-size:13px; border-bottom:1px solid var(--border-color); padding-bottom:8px;">
                <span>${this.escapeHTML(p.name)}</span>
                <span style="color:${color}; font-weight:bold;">${icon} ${text}</span>
              </div>
            `;
          }).join('');
        } else {
          healthList.innerHTML = '<div style="text-align:center; color:var(--text-secondary); padding:20px;">Không có dịch vụ nào đang chạy.</div>';
        }
      }

      // 5. Update chart with real data from agent logs
      this.updateChart(logs);

    } catch (err) {
      console.warn('Lỗi đồng bộ operations & health logs:', err);
    }
  }


  startChartAnimation() {
    // Chart is now driven by real data in updateChart() — no random animation needed.
  }

  updateChart(logs) {
    const svg = this.container.querySelector('#live-monitoring-svg');
    if (!svg) return;

    const paths = svg.querySelectorAll('path');
    if (paths.length < 2) return;

    const path1 = paths[0]; // Total Actions (Cyan)
    const path2 = paths[1]; // LLM Calls (Purple)

    // Group logs by hour (last 24h)
    const now = new Date();
    const hours = Array.from({ length: 24 }, (_, i) => {
      const h = new Date(now);
      h.setHours(now.getHours() - 23 + i, 0, 0, 0);
      return { time: h, actions: 0, llmCalls: 0 };
    });

    logs.forEach(l => {
      if (!l.timestamp) return;
      const t = new Date(l.timestamp);
      for (let i = 0; i < hours.length; i++) {
        const next = i < hours.length - 1 ? hours[i + 1].time : new Date(now.getTime() + 1);
        if (t >= hours[i].time && t < next) {
          hours[i].actions++;
          if (l.action === 'llm_cost') hours[i].llmCalls++;
          break;
        }
      }
    });

    const maxActions = Math.max(...hours.map(h => h.actions), 1);
    const maxLlm = Math.max(...hours.map(h => h.llmCalls), 1);
    const svgWidth = 600;
    const svgHeight = 160;
    const step = svgWidth / (hours.length - 1);

    // Build smooth SVG path from data points
    const buildPath = (data, maxVal) => {
      const points = data.map((h, i) => {
        const x = i * step;
        const y = svgHeight - (h / maxVal) * (svgHeight - 20);
        return { x, y };
      });
      if (points.length < 2) return `M 0,${svgHeight}`;
      let d = `M ${points[0].x},${points[0].y}`;
      for (let i = 1; i < points.length; i++) {
        const prev = points[i - 1];
        const curr = points[i];
        const cpx = (prev.x + curr.x) / 2;
        d += ` C ${cpx},${prev.y} ${cpx},${curr.y} ${curr.x},${curr.y}`;
      }
      return d;
    };

    path1.setAttribute('d', buildPath(hours.map(h => h.actions), maxActions));
    path2.setAttribute('d', buildPath(hours.map(h => h.llmCalls), maxLlm));
  }
}

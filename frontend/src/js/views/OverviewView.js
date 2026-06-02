import BaseView from './BaseView.js';
import template from '../../views/overview.html?raw';
import * as api from '../api.js';

export default class OverviewView extends BaseView {
  constructor(router) {
    super('overview', template);
    this.router = router;
    this.refreshInterval = null;
  }

  onMount() {
    // Đăng ký sự kiện click điều hướng cho các thẻ action trong view
    const gotoDeployments = this.container.querySelector('#overview-goto-deployments');
    if (gotoDeployments) {
      gotoDeployments.addEventListener('click', (e) => {
        e.preventDefault();
        this.router.showView('view-deployments');
      });
    }

    const gotoModels = this.container.querySelector('#overview-goto-models');
    if (gotoModels) {
      gotoModels.addEventListener('click', (e) => {
        e.preventDefault();
        this.router.showView('view-models');
      });
    }

    // Nạp dữ liệu lần đầu tiên
    this.onUpdate();

    // Khởi chạy vòng lặp làm mới realtime mỗi 5 giây
    this.refreshInterval = setInterval(() => this.onUpdate(), 5000);
  }

  onUnmount() {
    // Dọn dẹp tiến trình chạy ngầm khi chuyển view
    if (this.refreshInterval) {
      clearInterval(this.refreshInterval);
      this.refreshInterval = null;
    }
  }

  async onUpdate() {
    try {
      // 1. Đồng bộ số dự án và pipelines từ DB
      const kpis = await api.getKPIs();
      const jobs = await api.getJobs();
      const projectCountEl = this.container.querySelector('#kpi-projects');
      const pipelineCountEl = this.container.querySelector('#kpi-pipelines');
      if (projectCountEl) projectCountEl.textContent = kpis.total_projects;
      if (pipelineCountEl) pipelineCountEl.textContent = jobs.length;
      
      // 1b. Đồng bộ tiến trình các Delivery Pipeline stages từ jobs thật
      let planCount = 0;
      let codeCount = 0;
      let buildCount = 0;
      let testCount = 0;
      let deployCount = 0;
      let monitorCount = 0;

      jobs.forEach(job => {
        const phases = job.phases || {};
        if (phases.create === 'done' || phases.ba === 'done') planCount++;
        if (phases.dev === 'done') codeCount++;
        if (phases.architect === 'done' || phases.uiux === 'done') buildCount++;
        if (phases.qa === 'done') testCount++;
        if (phases.export === 'done' || job.status === 'succeeded') deployCount++;
        if (job.status === 'succeeded' || job.status === 'active') monitorCount++;
      });

      const planValEl = this.container.querySelector('#stage-plan-val');
      const codeValEl = this.container.querySelector('#stage-code-val');
      const buildValEl = this.container.querySelector('#stage-build-val');
      const testValEl = this.container.querySelector('#stage-test-val');
      const deployValEl = this.container.querySelector('#stage-deploy-val');
      const monitorValEl = this.container.querySelector('#stage-monitor-val');

      if (planValEl) planValEl.textContent = planCount;
      if (codeValEl) codeValEl.textContent = codeCount;
      if (buildValEl) buildValEl.textContent = buildCount;
      if (testValEl) testValEl.textContent = testCount;
      if (deployValEl) deployValEl.textContent = deployCount;
      if (monitorValEl) monitorValEl.textContent = monitorCount;

      // 2. Đồng bộ danh sách Deployments gần đây từ các jobs thật
      const deploymentsList = this.container.querySelector('#overview-deployments');
      if (deploymentsList && jobs.length > 0) {
        deploymentsList.innerHTML = jobs.slice(0, 5).map(job => {
          const timeText = job.updated_at ? new Date(job.updated_at).toLocaleTimeString() : 'Recent';
          const isDone = job.status === 'done' || job.status === 'success' || job.status === 'active' || job.status === 'succeeded';
          const isFail = job.status === 'failed' || job.status === 'error';
          
          let badgeStatus = 'badge-running';
          let statusText = job.status;
          if (isDone) {
            badgeStatus = 'badge-success';
            statusText = '✓ SUCCESS';
          } else if (isFail) {
            badgeStatus = 'badge-error';
            statusText = '✗ FAILED';
          }

          return `
            <div class="deployment-row">
              <div class="deploy-service-info">
                <div class="deploy-icon-box">📱</div>
                <div class="deploy-meta">
                  <span class="deploy-title">${this.escapeHTML(job.name)}</span>
                  <span class="deploy-slug">${this.escapeHTML(job.slug)}</span>
                </div>
              </div>
              <div class="deploy-pills">
                <span class="pill pill-prod">MVP</span>
                <span class="badge ${badgeStatus}">${statusText.toUpperCase()}</span>
              </div>
              <span class="deploy-time">${timeText}</span>
            </div>
          `;
        }).join('');
      } else if (deploymentsList) {
        deploymentsList.innerHTML = '<p style="color:var(--text-secondary); padding: 10px; font-size: 13px;">Chưa có bản phát hành nào</p>';
      }

      // 3. Đồng bộ KPI chi phí và biểu đồ Donut tròn màu sắc
      const costs = await api.getCosts();
      const totalCost = parseFloat(costs.total_cost_usd || 0);
      const kpiCostEl = this.container.querySelector('#kpi-cost');
      const totalDonutEl = this.container.querySelector('#overview-cost-total-donut');
      const footerCostEl = this.container.querySelector('#overview-cost-footer');
      
      if (kpiCostEl) kpiCostEl.textContent = '$' + totalCost.toFixed(2);
      if (totalDonutEl) totalDonutEl.textContent = '$' + totalCost.toFixed(2);
      if (footerCostEl) footerCostEl.textContent = '$' + totalCost.toFixed(2);

      const donutChart = this.container.querySelector('#overview-cost-donut');
      const legendContainer = this.container.querySelector('#overview-cost-legend');
      
      if (donutChart && legendContainer) {
        if (costs.by_agent && Object.keys(costs.by_agent).length > 0) {
          let accum = 0;
          const colors = ['var(--accent-blue)', 'var(--accent-cyan)', 'var(--accent-purple)', 'var(--accent-amber)', 'var(--text-muted)'];
          const gradientParts = [];
          const legendHTML = [];
          
          const sortedAgents = Object.entries(costs.by_agent)
            .sort((a, b) => b[1].cost_usd - a[1].cost_usd);
            
          sortedAgents.forEach(([agent, info], idx) => {
            const pct = totalCost > 0 ? (info.cost_usd / totalCost * 100) : 0;
            const nextAccum = accum + pct;
            const color = colors[idx % colors.length];
            gradientParts.push(`${color} ${accum.toFixed(1)}% ${nextAccum.toFixed(1)}%`);
            accum = nextAccum;
            
            legendHTML.push(`
              <div class="legend-item">
                <span class="legend-label"><span class="legend-dot" style="background:${color}"></span>${agent}</span>
                <span class="legend-val">$${info.cost_usd.toFixed(3)}<span class="legend-pct">${pct.toFixed(1)}%</span></span>
              </div>
            `);
          });
          
          if (accum < 100) {
            gradientParts.push(`var(--text-muted) ${accum.toFixed(1)}% 100%`);
          }
          
          donutChart.style.background = `conic-gradient(${gradientParts.join(', ')})`;
          legendContainer.innerHTML = legendHTML.join('');
        } else {
          donutChart.style.background = `conic-gradient(var(--text-muted) 0% 100%)`;
          legendContainer.innerHTML = '<div style="text-align: center; width: 100%; color: var(--text-muted); font-size: 12.5px;">Chưa có chi phí tiêu hao.</div>';
        }
      }

      // 4. Đồng bộ Success Rate KPI từ backend kpis
      const successRate = kpis.success_rate ?? 0;
      const successRateEl = this.container.querySelector('#kpi-success-rate');
      const successPctEl = this.container.querySelector('#overview-success-pct');
      const successFillEl = this.container.querySelector('#overview-progress-bar');
      
      if (successRateEl) successRateEl.textContent = successRate.toFixed(1) + '%';
      if (successPctEl) successPctEl.textContent = successRate.toFixed(1) + '%';
      if (successFillEl) successFillEl.style.width = successRate.toFixed(1) + '%';

      // 5. Đồng bộ Activity Feed từ Agents log thật
      const agentLogs = await api.getAgents();
      const timelineContainer = this.container.querySelector('#overview-activity-feed');
      if (timelineContainer) {
        if (agentLogs.length > 0) {
          timelineContainer.innerHTML = agentLogs.slice(-4).reverse().map(l => {
            const timeText = l.timestamp ? l.timestamp.slice(11, 19) : 'Recent';
            return `
              <div class="timeline-item">
                <div class="timeline-dot"></div>
                <div class="timeline-text">
                  Agent <strong>${this.escapeHTML(l.agent)}</strong> performed <strong>${this.escapeHTML(l.action)}</strong>.
                </div>
                <span class="timeline-time">${timeText}</span>
              </div>
            `;
          }).join('');
        } else {
          timelineContainer.innerHTML = '<p style="color:var(--text-secondary); padding: 10px; font-size: 13px;">Không có hoạt động gần đây.</p>';
        }
      }

      // 6. Đồng bộ số lượng AI Models đăng ký
      const modelsKpiEl = this.container.querySelector('#kpi-models');
      if (modelsKpiEl) {
        modelsKpiEl.textContent = kpis.active_models_count ?? 0;
      }

      // 7. Đồng bộ danh sách AI Models hoạt động trên Dashboard
      const modelsTableBody = this.container.querySelector('#overview-models-table-body');
      if (modelsTableBody) {
        try {
          const modelsData = await api.getModels();
          const models = modelsData.models || [];
          if (models.length > 0) {
            modelsTableBody.innerHTML = models.slice(0, 5).map(model => {
              return `
                <tr>
                  <td><span style="font-weight: 700; color:#fff;">${this.escapeHTML(model.name || model.id)}</span><br/><span style="font-size:10px; font-family:monospace; color:var(--accent-blue);">${this.escapeHTML(model.id)}</span></td>
                  <td style="font-family:monospace;">${this.escapeHTML(modelsData.provider || 'unknown')}</td>
                  <td><span class="badge badge-success">ACTIVE</span></td>
                </tr>
              `;
            }).join('');
          } else {
            modelsTableBody.innerHTML = '<tr><td colspan="3" style="text-align: center; color: var(--text-muted); font-size: 12.5px; padding: 20px;">Không có mô hình nào</td></tr>';
          }
        } catch (modelErr) {
          console.warn('Lỗi đồng bộ models overview:', modelErr);
          modelsTableBody.innerHTML = '<tr><td colspan="3" style="text-align: center; color: var(--accent-rose); font-size: 12.5px; padding: 20px;">Lỗi tải mô hình</td></tr>';
        }
      }
    } catch (err) {
      console.warn('Đồng bộ dữ liệu Overview gặp lỗi:', err);
    }
  }

}

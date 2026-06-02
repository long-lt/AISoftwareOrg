import './styles/main.css';
import './styles/sidebar.css';
import './styles/overview.css';
import './styles/projects.css';
import './styles/pipelines.css';
import './styles/models.css';

import Router from './js/router.js';

// Nạp toàn bộ các Views modular
import OverviewView from './js/views/OverviewView.js';
import ProjectsView from './js/views/ProjectsView.js';
import ProjectDetailView from './js/views/ProjectDetailView.js';
import PipelinesView from './js/views/PipelinesView.js';
import PipelineDetailView from './js/views/PipelineDetailView.js';
import ModelsView from './js/views/ModelsView.js';
import ModelDetailView from './js/views/ModelDetailView.js';
import AgentsView from './js/views/AgentsView.js';
import AgentDetailView from './js/views/AgentDetailView.js';
import CodeView from './js/views/CodeView.js';
import EvaluationsView from './js/views/EvaluationsView.js';
import DeploymentsView from './js/views/DeploymentsView.js';
import MonitoringView from './js/views/MonitoringView.js';
import CostsView from './js/views/CostsView.js';
import KnowledgeView from './js/views/KnowledgeView.js';
import AutomationsView from './js/views/AutomationsView.js';
import TeamView from './js/views/TeamView.js';
import SettingsView from './js/views/SettingsView.js';
import WizardView from './js/views/WizardView.js';

document.addEventListener('DOMContentLoaded', () => {
  const container = document.getElementById('main-view-viewport');
  if (!container) {
    console.error('Không tìm thấy cổng hiển thị chính (#main-view-viewport)');
    return;
  }

  // 1. Khởi tạo bộ định tuyến Router rỗng trước để tránh lỗi ReferenceError từ vế phải gán const
  const router = new Router(container, {});

  // 2. Gán các views cụ thể vào bộ định tuyến
  router.views = {
    'view-overview': new OverviewView(router),
    'view-projects': new ProjectsView(router),
    'view-project-detail': new ProjectDetailView(router),
    'view-pipelines': new PipelinesView(router),
    'view-pipeline-detail': new PipelineDetailView(router),
    'view-models': new ModelsView(router),
    'view-model-detail': new ModelDetailView(router),
    'view-agents': new AgentsView(router),
    'view-agent-detail': new AgentDetailView(router),
    'view-code': new CodeView(router),
    'view-evaluations': new EvaluationsView(router),
    'view-deployments': new DeploymentsView(router),
    'view-monitoring': new MonitoringView(router),
    'view-costs': new CostsView(router),
    'view-knowledge': new KnowledgeView(router),
    'view-automations': new AutomationsView(router),
    'view-team': new TeamView(router),
    'view-settings': new SettingsView(router),
    'view-project-wizard': new WizardView(router)
  };

  // 3. Expose showTab ra window toàn cục để tương thích ngược với các inline onclick trong sidebar
  window.showTab = (viewId, params = null) => {
    router.showView(viewId, params);
  };

  // 4. Expose toggleSidebar thu gọn/mở rộng thanh công cụ bên trái
  window.toggleSidebar = () => {
    const sidebar = document.getElementById('sidebar-nav');
    const mainContent = document.getElementById('main-content-panel');
    if (sidebar && mainContent) {
      sidebar.classList.toggle('collapsed');
      mainContent.classList.toggle('sidebar-collapsed');
    }
  };

  // 5. Hiển thị view mặc định khi bắt đầu tải trang
  router.showView('view-overview');
});

export default class Router {
  constructor(containerEl, viewsMap) {
    this.container = containerEl;
    this.views = viewsMap;
    this.activeView = null;
    this.activeViewId = null;
  }

  // Chuyển đổi màn hình hiển thị
  showView(viewId, params = null) {
    if (this.activeViewId === viewId) {
      if (this.activeView) {
        this.activeView.params = params;
        if (typeof this.activeView.onUpdate === 'function') {
          this.activeView.onUpdate();
        }
      }
      return;
    }

    // 1. Huỷ liên kết view cũ (onUnmount)
    if (this.activeView) {
      if (typeof this.activeView.onUnmount === 'function') {
        this.activeView.onUnmount();
      }
    }

    // 2. Gỡ bỏ active class của menu cũ
    if (this.activeViewId) {
      const oldMenuId = this.getMenuId(this.activeViewId);
      const oldMenuItem = document.getElementById(oldMenuId);
      if (oldMenuItem) oldMenuItem.classList.remove('active');
    }

    // 3. Tìm view instance mới
    const viewInstance = this.views[viewId];
    if (!viewInstance) {
      console.error(`Không tìm thấy View: ${viewId}`);
      return;
    }

    this.activeView = viewInstance;
    this.activeViewId = viewId;

    // 4. Kích hoạt menu active mới
    const newMenuId = this.getMenuId(viewId);
    const newMenuItem = document.getElementById(newMenuId);
    if (newMenuItem) newMenuItem.classList.add('active');

    // 5. Render HTML vào container
    viewInstance.render(this.container, params);

    // 6. Cập nhật Tiêu đề và Mô tả trên Top Header
    this.updateHeader(viewId);

    // Tự động cuộn lên đầu trang khi chuyển màn hình
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }

  // Lấy ID menu tương ứng với View ID
  getMenuId(viewId) {
    const menuMap = {
      'view-overview': 'menu-overview',
      'view-projects': 'menu-projects',
      'view-project-detail': 'menu-projects', // Project detail thuộc tab Projects
      'view-pipelines': 'menu-pipelines',
      'view-pipeline-detail': 'menu-pipelines',
      'view-models': 'menu-models',
      'view-model-detail': 'menu-models',
      'view-agents': 'menu-agents',
      'view-agent-detail': 'menu-agents',
      'view-code': 'menu-code',
      'view-evaluations': 'menu-evaluations',
      'view-deployments': 'menu-deployments',
      'view-monitoring': 'menu-monitoring',
      'view-costs': 'menu-costs',
      'view-knowledge': 'menu-knowledge',
      'view-automations': 'menu-automations',
      'view-team': 'menu-team',
      'view-settings': 'menu-settings',
      'view-login': '',
      'view-project-wizard': 'menu-projects'
    };
    return menuMap[viewId] || '';
  }

  // Cập nhật Header
  updateHeader(viewId) {
    const titleMap = {
      'view-overview': 'AI Software Factory Dashboard',
      'view-projects': 'Projects',
      'view-project-detail': 'Project Details',
      'view-pipelines': 'Pipelines',
      'view-pipeline-detail': 'Pipeline Execution Details',
      'view-models': 'AI Models',
      'view-model-detail': 'Model Metrics & Evaluation',
      'view-agents': 'AI Agents',
      'view-agent-detail': 'Agent Profile',
      'view-code': 'Code Assets',
      'view-evaluations': 'Evaluations',
      'view-deployments': 'Deployments',
      'view-monitoring': 'Monitoring',
      'view-costs': 'Cost Management',
      'view-knowledge': 'Knowledge Hub',
      'view-automations': 'Automations',
      'view-team': 'Team',
      'view-settings': 'Settings',
      'view-login': 'Welcome back',
      'view-project-wizard': 'Create New Project'
    };

    const subtitleMap = {
      'view-overview': 'End-to-end visibility into AI-powered software delivery',
      'view-projects': 'Manage software initiatives, AI apps, internal tools, and automation products',
      'view-project-detail': 'View complete project lifecycle, pipeline, model usage, and deployment history',
      'view-pipelines': 'Build, test, evaluate, and deploy AI-powered software automatically',
      'view-pipeline-detail': 'Show detailed execution status of a software delivery pipeline',
      'view-models': 'Track model performance, usage, cost, drift, and deployment readiness',
      'view-model-detail': 'Show model performance, evaluations, deployments, usage, cost, and drift',
      'view-agents': 'Monitor AI workers that plan, code, test, review, deploy, and analyze software',
      'view-agent-detail': 'Show the work history, permissions, task queue, memory, tools, and performance of an AI agent',
      'view-code': 'Track repositories, services, modules, APIs, and reusable software components',
      'view-evaluations': 'Measure AI quality, safety, reliability, and production readiness',
      'view-deployments': 'Track releases, environments, rollouts, and production health',
      'view-monitoring': 'Observe AI services, software systems, and production behavior in real time',
      'view-costs': 'Track AI usage, cloud spend, token cost, and budget efficiency',
      'view-knowledge': 'Centralized project knowledge for humans and AI agents',
      'view-automations': 'Create rules that keep your AI software factory running automatically',
      'view-team': 'Manage people, roles, permissions, and ownership across your software factory',
      'view-settings': 'Configure your AI Software Factory workspace',
      'view-login': 'Sign in to your workspace',
      'view-project-wizard': 'Configure a new AI software project'
    };

    const titleEl = document.getElementById('view-title');
    if (titleEl) titleEl.textContent = titleMap[viewId] || '';

    const subtitleEl = document.getElementById('view-subtitle');
    if (subtitleEl) subtitleEl.textContent = subtitleMap[viewId] || '';
  }

  // Gọi update dữ liệu realtime
  updateActiveView() {
    if (this.activeView && typeof this.activeView.onUpdate === 'function') {
      this.activeView.onUpdate();
    }
  }
}

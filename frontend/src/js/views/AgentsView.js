import BaseView from './BaseView.js';
import template from '../../views/agents.html?raw';
import * as api from '../api.js';

export default class AgentsView extends BaseView {
  constructor(router) {
    super('agents', template);
    this.router = router;
    this.refreshInterval = null;
  }

  onMount() {
    // 1. Đồng bộ các cấu hình Agent đã được lưu trữ cục bộ lên các thẻ giao diện
    this.applyAllSavedConfigs();
    this.loadDynamicData();
    this.refreshInterval = setInterval(() => this.loadDynamicData(), 5000);

    // 2. Gán click cho nút xem chi tiết của Code Writer Agent
    const btnGotoProfile = this.container.querySelector('#btn-goto-writer-agent');
    if (btnGotoProfile) {
      btnGotoProfile.addEventListener('click', (e) => {
        e.preventDefault();
        this.router.showView('view-agent-detail');
      });
    }

    const cardGotoProfile = this.container.querySelector('#agent-card-code-writer');
    if (cardGotoProfile) {
      cardGotoProfile.style.cursor = 'pointer';
      cardGotoProfile.addEventListener('click', (e) => {
        // Tránh kích hoạt khi bấm vào các nút bên trong thẻ
        if (e.target.tagName !== 'BUTTON' && !e.target.closest('.btn-edit-agent')) {
          this.router.showView('view-agent-detail');
        }
      });
    }

    // 3. Quản lý việc mở Modal cấu hình khi click Edit Config của từng Agent
    const editBtns = this.container.querySelectorAll('.btn-edit-agent');
    editBtns.forEach(btn => {
      btn.addEventListener('click', (e) => {
        e.preventDefault();
        e.stopPropagation();
        const agentId = btn.getAttribute('data-agent-id');
        this.openConfigModal(agentId);
      });
    });

    // 4. Sự kiện đóng Modal
    const closeBtn = this.container.querySelector('#modal-close-btn');
    if (closeBtn) {
      closeBtn.addEventListener('click', () => this.closeModal());
    }

    const cancelBtn = this.container.querySelector('#modal-cancel-btn');
    if (cancelBtn) {
      cancelBtn.addEventListener('click', () => this.closeModal());
    }

    // 5. Sự kiện Submit Form Lưu cấu hình Agent
    const configForm = this.container.querySelector('#agent-config-form');
    if (configForm) {
      configForm.addEventListener('submit', (e) => {
        e.preventDefault();
        this.saveAgentConfig();
      });
    }

    // 6. Sự kiện thay đổi LLM Provider
    const providerSelect = this.container.querySelector('#modal-field-provider');
    if (providerSelect) {
      providerSelect.addEventListener('change', (e) => {
        const val = e.target.value;
        this.fetchAndPopulateModels(val, '');
      });
    }
  }

  // Lấy dữ liệu mặc định của 6 Agents ban đầu
  getAgentDefaultData(agentId) {
    const defaults = {
      'planner': {
        title: '🕵️ Product Planner Agent',
        desc: 'Converts ideas, feature requests, and Figma mockups into detailed PRDs, system architectures, and development task plans.',
        provider: 'openrouter',
        model: 'google/gemini-2.5-flash',
        tools: 'Figma, Linear, Hub',
        knowledge: 'Product Specifications rules, Feature list priorities.'
      },
      'writer': {
        title: '💻 Code Writer Agent',
        desc: 'Implements features, resolves bugs, and structures modular packages based on Linear tickets or requirements files.',
        provider: 'openrouter',
        model: 'qwen/qwen-2.5-coder-32b',
        tools: 'GitHub, Terminal, Sandbox',
        knowledge: 'Strict static typing checking, keep functions below 50 lines.'
      },
      'qa': {
        title: '🔬 QA Agent',
        desc: 'Generates integration tests, writes unit assertions, and performs extensive smoke testing before merging pull requests.',
        provider: 'openrouter',
        model: 'meta-llama/llama-3.3-70b-instruct',
        tools: 'Browser, Terminal, Playwright',
        knowledge: 'Playwright E2E assert patterns, automated check rules.'
      },
      'devops': {
        title: '🚀 DevOps Agent',
        desc: 'Manages Kubernetes clusters, deploys docker containers, configures CDN gateways, and automates rollbacks.',
        provider: 'openrouter',
        model: 'google/gemini-2.5-flash',
        tools: 'Cloudflare, AWS, Supabase',
        knowledge: 'Kubernetes ingress bindings, AWS deployment checklists.'
      },
      'cost': {
        title: '💰 Cost Monitor Agent',
        desc: 'Tracks API call volumes, alerts on billing spikes, detects anomalous LLM token usages, and suggest caching optimization policies.',
        provider: 'openrouter',
        model: 'qwen/qwen-2.5-coder-32b',
        tools: 'Stripe, AWS, OpenRouter',
        knowledge: 'Billing spike alert configurations, Stripe API cost auditing.'
      },
      'security': {
        title: '🛡️ Security Reviewer',
        desc: 'Audits code assets, scans third-party packages for vulnerabilities, inspects container networks, and sanitizes API keys.',
        provider: 'deepseek',
        model: 'deepseek-chat',
        tools: 'Snyk, GitHub, Sandbox',
        knowledge: 'Snyk CVE scanners, API Key sanitizing guidelines.'
      }
    };
    return defaults[agentId] || null;
  }

  // Nạp danh sách model động của Provider và gán vào datalist
  async fetchAndPopulateModels(provider, selectedValue = '') {
    const listEl = this.container.querySelector('#modal-field-model-list');
    const statusEl = this.container.querySelector('#modal-field-model-status');
    const inputEl = this.container.querySelector('#modal-field-model');
    if (!listEl) return;

    if (statusEl) {
      statusEl.textContent = 'Đang nạp danh sách model...';
      statusEl.style.color = 'var(--text-secondary)';
    }

    // Đọc API Key & Base URL từ localStorage
    const key = localStorage.getItem(`api_key_${provider}`) || '';
    const baseurl = localStorage.getItem(`base_url_${provider}`) || '';

    try {
      const data = await api.getModels(provider, key, baseurl);
      const models = data.models || [];

      listEl.innerHTML = models.map(m => {
        const name = m.name || m.id;
        return `<option value="${m.id}">${name}</option>`;
      }).join('');

      if (statusEl) {
        statusEl.textContent = `Nạp thành công ${models.length} model từ ${provider.toUpperCase()}.`;
        statusEl.style.color = 'var(--accent-green)';
      }

      if (selectedValue) {
        inputEl.value = selectedValue;
      } else {
        // Tự động gợi ý model đầu tiên trong danh sách nếu có
        if (models.length > 0) {
          inputEl.value = models[0].id;
        } else {
          inputEl.value = '';
        }
      }
    } catch (err) {
      console.error('Lỗi khi nạp models:', err);
      listEl.innerHTML = '';
      if (statusEl) {
        statusEl.textContent = `Lỗi nạp model: ${err.message}. Hãy gõ tự do.`;
        statusEl.style.color = 'var(--accent-rose)';
      }
      if (selectedValue) {
        inputEl.value = selectedValue;
      }
    }
  }

  // Mở Modal cấu hình Agent
  openConfigModal(agentId) {
    const modal = this.container.querySelector('#agent-config-modal');
    if (!modal) return;

    // Lấy cấu hình đã lưu hoặc lấy giá trị mặc định ban đầu
    const saved = localStorage.getItem(`agent_config_${agentId}`);
    const data = saved ? JSON.parse(saved) : this.getAgentDefaultData(agentId);

    if (!data) return;

    // Điền dữ liệu vào form modal
    this.container.querySelector('#modal-field-id').value = agentId;
    this.container.querySelector('#modal-field-title').value = data.title;
    this.container.querySelector('#modal-field-desc').value = data.desc;
    this.container.querySelector('#modal-field-tools').value = data.tools;
    
    const kbEl = this.container.querySelector('#modal-field-knowledge');
    if (kbEl) kbEl.value = data.knowledge || '';

    // Cập nhật nhãn tiêu đề modal
    this.container.querySelector('#modal-agent-title').textContent = `⚙️ Cấu hình: ${data.title}`;

    // Cập nhật LLM Provider select
    const provider = data.provider || 'openrouter';
    const providerSelect = this.container.querySelector('#modal-field-provider');
    if (providerSelect) {
      providerSelect.value = provider;
    }

    // Gọi nạp models cho provider này
    this.fetchAndPopulateModels(provider, data.model);

    // Hiển thị modal dạng flex
    modal.style.display = 'flex';
  }

  closeModal() {
    const modal = this.container.querySelector('#agent-config-modal');
    if (modal) modal.style.display = 'none';
  }

  mapUIToDBAgentId(uiId) {
    const mapping = {
      'planner': 'pm',
      'writer': 'dev',
      'qa': 'qa',
      'devops': 'reviewer',
      'cost': 'uiux',
      'security': 'security'
    };
    return mapping[uiId] || uiId;
  }

  // Lưu cấu hình Agent xuống LocalStorage và SQLite DB trên backend
  async saveAgentConfig() {
    const agentId = this.container.querySelector('#modal-field-id').value;
    if (!agentId) return;

    const data = {
      title: this.container.querySelector('#modal-field-title').value,
      desc: this.container.querySelector('#modal-field-desc').value,
      provider: this.container.querySelector('#modal-field-provider').value,
      model: this.container.querySelector('#modal-field-model').value,
      tools: this.container.querySelector('#modal-field-tools').value,
      knowledge: this.container.querySelector('#modal-field-knowledge').value
    };

    localStorage.setItem(`agent_config_${agentId}`, JSON.stringify(data));
    
    // Đồng bộ lên SQLite DB trên Backend
    try {
      const dbId = this.mapUIToDBAgentId(agentId);
      const systemPrompt = `${data.desc}\nKiến thức chuyên sâu:\n${data.knowledge}`;
      await api.saveAgentConfig(dbId, {
        model: data.model,
        system_prompt: systemPrompt
      });
    } catch (err) {
      console.warn('Lỗi đồng bộ cấu hình agent lên backend:', err);
    }
    
    // Cập nhật giao diện của thẻ ngay lập tức
    this.applyConfigToCard(agentId, data);
    
    this.closeModal();
  }

  // Áp dụng một cấu hình cụ thể lên Card giao diện
  applyConfigToCard(agentId, data) {
    const card = this.container.querySelector(`#agent-card-${agentId}`);
    if (!card) return;

    const titleEl = card.querySelector('.agent-title-text');
    if (titleEl) titleEl.textContent = data.title;

    const descEl = card.querySelector('.agent-desc-text');
    if (descEl) descEl.textContent = data.desc;

    const modelEl = card.querySelector('.agent-model-text');
    if (modelEl) {
      const providerPrefix = data.provider ? `${data.provider.toUpperCase()} / ` : '';
      modelEl.textContent = `${providerPrefix}${data.model}`;
    }

    const toolsEl = card.querySelector('.agent-tools-text');
    if (toolsEl) toolsEl.textContent = `TOOLS: ${data.tools}`;
  }

  // Áp dụng toàn bộ cấu hình nạp động từ backend SQLite DB
  async applyAllSavedConfigs() {
    try {
      const dbConfigs = await api.getAgentConfigs();
      const dbMap = {};
      dbConfigs.forEach(c => {
        dbMap[c.agent_id] = c;
      });

      const agentIds = ['planner', 'writer', 'qa', 'devops', 'cost', 'security'];
      agentIds.forEach(id => {
        const dbId = this.mapUIToDBAgentId(id);
        const config = dbMap[dbId];
        
        const saved = localStorage.getItem(`agent_config_${id}`);
        const uiData = saved ? JSON.parse(saved) : this.getAgentDefaultData(id);
        
        if (config) {
          uiData.model = config.model;
          if (config.system_prompt) {
            const parts = config.system_prompt.split('\nKiến thức chuyên sâu:\n');
            uiData.desc = parts[0] || uiData.desc;
            uiData.knowledge = parts[1] || uiData.knowledge;
          }
        }
        this.applyConfigToCard(id, uiData);
      });
    } catch (err) {
      console.warn('Lỗi đồng bộ cấu hình agents từ backend, dùng fallback local:', err);
      const agentIds = ['planner', 'writer', 'qa', 'devops', 'cost', 'security'];
      agentIds.forEach(id => {
        const saved = localStorage.getItem(`agent_config_${id}`);
        if (saved) {
          this.applyConfigToCard(id, JSON.parse(saved));
        } else {
          const defaultData = this.getAgentDefaultData(id);
          if (defaultData) {
            this.applyConfigToCard(id, defaultData);
          }
        }
      });
    }
  }

  onUnmount() {
    if (this.refreshInterval) {
      clearInterval(this.refreshInterval);
      this.refreshInterval = null;
    }
  }

  async loadDynamicData() {
    try {
      const [jobs, configs, costs] = await Promise.all([
        api.getJobs(),
        api.getAgentConfigs(),
        api.getCosts()
      ]);

      // 1. Cập nhật top KPI cards
      const activeEl = this.container.querySelector('#agents-kpi-active');
      const runningEl = this.container.querySelector('#agents-kpi-running');
      const completedEl = this.container.querySelector('#agents-kpi-completed');
      const failedEl = this.container.querySelector('#agents-kpi-failed');
      const durationEl = this.container.querySelector('#agents-kpi-duration');

      if (activeEl) activeEl.textContent = configs.length || 6;
      
      const runningCount = jobs.filter(j => j.status === 'running' || j.status === 'queued').length;
      if (runningEl) runningEl.textContent = runningCount;

      const completedCount = jobs.filter(j => j.status === 'done' || j.status === 'success' || j.status === 'succeeded').length;
      if (completedEl) completedEl.textContent = completedCount;

      const failedCount = jobs.filter(j => j.status === 'failed' || j.status === 'error').length;
      if (failedEl) failedEl.textContent = failedCount;

      if (durationEl) {
        durationEl.textContent = completedCount > 0 ? '1m 15s' : '0s';
      }

      // 2. Tìm job đang chạy để ánh xạ Current Task của Agent
      const runningJob = jobs.find(j => j.status === 'running');
      
      // 3. Cập nhật từng Agent Card
      const agentIds = ['planner', 'writer', 'qa', 'devops', 'cost', 'security'];
      agentIds.forEach(id => {
        const card = this.container.querySelector(`#agent-card-${id}`);
        if (!card) return;

        const dbId = this.mapUIToDBAgentId(id);
        const agentCostInfo = costs.by_agent?.[dbId] || costs.by_agent?.[id] || { cost_usd: 0, calls: 0 };
        
        // Cập nhật Cost Today
        const costEl = card.querySelector('.agent-cost-text');
        if (costEl) {
          costEl.textContent = `$${parseFloat(agentCostInfo.cost_usd || 0).toFixed(2)}`;
        }

        // Cập nhật Success Rate
        const successEl = card.querySelector('.agent-success-rate');
        if (successEl) {
          if (agentCostInfo.calls > 0) {
            // Có cuộc gọi thật -> success rate thật (mặc định 96% hoặc nếu có failed jobs thì giảm)
            const failedRatio = failedCount > 0 ? (failedCount / jobs.length) : 0;
            const rate = Math.round((1 - failedRatio) * 100);
            successEl.textContent = `${rate}%`;
          } else {
            // Database rỗng -> 0%
            successEl.textContent = '0%';
          }
        }

        // Cập nhật Current Task
        const taskEl = card.querySelector('.agent-task-text');
        if (taskEl) {
          let taskText = 'Idle';
          if (runningJob) {
            const phases = runningJob.phases || {};
            // Phân bổ trạng thái công việc dựa trên pipeline phase
            if (id === 'planner' && (phases.create === 'running' || phases.ba === 'running')) {
              taskText = `Working on ${runningJob.name} (PRD Specs)`;
            } else if (id === 'writer' && (phases.dev === 'running' || phases.refactor === 'running' || phases.repair === 'running')) {
              taskText = `Coding ${runningJob.name} modules`;
            } else if (id === 'qa' && phases.qa === 'running') {
              taskText = `Running tests for ${runningJob.name}`;
            } else if (id === 'devops' && phases.reviewer === 'running') {
              taskText = `Deploying ${runningJob.name}`;
            } else if (id === 'cost' && (phases.uiux === 'running' || phases.export === 'running')) {
              taskText = `Optimizing UI & Assets for ${runningJob.name}`;
            } else if (id === 'security' && phases.security === 'running') {
              taskText = `Audits safety of ${runningJob.name}`;
            }
          }
          taskEl.textContent = taskText;
        }
      });
    } catch (err) {
      console.warn('Lỗi load dynamic data cho Agents:', err);
    }
  }
}

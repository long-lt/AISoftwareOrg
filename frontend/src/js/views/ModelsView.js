import BaseView from './BaseView.js';
import template from '../../views/models.html?raw';
import * as api from '../api.js';

export default class ModelsView extends BaseView {
  constructor(router) {
    super('models', template);
    this.router = router;
    this.refreshInterval = null;
    this.cachedModels = [];
    this.currentActiveProvider = '';
  }

  onMount() {
    // 1. Gán nút so sánh -> đi tới Model Detail
    const compareBtn = this.container.querySelector('#models-compare-btn');
    if (compareBtn) {
      compareBtn.addEventListener('click', () => {
        this.router.showView('view-model-detail');
      });
    }

    // 2. Gán sự kiện đổi active provider
    const select = this.container.querySelector('#active-provider-select');
    if (select) {
      select.addEventListener('change', async (e) => {
        const val = e.target.value;
        if (!val) return;
        try {
          await api.changeActiveProvider(val);
          this.currentActiveProvider = val;
          this.syncProviderInputs(val);
          this.onUpdate();
        } catch (err) {
          this.showToast(`Không thể kích hoạt provider: ${err.message}`, 'error');
        }
      });
    }

    // 3. Gán sự kiện lưu cấu hình Provider Key & Base URL vào LocalStorage
    const saveConfigBtn = this.container.querySelector('#btn-save-provider-config');
    if (saveConfigBtn) {
      saveConfigBtn.addEventListener('click', (e) => {
        e.preventDefault();
        this.saveProviderConfig();
      });
    }

    // 4. Gán sự kiện tìm kiếm model cục bộ
    const searchInput = this.container.querySelector('#models-search');
    if (searchInput) {
      searchInput.addEventListener('input', () => this.filterModels());
    }

    this.onUpdate();
    this.refreshInterval = setInterval(() => this.onUpdate(), 8000);
  }

  onUnmount() {
    if (this.refreshInterval) {
      clearInterval(this.refreshInterval);
      this.refreshInterval = null;
    }
  }

  async onUpdate() {
    await this.loadProviders();
    await Promise.all([
      this.loadCosts(),
      this.loadRealModels()
    ]);
  }

  // Đồng bộ giá trị input khi chuyển đổi active provider
  syncProviderInputs(providerName) {
    const keyInput = this.container.querySelector('#provider-config-key');
    const urlInput = this.container.querySelector('#provider-config-baseurl');
    if (keyInput) {
      keyInput.value = localStorage.getItem(`api_key_${providerName}`) || '';
    }
    if (urlInput) {
      urlInput.value = localStorage.getItem(`base_url_${providerName}`) || '';
    }
  }

  // Lưu cấu hình xuống LocalStorage
  saveProviderConfig() {
    const select = this.container.querySelector('#active-provider-select');
    const providerName = select ? select.value : this.currentActiveProvider;
    if (!providerName) {
      this.showToast('Vui lòng chọn hoặc đợi tải Provider đang hoạt động.', 'warning');
      return;
    }

    const key = this.container.querySelector('#provider-config-key').value.trim();
    const baseurl = this.container.querySelector('#provider-config-baseurl').value.trim();

    localStorage.setItem(`api_key_${providerName}`, key);
    localStorage.setItem(`base_url_${providerName}`, baseurl);

    this.showToast(`Đã lưu cấu hình API Key & Endpoint thành công cho Provider ${providerName.toUpperCase()}!`, 'success');
    this.onUpdate(); // Kích hoạt nạp lại model ngay lập tức
  }

  async loadProviders() {
    const select = this.container.querySelector('#active-provider-select');
    const tableBody = this.container.querySelector('#providers-table tbody');
    if (!select || !tableBody) return;
    try {
      const data = await api.getProviders();
      const active = data.active || 'legacy';
      
      const isNewActive = this.currentActiveProvider !== active;
      this.currentActiveProvider = active;

      // Cập nhật select dropdown
      select.innerHTML = Object.keys(data.providers).map(name => `
        <option value="${name}" ${name === active ? 'selected' : ''}>${name.toUpperCase()} ${name === active ? '(Đang hoạt động)' : ''}</option>
      `).join('');

      // Đồng bộ các trường nhập liệu nếu có sự thay đổi
      if (isNewActive) {
        this.syncProviderInputs(active);
      }

      // Cập nhật bảng
      tableBody.innerHTML = Object.entries(data.providers).map(([name, p]) => `
        <tr class="${p.active ? 'active-row' : ''}">
          <td style="font-weight:700;">${this.escapeHTML(p.name.toUpperCase())}</td>
          <td><code>${this.escapeHTML(p.default_model)}</code></td>
          <td><code>${this.escapeHTML(p.base_url)}</code></td>
          <td>${p.active ? `<span class="badge badge-success">ACTIVE</span>` : '<span style="color:var(--text-secondary)">Sẵn sàng</span>'}</td>
        </tr>
      `).join('');
    } catch (err) {
      tableBody.innerHTML = `<tr><td colspan="4" style="color:var(--accent-rose)">Lỗi nạp providers: ${err.message}</td></tr>`;
    }
  }

  async loadCosts() {
    const target = this.container.querySelector('#costs-summary');
    if (!target) return;
    try {
      const data = await api.getCosts();
      target.innerHTML = `
        <div class="stat-row" style="display:flex; justify-content:space-between; margin-bottom:12px;">
          <div class="stat"><span class="stat-value" style="font-size:18px; font-weight:800;">$${parseFloat(data.total_cost_usd || 0).toFixed(4)}</span><div class="stat-label" style="font-size:10px; color:var(--text-secondary);">Tổng chi phí (USD)</div></div>
          <div class="stat"><span class="stat-value" style="font-size:18px; font-weight:800;">${parseInt(data.total_tokens || 0).toLocaleString()}</span><div class="stat-label" style="font-size:10px; color:var(--text-secondary);">Tokens đã dùng</div></div>
          <div class="stat"><span class="stat-value" style="font-size:18px; font-weight:800;">${data.calls || 0}</span><div class="stat-label" style="font-size:10px; color:var(--text-secondary);">Số cuộc gọi</div></div>
        </div>
        
        <h3 style="font-size:12px; margin: 15px 0 8px; color:var(--text-secondary); text-transform:uppercase; font-weight:700;">Chi phí theo Agent:</h3>
        <table>
          <thead>
            <tr><th>Agent</th><th>Chi phí (USD)</th><th>Cuộc gọi</th></tr>
          </thead>
          <tbody>
            ${Object.entries(data.by_agent || {}).map(([agent, val]) => `
            <tr>
              <td><strong>${this.escapeHTML(agent)}</strong></td>
              <td>$${parseFloat(val.cost_usd).toFixed(4)}</td>
              <td>${val.calls}</td>
            </tr>`).join('')}
          </tbody>
        </table>
      `;
    } catch (err) {
      target.innerHTML = `<p style="color:var(--accent-rose)">Lỗi nạp chi phí: ${err.message}</p>`;
    }
  }

  // Nạp danh sách model thật từ API sử dụng cấu hình tùy chọn
  async loadRealModels() {
    const tableBody = this.container.querySelector('#real-models-table tbody');
    const badgeCount = this.container.querySelector('#models-count-badge');
    if (!tableBody) return;

    try {
      const provider = this.currentActiveProvider;
      const key = localStorage.getItem(`api_key_${provider}`) || '';
      const baseurl = localStorage.getItem(`base_url_${provider}`) || '';

      const data = await api.getModels(provider, key, baseurl);
      const models = data.models || [];
      this.cachedModels = models;

      if (badgeCount) {
        badgeCount.textContent = `${models.length} Models`;
      }

      this.renderModelsTable(models);
    } catch (err) {
      tableBody.innerHTML = `<tr><td colspan="6" style="color:var(--accent-rose); text-align:center; padding:20px;">Lỗi nạp danh sách model: ${err.message}</td></tr>`;
    }
  }

  renderModelsTable(models) {
    const tableBody = this.container.querySelector('#real-models-table tbody');
    if (!tableBody) return;

    if (models.length === 0) {
      tableBody.innerHTML = `<tr><td colspan="6" style="text-align:center; padding:20px; color:var(--text-secondary);">Không có model nào được hỗ trợ hoặc đang ngoại tuyến.</td></tr>`;
      return;
    }

    tableBody.innerHTML = models.map(m => {
      // Định dạng độ dài ngữ cảnh (Context Window)
      const contextLen = m.context_length ? parseInt(m.context_length) : 0;
      let contextText = `${contextLen.toLocaleString()} tokens`;
      if (contextLen >= 1048576) {
        contextText = `${(contextLen / 1048576).toFixed(0)}M (Mega)`;
      } else if (contextLen >= 1000) {
        contextText = `${(contextLen / 1000).toFixed(0)}K`;
      }

      // Định dạng chi phí trên 1 triệu tokens (1M tokens) cho dễ hình dung
      const pricing = m.pricing || {};
      const promptPrice = pricing.prompt ? parseFloat(pricing.prompt) * 1000000 : 0;
      const completionPrice = pricing.completion ? parseFloat(pricing.completion) * 1000000 : 0;
      
      const inputCostText = promptPrice > 0 ? `$${promptPrice.toFixed(2)}` : 'Free';
      const outputCostText = completionPrice > 0 ? `$${completionPrice.toFixed(2)}` : 'Free';

      // Lấy thông tin phụ đề, mô tả
      const name = m.name || m.id;
      const desc = m.description ? m.description.slice(0, 120) + (m.description.length > 120 ? '...' : '') : 'No description provided.';
      const modality = m.architecture?.modality || m.modality || 'Text';

      return `
        <tr>
          <td>
            <div style="font-weight: 700; color:#fff;">${this.escapeHTML(name)}</div>
            <div style="font-size:10.5px; font-family:monospace; color:var(--accent-blue); margin-top:2px;">${this.escapeHTML(m.id)}</div>
          </td>
          <td style="font-weight:700; font-family:monospace;">${contextText}</td>
          <td style="font-family:monospace; color:var(--text-secondary);">${inputCostText}</td>
          <td style="font-family:monospace; color:var(--text-secondary);">${outputCostText}</td>
          <td>
            <div style="font-size:11px; color:var(--accent-cyan); font-weight:700; text-transform:uppercase; margin-bottom:2px;">${this.escapeHTML(modality)}</div>
            <div style="font-size:11px; color:var(--text-secondary); line-height:1.4;" title="${this.escapeHTML(m.description || '')}">${this.escapeHTML(desc)}</div>
          </td>
          <td>
            <span class="badge badge-success">Supported</span>
          </td>
        </tr>
      `;
    }).join('');
  }

  // Tìm kiếm cục bộ model qua từ khóa
  filterModels() {
    const searchVal = this.container.querySelector('#models-search').value.toLowerCase();
    const filtered = this.cachedModels.filter(m => {
      const name = (m.name || '').toLowerCase();
      const id = (m.id || '').toLowerCase();
      const desc = (m.description || '').toLowerCase();
      return name.includes(searchVal) || id.includes(searchVal) || desc.includes(searchVal);
    });

    this.renderModelsTable(filtered);
    const badgeCount = this.container.querySelector('#models-count-badge');
    if (badgeCount) {
      badgeCount.textContent = `${filtered.length} / ${this.cachedModels.length} Models`;
    }
  }
}

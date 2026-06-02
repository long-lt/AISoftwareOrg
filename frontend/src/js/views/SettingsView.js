import BaseView from './BaseView.js';
import template from '../../views/settings.html?raw';
import * as api from '../api.js';

export default class SettingsView extends BaseView {
  constructor(router) {
    super('settings', template);
    this.router = router;
  }

  onMount() {
    // 1. Đồng bộ các giá trị từ LocalStorage hoặc bộ nhớ đệm
    this.syncFormFields();

    // 2. Chuyển đổi các danh mục submenu bên trái
    const submenus = this.container.querySelectorAll('#settings-submenu button');
    submenus.forEach(btn => {
      btn.addEventListener('click', (e) => {
        e.preventDefault();
        submenus.forEach(b => {
          b.classList.remove('active');
          b.style.color = 'var(--text-secondary)';
          b.style.fontWeight = '600';
        });

        btn.classList.add('active');
        btn.style.color = '#fff';
        btn.style.fontWeight = '700';

        const tabName = btn.getAttribute('data-set-tab');
        this.switchSubTab(tabName);
      });
    });

    // 3. Gán sự kiện lưu cấu hình General
    const saveGenBtn = this.container.querySelector('#btn-save-general');
    if (saveGenBtn) {
      saveGenBtn.addEventListener('click', () => {
        const name = this.container.querySelector('#set-workspace-name').value;
        const tz = this.container.querySelector('#set-timezone').value;
        
        localStorage.setItem('set_workspace_name', name);
        localStorage.setItem('set_timezone', tz);
        
        // Cập nhật Workspace name hiển thị ở sidebar logo hoặc header nếu cần thiết
        this.showToast('Đã lưu cấu hình General thành công!', 'success');
      });
    }

    // 4. Gán sự kiện lưu cấu hình AI
    const saveAiBtn = this.container.querySelector('#btn-save-ai');
    if (saveAiBtn) {
      saveAiBtn.addEventListener('click', async () => {
        const tokens = this.container.querySelector('#set-max-tokens').value;
        const approval = this.container.querySelector('#human-approval').checked;
        
        localStorage.setItem('set_max_tokens', tokens);
        localStorage.setItem('set_human_approval', approval ? 'true' : 'false');
        
        // Đồng bộ lên SQLite DB trên Backend
        try {
          const costLimit = this.container.querySelector('#set-daily-cost-limit').value;
          const fallbackModel = this.container.querySelector('#set-smart-model-fallback').value;
          const maxRepair = this.container.querySelector('#set-max-repair-attempts').value;
          
          await api.saveSystemSettings({
            daily_cost_limit: costLimit,
            smart_model_fallback: fallbackModel,
            max_repair_attempts: maxRepair
          });
        } catch (err) {
          console.warn('Lỗi lưu cài đặt hệ thống lên backend:', err);
        }
        
        this.showToast('Đã lưu cấu hình AI Defaults thành công!', 'success');
      });
    }

    // 5. Gán sự kiện cho nút reset Danger Zone
    const wipeDataBtn = this.container.querySelector('#btn-wipe-data');
    if (wipeDataBtn) {
      wipeDataBtn.addEventListener('click', async () => {
        const doubleCheck = confirm("⚠️ BẠN CÓ CHẮC CHẮN MUỐN XÓA SẠCH DỮ LIỆU?\n\nHành động này sẽ xóa sạch toàn bộ lịch sử các jobs sinh ứng dụng, các sáng kiến portfolio, các tệp nguồn trong workspace và bộ nhớ tự học của Agent.");
        if (!doubleCheck) return;
        
        const tripleCheck = confirm("🔥 XÁC NHẬN LẦN CUỐI:\nHành động này sẽ khôi phục hệ thống về trạng thái mặc định ban đầu và không thể hoàn tác!");
        if (!tripleCheck) return;
        
        try {
          await api.wipeSystemData();
          this.showToast("Đã xóa sạch dữ liệu và khôi phục cài đặt mặc định thành công!", 'success');
          window.location.reload();
        } catch (err) {
          console.error("Lỗi xóa dữ liệu:", err);
          this.showToast("Lỗi: Không thể xóa sạch dữ liệu hệ thống!", 'error');
        }
      });
    }
  }

  async syncFormFields() {
    const wsName = localStorage.getItem('set_workspace_name') || 'AI Software Factory Workspace';
    const wsTz = localStorage.getItem('set_timezone') || 'Asia/Ho_Chi_Minh';
    const maxTokens = localStorage.getItem('set_max_tokens') || '1000000';
    const humanApproval = localStorage.getItem('set_human_approval') !== 'false'; // default true

    const nameEl = this.container.querySelector('#set-workspace-name');
    if (nameEl) nameEl.value = wsName;

    const tzEl = this.container.querySelector('#set-timezone');
    if (tzEl) tzEl.value = wsTz;

    const tokensEl = this.container.querySelector('#set-max-tokens');
    if (tokensEl) tokensEl.value = maxTokens;

    const approvalEl = this.container.querySelector('#human-approval');
    if (approvalEl) approvalEl.checked = humanApproval;

    // Nạp các cấu hình hệ thống thật từ SQLite database trên backend
    try {
      const dbSettings = await api.getSystemSettings();
      const costLimitEl = this.container.querySelector('#set-daily-cost-limit');
      if (costLimitEl && dbSettings.daily_cost_limit) costLimitEl.value = dbSettings.daily_cost_limit;

      const fallbackModelEl = this.container.querySelector('#set-smart-model-fallback');
      if (fallbackModelEl && dbSettings.smart_model_fallback) fallbackModelEl.value = dbSettings.smart_model_fallback;

      const maxRepairEl = this.container.querySelector('#set-max-repair-attempts');
      if (maxRepairEl && dbSettings.max_repair_attempts) maxRepairEl.value = dbSettings.max_repair_attempts;
    } catch (err) {
      console.warn('Lỗi nạp cài đặt hệ thống từ backend:', err);
    }
  }

  switchSubTab(tabName) {
    const sections = this.container.querySelectorAll('.settings-panel-section');
    sections.forEach(s => {
      s.style.display = 'none';
      s.classList.remove('active');
    });

    const targetSection = this.container.querySelector(`#settings-section-${tabName}`);
    if (targetSection) {
      targetSection.style.display = 'block';
      targetSection.classList.add('active');
    }
  }
}

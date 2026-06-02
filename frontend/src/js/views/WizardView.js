import BaseView from './BaseView.js';
import template from '../../views/project-wizard.html?raw';
import * as api from '../api.js';

export default class WizardView extends BaseView {
  constructor(router) {
    super('wizard', template);
    this.router = router;
    this.currentStep = 1;
  }

  onMount() {
    this.currentStep = 1;
    this.updateStepDisplay();

    // Quay lại Projects
    const backHeader = this.container.querySelector('#wizard-back-projects');
    if (backHeader) {
      backHeader.addEventListener('click', (e) => {
        e.preventDefault();
        this.router.showView('view-projects');
      });
    }

    // Nút Next / Launch
    const nextBtn = this.container.querySelector('#wizard-next-btn');
    if (nextBtn) {
      nextBtn.addEventListener('click', async () => {
        if (this.currentStep < 5) {
          this.currentStep++;
          this.updateStepDisplay();
          return;
        }
        await this.handleLaunch();
      });
    }

    // Nút Back
    const prevBtn = this.container.querySelector('#wizard-prev-btn');
    if (prevBtn) {
      prevBtn.addEventListener('click', () => {
        if (this.currentStep > 1) {
          this.currentStep--;
          this.updateStepDisplay();
        }
      });
    }
  }

  async handleLaunch() {
    const nextBtn = this.container.querySelector('#wizard-next-btn');
    const prevBtn = this.container.querySelector('#wizard-prev-btn');
    if (nextBtn) {
      nextBtn.disabled = true;
      nextBtn.textContent = '⏳ Đang khởi tạo...';
    }
    if (prevBtn) prevBtn.disabled = true;

    try {
      const getVal = (sel) => {
        const el = this.container.querySelector(sel);
        return el ? (el.value || '').trim() : '';
      };
      const getChecked = (sel) => {
        const el = this.container.querySelector(sel);
        return el ? el.checked : false;
      };

      const name = getVal('#wizard-name') || 'Untitled Initiative';
      const description = getVal('#wizard-description');
      const repository = getVal('#wizard-repo');
      const aiModel = getVal('#wizard-model') || 'google/gemini-2.5-flash';
      const enablePipelines = getChecked('#wizard-pipelines');
      const enableHitl = getChecked('#wizard-hitl');

      const slug = name
        .toLowerCase()
        .replace(/[^a-z0-9]+/g, '_')
        .replace(/^_+|_+$/g, '')
        .slice(0, 60) || `init_${Date.now()}`;

      const projectData = {
        slug,
        name,
        description:
          description ||
          `Initiative tạo qua Wizard ngày ${new Date().toLocaleDateString('vi-VN')}`,
        status: 'discovery',
        health: 'healthy',
        icon: '🤖',
        repository: repository || '',
        monthly_spend: 0.0,
        sla: '99%',
        build_progress: 0,
        features_json: JSON.stringify({
          pipelines: enablePipelines,
          hitl: enableHitl,
          model: aiModel
        })
      };

      const created = await api.createProject(projectData);

      this.showToast(`✅ Đã tạo Initiative "${created.name}"`, 'success');

      setTimeout(() => this.router.showView('view-projects'), 1200);
    } catch (err) {
      this.showToast(`❌ Lỗi: ${err.message}`, 'error');
      if (nextBtn) {
        nextBtn.disabled = false;
        nextBtn.textContent = '🚀 Launch Initiative';
      }
      if (prevBtn) prevBtn.disabled = false;
    }
  }

  updateStepDisplay() {
    const nextBtn = this.container.querySelector('#wizard-next-btn');
    const prevBtn = this.container.querySelector('#wizard-prev-btn');
    const progress = this.container.querySelector('#wizard-stepper-progress');

    // 1. Quản lý việc hiển thị sections
    for (let i = 1; i <= 5; i++) {
      const secActual = this.container.querySelector(`#wizard-step-${i}-content`);
      if (secActual) {
        secActual.style.display = i === this.currentStep ? 'block' : 'none';
      }

      // Cập nhật nhãn text của stepper ở đầu trang
      const lbl = this.container.querySelector(`#step-lbl-${i}`);
      if (lbl) {
        if (i === this.currentStep) {
          lbl.style.color = 'var(--accent-blue)';
          lbl.textContent = `● Step ${i}: ${this.getStepName(i)}`;
        } else if (i < this.currentStep) {
          lbl.style.color = 'var(--accent-green)';
          lbl.textContent = `✓ Step ${i}: ${this.getStepName(i)}`;
        } else {
          lbl.style.color = 'var(--text-muted)';
          lbl.textContent = `○ Step ${i}: ${this.getStepName(i)}`;
        }
      }
    }

    // 2. Quản lý nút Back/Next
    if (prevBtn) {
      prevBtn.style.visibility = this.currentStep === 1 ? 'hidden' : 'visible';
    }

    if (nextBtn) {
      nextBtn.textContent =
        this.currentStep === 5 ? '🚀 Launch Initiative' : 'Next Step';
    }

    // 3. Tiến trình thanh tiến độ ngang
    if (progress) {
      progress.style.width = `${this.currentStep * 20}%`;
    }
  }

  getStepName(step) {
    const names = {
      1: 'Basics',
      2: 'Source Repo',
      3: 'AI Setup',
      4: 'Pipelines Gate',
      5: 'Review'
    };
    return names[step] || '';
  }
}

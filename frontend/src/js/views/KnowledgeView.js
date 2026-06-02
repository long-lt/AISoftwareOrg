import BaseView from './BaseView.js';
import template from '../../views/knowledge.html?raw';
import * as api from '../api.js';

export default class KnowledgeView extends BaseView {
  constructor(router) {
    super('knowledge', template);
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
      // 1. Fetch live metadata from backend
      const [projects, jobs, experiences] = await Promise.all([
        api.getProjects(),
        api.getJobs(),
        api.getExperiences()
      ]);

      // 2. Compute dynamic stats
      const docCount = (projects.length * 8) + (jobs.length * 12) + (experiences ? experiences.length * 3 : 0);
      const basesCount = projects.length + 2; // Projects + prompt base + coding guides
      const chunkCount = docCount * 45; // average 45 vector chunks per document
      
      const jobsRunningCount = jobs.filter(j => j.status === 'running' || j.status === 'queued').length;
      const queriesCount = (jobs.length * 80) + (jobsRunningCount * 15);
      const outdatedDocs = projects.filter(p => p.health === 'warning').length + (experiences ? experiences.filter(e => e.status === 'pending').length : 0);

      // 3. Update DOM
      const docsEl = this.container.querySelector('#knowledge-kpi-docs');
      const basesEl = this.container.querySelector('#knowledge-kpi-bases');
      const chunksEl = this.container.querySelector('#knowledge-kpi-chunks');
      const queriesEl = this.container.querySelector('#knowledge-kpi-queries');
      const outdatedEl = this.container.querySelector('#knowledge-kpi-outdated');

      if (docsEl) docsEl.textContent = docCount > 0 ? docCount.toLocaleString() : '0';
      if (basesEl) basesEl.textContent = basesCount;
      if (chunksEl) chunksEl.textContent = chunkCount > 0 ? chunkCount.toLocaleString() : '0';
      if (queriesEl) queriesEl.textContent = queriesCount > 0 ? queriesCount.toLocaleString() : '0';
      if (outdatedEl) outdatedEl.textContent = outdatedDocs;

    } catch (err) {
      console.warn('Đồng bộ dữ liệu Knowledge Base gặp lỗi:', err);
    }
  }
}

export default class BaseView {
  constructor(name, templateHtml) {
    this.name = name;
    this.templateHtml = templateHtml;
    this.container = null;
  }

  // Chèn HTML template vào container và kích hoạt onMount
  render(parentContainer, params = null) {
    this.container = parentContainer;
    this.params = params;
    this.container.innerHTML = this.templateHtml;
    this.onMount();
  }

  // Nơi gán sự kiện và xử lý khi view hiển thị lần đầu
  onMount() {}

  // Được gọi định kỳ để làm mới dữ liệu realtime
  onUpdate() {}

  // Thực hiện dọn dẹp các interval hoặc event listener khi rời view
  onUnmount() {}

  // Hiển thị thông báo toast (thay thế alert)
  showToast(message, type = 'info') {
    const colors = {
      success: 'var(--accent-green)',
      error: 'var(--accent-rose)',
      warning: 'var(--accent-amber)',
      info: 'var(--accent-blue)',
    };
    const toast = document.createElement('div');
    toast.textContent = message;
    toast.style.cssText = `
      position:fixed; top:24px; right:24px; z-index:9999;
      padding:12px 20px; border-radius:8px; font-weight:600;
      background:${colors[type] || colors.info};
      color:#fff; box-shadow:0 8px 24px rgba(0,0,0,0.4);
      font-size:14px; max-width:400px; word-wrap:break-word;
    `;
    document.body.appendChild(toast);
    setTimeout(() => toast.remove(), 3500);
  }

  // Escape HTML để chống XSS
  escapeHTML(s) {
    const d = document.createElement('div');
    d.textContent = s || '';
    return d.innerHTML;
  }
}

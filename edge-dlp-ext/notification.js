// notification.js
// Modern notification system for EdgeDLP extension
// Shows popup notifications when PII is detected

class NotificationManager {
  constructor() {
    this.activeNotifications = [];
    this.notificationId = 0;
  }

  showPIIDetected(numItems, itemsPreview, source, undoCallback) {
    const notification = new PIINotification({
      numItems,
      itemsPreview,
      source,
      undoCallback,
      onClose: () => this._removeNotification(notification)
    });

    this.activeNotifications.push(notification);
    this.notificationId++;
    // Auto-dismiss is handled by the notification's own _startProgress() method
  }

  _removeNotification(notification) {
    const index = this.activeNotifications.indexOf(notification);
    if (index > -1) {
      this.activeNotifications.splice(index, 1);
    }
  }

  dismissAll() {
    this.activeNotifications.forEach(n => n.dismiss());
    this.activeNotifications = [];
  }
}

class PIINotification {
  constructor({ numItems, itemsPreview, source, undoCallback, onClose }) {
    this.numItems = numItems;
    this.itemsPreview = itemsPreview || '';
    this.source = source || 'typing';
    this.undoCallback = undoCallback;
    this.onClose = onClose;
    this.dismissed = false;
    
    this._createNotification();
    this._animateEntrance();
  }

  _createNotification() {
    // Get notification manager to calculate position
    const manager = getNotificationManager();
    const stackIndex = manager.activeNotifications.length;
    
    // Create notification container
    this.container = document.createElement('div');
    this.container.className = 'edgedlp-notification';
    const topOffset = 24 + (stackIndex * 180); // Stack notifications with 180px offset
    this.container.style.cssText = `
      position: fixed;
      top: ${topOffset}px;
      right: 24px;
      width: 400px;
      min-height: 160px;
      background: #FFFFFF;
      border-radius: 24px;
      box-shadow: 0 8px 32px rgba(0, 0, 0, 0.12);
      z-index: ${999999 + stackIndex};
      font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, sans-serif;
      opacity: 0;
      transform: scale(0.9) translateY(-20px);
      transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
      border: 1px solid rgba(148, 163, 184, 0.2);
      overflow: hidden;
    `;

    // Accent bar
    const accentBar = document.createElement('div');
    accentBar.style.cssText = `
      position: absolute;
      left: 0;
      top: 0;
      bottom: 0;
      width: 8px;
      background: linear-gradient(180deg, #667EEA 0%, #764BA2 100%);
    `;
    this.container.appendChild(accentBar);

    // Content wrapper
    const content = document.createElement('div');
    content.style.cssText = `
      padding: 20px 24px 20px 44px;
      position: relative;
    `;
    this.container.appendChild(content);

    // Header
    const header = document.createElement('div');
    header.style.cssText = `
      display: flex;
      align-items: center;
      margin-bottom: 12px;
    `;
    content.appendChild(header);

    // Icon
    const icon = document.createElement('div');
    icon.textContent = '🛡';
    icon.style.cssText = `
      font-size: 22px;
      margin-right: 12px;
    `;
    header.appendChild(icon);

    // Title section
    const titleSection = document.createElement('div');
    titleSection.style.cssText = `
      flex: 1;
    `;
    header.appendChild(titleSection);

    const title = document.createElement('div');
    title.textContent = 'PII Protected';
    title.style.cssText = `
      font-size: 13px;
      font-weight: 600;
      color: #667EEA;
      line-height: 1.2;
    `;
    titleSection.appendChild(title);

    const subtitle = document.createElement('div');
    subtitle.textContent = 'Data secured automatically';
    subtitle.style.cssText = `
      font-size: 8px;
      color: #94A3B8;
      margin-top: 2px;
    `;
    titleSection.appendChild(subtitle);

    // Close button
    const closeBtn = document.createElement('div');
    closeBtn.textContent = '✕';
    closeBtn.style.cssText = `
      font-size: 16px;
      color: #94A3B8;
      cursor: pointer;
      padding: 4px 8px;
      border-radius: 4px;
      transition: all 0.2s;
      user-select: none;
    `;
    closeBtn.addEventListener('mouseenter', () => {
      closeBtn.style.color = '#EF4444';
      closeBtn.style.background = '#FEE2E2';
    });
    closeBtn.addEventListener('mouseleave', () => {
      closeBtn.style.color = '#94A3B8';
      closeBtn.style.background = 'transparent';
    });
    closeBtn.addEventListener('click', () => this.dismiss());
    header.appendChild(closeBtn);

    // Message
    const message = document.createElement('div');
    const itemText = this.numItems === 1 ? 'item' : 'items';
    message.textContent = `Protected ${this.numItems} ${itemText} • ${this.source}`;
    message.style.cssText = `
      font-size: 10px;
      font-weight: 600;
      color: #1E293B;
      margin-bottom: 6px;
    `;
    content.appendChild(message);

    // Preview
    if (this.itemsPreview && this.itemsPreview.length > 0) {
      const preview = document.createElement('div');
      const previewText = this.itemsPreview.length > 70 
        ? this.itemsPreview.substring(0, 70) + '...'
        : this.itemsPreview;
      preview.textContent = previewText;
      preview.style.cssText = `
        font-size: 9px;
        color: #64748B;
        margin-bottom: 12px;
        line-height: 1.4;
      `;
      content.appendChild(preview);
    }

    // Bottom row
    const bottom = document.createElement('div');
    bottom.style.cssText = `
      display: flex;
      align-items: center;
      justify-content: space-between;
      margin-top: 12px;
    `;
    content.appendChild(bottom);

    // Progress dots
    this.progressContainer = document.createElement('div');
    this.progressContainer.style.cssText = `
      display: flex;
      gap: 4px;
    `;
    this.progressDots = [];
    for (let i = 0; i < 5; i++) {
      const dot = document.createElement('div');
      dot.textContent = '●';
      dot.style.cssText = `
        font-size: 8px;
        color: #94A3B8;
        transition: color 0.2s;
      `;
      this.progressDots.push(dot);
      this.progressContainer.appendChild(dot);
    }
    bottom.appendChild(this.progressContainer);

    // Undo button
    if (this.undoCallback) {
      const undoBtn = document.createElement('div');
      undoBtn.textContent = '↶ Undo';
      undoBtn.style.cssText = `
        font-size: 9px;
        font-weight: 600;
        color: #475569;
        background: #F1F5F9;
        padding: 7px 16px;
        border-radius: 20px;
        cursor: pointer;
        transition: all 0.2s;
        user-select: none;
      `;
      undoBtn.addEventListener('mouseenter', () => {
        undoBtn.style.background = '#E2E8F0';
        undoBtn.style.color = '#1E293B';
      });
      undoBtn.addEventListener('mouseleave', () => {
        undoBtn.style.background = '#F1F5F9';
        undoBtn.style.color = '#475569';
      });
      undoBtn.addEventListener('click', () => this._handleUndo());
      bottom.appendChild(undoBtn);
    }

    // Add to page
    document.body.appendChild(this.container);

    // Start progress animation
    this._startProgress();
  }

  _animateEntrance() {
    requestAnimationFrame(() => {
      this.container.style.opacity = '1';
      this.container.style.transform = 'scale(1) translateY(0)';
    });
  }

  _startProgress() {
    const startTime = Date.now();
    const duration = 5000; // 5 seconds
    
    const updateProgress = () => {
      if (this.dismissed) return;
      
      const elapsed = Date.now() - startTime;
      const progress = elapsed / duration;
      
      if (progress >= 1.0) {
        this.dismiss();
        return;
      }
      
      // Update dots
      const filledDots = Math.floor(progress * this.progressDots.length);
      this.progressDots.forEach((dot, i) => {
        if (i < filledDots) {
          dot.style.color = '#667EEA';
        } else {
          dot.style.color = '#94A3B8';
        }
      });
      
      requestAnimationFrame(updateProgress);
    };
    
    updateProgress();
  }

  _handleUndo() {
    if (this.undoCallback && !this.dismissed) {
      this.dismissed = true;
      try {
        this.undoCallback();
      } catch (e) {
        console.error('[EdgeDLP] Error in undo callback:', e);
      }
    }
    this.dismiss();
  }

  dismiss() {
    if (this.dismissed) return;
    this.dismissed = true;
    
    // Fade out
    this.container.style.opacity = '0';
    this.container.style.transform = 'scale(0.9) translateY(-20px)';
    
    setTimeout(() => {
      if (this.container.parentNode) {
        this.container.parentNode.removeChild(this.container);
      }
      if (this.onClose) {
        this.onClose();
      }
    }, 300);
  }
}

// Global notification manager instance
let _notificationManager = null;

function getNotificationManager() {
  if (!_notificationManager) {
    _notificationManager = new NotificationManager();
  }
  return _notificationManager;
}

function showPIINotification(numItems, itemsPreview = '', source = 'typing', undoCallback = null) {
  const manager = getNotificationManager();
  manager.showPIIDetected(numItems, itemsPreview, source, undoCallback);
}

// Export for use in content script
if (typeof module !== 'undefined' && module.exports) {
  module.exports = { showPIINotification, getNotificationManager };
}


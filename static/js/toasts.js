/**
 * Auto-hide Toast/Notification System
 * Automatically dismisses toasts after 3-4 seconds
 * Works across entire application
 */

const TOAST_CONFIG = {
  SUCCESS: 3500,  // 3.5 seconds
  ERROR: 4500,    // 4.5 seconds (longer for errors)
  WARNING: 4000,  // 4 seconds
  INFO: 3500,     // 3.5 seconds
};

function initializeToasts() {
  const toasts = document.querySelectorAll('.toast');
  
  toasts.forEach((toast) => {
    // Determine timeout based on toast type
    let timeout = TOAST_CONFIG.INFO; // default
    
    if (toast.classList.contains('toast-success')) {
      timeout = TOAST_CONFIG.SUCCESS;
    } else if (toast.classList.contains('toast-error')) {
      timeout = TOAST_CONFIG.ERROR;
    } else if (toast.classList.contains('toast-warning')) {
      timeout = TOAST_CONFIG.WARNING;
    } else if (toast.classList.contains('toast-info')) {
      timeout = TOAST_CONFIG.INFO;
    }
    
    // Set timeout to hide and remove toast
    setTimeout(() => {
      hideToast(toast);
    }, timeout);
    
    // Optional: Add click to dismiss
    toast.addEventListener('click', () => {
      hideToast(toast);
    });
    
    toast.style.cursor = 'pointer';
  });
}

function hideToast(toast) {
  if (!toast) return;
  
  // Add closing animation class
  toast.classList.add('toast-closing');
  
  // Remove after animation completes
  setTimeout(() => {
    toast.remove();
  }, 300); // matches animation duration
}

// Initialize on DOM ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initializeToasts);
} else {
  initializeToasts();
}

// Also watch for dynamically added toasts
const observer = new MutationObserver((mutations) => {
  mutations.forEach((mutation) => {
    if (mutation.addedNodes.length) {
      mutation.addedNodes.forEach((node) => {
        if (node.classList && node.classList.contains('toast')) {
          // Handle newly added toast
          let timeout = TOAST_CONFIG.INFO;
          
          if (node.classList.contains('toast-success')) {
            timeout = TOAST_CONFIG.SUCCESS;
          } else if (node.classList.contains('toast-error')) {
            timeout = TOAST_CONFIG.ERROR;
          } else if (node.classList.contains('toast-warning')) {
            timeout = TOAST_CONFIG.WARNING;
          }
          
          setTimeout(() => {
            hideToast(node);
          }, timeout);
          
          node.addEventListener('click', () => {
            hideToast(node);
          });
          
          node.style.cursor = 'pointer';
        }
      });
    }
  });
});

// Observe the toast container for changes
const toastContainer = document.querySelector('.toast-container');
if (toastContainer) {
  observer.observe(toastContainer, {
    childList: true,
    subtree: false,
  });
}

/**
 * Toast Notification System
 */

// Create toast container if it doesn't exist
function ensureToastContainer() {
    if (!document.querySelector('.toast-container')) {
        const container = document.createElement('div');
        container.className = 'toast-container';
        document.body.appendChild(container);
    }
    return document.querySelector('.toast-container');
}

/**
 * Show a toast notification
 * @param {string} message - The message to display
 * @param {string} type - The type of toast (success, danger, warning, info)
 * @param {number} duration - Duration in milliseconds
 */
function showToast(message, type = 'info', duration = 5000) {
    const container = ensureToastContainer();
    
    // Create toast element
    const toast = document.createElement('div');
    toast.className = `toast toast-${type} show`;
    toast.setAttribute('role', 'alert');
    toast.setAttribute('aria-live', 'assertive');
    toast.setAttribute('aria-atomic', 'true');
    
    // Create toast content
    let icon = '';
    switch(type) {
        case 'success':
            icon = '<i class="fas fa-check-circle me-2"></i>';
            break;
        case 'danger':
            icon = '<i class="fas fa-exclamation-circle me-2"></i>';
            break;
        case 'warning':
            icon = '<i class="fas fa-exclamation-triangle me-2"></i>';
            break;
        case 'info':
        default:
            icon = '<i class="fas fa-info-circle me-2"></i>';
            break;
    }
    
    // Create toast structure
    toast.innerHTML = `
        <div class="toast-header">
            <strong class="me-auto">${icon} Thông báo</strong>
            <button class="custom-close-btn" aria-label="Close">
                <i class="fas fa-times"></i>
            </button>
        </div>
        <div class="toast-body">
            ${message}
        </div>
    `;
    
    // Add close functionality
    const closeButton = toast.querySelector('.custom-close-btn');
    closeButton.addEventListener('click', () => {
        removeToast(toast);
    });
    
    // Add to container
    container.appendChild(toast);
    
    // Auto remove after duration
    setTimeout(() => {
        removeToast(toast);
    }, duration);
    
    return toast;
}

/**
 * Remove a toast with animation
 * @param {HTMLElement} toast - The toast element to remove
 */
function removeToast(toast) {
    toast.style.animation = 'fadeOut 0.3s forwards';
    
    // Wait for animation to finish before removing
    setTimeout(() => {
        if (toast.parentNode) {
            toast.parentNode.removeChild(toast);
        }
    }, 300);
}

// Convenience methods
function showSuccessToast(message, duration) {
    return showToast(message, 'success', duration);
}

function showErrorToast(message, duration) {
    return showToast(message, 'danger', duration);
}

function showWarningToast(message, duration) {
    return showToast(message, 'warning', duration);
}

function showInfoToast(message, duration) {
    return showToast(message, 'info', duration);
}
// Main JavaScript file

document.addEventListener('DOMContentLoaded', function() {
    // Initialize tooltips
    const tooltipTriggerList = document.querySelectorAll('[data-bs-toggle="tooltip"]')
    const tooltipList = [...tooltipTriggerList].map(tooltipTriggerEl => new bootstrap.Tooltip(tooltipTriggerEl))
    
    // Initialize popovers
    const popoverTriggerList = document.querySelectorAll('[data-bs-toggle="popover"]')
    const popoverList = [...popoverTriggerList].map(popoverTriggerEl => new bootstrap.Popover(popoverTriggerEl))
    
    // Auto-dismiss alerts after 5 seconds
    setTimeout(function() {
        const alerts = document.querySelectorAll('.alert-dismissible');
        alerts.forEach(function(alert) {
            const bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        });
    }, 5000);
    
    // Copy to clipboard functionality
    const copyButtons = document.querySelectorAll('.copy-btn');
    copyButtons.forEach(function(button) {
        button.addEventListener('click', function() {
            const textToCopy = this.getAttribute('data-copy');
            const originalText = this.innerHTML;
            
            navigator.clipboard.writeText(textToCopy).then(function() {
                button.innerHTML = 'Copied!';
                setTimeout(function() {
                    button.innerHTML = originalText;
                }, 2000);
            }).catch(function(err) {
                console.error('Failed to copy text: ', err);
            });
        });
    });
    
    // Form validation styles
    const forms = document.querySelectorAll('.needs-validation');
    Array.from(forms).forEach(form => {
        form.addEventListener('submit', event => {
            if (!form.checkValidity()) {
                event.preventDefault();
                event.stopPropagation();
            }
            form.classList.add('was-validated');
        }, false);
    });
    
    // Category filter functionality
    const categoryLinks = document.querySelectorAll('.category-filter');
    categoryLinks.forEach(link => {
        link.addEventListener('click', function(e) {
            categoryLinks.forEach(l => l.classList.remove('active'));
            this.classList.add('active');
        });
    });
    
    // Search form handling
    const searchForm = document.getElementById('search-form');
    if (searchForm) {
        searchForm.addEventListener('submit', function(e) {
            const searchInput = document.getElementById('search-input');
            if (!searchInput.value.trim()) {
                e.preventDefault();
                searchInput.focus();
            }
        });
    }
    
    // Sort products functionality
    const sortSelect = document.getElementById('sort-by');
    if (sortSelect) {
        sortSelect.addEventListener('change', function() {
            // Lấy URL hiện tại
            const currentUrl = new URL(window.location.href);
            
            // Cập nhật tham số sort
            currentUrl.searchParams.set('sort', this.value);
            
            // Chuyển hướng đến URL mới
            window.location.href = currentUrl.toString();
        });
        
        // Đặt giá trị sort từ URL (nếu có)
        const urlParams = new URLSearchParams(window.location.search);
        let sortValue = urlParams.get('sort');
        
        // Xử lý cả hai định dạng (dấu gạch ngang hoặc gạch dưới)
        if (sortValue) {
            // Chuyển đổi price-high và price-low sang price_high và price_low nếu cần
            if (sortValue === 'price-high') sortValue = 'price_high';
            if (sortValue === 'price-low') sortValue = 'price_low';
            
            // Đặt giá trị cho dropdown
            if (sortSelect.querySelector(`option[value="${sortValue}"]`)) {
                sortSelect.value = sortValue;
            }
        }
    }

    // Transaction filter functionality
    const transactionTypeFilter = document.getElementById('transaction-type-filter');
    if (transactionTypeFilter) {
        transactionTypeFilter.addEventListener('change', function() {
            const type = this.value;
            const items = document.querySelectorAll('.transaction-item');
            
            items.forEach(item => {
                if (type === 'all' || item.classList.contains(type)) {
                    item.style.display = 'block';
                } else {
                    item.style.display = 'none';
                }
            });
        });
    }
    
    // Show/hide password toggle
    const togglePasswordButtons = document.querySelectorAll('.toggle-password');
    togglePasswordButtons.forEach(button => {
        button.addEventListener('click', function() {
            const passwordField = document.querySelector(this.getAttribute('data-target'));
            const type = passwordField.getAttribute('type') === 'password' ? 'text' : 'password';
            passwordField.setAttribute('type', type);
            
            // Toggle icon
            this.querySelector('i').classList.toggle('fa-eye');
            this.querySelector('i').classList.toggle('fa-eye-slash');
        });
    });
});

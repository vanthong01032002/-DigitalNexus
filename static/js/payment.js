// Payment page JavaScript

document.addEventListener('DOMContentLoaded', function() {
    // Toggle payment methods
    const paymentMethods = document.querySelectorAll('.payment-method');
    if (paymentMethods.length) {
        paymentMethods.forEach(method => {
            method.addEventListener('click', function() {
                // Remove active class from all methods
                paymentMethods.forEach(m => m.classList.remove('active'));
                
                // Add active class to clicked method
                this.classList.add('active');
                
                // Update hidden input value
                const paymentMethodInput = document.getElementById('payment_method');
                if (paymentMethodInput) {
                    paymentMethodInput.value = this.getAttribute('data-method');
                }
                
                // Show relevant details
                const methodDetails = document.querySelectorAll('.method-details');
                methodDetails.forEach(detail => {
                    detail.classList.add('d-none');
                });
                
                const selectedDetail = document.getElementById(this.getAttribute('data-method') + '-details');
                if (selectedDetail) {
                    selectedDetail.classList.remove('d-none');
                }
            });
        });
    }
    
    // Amount selector
    const amountSelectors = document.querySelectorAll('.amount-selector');
    const amountInput = document.getElementById('amount');
    
    if (amountSelectors.length && amountInput) {
        amountSelectors.forEach(selector => {
            selector.addEventListener('click', function() {
                amountSelectors.forEach(s => s.classList.remove('active'));
                this.classList.add('active');
                
                const amount = this.getAttribute('data-amount');
                amountInput.value = amount;
            });
        });
    }
    
    // Custom amount input handling
    const customAmountInput = document.getElementById('custom-amount');
    if (customAmountInput && amountInput) {
        customAmountInput.addEventListener('input', function() {
            amountInput.value = this.value;
            
            // Remove active class from predefined amounts
            amountSelectors.forEach(s => s.classList.remove('active'));
        });
    }
    
    // Form validation
    const topupForm = document.getElementById('topup-form');
    if (topupForm) {
        topupForm.addEventListener('submit', function(e) {
            const amount = parseFloat(amountInput.value);
            
            if (isNaN(amount) || amount <= 0) {
                e.preventDefault();
                alert('Please enter a valid amount');
                return false;
            }
            
            // Additional validation can be added here
        });
    }
    
    // Simulation of payment verification (for demo purposes only)
    const verifyPaymentBtn = document.getElementById('verify-payment');
    if (verifyPaymentBtn) {
        verifyPaymentBtn.addEventListener('click', function() {
            this.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Verifying...';
            this.disabled = true;
            
            // Simulate verification process
            setTimeout(() => {
                const form = document.getElementById('complete-topup-form');
                if (form) {
                    form.submit();
                }
            }, 2000);
        });
    }
    
    // Order success modal handler
    const orderSuccessModal = document.getElementById('orderSuccessModal');
    if (orderSuccessModal) {
        const orderSuccessDetails = document.getElementById('orderSuccessDetails');
        
        // Check if there's order success in URL parameters
        const urlParams = new URLSearchParams(window.location.search);
        if (urlParams.get('order_success') === 'true') {
            // Show modal
            const bsModal = new bootstrap.Modal(orderSuccessModal);
            bsModal.show();
            
            const orderId = urlParams.get('order_id');
            if (orderId && orderSuccessDetails) {
                // Get order details from server and fill modal
                fetch(`/api/order/${orderId}`)
                    .then(response => response.json())
                    .then(data => {
                        console.log("Order data:", data);
                        // Fill order details
                        let html = `
                            <div class="card border-success mb-3">
                                <div class="card-header bg-success text-white">
                                    <h5 class="card-title mb-0">Thông tin đơn hàng #${data.reference_code || ''}</h5>
                                </div>
                                <div class="card-body p-4 bg-light">
                                    <div class="row mb-2">
                                        <div class="col-5 text-secondary">Mã đơn hàng:</div>
                                        <div class="col-7 fw-bold text-primary text-end">${data.reference_code || ''}</div>
                                    </div>
                                    <div class="row mb-2">
                                        <div class="col-5 text-secondary">Sản phẩm:</div>
                                        <div class="col-7 fw-bold text-dark text-end">${data.product_name || ''}</div>
                                    </div>
                                    <div class="row mb-2">
                                        <div class="col-5 text-secondary">Số lượng:</div>
                                        <div class="col-7 fw-bold text-dark text-end">${data.quantity || 1}</div>
                                    </div>
                                    <div class="row mb-3 border-bottom pb-3">
                                        <div class="col-5 text-secondary">Ngày mua:</div>
                                        <div class="col-7 fw-bold text-dark text-end">${data.order_date || ''}</div>
                                    </div>
                                    <div class="row">
                                        <div class="col-5 text-secondary fs-5">Tổng tiền:</div>
                                        <div class="col-7 fw-bold text-success fs-5 text-end">${new Intl.NumberFormat('vi-VN').format(data.total_amount || 0)} VND</div>
                                    </div>
                                </div>
                            </div>
                        `;
                        orderSuccessDetails.innerHTML = html;
                    })
                    .catch(error => {
                        console.error('Error fetching order details:', error);
                        orderSuccessDetails.innerHTML = '<div class="alert alert-danger">Không thể tải thông tin đơn hàng.</div>';
                    });
            }
        }
    }
});

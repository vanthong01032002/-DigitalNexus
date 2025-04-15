// Dashboard page JavaScript

document.addEventListener('DOMContentLoaded', function() {
    // Transaction history chart
    const transactionChartCanvas = document.getElementById('transactionChart');
    
    if (transactionChartCanvas) {
        // Get transaction data from the data attribute
        const transactionData = JSON.parse(transactionChartCanvas.getAttribute('data-transactions') || '[]');
        
        // Process data for chart
        const dates = [];
        const credits = [];
        const debits = [];
        
        // Group transactions by date
        const groupedByDate = {};
        
        transactionData.forEach(transaction => {
            const date = new Date(transaction.created_at).toLocaleDateString();
            
            if (!groupedByDate[date]) {
                groupedByDate[date] = {
                    credit: 0,
                    debit: 0
                };
            }
            
            if (transaction.transaction_type === 'credit') {
                groupedByDate[date].credit += parseFloat(transaction.amount);
            } else {
                groupedByDate[date].debit += parseFloat(transaction.amount);
            }
        });
        
        // Convert grouped data to arrays for chart
        Object.keys(groupedByDate).forEach(date => {
            dates.push(date);
            credits.push(groupedByDate[date].credit);
            debits.push(groupedByDate[date].debit);
        });
        
        // Create chart
        const ctx = transactionChartCanvas.getContext('2d');
        const chart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: dates,
                datasets: [
                    {
                        label: 'Credits',
                        data: credits,
                        backgroundColor: 'rgba(40, 167, 69, 0.5)',
                        borderColor: 'rgba(40, 167, 69, 1)',
                        borderWidth: 1
                    },
                    {
                        label: 'Debits',
                        data: debits,
                        backgroundColor: 'rgba(220, 53, 69, 0.5)',
                        borderColor: 'rgba(220, 53, 69, 1)',
                        borderWidth: 1
                    }
                ]
            },
            options: {
                responsive: true,
                scales: {
                    y: {
                        beginAtZero: true,
                        title: {
                            display: true,
                            text: 'Amount (VND)'
                        }
                    },
                    x: {
                        title: {
                            display: true,
                            text: 'Date'
                        }
                    }
                }
            }
        });
    }
    
    // Notification handling
    const markAsReadButtons = document.querySelectorAll('.mark-as-read');
    markAsReadButtons.forEach(button => {
        button.addEventListener('click', function() {
            const notificationId = this.getAttribute('data-id');
            
            // Send AJAX request to mark notification as read
            fetch(`/notifications/${notificationId}/read`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                }
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    // Update UI
                    const notificationItem = document.querySelector(`.notification-item[data-id="${notificationId}"]`);
                    if (notificationItem) {
                        notificationItem.classList.remove('unread');
                        notificationItem.classList.add('read');
                    }
                    
                    // Update count
                    const notificationCount = document.querySelector('.notification-count');
                    if (notificationCount) {
                        let count = parseInt(notificationCount.innerText);
                        if (count > 0) {
                            notificationCount.innerText = count - 1;
                        }
                    }
                }
            })
            .catch(error => {
                console.error('Error marking notification as read:', error);
            });
        });
    });
});

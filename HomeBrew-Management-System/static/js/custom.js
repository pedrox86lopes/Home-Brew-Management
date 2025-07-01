// Timer functionality for brewing lab
class BrewTimer {
    constructor(timerId, name, durationMinutes) {
        this.timerId = timerId;
        this.name = name;
        this.durationMinutes = durationMinutes;
        this.startTime = new Date();
        this.isActive = true;
        this.element = document.getElementById(`timer-${timerId}`);
        
        this.updateDisplay();
        this.interval = setInterval(() => this.updateDisplay(), 1000);
    }
    
    updateDisplay() {
        if (!this.isActive) return;
        
        const now = new Date();
        const elapsed = Math.floor((now - this.startTime) / 1000 / 60);
        const remaining = Math.max(0, this.durationMinutes - elapsed);
        
        if (this.element) {
            const minutes = Math.floor(remaining);
            const seconds = Math.floor((remaining - minutes) * 60);
            
            this.element.querySelector('.timer-display').textContent = 
                `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
            
            // Change color when time is running out
            if (remaining <= 5) {
                this.element.classList.add('timer-warning');
            }
            
            // Timer finished
            if (remaining <= 0) {
                this.finish();
            }
        }
    }
    
    finish() {
        this.isActive = false;
        clearInterval(this.interval);
        
        if (this.element) {
            this.element.classList.add('timer-finished');
            this.element.querySelector('.timer-display').textContent = '00:00';
        }
        
        // Show notification
        this.showNotification();
        
        // Play sound (if supported)
        this.playSound();
    }
    
    showNotification() {
        if ('Notification' in window && Notification.permission === 'granted') {
            new Notification(`Timer Finished: ${this.name}`, {
                body: 'Your brewing timer has finished!',
                icon: '/static/img/timer-icon.png'
            });
        } else {
            // Fallback to alert
            alert(`Timer Finished: ${this.name}`);
        }
    }
    
    playSound() {
        // Simple beep sound
        const audioContext = new (window.AudioContext || window.webkitAudioContext)();
        const oscillator = audioContext.createOscillator();
        const gainNode = audioContext.createGain();
        
        oscillator.connect(gainNode);
        gainNode.connect(audioContext.destination);
        
        oscillator.frequency.value = 800;
        oscillator.type = 'sine';
        
        gainNode.gain.setValueAtTime(0.3, audioContext.currentTime);
        gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + 1);
        
        oscillator.start(audioContext.currentTime);
        oscillator.stop(audioContext.currentTime + 1);
    }
    
    stop() {
        this.isActive = false;
        clearInterval(this.interval);
        
        if (this.element) {
            this.element.style.display = 'none';
        }
    }
}

// Global timer management
const activeTimers = new Map();

function startBrewTimer(sessionId, name, duration) {
    const timerId = Date.now();
    const timer = new BrewTimer(timerId, name, duration);
    activeTimers.set(timerId, timer);
    
    // Send to server
    fetch(`/brewing/session/${sessionId}/timer/`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
            'X-CSRFToken': getCookie('csrftoken')
        },
        body: `name=${encodeURIComponent(name)}&duration=${duration}`
    });
    
    return timerId;
}

function stopBrewTimer(timerId) {
    const timer = activeTimers.get(timerId);
    if (timer) {
        timer.stop();
        activeTimers.delete(timerId);
    }
    
    // Send to server
    fetch(`/brewing/timer/${timerId}/stop/`, {
        method: 'POST',
        headers: {
            'X-CSRFToken': getCookie('csrftoken')
        }
    });
}

// Recipe calculator functions
function calculateRecipeStats() {
    // This would implement real-time recipe calculations
    // For now, it's a placeholder that shows loading state
    const statsContainer = document.getElementById('recipe-stats');
    if (statsContainer) {
        statsContainer.innerHTML = '<div class="loading">Calculating...</div>';
        
        setTimeout(() => {
            statsContainer.innerHTML = `
                <div class="calculator-result">
                    <div class="calculator-value">1.055</div>
                    <div class="calculator-label">Estimated OG</div>
                </div>
                <div class="calculator-result mt-2">
                    <div class="calculator-value">35</div>
                    <div class="calculator-label">Estimated IBU</div>
                </div>
            `;
        }, 1000);
    }
}

// Formset management for recipe forms
function addFormsetItem(formsetPrefix) {
    const formset = document.getElementById(`${formsetPrefix}-formset`);
    const totalForms = document.getElementById(`id_${formsetPrefix}-TOTAL_FORMS`);
    const emptyForm = document.getElementById(`${formsetPrefix}-empty-form`);
    
    if (!formset || !totalForms || !emptyForm) return;
    
    const newFormIndex = parseInt(totalForms.value);
    const newForm = emptyForm.cloneNode(true);
    
    // Update form index in all fields
    newForm.innerHTML = newForm.innerHTML.replace(/__prefix__/g, newFormIndex);
    newForm.id = `${formsetPrefix}-${newFormIndex}`;
    newForm.classList.remove('empty-form');
    newForm.style.display = 'block';
    
    // Add delete button
    const deleteBtn = document.createElement('button');
    deleteBtn.type = 'button';
    deleteBtn.className = 'btn btn-outline-danger btn-sm delete-formset-btn';
    deleteBtn.innerHTML = '<i class="bi bi-trash"></i>';
    deleteBtn.onclick = () => deleteFormsetItem(newForm);
    
    const formHeader = newForm.querySelector('.formset-header');
    if (formHeader) {
        formHeader.appendChild(deleteBtn);
    }
    
    formset.appendChild(newForm);
    totalForms.value = newFormIndex + 1;
}

function deleteFormsetItem(formElement) {
    const deleteInput = formElement.querySelector('input[name$="-DELETE"]');
    if (deleteInput) {
        deleteInput.checked = true;
        formElement.style.display = 'none';
    } else {
        formElement.remove();
    }
}

// Inventory management
function updateStock(itemId, change) {
    const stockElement = document.getElementById(`stock-${itemId}`);
    const currentStock = parseFloat(stockElement.textContent);
    const newStock = Math.max(0, currentStock + change);
    
    stockElement.textContent = newStock.toFixed(2);
    
    // Send update to server
    fetch(`/inventory/${itemId}/update-stock/`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
            'X-CSRFToken': getCookie('csrftoken')
        },
        body: `transaction_type=adjustment&quantity=${newStock}`
    });
}

// Shopping list functionality
function toggleShoppingItem(itemId) {
    const item = document.getElementById(`shopping-item-${itemId}`);
    const checkbox = item.querySelector('.shopping-checkbox');
    
    item.classList.toggle('purchased', checkbox.checked);
    
    // Update server
    fetch(`/inventory/shopping-list/toggle/${itemId}/`, {
        method: 'POST',
        headers: {
            'X-CSRFToken': getCookie('csrftoken')
        }
    });
}

// Temperature and gravity readings
function addTemperatureReading(sessionId) {
    const modal = new bootstrap.Modal(document.getElementById('tempModal'));
    
    document.getElementById('tempForm').onsubmit = function(e) {
        e.preventDefault();
        
        const formData = new FormData(this);
        
        fetch(`/brewing/session/${sessionId}/temperature/`, {
            method: 'POST',
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            },
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            modal.hide();
            location.reload(); // Refresh to show new reading
        });
    };
    
    modal.show();
}

function addGravityReading(sessionId) {
    const modal = new bootstrap.Modal(document.getElementById('gravityModal'));
    
    document.getElementById('gravityForm').onsubmit = function(e) {
        e.preventDefault();
        
        const formData = new FormData(this);
        
        fetch(`/brewing/session/${sessionId}/gravity/`, {
            method: 'POST',
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            },
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            modal.hide();
            location.reload(); // Refresh to show new reading
        });
    };
    
    modal.show();
}

// Chart initialization for analytics
function initializeCharts() {
    // Monthly brewing activity chart
    const monthlyCtx = document.getElementById('monthlyChart');
    if (monthlyCtx && typeof monthlyData !== 'undefined') {
        new Chart(monthlyCtx, {
            type: 'line',
            data: {
                labels: monthlyData.map(d => d.label),
                datasets: [{
                    label: 'Brews per Month',
                    data: monthlyData.map(d => d.brews),
                    borderColor: '#0d6efd',
                    backgroundColor: 'rgba(13, 110, 253, 0.1)',
                    tension: 0.1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: {
                            stepSize: 1
                        }
                    }
                }
            }
        });
    }
    
    // Style breakdown chart
    const styleCtx = document.getElementById('styleChart');
    if (styleCtx && typeof styleData !== 'undefined') {
        new Chart(styleCtx, {
            type: 'doughnut',
            data: {
                labels: styleData.map(d => d.style),
                datasets: [{
                    data: styleData.map(d => d.count),
                    backgroundColor: [
                        '#0d6efd', '#198754', '#ffc107', '#dc3545',
                        '#0dcaf0', '#6c757d', '#f8f9fa', '#212529'
                    ]
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false
            }
        });
    }
    
    // Efficiency trend chart
    const efficiencyCtx = document.getElementById('efficiencyChart');
    if (efficiencyCtx && typeof efficiencyData !== 'undefined') {
        new Chart(efficiencyCtx, {
            type: 'line',
            data: {
                labels: efficiencyData.map(d => d.date),
                datasets: [{
                    label: 'Brewing Efficiency %',
                    data: efficiencyData.map(d => d.efficiency),
                    borderColor: '#198754',
                    backgroundColor: 'rgba(25, 135, 84, 0.1)',
                    tension: 0.1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        min: 50,
                        max: 100,
                        ticks: {
                            callback: function(value) {
                                return value + '%';
                            }
                        }
                    }
                }
            }
        });
    }
}

// Utility functions
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

function showToast(message, type = 'info') {
    const toastContainer = document.getElementById('toast-container') || createToastContainer();
    const toast = document.createElement('div');
    toast.className = `toast align-items-center text-white bg-${type} border-0 show`;
    toast.setAttribute('role', 'alert');
    
    toast.innerHTML = `
        <div class="d-flex">
            <div class="toast-body">${message}</div>
            <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
        </div>
    `;
    
    toastContainer.appendChild(toast);
    
    setTimeout(() => {
        toast.remove();
    }, 5000);
}

function createToastContainer() {
    const container = document.createElement('div');
    container.id = 'toast-container';
    container.className = 'toast-container position-fixed bottom-0 end-0 p-3';
    document.body.appendChild(container);
    return container;
}

// Request notification permission
function requestNotificationPermission() {
    if ('Notification' in window && Notification.permission === 'default') {
        Notification.requestPermission();
    }
}

// Initialize everything when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    // Request notification permission
    requestNotificationPermission();
    
    // Initialize charts if on analytics page
    if (document.querySelector('[data-page="analytics"]')) {
        initializeCharts();
    }
    
    // Initialize tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
    
    // Initialize popovers
    const popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    popoverTriggerList.map(function (popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });
    
    // Auto-hide alerts after 5 seconds
    const alerts = document.querySelectorAll('.alert:not(.alert-permanent)');
    alerts.forEach(alert => {
        setTimeout(() => {
            alert.classList.add('fade');
            setTimeout(() => alert.remove(), 150);
        }, 5000);
    });
});

// Export functions for global use
window.BrewTimer = BrewTimer;
window.startBrewTimer = startBrewTimer;
window.stopBrewTimer = stopBrewTimer;
window.calculateRecipeStats = calculateRecipeStats;
window.addFormsetItem = addFormsetItem;
window.deleteFormsetItem = deleteFormsetItem;
window.updateStock = updateStock;
window.toggleShoppingItem = toggleShoppingItem;
window.addTemperatureReading = addTemperatureReading;
window.addGravityReading = addGravityReading;
window.showToast = showToast;
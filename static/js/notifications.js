// Notifications functionality
let notificationsDropdownOpen = false;

// Fetch and display notifications
async function fetchNotifications() {
    try {
        const response = await fetch('/api/notifications');
        const data = await response.json();

        if (data.success) {
            updateNotificationBadge(data.unread_count);
            displayNotifications(data.notifications);
        }
    } catch (error) {
        console.error('Erreur lors de la récupération des notifications:', error);
    }
}

// Update notification badge count
function updateNotificationBadge(count) {
    const badge = document.getElementById('notificationBadge');
    if (badge) {
        if (count > 0) {
            badge.textContent = count > 99 ? '99+' : count;
            badge.style.display = 'flex';
        } else {
            badge.style.display = 'none';
        }
    }
}

// Display notifications in dropdown
function displayNotifications(notifications) {
    const container = document.getElementById('notificationsList');
    if (!container) return;

    if (notifications.length === 0) {
        container.innerHTML = `
            <div class="notification-empty">
                <i class="fas fa-bell-slash"></i>
                <p>Aucune notification</p>
            </div>
        `;
        return;
    }

    container.innerHTML = notifications.map(notif => `
        <div class="notification-item ${notif.is_read ? 'read' : 'unread'}" data-id="${notif.id}">
            <div class="notification-icon ${notif.type}">
                <i class="fas ${getNotificationIcon(notif.type)}"></i>
            </div>
            <div class="notification-content">
                <p class="notification-message">${notif.message}</p>
                <span class="notification-time">${formatNotificationTime(notif.created_at)}</span>
            </div>
            <div class="notification-actions">
                ${!notif.is_read ? `<button onclick="markAsRead(${notif.id})" class="btn-mark-read" title="Marquer comme lu">
                    <i class="fas fa-check"></i>
                </button>` : ''}
                <button onclick="deleteNotification(${notif.id})" class="btn-delete" title="Supprimer">
                    <i class="fas fa-trash"></i>
                </button>
            </div>
        </div>
    `).join('');
}

// Get icon based on notification type
function getNotificationIcon(type) {
    const icons = {
        'info': 'fa-info-circle',
        'success': 'fa-check-circle',
        'warning': 'fa-exclamation-triangle',
        'error': 'fa-times-circle'
    };
    return icons[type] || 'fa-bell';
}

// Format notification time
function formatNotificationTime(timestamp) {
    const date = new Date(timestamp);
    const now = new Date();
    const diff = now - date;

    const minutes = Math.floor(diff / 60000);
    const hours = Math.floor(diff / 3600000);
    const days = Math.floor(diff / 86400000);

    if (minutes < 1) return 'À l\'instant';
    if (minutes < 60) return `Il y a ${minutes} min`;
    if (hours < 24) return `Il y a ${hours}h`;
    if (days < 7) return `Il y a ${days}j`;

    return date.toLocaleDateString('fr-FR');
}

// Toggle notification dropdown
function toggleNotifications() {
    const dropdown = document.getElementById('notificationDropdown');
    if (!dropdown) return;

    notificationsDropdownOpen = !notificationsDropdownOpen;
    dropdown.style.display = notificationsDropdownOpen ? 'block' : 'none';

    if (notificationsDropdownOpen) {
        fetchNotifications();
    }
}

// Mark notification as read
async function markAsRead(notificationId) {
    try {
        const response = await fetch(`/api/notifications/${notificationId}/mark-read`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });

        const data = await response.json();
        if (data.success) {
            fetchNotifications();
        }
    } catch (error) {
        console.error('Erreur lors du marquage de la notification:', error);
    }
}

// Mark all notifications as read
async function markAllAsRead() {
    try {
        const response = await fetch('/api/notifications/mark-all-read', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });

        const data = await response.json();
        if (data.success) {
            fetchNotifications();
        }
    } catch (error) {
        console.error('Erreur lors du marquage des notifications:', error);
    }
}

// Delete notification
async function deleteNotification(notificationId) {
    try {
        const response = await fetch(`/api/notifications/${notificationId}`, {
            method: 'DELETE',
            headers: {
                'Content-Type': 'application/json'
            }
        });

        const data = await response.json();
        if (data.success) {
            fetchNotifications();
        }
    } catch (error) {
        console.error('Erreur lors de la suppression de la notification:', error);
    }
}

// Close dropdown when clicking outside
document.addEventListener('click', function (event) {
    const notificationBtn = document.getElementById('notificationBtn');
    const dropdown = document.getElementById('notificationDropdown');

    if (notificationBtn && dropdown && notificationsDropdownOpen) {
        if (!notificationBtn.contains(event.target) && !dropdown.contains(event.target)) {
            notificationsDropdownOpen = false;
            dropdown.style.display = 'none';
        }
    }
});

// Auto-refresh notifications every 30 seconds
setInterval(fetchNotifications, 30000);

// Initial fetch on page load
document.addEventListener('DOMContentLoaded', function () {
    fetchNotifications();
});

// Shared logout function
async function logout() {
    try {
        const response = await fetch('/logout');
        if (response.redirected) {
            window.location.href = response.url;
        } else {
            window.location.href = '/login';
        }
    } catch (error) {
        console.error('Erreur de déconnexion:', error);
        window.location.href = '/login';
    }
}


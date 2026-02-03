// Variables globales pour les graphiques
let monthlyChartInstance = null;
let weeklyChartInstance = null;

// Initialisation au chargement de la page
document.addEventListener('DOMContentLoaded', () => {
    loadUserInfo();
    loadStatistics();
    initializeCharts();
    setupMenuToggle();
    markActiveLink();
});

// Charger les informations de l'utilisateur
async function loadUserInfo() {
    try {
        const response = await fetch('/api/user/info');
        const data = await response.json();

        if (data.success) {
            // Mettre à jour le username
            const usernameEl = document.getElementById('headerUsername');
            if (usernameEl) {
                usernameEl.textContent = data.username;
            }
            // Fallback pour ancien id
            const userEmailEl = document.getElementById('userEmail');
            if (userEmailEl) {
                userEmailEl.textContent = data.username;
            }

            // Mettre à jour la photo de profil
            const avatarEl = document.getElementById('headerAvatar');
            if (avatarEl && data.profile_picture) {
                avatarEl.src = data.profile_picture;
            }
            // Fallback pour ancien sélecteur
            const avatarOld = document.querySelector('.user-avatar');
            if (avatarOld && data.profile_picture) {
                avatarOld.src = data.profile_picture;
            }
        }
    } catch (error) {
        console.error('Erreur chargement info utilisateur:', error);
    }
}

// Charger les statistiques
async function loadStatistics() {
    try {
        const [currentMonth, lastMonth, total] = await Promise.all([
            fetch('/api/stats/current-month').then(r => r.json()),
            fetch('/api/stats/last-month').then(r => r.json()),
            fetch('/api/stats/total').then(r => r.json())
        ]);

        displayStats('currentMonthTotal', 'currentMonthWaste', currentMonth);
        displayStats('lastMonthTotal', 'lastMonthWaste', lastMonth);
        displayStats('totalSince', 'totalWaste', total);
    } catch (error) {
        console.error('Erreur lors du chargement des statistiques:', error);
    }
}

// Afficher les statistiques
function displayStats(totalId, wasteId, data) {
    document.getElementById(totalId).textContent = data.total;

    const wasteContainer = document.getElementById(wasteId);
    wasteContainer.innerHTML = '';

    const colors = {
        'Papier': '#2196F3',
        'Plastique': '#9C27B0',
        'Métal': '#FF9800',
        'Verre': '#00BCD4',
        'Carton': '#FF5722'
    };

    for (const [type, quantity] of Object.entries(data.waste_types)) {
        const color = colors[type] || '#4CAF50';
        const item = document.createElement('div');
        item.className = 'waste-item';
        item.innerHTML = `
            <span class="dot" style="background: ${color};"></span>
            <span>${type}: ${quantity}</span>
        `;
        wasteContainer.appendChild(item);
    }
}

// Initialiser les graphiques
async function initializeCharts() {
    await updateMonthlyChart();
    await updateWeeklyChart();
}

// Mettre à jour le graphique mensuel
async function updateMonthlyChart() {
    const year = document.getElementById('yearFilter').value;
    const wasteType = document.getElementById('monthWasteFilter').value;

    // Mettre à jour le titre
    const typeLabel = wasteType === 'all' ? 'tri mensuel' : `tri mensuel (${wasteType})`;
    document.getElementById('selectedMonthWaste').textContent = typeLabel;

    try {
        const response = await fetch(`/api/chart/monthly?year=${year}&waste_type=${wasteType}`);
        const data = await response.json();

        const ctx = document.getElementById('monthlyChart').getContext('2d');

        if (monthlyChartInstance) {
            monthlyChartInstance.destroy();
        }

        monthlyChartInstance = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: data.months,
                datasets: [{
                    label: 'Objets triés',
                    data: data.data,
                    backgroundColor: '#4CAF50',
                    borderRadius: 5,
                    borderSkipped: false
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                plugins: {
                    legend: {
                        display: false
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        max: Math.max(...data.data, 100)
                    }
                }
            }
        });
    } catch (error) {
        console.error('Erreur lors du chargement du graphique mensuel:', error);
    }
}

// Mettre à jour le graphique hebdomadaire
async function updateWeeklyChart() {
    const weekOffset = document.getElementById('weekFilter').value;
    const wasteType = document.getElementById('weekWasteFilter').value;

    // Mettre à jour le titre
    const typeLabel = wasteType === 'all' ? 'tri hebdomadaire' : `tri hebdomadaire (${wasteType})`;
    document.getElementById('selectedWeeklyWaste').textContent = typeLabel;

    try {
        const response = await fetch(`/api/chart/weekly?week_offset=${weekOffset}&waste_type=${wasteType}`);
        const data = await response.json();

        const ctx = document.getElementById('weeklyChart').getContext('2d');

        if (weeklyChartInstance) {
            weeklyChartInstance.destroy();
        }

        weeklyChartInstance = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: data.days,
                datasets: [{
                    label: 'Objets triés',
                    data: data.data,
                    backgroundColor: '#4CAF50',
                    borderRadius: 5,
                    borderSkipped: false
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                plugins: {
                    legend: {
                        display: false
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        max: Math.max(...data.data, 100)
                    }
                }
            }
        });
    } catch (error) {
        console.error('Erreur lors du chargement du graphique hebdomadaire:', error);
    }
}

// Marquer le lien actif
function markActiveLink() {
    const currentPath = window.location.pathname;
    const links = document.querySelectorAll('.sidebar nav a');

    links.forEach(link => {
        link.parentElement.classList.remove('active');
        if (link.getAttribute('href') === currentPath) {
            link.parentElement.classList.add('active');
        }
    });
}

// Gérer le menu toggle mobile
function setupMenuToggle() {
    const toggle = document.querySelector('.menu-toggle');
    const sidebar = document.querySelector('.sidebar');

    if (toggle) {
        toggle.addEventListener('click', () => {
            sidebar.classList.toggle('active');
        });
    }
}

// Déconnexion
async function logout() {
    try {
        const response = await fetch('/api/logout', {
            method: 'POST'
        });

        if (response.ok) {
            window.location.href = '/';
        }
    } catch (error) {
        console.error('Erreur de déconnexion:', error);
    }
}
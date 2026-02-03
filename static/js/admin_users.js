// Gestion des utilisateurs - Admin

document.addEventListener('DOMContentLoaded', () => {
    loadUserInfo();
    loadUsers();
    setupMenuToggle();
});

// Charger les informations de l'utilisateur pour le header
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

// Charger la liste des utilisateurs
async function loadUsers() {
    try {
        const response = await fetch('/api/admin/users');
        const data = await response.json();

        if (data.success) {
            displayUsers(data.users);
        } else {
            showError('Erreur lors du chargement des utilisateurs');
        }
    } catch (error) {
        console.error('Erreur:', error);
        showError('Erreur de connexion au serveur');
    }
}

// Afficher les utilisateurs dans le tableau
function displayUsers(users) {
    const tbody = document.getElementById('usersTableBody');

    if (users.length === 0) {
        tbody.innerHTML = '<tr><td colspan="5" class="no-users">Aucun utilisateur</td></tr>';
        return;
    }

    tbody.innerHTML = users.map(user => `
        <tr>
            <td>${user.email}</td>
            <td>
                <span class="role-badge ${user.role}">
                    ${user.role === 'admin' ? 'Admin' : 'Utilisateur'}
                </span>
            </td>
            <td class="date-text">${formatDate(user.created_at)}</td>
            <td class="date-text">
                ${user.last_login ? formatDate(user.last_login) : '<span class="never-logged">Jamais connecté</span>'}
            </td>
            <td>
                <div class="action-buttons">
                    <button class="btn-small btn-role" onclick="toggleRole(${user.id}, '${user.role}')">
                        ${user.role === 'admin' ? '↓ User' : '↑ Admin'}
                    </button>
                    <button class="btn-small btn-delete" onclick="deleteUser(${user.id}, '${user.email}')">
                        🗑️ Supprimer
                    </button>
                </div>
            </td>
        </tr>
    `).join('');
}

// Changer le rôle d'un utilisateur
async function toggleRole(userId, currentRole) {
    const newRole = currentRole === 'admin' ? 'user' : 'admin';

    if (!confirm(`Voulez-vous vraiment changer ce rôle en ${newRole === 'admin' ? 'Admin' : 'Utilisateur'} ?`)) {
        return;
    }

    try {
        const response = await fetch(`/api/admin/users/${userId}/role`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ role: newRole })
        });

        const data = await response.json();

        if (data.success) {
            showSuccess(data.message);
            loadUsers(); // Recharger la liste
        } else {
            showError(data.message);
        }
    } catch (error) {
        console.error('Erreur:', error);
        showError('Erreur lors de la modification du rôle');
    }
}

// Supprimer un utilisateur
async function deleteUser(userId, email) {
    if (!confirm(`Voulez-vous vraiment supprimer l'utilisateur ${email} ?\n\nCette action est irréversible et supprimera toutes ses données.`)) {
        return;
    }

    try {
        const response = await fetch(`/api/admin/users/${userId}`, {
            method: 'DELETE'
        });

        const data = await response.json();

        if (data.success) {
            showSuccess(data.message);
            loadUsers(); // Recharger la liste
        } else {
            showError(data.message);
        }
    } catch (error) {
        console.error('Erreur:', error);
        showError('Erreur lors de la suppression');
    }
}

// Formater les dates
function formatDate(dateString) {
    if (!dateString) return 'N/A';

    const date = new Date(dateString);
    const options = {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    };

    return date.toLocaleDateString('fr-FR', options);
}

// Afficher un message de succès
function showSuccess(message) {
    alert('✅ ' + message);
}

// Afficher un message d'erreur
function showError(message) {
    alert('❌ ' + message);
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

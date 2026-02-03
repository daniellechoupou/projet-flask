// Charger le profil au démarrage
document.addEventListener('DOMContentLoaded', function () {
    loadProfile();
    loadUserInfo();
});

// Charger les informations du profil
async function loadProfile() {
    try {
        const response = await fetch('/api/profile');
        const data = await response.json();

        if (data.success) {
            document.getElementById('email').value = data.email;
            document.getElementById('username').value = data.username || '';
            document.getElementById('role').value = data.role === 'admin' ? 'Administrateur' : 'Utilisateur';

            // Formater la date
            if (data.created_at) {
                const date = new Date(data.created_at);
                document.getElementById('createdAt').value = date.toLocaleDateString('fr-FR', {
                    year: 'numeric',
                    month: 'long',
                    day: 'numeric'
                });
            }

            // Photo de profil
            if (data.profile_picture) {
                document.getElementById('profilePicture').src = data.profile_picture;
            }
        }
    } catch (error) {
        console.error('Erreur chargement profil:', error);
        showToast('Erreur lors du chargement du profil', 'error');
    }
}

// Charger les infos utilisateur pour le header
async function loadUserInfo() {
    try {
        const response = await fetch('/api/user/info');
        const data = await response.json();

        if (data.success) {
            document.getElementById('headerUsername').textContent = data.username;
            if (data.profile_picture) {
                document.getElementById('headerAvatar').src = data.profile_picture;
            }
        }
    } catch (error) {
        console.error('Erreur chargement info header:', error);
    }
}

// Mettre à jour le profil
async function updateProfile() {
    const username = document.getElementById('username').value.trim();

    try {
        const response = await fetch('/api/profile/update', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ username })
        });

        const data = await response.json();

        if (data.success) {
            showToast('Profil mis à jour avec succès !', 'success');
            // Mettre à jour le header
            document.getElementById('headerUsername').textContent = username;
        } else {
            showToast(data.message || 'Erreur lors de la mise à jour', 'error');
        }
    } catch (error) {
        console.error('Erreur mise à jour profil:', error);
        showToast('Erreur lors de la mise à jour', 'error');
    }
}

// Changer le mot de passe
async function changePassword() {
    const currentPassword = document.getElementById('currentPassword').value;
    const newPassword = document.getElementById('newPassword').value;
    const confirmPassword = document.getElementById('confirmPassword').value;

    // Validation côté client
    if (!currentPassword || !newPassword || !confirmPassword) {
        showToast('Veuillez remplir tous les champs', 'warning');
        return;
    }

    if (newPassword !== confirmPassword) {
        showToast('Les mots de passe ne correspondent pas', 'error');
        return;
    }

    if (newPassword.length < 6) {
        showToast('Le mot de passe doit contenir au moins 6 caractères', 'warning');
        return;
    }

    try {
        const response = await fetch('/api/profile/change-password', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                current_password: currentPassword,
                new_password: newPassword,
                confirm_password: confirmPassword
            })
        });

        const data = await response.json();

        if (data.success) {
            showToast('Mot de passe modifié avec succès !', 'success');
            // Vider les champs
            document.getElementById('currentPassword').value = '';
            document.getElementById('newPassword').value = '';
            document.getElementById('confirmPassword').value = '';
        } else {
            showToast(data.message || 'Erreur lors du changement de mot de passe', 'error');
        }
    } catch (error) {
        console.error('Erreur changement mot de passe:', error);
        showToast('Erreur lors du changement de mot de passe', 'error');
    }
}

// Prévisualiser et uploader la photo
async function previewAndUpload(input) {
    if (input.files && input.files[0]) {
        const file = input.files[0];

        // Vérifier la taille (max 5 Mo)
        if (file.size > 5 * 1024 * 1024) {
            showToast('La taille du fichier ne doit pas dépasser 5 Mo', 'warning');
            return;
        }

        // Prévisualiser
        const reader = new FileReader();
        reader.onload = function (e) {
            document.getElementById('profilePicture').src = e.target.result;
        };
        reader.readAsDataURL(file);

        // Uploader
        const formData = new FormData();
        formData.append('file', file);

        try {
            const response = await fetch('/api/profile/upload-picture', {
                method: 'POST',
                body: formData
            });

            const data = await response.json();

            if (data.success) {
                showToast('Photo de profil mise à jour !', 'success');
                // Mettre à jour le header
                if (data.picture_url) {
                    document.getElementById('headerAvatar').src = data.picture_url;
                }
            } else {
                showToast(data.message || 'Erreur lors de l\'upload', 'error');
                // Recharger la photo actuelle
                loadProfile();
            }
        } catch (error) {
            console.error('Erreur upload photo:', error);
            showToast('Erreur lors de l\'upload de la photo', 'error');
            loadProfile();
        }
    }
}

// Toggle visibilité mot de passe
function togglePassword(inputId) {
    const input = document.getElementById(inputId);
    const button = input.nextElementSibling;

    if (input.type === 'password') {
        input.type = 'text';
        button.textContent = '🙈';
    } else {
        input.type = 'password';
        button.textContent = '👁️';
    }
}

// Déconnexion
async function logout() {
    try {
        const response = await fetch('/api/logout', {
            method: 'POST'
        });

        if (response.ok) {
            window.location.href = '/login';
        }
    } catch (error) {
        console.error('Erreur déconnexion:', error);
    }
}

// Afficher un toast
function showToast(message, type = 'success') {
    const toast = document.getElementById('toast');
    toast.textContent = message;
    toast.className = `toast ${type} show`;

    setTimeout(() => {
        toast.classList.remove('show');
    }, 3000);
}

// Toggle sidebar mobile
document.querySelector('.menu-toggle')?.addEventListener('click', function () {
    document.querySelector('.sidebar').classList.toggle('active');
});

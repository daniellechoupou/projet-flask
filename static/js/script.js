// Toggle entre les formulaires de login et register
function toggleForm() {
    document.getElementById('loginForm').classList.toggle('form-hidden');
    document.getElementById('registerForm').classList.toggle('form-hidden');
    document.getElementById('toggleLoginText').classList.toggle('form-hidden');
    document.getElementById('toggleRegisterText').classList.toggle('form-hidden');
}

// Gestion du formulaire de Login
document.getElementById('loginForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const email = document.getElementById('loginEmail').value;
    const password = document.getElementById('loginPassword').value;
    const loginBtn = document.querySelector('#loginForm .btn-login');
    const loading = document.getElementById('loginLoading');
    const text = document.getElementById('loginText');
    const message = document.getElementById('loginMessage');
    
    // Afficher le chargement
    loginBtn.disabled = true;
    loading.style.display = 'inline';
    text.style.display = 'none';
    
    try {
        const response = await fetch('/api/login', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ email, password })
        });
        
        const data = await response.json();
        
        if (data.success) {
            message.classList.remove('error');
            message.classList.add('success');
            message.textContent = 'Connexion réussie ! Redirection...';
            setTimeout(() => {
                window.location.href = '/dashboard';
            }, 1500);
        } else {
            message.classList.remove('success');
            message.classList.add('error');
            message.textContent = data.message;
        }
    } catch (error) {
        message.classList.remove('success');
        message.classList.add('error');
        message.textContent = 'Erreur de connexion au serveur';
        console.error('Error:', error);
    } finally {
        loginBtn.disabled = false;
        loading.style.display = 'none';
        text.style.display = 'inline';
    }
});

// Gestion du formulaire d'Inscription
document.getElementById('registerForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const email = document.getElementById('registerEmail').value;
    const password = document.getElementById('registerPassword').value;
    const confirmPassword = document.getElementById('confirmPassword').value;
    const message = document.getElementById('registerMessage');
    
    // Vérification que les mots de passe correspondent
    if (password !== confirmPassword) {
        message.classList.remove('success');
        message.classList.add('error');
        message.textContent = 'Les mots de passe ne correspondent pas';
        return;
    }
    
    // Vérification de la longueur minimale du mot de passe
    if (password.length < 6) {
        message.classList.remove('success');
        message.classList.add('error');
        message.textContent = 'Le mot de passe doit contenir au moins 6 caractères';
        return;
    }
    
    const registerBtn = document.querySelector('#registerForm .btn-login');
    const loading = document.getElementById('registerLoading');
    const text = document.getElementById('registerText');
    
    // Afficher le chargement
    registerBtn.disabled = true;
    loading.style.display = 'inline';
    text.style.display = 'none';
    
    try {
        const response = await fetch('/api/register', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ email, password })
        });
        
        const data = await response.json();
        
        if (data.success) {
            message.classList.remove('error');
            message.classList.add('success');
            message.textContent = 'Inscription réussie ! Veuillez vous connecter.';
            setTimeout(() => {
                document.getElementById('registerForm').reset();
                toggleForm();
            }, 1500);
        } else {
            message.classList.remove('success');
            message.classList.add('error');
            message.textContent = data.message;
        }
    } catch (error) {
        message.classList.remove('success');
        message.classList.add('error');
        message.textContent = 'Erreur de connexion au serveur';
        console.error('Error:', error);
    } finally {
        registerBtn.disabled = false;
        loading.style.display = 'none';
        text.style.display = 'inline';
    }
});
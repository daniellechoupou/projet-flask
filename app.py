from flask import Flask, render_template, request, jsonify, session, redirect, Response,send_file
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import sqlite3
import uuid
from datetime import datetime, timedelta
from functools import wraps
import os
import cv2
import numpy as np
from yolo_detector import WasteDetector
from ultralytics import YOLO

app = Flask(__name__)
app.secret_key = 'your-secret-key-wasteai'

# Chemin de la base de données
DB_PATH = os.path.join(os.path.dirname(__file__), 'waste.db')

# Initialiser le détecteur YOLO
try:
    YOLO_DETECTOR = WasteDetector('my_model.pt')
    print("✅ Modèle YOLO personnalisé (my_model.pt) chargé avec succès")
except Exception as e:
    print(f"⚠️ Erreur chargement YOLO: {e}")
    YOLO_DETECTOR = None

# Variable globale pour la caméra
camera = None
detection_buffer = {}  # Buffer pour accumuler les détections
frame_count = 0  # Compteur de frames
SAVE_INTERVAL = 10  # Sauvegarder toutes les 10 frames

def get_camera():
    global camera
    if camera is None:
        camera = cv2.VideoCapture(0)
    return camera

def release_camera():
    global camera
    if camera is not None:
        camera.release()
        camera = None

# Initialiser la base de données
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Table des utilisateurs
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (id INTEGER PRIMARY KEY, 
                  email TEXT UNIQUE, 
                  password TEXT, 
                  role TEXT DEFAULT 'user',
                  created_at TIMESTAMP,
                  last_login TIMESTAMP)''')
    
    # Migration : ajouter les colonnes role et last_login si elles n'existent pas
    try:
        c.execute("ALTER TABLE users ADD COLUMN role TEXT DEFAULT 'user'")
    except sqlite3.OperationalError:
        pass  # La colonne existe déjà
    
    try:
        c.execute("ALTER TABLE users ADD COLUMN last_login TIMESTAMP")
    except sqlite3.OperationalError:
        pass  # La colonne existe déjà
    
    # Migration : ajouter username et profile_picture
    try:
        c.execute("ALTER TABLE users ADD COLUMN username TEXT")
    except sqlite3.OperationalError:
        pass  # La colonne existe déjà
    
    try:
        c.execute("ALTER TABLE users ADD COLUMN profile_picture TEXT")
    except sqlite3.OperationalError:
        pass  # La colonne existe déjà
    
    # Table des déchets détectés
    c.execute('''CREATE TABLE IF NOT EXISTS waste_detection
                 (id INTEGER PRIMARY KEY, 
                  user_id INTEGER, 
                  waste_type TEXT, 
                  quantity INTEGER,
                  detection_date TIMESTAMP,
                  FOREIGN KEY(user_id) REFERENCES users(id))''')
    
    # Table des robots
    c.execute('''CREATE TABLE IF NOT EXISTS robots
                 (id INTEGER PRIMARY KEY,
                  user_id INTEGER,
                  location TEXT,
                  battery_level INTEGER,
                  is_active BOOLEAN,
                  camera_status TEXT,
                  FOREIGN KEY(user_id) REFERENCES users(id))''')
    
    conn.commit()
    conn.close()

init_db()

# Décorateur pour vérifier l'authentification
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect('/login')
        return f(*args, **kwargs)
    return decorated_function

# Décorateur pour vérifier les droits admin
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect('/login')
        if session.get('role') != 'admin':
            return jsonify({'success': False, 'message': 'Accès refusé - Admin uniquement'}), 403
        return f(*args, **kwargs)
    return decorated_function

# ==================== ROUTES D'AUTHENTIFICATION ====================

@app.route('/')
def index():
    return redirect('/login')

@app.route('/login')
def login_page():
    if 'user_id' in session:
        return redirect('/dashboard')
    return render_template('login.html')

@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    email = data.get('email')
    password = data.get('password')
    
    if not email or not password:
        return jsonify({'success': False, 'message': 'Email et mot de passe requis'}), 400
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT id, password, role FROM users WHERE email = ?', (email,))
    user = c.fetchone()
    
    if user and check_password_hash(user[1], password):
        # Mettre à jour last_login
        c.execute('UPDATE users SET last_login = ? WHERE id = ?', (datetime.now(), user[0]))
        conn.commit()
        conn.close()
        
        # Stocker les infos en session
        session['user_id'] = user[0]
        session['email'] = email
        session['role'] = user[2] if user[2] else 'user'
        return jsonify({'success': True, 'message': 'Connexion réussie'})
    
    conn.close()
    return jsonify({'success': False, 'message': 'Email ou mot de passe incorrect'}), 401

@app.route('/api/register', methods=['POST'])
def register():
    data = request.json
    email = data.get('email')
    password = data.get('password')
    
    if not email or not password:
        return jsonify({'success': False, 'message': 'Email et mot de passe requis'}), 400
    
    hashed_password = generate_password_hash(password)
    
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        
        # Vérifier si c'est le premier utilisateur
        c.execute('SELECT COUNT(*) FROM users')
        user_count = c.fetchone()[0]
        
        # Premier utilisateur = admin, sinon user
        role = 'admin' if user_count == 0 else 'user'
        
        c.execute('INSERT INTO users (email, password, role, created_at) VALUES (?, ?, ?, ?)',
                  (email, hashed_password, role, datetime.now()))
        conn.commit()
        conn.close()
        return jsonify({'success': True, 'message': 'Inscription réussie'})
    except sqlite3.IntegrityError:
        return jsonify({'success': False, 'message': 'Cet email est déjà utilisé'}), 400

@app.route('/api/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({'success': True, 'message': 'Déconnexion réussie'})

# ==================== ROUTES PROFIL ====================

# Configuration upload
UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'static', 'uploads', 'profiles')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/profile')
@login_required
def profile_page():
    """Page de profil utilisateur"""
    return render_template('profile.html', email=session.get('email'))

@app.route('/api/profile', methods=['GET'])
@login_required
def get_profile():
    """Récupérer les informations du profil"""
    user_id = session.get('user_id')
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT email, username, profile_picture, role, created_at FROM users WHERE id = ?', (user_id,))
    user = c.fetchone()
    conn.close()
    
    if user:
        return jsonify({
            'success': True,
            'email': user[0],
            'username': user[1] or '',
            'profile_picture': user[2] or '',
            'role': user[3] if user[3] else 'user',
            'created_at': user[4]
        })
    
    return jsonify({'success': False, 'message': 'Utilisateur non trouvé'}), 404

@app.route('/api/profile/update', methods=['POST'])
@login_required
def update_profile():
    """Mettre à jour le profil (username)"""
    user_id = session.get('user_id')
    data = request.json
    username = data.get('username', '').strip()
    
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('UPDATE users SET username = ? WHERE id = ?', (username, user_id))
        conn.commit()
        conn.close()
        
        # Mettre à jour la session
        session['username'] = username
        
        return jsonify({'success': True, 'message': 'Profil mis à jour'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/profile/change-password', methods=['POST'])
@login_required
def change_password():
    """Changer le mot de passe"""
    user_id = session.get('user_id')
    data = request.json
    
    current_password = data.get('current_password')
    new_password = data.get('new_password')
    confirm_password = data.get('confirm_password')
    
    if not current_password or not new_password or not confirm_password:
        return jsonify({'success': False, 'message': 'Tous les champs sont requis'}), 400
    
    if new_password != confirm_password:
        return jsonify({'success': False, 'message': 'Les mots de passe ne correspondent pas'}), 400
    
    if len(new_password) < 6:
        return jsonify({'success': False, 'message': 'Le mot de passe doit contenir au moins 6 caractères'}), 400
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT password FROM users WHERE id = ?', (user_id,))
    user = c.fetchone()
    
    if not user or not check_password_hash(user[0], current_password):
        conn.close()
        return jsonify({'success': False, 'message': 'Mot de passe actuel incorrect'}), 401
    
    hashed_password = generate_password_hash(new_password)
    c.execute('UPDATE users SET password = ? WHERE id = ?', (hashed_password, user_id))
    conn.commit()
    conn.close()
    
    return jsonify({'success': True, 'message': 'Mot de passe modifié avec succès'})

@app.route('/api/profile/upload-picture', methods=['POST'])
@login_required
def upload_profile_picture():
    """Uploader une photo de profil"""
    user_id = session.get('user_id')
    
    if 'file' not in request.files:
        return jsonify({'success': False, 'message': 'Aucun fichier envoyé'}), 400
    
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({'success': False, 'message': 'Aucun fichier sélectionné'}), 400
    
    if file and allowed_file(file.filename):
        # Créer le dossier s'il n'existe pas
        os.makedirs(UPLOAD_FOLDER, exist_ok=True)
        
        # Générer un nom unique
        ext = file.filename.rsplit('.', 1)[1].lower()
        filename = f"{user_id}_{uuid.uuid4().hex}.{ext}"
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        
        # Supprimer l'ancienne photo si elle existe
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('SELECT profile_picture FROM users WHERE id = ?', (user_id,))
        old_picture = c.fetchone()
        
        if old_picture and old_picture[0]:
            old_path = os.path.join(os.path.dirname(__file__), 'static', old_picture[0].lstrip('/static/'))
            if os.path.exists(old_path):
                try:
                    os.remove(old_path)
                except:
                    pass
        
        # Sauvegarder le nouveau fichier
        file.save(filepath)
        
        # Mettre à jour la BDD
        picture_url = f"/static/uploads/profiles/{filename}"
        c.execute('UPDATE users SET profile_picture = ? WHERE id = ?', (picture_url, user_id))
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': 'Photo de profil mise à jour',
            'picture_url': picture_url
        })
    
    return jsonify({'success': False, 'message': 'Type de fichier non autorisé (png, jpg, jpeg, gif)'}), 400

@app.route('/api/user/info', methods=['GET'])
@login_required
def get_user_info():
    """Récupérer les infos utilisateur pour le header"""
    user_id = session.get('user_id')
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT username, profile_picture, email FROM users WHERE id = ?', (user_id,))
    user = c.fetchone()
    conn.close()
    
    if user:
        return jsonify({
            'success': True,
            'username': user[0] or user[2].split('@')[0],  # Username ou partie avant @ de l'email
            'profile_picture': user[1] or '',
            'email': user[2]
        })
    
    return jsonify({'success': False}), 404

# ==================== ROUTES DASHBOARD ====================

@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html', email=session.get('email'))

@app.route('/api/stats/current-month', methods=['GET'])
@login_required
def get_current_month_stats():
    user_id = session.get('user_id')
    today = datetime.now()
    first_day = today.replace(day=1)
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute('''SELECT SUM(quantity) FROM waste_detection 
                 WHERE user_id = ? AND detection_date >= ?''',
              (user_id, first_day))
    total = c.fetchone()[0] or 0
    
    c.execute('''SELECT waste_type, SUM(quantity) FROM waste_detection 
                 WHERE user_id = ? AND detection_date >= ?
                 GROUP BY waste_type''',
              (user_id, first_day))
    waste_types = c.fetchall()
    conn.close()
    
    waste_data = {row[0]: row[1] for row in waste_types}
    
    return jsonify({'total': total, 'waste_types': waste_data})

@app.route('/api/stats/last-month', methods=['GET'])
@login_required
def get_last_month_stats():
    user_id = session.get('user_id')
    today = datetime.now()
    first_day_current = today.replace(day=1)
    first_day_last = (first_day_current - timedelta(days=1)).replace(day=1)
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute('''SELECT SUM(quantity) FROM waste_detection 
                 WHERE user_id = ? AND detection_date >= ? AND detection_date < ?''',
              (user_id, first_day_last, first_day_current))
    total = c.fetchone()[0] or 0
    
    c.execute('''SELECT waste_type, SUM(quantity) FROM waste_detection 
                 WHERE user_id = ? AND detection_date >= ? AND detection_date < ?
                 GROUP BY waste_type''',
              (user_id, first_day_last, first_day_current))
    waste_types = c.fetchall()
    conn.close()
    
    waste_data = {row[0]: row[1] for row in waste_types}
    
    return jsonify({'total': total, 'waste_types': waste_data})

@app.route('/api/stats/total', methods=['GET'])
@login_required
def get_total_stats():
    user_id = session.get('user_id')
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute('''SELECT SUM(quantity) FROM waste_detection WHERE user_id = ?''', (user_id,))
    total = c.fetchone()[0] or 0
    
    c.execute('''SELECT waste_type, SUM(quantity) FROM waste_detection 
                 WHERE user_id = ?
                 GROUP BY waste_type''', (user_id,))
    waste_types = c.fetchall()
    conn.close()
    
    waste_data = {row[0]: row[1] for row in waste_types}
    
    return jsonify({'total': total, 'waste_types': waste_data})

@app.route('/api/chart/monthly', methods=['GET'])
@login_required
def get_monthly_chart():
    user_id = session.get('user_id')
    year = request.args.get('year', datetime.now().year, type=int)
    waste_type = request.args.get('waste_type', 'all')
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    months = list(range(1, 13))
    data = []
    
    for month in months:
        if waste_type == 'all':
            c.execute('''SELECT SUM(quantity) FROM waste_detection 
                         WHERE user_id = ? AND strftime('%Y-%m', detection_date) = ?''',
                      (user_id, f'{year:04d}-{month:02d}'))
        else:
            c.execute('''SELECT SUM(quantity) FROM waste_detection 
                         WHERE user_id = ? AND waste_type = ? AND strftime('%Y-%m', detection_date) = ?''',
                      (user_id, waste_type, f'{year:04d}-{month:02d}'))
        
        result = c.fetchone()[0] or 0
        data.append(result)
    
    conn.close()
    month_names = ['Jan', 'Fév', 'Mar', 'Avr', 'Mai', 'Jun', 'Jul', 'Aoû', 'Sep', 'Oct', 'Nov', 'Déc']
    
    return jsonify({'months': month_names, 'data': data})

@app.route('/api/chart/weekly', methods=['GET'])
@login_required
def get_weekly_chart():
    user_id = session.get('user_id')
    week_offset = request.args.get('week_offset', 0, type=int)
    waste_type = request.args.get('waste_type', 'all')
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    today = datetime.now()
    week_start = today - timedelta(days=today.weekday()) - timedelta(weeks=week_offset)
    
    days = []
    data = []
    day_names = ['Lun', 'Mar', 'Mer', 'Jeu', 'Ven', 'Sam', 'Dim']
    
    for i in range(7):
        day = week_start + timedelta(days=i)
        day_str = day.strftime('%Y-%m-%d')
        
        if waste_type == 'all':
            c.execute('''SELECT SUM(quantity) FROM waste_detection 
                         WHERE user_id = ? AND DATE(detection_date) = ?''',
                      (user_id, day_str))
        else:
            c.execute('''SELECT SUM(quantity) FROM waste_detection 
                         WHERE user_id = ? AND waste_type = ? AND DATE(detection_date) = ?''',
                      (user_id, waste_type, day_str))
        
        result = c.fetchone()[0] or 0
        days.append(day_names[i])
        data.append(result)
    
    conn.close()
    
    return jsonify({'days': days, 'data': data})

@app.route('/api/waste/add', methods=['POST'])
@login_required
def add_waste_detection():
    user_id = session.get('user_id')
    data = request.json
    
    waste_type = data.get('waste_type')
    quantity = data.get('quantity', 1)
    detection_date = data.get('detection_date', datetime.now())
    
    if not waste_type:
        return jsonify({'success': False, 'message': 'Type de déchet requis'}), 400
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''INSERT INTO waste_detection (user_id, waste_type, quantity, detection_date)
                 VALUES (?, ?, ?, ?)''',
              (user_id, waste_type, quantity, detection_date))
    conn.commit()
    conn.close()
    
    return jsonify({'success': True, 'message': 'Déchet ajouté'})

# ==================== ROUTES CAMERA ====================

@app.route('/camera')
@login_required
def camera_page():
    return render_template('camera.html', email=session.get('email'))

def gen_frames():
    global frame_count, detection_buffer
    
    cam = get_camera()
    if not cam.isOpened():
        print("❌ Caméra non accessible (isOpened=False)")
    else:
        print("📸 Flux caméra démarré")

    while True:
        success, frame = cam.read()
        if not success:
            print("❌ Echec lecture frame caméra")
            # Générer une image d'erreur
            error_frame = np.zeros((480, 640, 3), dtype=np.uint8)
            cv2.putText(error_frame, "ERREUR CAMERA", (50, 240), 
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
            ret, buffer = cv2.imencode('.jpg', error_frame)
            frame = buffer.tobytes()
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
            break
        else:
            # Detection YOLO si disponible
            detections_summary = {}
            if YOLO_DETECTOR:
                frame, detections_summary = YOLO_DETECTOR.detect_from_frame(frame)
                
                # Accumuler les détections dans le buffer
                if detections_summary:
                    for waste_type, count in detections_summary.items():
                        if waste_type not in detection_buffer:
                            detection_buffer[waste_type] = 0
                        detection_buffer[waste_type] += count
            
            # Sauvegarder toutes les SAVE_INTERVAL frames
            frame_count += 1
            if frame_count >= SAVE_INTERVAL and detection_buffer:
                # Sauvegarder dans la BD
                user_id = session.get('user_id')
                if user_id and YOLO_DETECTOR:
                    try:
                        YOLO_DETECTOR.save_detections_to_db(user_id, detection_buffer)
                        print(f"✅ Détections sauvegardées: {detection_buffer}")
                    except Exception as e:
                        print(f"❌ Erreur sauvegarde détections: {e}")
                
                # Réinitialiser le buffer et le compteur
                detection_buffer = {}
                frame_count = 0
            
            ret, buffer = cv2.imencode('.jpg', frame)
            frame = buffer.tobytes()
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

@app.route('/video_feed')
@login_required
def video_feed():
    return Response(gen_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/api/robot/status', methods=['GET'])
@login_required
def get_robot_status():
    user_id = session.get('user_id')
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT location, battery_level, is_active FROM robots WHERE user_id = ?', (user_id,))
    robot = c.fetchone()
    conn.close()
    
    if robot:
        return jsonify({
            'success': True,
            'location': robot[0],
            'battery': robot[1],
            'is_active': robot[2]
        })
    
    return jsonify({
        'success': True,
        'location': 'Glacier Moderne, Bonamoussadi, Douala Cameroun',
        'battery': 85,
        'is_active': False
    })

@app.route('/api/camera/toggle', methods=['POST'])
@login_required
def toggle_camera_route():
    global detection_buffer, frame_count
    
    data = request.json
    action = data.get('action')
    
    if action == 'start':
        get_camera()
        # Réinitialiser le buffer et le compteur au démarrage
        detection_buffer = {}
        frame_count = 0
    elif action == 'stop':
        release_camera()
        # Sauvegarder les détections restantes avant d'arrêter
        user_id = session.get('user_id')
        if user_id and detection_buffer and YOLO_DETECTOR:
            try:
                YOLO_DETECTOR.save_detections_to_db(user_id, detection_buffer)
                print(f"✅ Détections finales sauvegardées: {detection_buffer}")
            except Exception as e:
                print(f"❌ Erreur sauvegarde détections finales: {e}")
        detection_buffer = {}
        frame_count = 0
    
    return jsonify({
        'success': True,
        'message': f'Caméra {"activée" if action == "start" else "désactivée"}',
        'status': action
    })

@app.route('/api/camera/recent-detections', methods=['GET'])
@login_required
def get_recent_detections():
    """Récupérer les détections des 30 dernières secondes"""
    user_id = session.get('user_id')
    
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        
        # Récupérer les détections des 30 dernières secondes
        c.execute('''SELECT waste_type, SUM(quantity) as total 
                     FROM waste_detection 
                     WHERE user_id = ? 
                     AND detection_date >= datetime('now', '-30 seconds')
                     GROUP BY waste_type''', (user_id,))
        
        detections = c.fetchall()
        conn.close()
        
        # Formater les résultats
        result = {row[0]: row[1] for row in detections}
        
        return jsonify({
            'success': True,
            'detections': result
        })
    except Exception as e:
        print(f"❌ Erreur récupération détections: {e}")
        return jsonify({
            'success': False,
            'detections': {}
        })

@app.route('/api/robot/stats', methods=['GET'])
@login_required
def get_robot_stats():
    user_id = session.get('user_id')
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute('''SELECT COUNT(*), SUM(quantity) FROM waste_detection 
                 WHERE user_id = ? AND DATE(detection_date) = DATE('now')''', (user_id,))
    result = c.fetchone()
    detections_today = result[0] or 0
    quantity_today = result[1] or 0
    
    c.execute('''SELECT COUNT(*), SUM(quantity) FROM waste_detection 
                 WHERE user_id = ?''', (user_id,))
    result = c.fetchone()
    total_detections = result[0] or 0
    total_quantity = result[1] or 0
    
    conn.close()
    
    return jsonify({
        'today': {'detections': detections_today, 'quantity': quantity_today},
        'total': {'detections': total_detections, 'quantity': total_quantity}
    })

@app.route('/api/robot/add', methods=['POST'])
@login_required
def add_robot():
    user_id = session.get('user_id')
    data = request.json
    
    location = data.get('location', 'Glacier Moderne, Bonamoussadi, Douala Cameroun')
    battery = data.get('battery', 85)
    is_active = data.get('is_active', False)
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT id FROM robots WHERE user_id = ?', (user_id,))
    
    if c.fetchone():
        c.execute('''UPDATE robots SET location = ?, battery_level = ?, is_active = ? 
                     WHERE user_id = ?''',
                  (location, battery, is_active, user_id))
    else:
        c.execute('''INSERT INTO robots (user_id, location, battery_level, is_active, camera_status)
                     VALUES (?, ?, ?, ?, ?)''',
                  (user_id, location, battery, is_active, 'inactive'))
    
    conn.commit()
    conn.close()
    
    return jsonify({'success': True, 'message': 'Robot mis à jour'})

# ==================== ROUTES DÉTECTION ROBOT ====================

@app.route('/api/detection/record', methods=['POST'])
def record_detection():
    """
    Route pour enregistrer les détections du robot
    Le robot envoie les données quand il détecte un déchet
    """
    data = request.json
    
    # L'utilisateur peut être identifié par un token ou un ID robot
    user_id = data.get('user_id')
    robot_id = data.get('robot_id')
    waste_type = data.get('waste_type')
    quantity = data.get('quantity', 1)
    detection_date = data.get('detection_date', datetime.now())
    
    if not waste_type or not user_id:
        return jsonify({'success': False, 'message': 'user_id et waste_type requis'}), 400
    
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('''INSERT INTO waste_detection (user_id, waste_type, quantity, detection_date)
                     VALUES (?, ?, ?, ?)''',
                  (user_id, waste_type, quantity, detection_date))
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True, 
            'message': f'{waste_type} ({quantity}) détecté et enregistré'
        }), 201
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/detection/batch', methods=['POST'])
def record_batch_detection():
    """
    Route pour enregistrer plusieurs détections à la fois
    Utile pour les données collectées offline
    """
    data = request.json
    
    user_id = data.get('user_id')
    detections = data.get('detections', [])
    
    if not user_id or not detections:
        return jsonify({'success': False, 'message': 'user_id et detections requis'}), 400
    
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        
        for detection in detections:
            waste_type = detection.get('waste_type')
            quantity = detection.get('quantity', 1)
            detection_date = detection.get('detection_date', datetime.now())
            
            if waste_type:
                c.execute('''INSERT INTO waste_detection (user_id, waste_type, quantity, detection_date)
                             VALUES (?, ?, ?, ?)''',
                          (user_id, waste_type, quantity, detection_date))
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True, 
            'message': f'{len(detections)} détection(s) enregistrée(s)'
        }), 201
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

# ==================== ROUTES YOLO ====================

@app.route('/yolo-detect')
@login_required
def yolo_detect():
    """Page de détection YOLO"""
    return render_template('yolo_detect.html', email=session.get('email'))

@app.route('/api/yolo/detect-image', methods=['POST'])
@login_required
def yolo_detect_image():
    """Détecter les déchets dans une image uploadée"""
    user_id = session.get('user_id')
    
    # Charger YOLO
    if not load_yolo():
        return jsonify({'success': False, 'message': 'Modèle YOLO non disponible'}), 500
    
    if 'file' not in request.files:
        return jsonify({'success': False, 'message': 'Aucun fichier uploadé'}), 400
    
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({'success': False, 'message': 'Fichier vide'}), 400
    
    try:
        # Sauvegarder le fichier temporairement
        temp_path = f'temp_{datetime.now().timestamp()}.jpg'
        file.save(temp_path)
        
        # Détection
        detections, results = YOLO_DETECTOR.detect_from_image(temp_path)
        
        # Nettoyer
        os.remove(temp_path)
        
        if detections:
            # Résumer les détections
            summary = {}
            for det in detections:
                waste_type = det['waste_type']
                if waste_type not in summary:
                    summary[waste_type] = 0
                summary[waste_type] += 1
            
            return jsonify({
                'success': True,
                'detections': summary,
                'total': sum(summary.values()),
                'message': f'{sum(summary.values())} déchet(s) détecté(s)'
            })
        else:
            return jsonify({
                'success': True,
                'detections': {},
                'total': 0,
                'message': 'Aucun déchet détecté'
            })
    
    except Exception as e:
        return jsonify({'success': False, 'message': f'Erreur: {str(e)}'}), 500

@app.route("/predict", methods=['POST'])
def predict():
    if 'image' not in request.files:
        return "No image found", 400
    
    file = request.files['image']
    image = cv2.imdecode(np.frombuffer(file.read(), np.uint8), cv2.IMREAD_COLOR)    
    
    results = model(image)
    names = results[0].names
    bboxes = results[0].boxes    
    
    for box in bboxes:
        x1, y1, x2, y2 = box.xyxy[0].tolist()
        label = names[int(box.cls[0])]
        confidence = box.conf[0]        
        
        cv2.rectangle(image, (int(x1), int(y1)), (int(x2), int(y2)), (0, 255, 0), 2)
        cv2.putText(image, f"{label} {confidence:.2f}", (int(x1), int(y1)-10), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)

    _, img_encoded = cv2.imencode(".jpg", image)    
    return send_file(io.BytesIO(img_encoded.tobytes()), mimetype="image/jpeg")

@app.route('/api/yolo/detect-webcam', methods=['POST'])
@login_required
def yolo_detect_webcam():
    """Détecter en temps réel depuis la webcam"""
    user_id = session.get('user_id')
    data = request.json
    duration = data.get('duration', 10)
    save_to_db = data.get('save_to_db', True)
    
    if not YOLO_DETECTOR:
        return jsonify({'success': False, 'message': 'Modèle YOLO non disponible'}), 500
    
    try:
        # Détection webcam
        detections = YOLO_DETECTOR.detect_from_webcam(user_id, duration)
        
        # Enregistrer dans la BD si demandé
        if save_to_db and detections:
            YOLO_DETECTOR.save_detections_to_db(user_id, detections)
        
        return jsonify({
            'success': True,
            'detections': detections,
            'total': sum(detections.values()) if detections else 0,
            'message': f'{sum(detections.values()) if detections else 0} déchet(s) détecté(s)'
        })
    
    except Exception as e:
        return jsonify({'success': False, 'message': f'Erreur: {str(e)}'}), 500

@app.route('/api/yolo/save-detections', methods=['POST'])
@login_required
def yolo_save_detections():
    """Enregistrer les détections YOLO dans la BD"""
    user_id = session.get('user_id')
    data = request.json
    detections = data.get('detections', {})
    
    if not detections:
        return jsonify({'success': False, 'message': 'Aucune détection à enregistrer'}), 400
    
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        
        for waste_type, quantity in detections.items():
            c.execute('''INSERT INTO waste_detection (user_id, waste_type, quantity, detection_date)
                         VALUES (?, ?, ?, ?)''',
                     (user_id, waste_type, quantity, datetime.now()))
        
        conn.commit()
        conn.close()
        
        print(f"✅ {len(detections)} détection(s) enregistrée(s) dans la BD")
        
        return jsonify({
            'success': True,
            'message': f'{len(detections)} type(s) de déchet enregistré(s)'
        })
    
    except Exception as e:
        return jsonify({'success': False, 'message': f'Erreur: {str(e)}'}), 500

# ==================== ROUTES ADMIN ====================

@app.route('/admin/users')
@login_required
@admin_required
def admin_users_page():
    """Page de gestion des utilisateurs (admin uniquement)"""
    return render_template('admin_users.html', email=session.get('email'))

@app.route('/api/admin/users', methods=['GET'])
@login_required
@admin_required
def get_all_users():
    """Récupérer la liste de tous les utilisateurs"""
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('''SELECT id, email, role, created_at, last_login 
                     FROM users ORDER BY created_at DESC''')
        users = c.fetchall()
        conn.close()
        
        users_list = []
        for user in users:
            users_list.append({
                'id': user[0],
                'email': user[1],
                'role': user[2] if user[2] else 'user',
                'created_at': user[3],
                'last_login': user[4]
            })
        
        return jsonify({'success': True, 'users': users_list})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/admin/users/<int:user_id>/role', methods=['PUT'])
@login_required
@admin_required
def update_user_role(user_id):
    """Modifier le rôle d'un utilisateur"""
    data = request.json
    new_role = data.get('role')
    
    if new_role not in ['admin', 'user']:
        return jsonify({'success': False, 'message': 'Rôle invalide'}), 400
    
    # Empêcher l'admin de se rétrograder lui-même
    if user_id == session.get('user_id') and new_role == 'user':
        return jsonify({'success': False, 'message': 'Vous ne pouvez pas vous rétrograder vous-même'}), 400
    
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('UPDATE users SET role = ? WHERE id = ?', (new_role, user_id))
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'message': f'Rôle mis à jour en {new_role}'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/admin/users/<int:user_id>', methods=['DELETE'])
@login_required
@admin_required
def delete_user(user_id):
    """Supprimer un utilisateur"""
    # Empêcher l'admin de se supprimer lui-même
    if user_id == session.get('user_id'):
        return jsonify({'success': False, 'message': 'Vous ne pouvez pas vous supprimer vous-même'}), 400
    
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        
        # Supprimer les détections de l'utilisateur
        c.execute('DELETE FROM waste_detection WHERE user_id = ?', (user_id,))
        
        # Supprimer le robot de l'utilisateur
        c.execute('DELETE FROM robots WHERE user_id = ?', (user_id,))
        
        # Supprimer l'utilisateur
        c.execute('DELETE FROM users WHERE id = ?', (user_id,))
        
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'message': 'Utilisateur supprimé'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)
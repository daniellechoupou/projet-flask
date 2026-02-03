"""
Script pour promouvoir un utilisateur en admin
"""
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), 'waste.db')

def list_users():
    """Afficher tous les utilisateurs"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT id, email, role FROM users')
    users = c.fetchall()
    conn.close()
    
    print("\n=== Liste des utilisateurs ===")
    if not users:
        print("Aucun utilisateur trouvé.")
        return []
    
    for user in users:
        role_display = "👑 ADMIN" if user[2] == 'admin' else "👤 user"
        print(f"  ID: {user[0]} | Email: {user[1]} | Rôle: {role_display}")
    
    return users

def make_admin(email):
    """Promouvoir un utilisateur en admin"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Vérifier si l'utilisateur existe
    c.execute('SELECT id, role FROM users WHERE email = ?', (email,))
    user = c.fetchone()
    
    if not user:
        print(f"❌ Aucun utilisateur trouvé avec l'email: {email}")
        conn.close()
        return False
    
    if user[1] == 'admin':
        print(f"ℹ️ L'utilisateur {email} est déjà admin.")
        conn.close()
        return True
    
    # Mettre à jour le rôle
    c.execute('UPDATE users SET role = ? WHERE email = ?', ('admin', email))
    conn.commit()
    conn.close()
    
    print(f"✅ L'utilisateur {email} est maintenant ADMIN !")
    return True

if __name__ == '__main__':
    print("=" * 50)
    print("  OUTIL DE GESTION ADMIN - WasteAI")
    print("=" * 50)
    
    users = list_users()
    
    if users:
        print("\n")
        email = input("Entrez l'email de l'utilisateur à promouvoir en admin: ").strip()
        
        if email:
            make_admin(email)
        else:
            print("❌ Email vide, opération annulée.")
    
    print("\n")
    input("Appuyez sur Entrée pour fermer...")

"""
Test de détection avec une image
"""

# Met une image de test dans ton dossier
# Exemple : test.jpg

try:
    from ultralytics import YOLO
    import os
    
    # Cherche une image
    image_path = None
    for file in os.listdir('.'):
        if file.endswith(('.jpg', '.png', '.jpeg')):
            image_path = test.jpg
            break
    
    if not image_path:
        print("⚠️  Mets une image (jpg/png) dans le dossier pour tester")
    else:
        print(f"🔍 Test avec image : {image_path}")
        
        try:
            model = YOLO('yolov8n.pt')
            print("✅ Modèle chargé")
            
            results = model(image_path, conf=0.5)
            print(f"✅ Détection effectuée")
            print(f"✅ {len(results[0].boxes)} objet(s) détecté(s)")
            
        except Exception as e:
            print(f"❌ Erreur PyTorch : {e}")
            print("   (C'est normal, utilise le test_model_simple.py à la place)")

except ImportError:
    print("YOLO non disponible, utilise test_model_simple.py")
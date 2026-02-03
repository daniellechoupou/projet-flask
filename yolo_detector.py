import cv2
import numpy as np
from datetime import datetime
import sqlite3
import os

# Fix pour certaines erreurs de DLL sur Windows
os.environ['KMP_DUPLICATE_LIB_OK'] = 'True'

try:
    from ultralytics import YOLO
    TORCH_AVAILABLE = True
except Exception as e:
    print(f"⚠️ Ultralytics non disponible: {e}")
    TORCH_AVAILABLE = False

# ==================== CONFIGURATION ====================

MODEL_PATH = 'my_model.pt'

WASTE_CLASSES = {
    0: 'Papier',
    1: 'Plastique',
    2: 'Métal',
    3: 'Verre',
    4: 'Carton'
}

CONFIDENCE_THRESHOLD = 0.5
DB_PATH = 'waste.db'

# ==================== CLASSE DÉTECTEUR YOLO ====================

class WasteDetector:
    def __init__(self, model_path=MODEL_PATH):
        """Initialiser le modèle YOLO"""
        if not TORCH_AVAILABLE:
            print("❌ YOLO/PyTorch non disponible")
            self.model = None
            return
        
        try:
            self.model = YOLO(model_path)
            print(f"✅ Modèle YOLO chargé: {model_path}")
        except Exception as e:
            print(f"❌ Erreur chargement modèle: {e}")
            self.model = None
    
    def detect_from_image(self, image_path):
        """Détecter les déchets dans une image"""
        if not self.model:
            return None, "Modèle non disponible"
        
        try:
            img = cv2.imread(image_path)
            
            if img is None:
                return None, "Erreur: Impossible de charger l'image"
            
            # Inférence YOLO
            results = self.model(img, conf=CONFIDENCE_THRESHOLD, verbose=False)
            
            detections = []
            
            # Traiter les résultats
            for r in results:
                boxes = r.boxes
                if boxes is not None:
                    for box in boxes:
                        try:
                            cls = int(box.cls[0])
                            conf = float(box.conf[0])
                            
                            waste_type = WASTE_CLASSES.get(cls, f'Déchet_{cls}')
                            
                            detections.append({
                                'waste_type': waste_type,
                                'confidence': conf,
                                'box': box.xyxy[0].cpu().numpy() if hasattr(box.xyxy[0], 'cpu') else box.xyxy[0]
                            })
                        except Exception as e:
                            print(f"⚠️ Erreur traitement detection: {e}")
                            continue
            
            return detections, results
        
        except Exception as e:
            print(f"❌ Erreur détection: {e}")
            return None, str(e)
    
    def detect_from_frame(self, frame):
        """Détecter les déchets dans une frame OpenCV"""
        if not self.model:
            return frame, {}
        
        try:
            # Inférence YOLO
            results = self.model(frame, conf=CONFIDENCE_THRESHOLD, verbose=False)
            
            detections_summary = {}
            
            # Traiter les résultats
            for r in results:
                boxes = r.boxes
                if boxes is not None:
                    for box in boxes:
                        try:
                            cls = int(box.cls[0])
                            conf = float(box.conf[0])
                            
                            waste_type = WASTE_CLASSES.get(cls, f'Déchet_{cls}')
                            
                            if waste_type not in detections_summary:
                                detections_summary[waste_type] = 0
                            detections_summary[waste_type] += 1
                            
                            # Afficher les détections sur l'image
                            try:
                                x1, y1, x2, y2 = map(int, box.xyxy[0][:4])
                                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                                label = f"{waste_type} {conf:.2f}"
                                cv2.putText(frame, label, (x1, y1 - 10), 
                                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
                            except:
                                pass
                        except Exception as e:
                            continue
            
            # Afficher le nombre de détections
            try:
                cv2.putText(frame, f"Detections: {sum(detections_summary.values())}", 
                           (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
            except:
                pass
            
            return frame, detections_summary
        
        except Exception as e:
            print(f"❌ Erreur détection frame: {e}")
            return frame, {}

    def detect_from_webcam(self, user_id, duration=10):
        """Détecter en temps réel depuis la webcam (Legacy - à supprimer si non utilisé)"""
        # ... (On garde pour l'instant au cas où)
        pass
    
    def save_detections_to_db(self, user_id, detections_dict):
        """Enregistrer les détections dans la BD"""
        try:
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            
            for waste_type, quantity in detections_dict.items():
                c.execute('''INSERT INTO waste_detection 
                            (user_id, waste_type, quantity, detection_date)
                            VALUES (?, ?, ?, ?)''',
                         (user_id, waste_type, quantity, datetime.now()))
            
            conn.commit()
            conn.close()
            
            print(f"✅ {len(detections_dict)} type(s) de déchet enregistré(s)")
            return True
        except Exception as e:
            print(f"❌ Erreur BD: {str(e)}")
            return False

# ==================== TEST ====================

if __name__ == "__main__":
    if TORCH_AVAILABLE:
        detector = WasteDetector()
        print("✅ Détecteur YOLO initialisé")
    else:
        print("❌ Impossible d'initialiser YOLO")
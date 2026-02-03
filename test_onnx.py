import onnxruntime as ort
import cv2
import numpy as np
import matplotlib.pyplot as plt

session = ort.InferenceSession("yolov8m.onnx", providers=["CPUExecutionProvider"])
input_name = session.get_inputs()[0].name

img = cv2.imread("test.jpg")
img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

img_resized = cv2.resize(img_rgb, (640, 640))
img_norm = img_resized / 255.0
img_tensor = np.transpose(img_norm, (2, 0, 1))[None].astype(np.float32)

outputs = session.run(None, {input_name: img_tensor})
preds = outputs[0][0].T

scores = preds[:, 4:].max(axis=1)
classes = preds[:, 4:].argmax(axis=1)
boxes = preds[:, :4]

mask = scores > 0.4
boxes, scores, classes = boxes[mask], scores[mask], classes[mask]

h, w, _ = img.shape
for box, score, cls in zip(boxes, scores, classes):
    cx, cy, bw, bh = box
    x1 = int((cx - bw/2) * w / 640)
    y1 = int((cy - bh/2) * h / 640)
    x2 = int((cx + bw/2) * w / 640)
    y2 = int((cy + bh/2) * h / 640)

    cv2.rectangle(img_rgb, (x1, y1), (x2, y2), (0,255,0), 2)
    cv2.putText(img_rgb, f"{cls}:{score:.2f}", (x1, y1-10),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255,0,0), 2)

plt.imshow(img_rgb)
plt.axis("off")

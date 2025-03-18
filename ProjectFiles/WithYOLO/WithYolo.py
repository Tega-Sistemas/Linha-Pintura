import cv2
import numpy as np
from ultralytics import YOLO
from sort import Sort  # Algoritmo de rastreamento SORT

# Caminho do vídeo
video_path = "C:/Users/NTB_ACER_DEV/Desktop/Testar/midia/Vid1.mp4"

# Carregar o modelo YOLO treinado
model = YOLO("C:/Users/NTB_ACER_DEV/Desktop/Testar/ultralytics/runs/detect/train2/weights/best.pt")

# Abrir o vídeo
cap = cv2.VideoCapture(video_path)

if not cap.isOpened():
    print("Erro ao abrir o vídeo.")
    exit()

# Definir codec e criar VideoWriter para salvar o vídeo processado
fourcc = cv2.VideoWriter_fourcc(*'XVID')  
out = cv2.VideoWriter('output.avi', fourcc, 30.0, (int(cap.get(3)), int(cap.get(4))))  

# Inicializar o rastreador SORT (para não repetir chapas já contadas)
tracker = Sort()

# Definir a linha de contagem
line_y = int(cap.get(4) * 0.5)  # Linha no meio do vídeo
count = 0
crossed_ids = set()

while True:
    ret, frame = cap.read()
    if not ret:
        break
    
    # Executar a detecção com YOLO
    results = model(frame)

    # Lista de detecções formatadas para o SORT
    detections = []
    for result in results:
        for box in result.boxes:
            confidence = box.conf[0].item()
            if confidence < 0.5:  # Limiar de confiança
                continue
            
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            area = (x2 - x1) * (y2 - y1)

            if area < 1000:  # Ignorar objetos muito pequenos
                continue
            
            detections.append([x1, y1, x2, y2, confidence])

    # Converter a lista para um numpy array esperado pelo SORT
    detections = np.array(detections)

    # Atualizar o rastreamento com SORT
    tracked_objects = tracker.update(detections)

    for obj in tracked_objects:
        x1, y1, x2, y2, obj_id = obj.astype(int)
        center_x = (x1 + x2) // 2
        center_y = (y1 + y2) // 2  # Centro do objeto

        # Desenhar bounding box e ID do objeto
        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
        cv2.putText(frame, f'ID {obj_id}', (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 2)

        # Verificar se o objeto cruzou a linha de contagem pela primeira vez
        if obj_id not in crossed_ids and y1 < line_y < y2:
            count += 1
            crossed_ids.add(obj_id)

    # Desenhar linha de contagem e exibir a contagem na tela
    cv2.line(frame, (0, line_y), (frame.shape[1], line_y), (255, 0, 255), 2)
    cv2.putText(frame, f'COUNT: {count}', (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)

    # Exibir frame com detecções
    cv2.imshow("Contagem de Chapas", frame)

    # Salvar o vídeo processado
    out.write(frame)

    # Pressione 'q' para sair
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# Liberar recursos
cap.release()
out.release()
cv2.destroyAllWindows()

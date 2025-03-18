import cv2
import numpy as np

# Caminho do vídeo
video_path = "C:/Users/NTB_ACER_DEV/Desktop/Testar/midia/Vid1.mp4"

# Abrir o vídeo
cap = cv2.VideoCapture(video_path)

# Verificar se o vídeo foi carregado corretamente
if not cap.isOpened():
    print("Erro ao abrir o vídeo.")
    exit()

# Configurações do vídeo de saída
fps = int(cap.get(cv2.CAP_PROP_FPS))
frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
output_path = "chapas_detectadas.mp4"
fourcc = cv2.VideoWriter_fourcc(*"mp4v")
out = cv2.VideoWriter(output_path, fourcc, fps, (frame_width, frame_height))

# Definir intervalo de cor das chapas no espaço HSV (ajuste conforme necessário)
lower_hsv = np.array([5, 30, 100])  # Tons amarelados/madeira
upper_hsv = np.array([25, 255, 255])

# Processar apenas os primeiros N segundos
max_frames = fps * 30  # altere 30 por algum número (ex: 45 para pegar de 0 até 45s)
frame_count = 0

while cap.isOpened() and frame_count < max_frames:
    ret, frame = cap.read()
    if not ret:
        break

    frame_count += 1

    # Converter para HSV (BGP para HSV) e aplicar máscara de cor 
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(hsv, lower_hsv, upper_hsv)

    # Aplicar filtro de mediana para remover ruído na máscara
    mask = cv2.medianBlur(mask, 5)

    # Detecção de bordas com Laplaciano
    laplacian = cv2.Laplacian(mask, cv2.CV_64F)
    laplacian = np.uint8(np.absolute(laplacian))  # Converter para valores inteiros não negativos

    # Aplicar um thresholding para filtrar as bordas fortes
    _, edges_threshold = cv2.threshold(laplacian, 100, 255, cv2.THRESH_BINARY)

    # Combinação com a máscara de cor usando bitwise OR
    combined_mask = cv2.bitwise_or(mask, edges_threshold)

    # Encontrar contornos
    contours, _ = cv2.findContours(combined_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    # Filtrar contornos por tamanho (removendo pequenos ruídos)
    min_area = 10000  # Ajuste conforme necessário
    contours = [cnt for cnt in contours if cv2.contourArea(cnt) > min_area]

    # Desenhar os contornos detectados
    cv2.drawContours(frame, contours, -1, (0, 255, 0), 2)

    # Exibindo a imagem com os contornos desenhados
    cv2.imshow("Detecção de Chapas", frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

    # Escrever no vídeo de saída
    out.write(frame)

# Liberar recursos
cap.release()
out.release()
cv2.destroyAllWindows()

print(f"Processamento concluído! O vídeo foi salvo como: {output_path}")

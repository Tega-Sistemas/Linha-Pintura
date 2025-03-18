import cv2
import os

def extract_frames(video_path, output_folder, frame_interval=1):
    # Criar pasta de saída se não existir
    os.makedirs(output_folder, exist_ok=True)
    
    # Abrir o vídeo
    cap = cv2.VideoCapture(video_path)
    frame_count = 0
    saved_count = 0
    
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
        
        # Salvar frame a cada 'frame_interval'
        if frame_count % frame_interval == 0:
            frame_filename = os.path.join(output_folder, f"frame_{saved_count:05d}.jpg")
            cv2.imwrite(frame_filename, frame)
            saved_count += 1
        
        frame_count += 1
    
    cap.release()
    print(f"Extração concluída! {saved_count} frames salvos em '{output_folder}'")

# Exemplo de uso
video_path = "C:/Users/NTB_ACER_DEV/Desktop/Testar/midia/Vid2.mp4"  # Substituir pelo caminho do vídeo
output_folder = "frames"  # Pasta de saída
tempo_entre_frames = 5  # Extrai um frame a cada 5 frames
extract_frames(video_path, output_folder, tempo_entre_frames)

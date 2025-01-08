import cv2
import numpy as np
import pandas as pd

# Passo 1: Ler o arquivo CSV com separador ';'
csv_file = './Teste_calculo_OpenCV/Padrao2/Leitura_2024.12.02_padrao.csv'
data = pd.read_csv(csv_file, sep=';', header=0)  # Pula o cabeçalho e usa as primeiras 43 colunas

# Passo 2: Selecionar apenas as primeiras 43 colunas (0 a 42)
data = data.iloc[:, :43]  # Pega apenas as 43 primeiras colunas

# Passo 3: Converter os dados para uma matriz NumPy
# Convertendo para uma matriz binária (0 = preto, 255 = branco)
image_data = data.to_numpy()

# Passo 4: Criar a imagem binária (0 = preto, 255 = branco)
binary_image = np.where(image_data == 1, 255, 0).astype(np.uint8)

# Passo 5: Usar o OpenCV para detectar os contornos
# Para encontrar objetos, usaremos a função findContours
contours, hierarchy = cv2.findContours(binary_image, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

# Passo 6: Contar o número de objetos
object_count = len(contours)

# Passo 7: Exibir o número de objetos encontrados
print(f"Quantidade de objetos encontrados: {object_count}")

# Passo 8: Desenhar os contornos na imagem original (opcional)
contour_image = cv2.cvtColor(binary_image, cv2.COLOR_GRAY2BGR)  # Convertendo para imagem colorida para desenhar contornos
cv2.drawContours(contour_image, contours, -1, (0, 255, 0), 2)  # Contornos em verde

# Passo 9: Exibir a imagem com os contornos
cv2.imshow('Contornos de objetos', contour_image)
cv2.waitKey(0)
cv2.destroyAllWindows()

# Se você quiser salvar a imagem com os contornos:
cv2.imwrite('contornos_de_objetos.png', contour_image)

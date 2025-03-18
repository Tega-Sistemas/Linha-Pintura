import numpy as np
import pandas as pd
from scipy.ndimage import label

# Carregar o CSV
df = pd.read_csv('Leitura_2_100x266.csv', delimiter=';', header=None)

# Converter para uma matriz numpy (assumindo que os dados começam a partir da primeira coluna)
data = df.iloc[:, :-4].values  # Ignora as últimas colunas (Largura, Percentual Bloqueado, Timestamp, Queimados)

# Encontrar blocos de 1s
# A função label irá identificar regiões conectadas de 1s
# Conectividade 2 significa que os vizinhos podem ser conectados diagonalmente, verticalmente ou horizontalmente
labeled_array, num_features = label(data, structure=[[1, 1, 1], [1, 1, 1], [1, 1, 1]])

# A variável num_features irá conter o número de blocos de 1s
print(f'Número de blocos de 1s encontrados: {num_features}')

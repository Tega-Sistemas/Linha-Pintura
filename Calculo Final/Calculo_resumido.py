#arquivo_csv = "./Padrao2/Leitura_2024.12.04_padrao.csv"
import pandas as pd
import numpy as np

velocidade_esteira = 0.2833  # m/s (17 m/min convertido para m/s)
tempo_por_linha = 0.1  # segundos (100 ms entre as leituras)
largura_por_unidade = 2.5 / 100  # 2,5 cm convertido para metros

arquivo_csv = "./Padrao2/Leitura1_100x266_560_padrao.csv"
dados = pd.read_csv(arquivo_csv, delimiter=";")

sensor_data = dados.iloc[:, :44].to_numpy()
print(sensor_data)

# Calcular quanto cada linha colabora para o comprimento a cada 100 ms, cada leitura
comprimento_por_linha = velocidade_esteira * tempo_por_linha  # em metros

areas = []
for linha in sensor_data:
    # Calcular a largura da peça (quantidade de 1's multiplicada por 2,5 cm)
    largura = np.sum(linha) * largura_por_unidade  # em metros
    
    # A área é a largura multiplicada pelo comprimento percorrido
    area = largura * comprimento_por_linha
    areas.append(area)

areas = np.array(areas)

soma_das_areas = np.sum(areas)
print("Soma das áreas:", soma_das_areas)
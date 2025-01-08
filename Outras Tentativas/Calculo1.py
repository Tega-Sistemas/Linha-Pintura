import pandas as pd
import numpy as np

VELOCIDADE = 17 # m/min
ESPACAMENTO_CENTROS = 0.025 # 2.5 cm em metros (distância entre o centro de cada sensor)
LARGURA_SENSOR = 0.00924

def calculo(file_path):
    df = pd.read_csv(file_path, delimiter=';')

    # Convertendo a coluna Timestamp para datetime
    df['Time_Stamp'] = pd.to_datetime(df['Timestamp'], format='%Y.%m.%d_%H.%M.%S')

    hora_inicial = df['Time_Stamp'].min()
    hora_final = df['Time_Stamp'].max()

    diferenca_tempo = (hora_final - hora_inicial).total_seconds() / 60.0
    print(diferenca_tempo)
    distancia_percorrida = diferenca_tempo * VELOCIDADE

    # Contagem de linhas (descontando header)
    total_linhas = df.shape[0]

    # Distância percorrida por registro
    distancia_por_registro = distancia_percorrida / total_linhas if total_linhas > 0 else 0

    # Sensores: Colunas de resultado dos sensores são da coluna 1 até a 44 (assumindo que
    # essas colunas se chamam por exemplo "S1", "S2", ..., ou que sejam numeradas)
    # Se no CSV não há header padronizado, ajustar aqui conforme necessário.
    # Assumiremos que após a coluna 'Timestamp', as colunas de sensores sejam as restantes.
    # Caso contrário, ajustar a seleção de colunas de acordo com o cabeçalho real do CSV.
    sensor_cols = df.columns.drop(['Timestamp', 'Time_Stamp'])

    # Garantir que temos exatamente 44 colunas de sensores
    # Se o arquivo tiver exatamente as 44 colunas adicionais para os sensores
    # if len(sensor_cols) >= 44:
    #     raise ValueError("O arquivo não possui 44 colunas de sensores conforme especificado.")

    # Cada sensor i tem seu centro em i * ESPACAMENTO_CENTROS (em metros)
    # A largura de cada sensor é LARGURA_SENSOR, então sua área coberta
    # no eixo perpendicular é um intervalo [centro - largura/2, centro + largura/2].

    # Vetorizar a detecção de sensores ligados
    sensor_values = df[sensor_cols].values  # Obter todos os valores dos sensores

    # Detectar sensores ligados (1) para cada linha
    sensores_ligados = np.where(sensor_values == 1)  # Índices de sensores ligados

    # Calcular os centros dos sensores ligados
    centros_sensores = sensores_ligados[1] * ESPACAMENTO_CENTROS  # Indices dos sensores * espaço entre eles

    # Calcular intervalos de cobertura para cada sensor
    intervalos = np.column_stack([centros_sensores - LARGURA_SENSOR / 2, centros_sensores + LARGURA_SENSOR / 2])

    # Calcular a largura total coberta por linha
    # Para isso, devemos unir os intervalos de cada linha e somar a largura coberta.
    largura_total_por_linha = []

    for linha in intervalos:
        # Unir intervalos de sensores ligados
        linha_sorted = sorted(linha, key=lambda x: x[0])
        merged_intervals = []
        current_start, current_end = linha_sorted[0]

        for start, end in linha_sorted[1:]:
            if start <= current_end:
                # Intervalos sobrepostos ou contíguos
                current_end = max(current_end, end)
            else:
                # Não sobrepostos, empurra o intervalo atual e começa um novo
                merged_intervals.append((current_start, current_end))
                current_start, current_end = start, end
        merged_intervals.append((current_start, current_end))  # Adicionar o último intervalo

        # Somar a largura de todos os intervalos unidos
        largura_total = sum(end - start for start, end in merged_intervals)
        largura_total_por_linha.append(largura_total)

    # Converter a lista de larguras em um array numpy
    largura_total_por_linha = np.array(largura_total_por_linha)

    # Calcular a área total coberta
    area_total = np.sum(largura_total_por_linha * distancia_por_registro)

    print("Hora inicial:", hora_inicial)
    print("Hora final:  ", hora_final)
    print(f"Diferença de tempo: {diferenca_tempo:.2f} minutos")
    print(f"Distância percorrida: {distancia_percorrida:.2f} metros")
    print(f"Total de linhas: {total_linhas}")
    print(f"Distância percorrida por registro: {distancia_por_registro:.4f} metros/regidstro")
    print(f"Área total coberta: {area_total:.4f} m²")

# Caminho para o arquivo CSV
caminho_csv = "./Padrao2/Leitura3_160x683_2250_padrao.csv"

calculo(caminho_csv)

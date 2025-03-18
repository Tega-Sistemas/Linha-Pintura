import pandas as pd

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

    # Índice dos sensores: 0 a 43
    # Cada sensor i tem seu centro em i * ESPACAMENTO_CENTROS (em metros)
    # A largura de cada sensor é LARGURA_SENSOR, então sua área coberta
    # no eixo perpendicular é um intervalo [centro - largura/2, centro + largura/2].

    # Cálculo da área total
    # Para cada linha (registro):
    # 1. Identificar quais sensores estão acionados (valor == 1)
    # 2. Unir os intervalos desses sensores e somar a largura total coberta
    # 3. Multiplicar pela distancia_por_registro para obter a área correspondente àquele registro
    # 4. Somar todas as áreas para obter a área total.

    area_total = 0.0

    for _, row in df.iterrows():
        # Obter os valores dos sensores na linha
        sensor_values = row[sensor_cols].values
        
        # Determinar quais sensores estão ligados (1)
        sensores_ligados = [i for i, val in enumerate(sensor_values) if val == 1]

        if not sensores_ligados:
            # Nenhum sensor ligado, área coberta nessa linha é zero
            continue

        # Calcular intervalos dos sensores ligados
        # Cada sensor i: intervalo [i*ESPACAMENTO_CENTROS - LARGURA_SENSOR/2, i*ESPACAMENTO_CENTROS + LARGURA_SENSOR/2]
        intervals = []
        for i_sensor in sensores_ligados:
            center = i_sensor * ESPACAMENTO_CENTROS
            interval = (center - LARGURA_SENSOR/2, center + LARGURA_SENSOR/2)
            intervals.append(interval)

        # Unir intervalos para calcular a cobertura contínua total
        # Ordenar intervalos pelo início
        intervals.sort(key=lambda x: x[0])

        # Função para unir intervalos
        merged_intervals = []
        current_start, current_end = intervals[0]

        for start, end in intervals[1:]:
            if start <= current_end:
                # Intervalos sobrepostos ou contíguos
                current_end = max(current_end, end)
            else:
                # Não sobrepostos, empurra o intervalo atual e começa um novo
                merged_intervals.append((current_start, current_end))
                current_start, current_end = start, end
        # Adicionar o último intervalo após iteração
        merged_intervals.append((current_start, current_end))

        # Somar o comprimento de todos os intervalos unidos
        largura_total = sum(end - start for start, end in merged_intervals)

        # Área para este registro é largura_total * distancia_por_registro
        area_por_registro = largura_total * distancia_por_registro
        area_total += area_por_registro

    print("Hora inicial:", hora_inicial)
    print("Hora final:  ", hora_final)
    print(f"Diferença de tempo: {diferenca_tempo:.2f} minutos")
    print(f"Distância percorrida: {distancia_percorrida:.2f} metros")
    print(f"Total de linhas: {total_linhas}")
    print(f"Distância percorrida por registro: {distancia_por_registro:.4f} metros/registro")
    print(f"Área total coberta: {area_total:.4f} m²")

# Caminho para o arquivo CSV
caminho_csv = "./Arquivos/Leitura_2024.11.27_padrao.csv"

calculo(caminho_csv)

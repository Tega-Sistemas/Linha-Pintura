import pandas as pd

VELOCIDADE = 17  # m/min
ESPACAMENTO_CENTROS = 0.025  # 2.5 cm em metros (distância entre o centro de cada sensor)
LARGURA_SENSOR = 0.00924

def calculo(file_path):
    df = pd.read_csv(file_path, delimiter=';')

    # Convertendo a coluna Timestamp para datetime
    df['Time_Stamp'] = pd.to_datetime(df['Timestamp'], format='%Y.%m.%d_%H.%M.%S')

    sensor_cols = df.columns.drop(['Largura', 'Percentual Bloqueado','Queimados','Timestamp', 'Time_Stamp'])

    # Identificar intervalos de leituras (linhas que não são 100% zero)
    intervals = []
    in_interval = False
    start_time = None

    print(sensor_cols)

    for index, row in df.iterrows():
        if row[sensor_cols].sum() > 0:  # Linha com ao menos um sensor ativo
            if not in_interval:
                # Iniciar um novo intervalo
                in_interval = True
                start_time = row['Time_Stamp']
        else:
            if in_interval:
                # Finalizar o intervalo atual
                end_time = row['Time_Stamp']
                intervals.append((start_time, end_time))
                in_interval = False

    # Fechar o último intervalo, se necessário
    if in_interval:
        intervals.append((start_time, df.iloc[-1]['Time_Stamp']))

    # Calcular minutos totais e área
    total_minutes = 0
    total_area = 0

    for start_time, end_time in intervals:
        interval_minutes = (end_time - start_time).total_seconds() / 60.0
        total_minutes += interval_minutes

        # Filtrar apenas as linhas do intervalo atual
        interval_data = df[(df['Time_Stamp'] >= start_time) & (df['Time_Stamp'] <= end_time)]
        total_linhas_intervalo = interval_data.shape[0]
        distancia_por_registro = (interval_minutes * VELOCIDADE) / total_linhas_intervalo if total_linhas_intervalo > 0 else 0

        # Calcular área para este intervalo
        for _, row in interval_data.iterrows():
            sensores_ligados = [i for i, val in enumerate(row[sensor_cols].values) if val == 1]
            if not sensores_ligados:
                continue

            # Calcular intervalos dos sensores ligados
            intervals = []
            for i_sensor in sensores_ligados:
                center = i_sensor * ESPACAMENTO_CENTROS
                interval = (center - LARGURA_SENSOR / 2, center + LARGURA_SENSOR / 2)
                intervals.append(interval)

            # Unir intervalos para calcular a cobertura contínua total
            intervals.sort(key=lambda x: x[0])
            merged_intervals = []
            current_start, current_end = intervals[0]
            for start, end in intervals[1:]:
                if start <= current_end:
                    current_end = max(current_end, end)
                else:
                    merged_intervals.append((current_start, current_end))
                    current_start, current_end = start, end
            merged_intervals.append((current_start, current_end))

            largura_total = sum(end - start for start, end in merged_intervals)
            area_por_registro = largura_total * distancia_por_registro
            total_area += area_por_registro

    print(f"Minutos totais com leituras: {total_minutes:.2f}")
    print(f"Área total coberta: {total_area:.4f} m²")  
    print("Hora inicial:", caminho_csv)


# Caminho para o arquivo CSV
caminho_csv = "./Padrao2/Leitura3_160x683_2250_padrao2.csv"

calculo(caminho_csv)

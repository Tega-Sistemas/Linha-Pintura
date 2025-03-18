import pandas as pd

# Carregar o CSV
df = pd.read_csv('Leitura_2_100x266.csv', delimiter=';')

# Certifique-se de que a coluna de Timestamp esteja no formato datetime
df['Timestamp'] = pd.to_datetime(df['Timestamp'], format='%Y.%m.%d_%H.%M.%S')

# Definir a velocidade da esteira (em cm/s), garantindo que seja um valor escalar
velocidade_esteira = 28.33  # (valor único, não uma lista ou tupla)

# Agrupar por Timestamp e encontrar a maior largura para cada segundo
df['Largura'] = df.iloc[:, :-3].max(axis=1)  # Considerando que a largura está entre as colunas 0 e 39

# Agrupar os dados por timestamp para encontrar a maior largura por segundo
df_max_largura = df.groupby(df['Timestamp']).agg({'Largura': 'max'}).reset_index()

# Salvar o resultado em um arquivo CSV
df_max_largura[['Timestamp', 'Largura']].to_csv('resultado_area.csv', index=False)

# Exibir o resultado total em metros quadrados
print("Arquivo 'resultado_area.csv' gerado com sucesso!")
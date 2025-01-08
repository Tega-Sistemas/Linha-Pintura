import pandas as pd

# Carregar o CSV
df = pd.read_csv('Leitura_2_100x266.csv', delimiter=';')

# Certifique-se de que a coluna de Timestamp esteja no formato datetime
df['Timestamp'] = pd.to_datetime(df['Timestamp'], format='%Y.%m.%d_%H.%M.%S')

# Definir a velocidade da esteira (em metros por segundo)
velocidade_esteira = 0.2833  # (em metros por segundo)

# Selecionar a coluna 'Largura' que está na posição 45
df['Largura'] = df.iloc[:, 45]

# Agrupar os dados por timestamp e calcular a média da largura para cada segundo
df_media_largura = df.groupby(df['Timestamp']).agg({'Largura': 'mean'}).reset_index()

# Converter a largura de cm para metros
df_media_largura['Largura_m'] = df_media_largura['Largura'] / 100  # Dividindo por 100 para converter de cm para metros

# Calcular a área em metros quadrados para cada segundo
df_media_largura['Area_m2'] = df_media_largura['Largura_m'] * velocidade_esteira

# Salvar o resultado em um arquivo CSV
df_media_largura[['Timestamp', 'Area_m2']].to_csv('resultado_area_m2.csv', index=False)

# Calcular a área total em metros quadrados
area_total = df_media_largura['Area_m2'].sum()

# Exibir o resultado total em metros quadrados
print(f"Área total que passa pela esteira: {area_total:.2f} metros quadrados.")
print("Arquivo 'resultado_area_m2.csv' gerado com sucesso!")

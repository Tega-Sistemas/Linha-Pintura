import pandas as pd

# Carregar o CSV em um DataFrame
df = pd.read_csv('Leitura_2_100x266.csv', sep=';')

# Calcular a largura média
media_largura = df['Largura'].mean()

# Defina a velocidade da esteira (em metros por segundo)
velocidade_esteira = 0.1135  # Substitua pelo valor correto

# Calcular o intervalo de tempo entre as leituras (em segundos)
df['Timestamp'] = pd.to_datetime(df['Timestamp'], format='%Y.%m.%d_%H.%M.%S')
df['Delta_t'] = df['Timestamp'].diff().dt.total_seconds().fillna(0)

# Verificar se há entradas com Delta_t zero
if any(df['Delta_t'] == 0):
    print("Aviso: Existem leituras com o mesmo timestamp. Isso pode afetar o cálculo.")

# Calcular a área parcial para cada leitura
df['Area_parcial'] = df['Largura'] * velocidade_esteira * df['Delta_t']

# Calcular a área total
area_total = df['Area_parcial'].sum()

print(f"A área total é {area_total} metros quadrados.")

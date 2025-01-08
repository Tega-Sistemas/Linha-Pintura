# streamlit run dashboard.py


import os
import streamlit as st
import pandas as pd
import ast
from dotenv import load_dotenv
import paramiko
from io import StringIO
import plotly.graph_objects as go
import matplotlib.pyplot as plt
import numpy as np

load_dotenv()
st.set_page_config(layout="wide")

# ---------------- SOMBRA ----------------
def gerar_sombra_plotly(df, start_time=None, end_time=None):
    df['Queimados'] = df['Queimados'].apply(lambda x: ast.literal_eval(x) if pd.notna(x) else [])
    sensores_queimados = set()
    for queimados in df['Queimados']:
        sensores_queimados.update(queimados)

    colunas_interesse = [str(i) for i in range(44)]
    df = df[colunas_interesse + ['Timestamp']].copy()

    df['Datetime'] = pd.to_datetime(df['Timestamp'], format="%Y.%m.%d_%H.%M.%S", errors='coerce')

    if start_time and end_time:
        df = df[(df['Datetime'] >= start_time) & (df['Datetime'] <= end_time)]

    x, y, cores = [], [], []

    # Função para adicionar dados em blocos
    def add_chunk(start_index, end_index):
        nonlocal x, y, cores
        chunk = df.iloc[start_index:end_index]
        for i, row in chunk.iterrows():
            for j in df.columns:
                if j != 'Datetime' and j != 'Timestamp':
                    valor = row[j]
                    pos_x = int(j) + 1
                    pos_y = row['Datetime']
                    x.append(pos_x)
                    y.append(pos_y)
                    cores.append('blue' if valor == 1 else 'lightgrey')

    chunk_size = 100  # Tamanho do bloco (chunk)
    num_chunks = len(df) // chunk_size + 1

    # Listas para armazenar dados do gráfico
    fig = go.Figure()

    # Gerar os gráficos por blocos (chunks)
    for i in range(num_chunks):
        start_index = i * chunk_size
        end_index = min((i + 1) * chunk_size, len(df))
        add_chunk(start_index, end_index)

        # Adicionar os dados ao gráfico
        fig.add_trace(go.Scatter(
            x=x,
            y=y,
            mode='markers',
            marker=dict(color=cores, size=5, opacity=0.7),
            name=f"Bloco {i + 1}"
        ))

    # Ajustando o gráfico
    fig.update_layout(
        title="Gráfico de Sombra",
        xaxis_title="Sensores",
        yaxis_title="Datetime",
        yaxis=dict(autorange="reversed"),
        template="plotly_dark",
        height=700
    )

    # Exibir gráfico
    st.plotly_chart(fig)

    return sensores_queimados

# ---------------- QUANT. PEÇA ----------------

def buscar_pecas(sensor_matrix):
    """
    Função para contar o número de peças (blocos de 1's conectados) em uma matriz de sensores.
    
    :param sensor_matrix: Matriz de sensores (0s e 1s)
    :return: número de peças (blocos de 1's conectados)
    """
    def dfs_iterativo(i, j):
        """
        Função para realizar a busca em profundidade (DFS) de forma iterativa.
        Marca todos os 1's conectados a partir da posição (i, j).
        """
        # Inicializar uma pilha com a célula inicial
        pilha = [(i, j)]
        
        while pilha:
            x, y = pilha.pop()
            
            # Se a célula estiver fora dos limites ou já foi visitada, continua
            if x < 0 or x >= len(sensor_matrix) or y < 0 or y >= len(sensor_matrix[0]) or sensor_matrix[x, y] == 0:
                continue
            
            # Marcar a célula como visitada (transformando em 0)
            sensor_matrix[x, y] = 0
            
            # Adicionar as 4 direções vizinhas (cima, baixo, esquerda, direita) à pilha
            pilha.append((x + 1, y))  # Baixo
            pilha.append((x - 1, y))  # Cima
            pilha.append((x, y + 1))  # Direita
            pilha.append((x, y - 1))  # Esquerda

    # Converte o sensor_matrix (se não for uma matriz NumPy) para uma matriz numpy se necessário
    if not isinstance(sensor_matrix, np.ndarray):
        sensor_matrix = np.array(sensor_matrix)

    num_pecas = 0

    # Percorrer a matriz para identificar blocos de 1's conectados
    for i in range(sensor_matrix.shape[0]):
        for j in range(sensor_matrix.shape[1]):
            if sensor_matrix[i, j] == 1:  # Se encontrar um 1, é o início de uma nova peça
                num_pecas += 1
                dfs_iterativo(i, j)  # Fazer DFS iterativo para marcar todos os 1's conectados à peça

    return num_pecas

def calcular_quantidade_pecas(df):
    quantidade_pecas = 0
    
    # Criar uma matriz completa de sensores com base nas primeiras 44 colunas
    sensores_matrix = df.iloc[:, :44].values  # Extrai todas as 44 colunas dos sensores

    # Agora passamos a matriz inteira para a função buscar_pecas
    quantidade_pecas = buscar_pecas(sensores_matrix)
    
    return quantidade_pecas



# ---------------- % POR TEMPO ----------------
def grafico_percentual_bloqueado(df, start_time=None, end_time=None):
    if 'Percentual Bloqueado' in df.columns and 'Datetime' in df.columns: 
        df['Datetime'] = pd.to_datetime(df['Datetime'], format="%Y.%m.%d_%H.%M.%S", errors='coerce')

        if start_time and end_time:
            df = df[(df['Datetime'] >= start_time) & (df['Datetime'] <= end_time)]

        fig = go.Figure(go.Scatter(
            x=df['Datetime'],
            y=df['Percentual Bloqueado'],
            mode='lines',
            fill='tozeroy', 
            fillcolor='rgba(0, 123, 255, 0.3)',  
            line=dict(color='rgba(0, 123, 255, 1)')  
        ))
        
        fig.update_layout(
            title="Percentual Bloqueado ao Longo do Tempo",
            xaxis_title="Tempo",
            yaxis_title="Percentual Bloqueado (%)",
            template="plotly_dark"  
        )

        st.plotly_chart(fig)
    else:
        st.write("As colunas 'Percentual Bloqueado' ou 'Datetime' estão ausentes no arquivo.")

# ---------------- GRÁFICO DE ROSCA ----------------
def grafico_de_rosca(percentual):
    fig = go.Figure(go.Pie(
        labels=['Bloqueado', 'Livre'],
        values=[percentual, 100 - percentual],
        hole=0.4,  
        marker=dict(colors=['#FF6347', '#90EE90']), 
        direction='clockwise',
        textinfo='percent+label',
        hoverinfo='label+percent'
    ))
    
    fig.update_layout(
        title="Percentual Bloqueado",
        showlegend=False,
        margin=dict(t=30, b=30, l=30, r=30), 
        width=300,  
        height=300  
    )
    
    st.plotly_chart(fig)

# ---------------- CALCULO AREA ----------------       
def calcular_area(velocidade, df):
    area_total = 0 
    comprimento = velocidade / 600  
        
    largura = df['Largura']

    for largura_valor in largura:  
        largura_metro = largura_valor / 100  
        area_linha = largura_metro * comprimento
        area_total += area_linha
    
    print (area_total)
    return area_total

# ---------------- SFTP ----------------
def download_file_from_sftp(hostname, port, username, password, remote_path):
    try:
        transport = paramiko.Transport((hostname, port))
        transport.connect(username=username, password=password)
        sftp = paramiko.SFTPClient.from_transport(transport)
        files = sftp.listdir(remote_path)
        sftp.close()
        transport.close()
        return files
    except Exception as e:
        st.error(f"Erro ao se conectar ao SFTP: {e}")
        return None

def get_file_content_from_sftp(hostname, port, username, password, remote_path):
    try:
        transport = paramiko.Transport((hostname, port))
        transport.connect(username=username, password=password)
        sftp = paramiko.SFTPClient.from_transport(transport)
        with sftp.file(remote_path, 'r') as file_handle:
            file_content = file_handle.read().decode('utf-8')
        sftp.close()
        transport.close()
        return file_content
    except Exception as e:
        st.error(f"Erro ao se conectar ao SFTP: {e}")
        return None

# ---------------- MAIN ----------------
def main():
    confVelEsteira = float(os.getenv('VEL_PADRAO'))
    st.title("Análise de Sensores")

    st.sidebar.header("Escolha a Fonte de Arquivo")
    source_option = st.sidebar.selectbox("Selecione a Fonte:", ["SFTP", "Local"])

    if source_option == "SFTP":
        st.sidebar.header("Escolha o Arquivo do SFTP")
        hostname = os.getenv('SFTP_IP')
        port = int(os.getenv('SFTP_PORT'))
        username = os.getenv('SFTP_USER')
        password = os.getenv('SFTP_PSW')
        remote_path = os.getenv('SFTP_PATH')

        files = download_file_from_sftp(hostname, port, username, password, remote_path)
        selected_file = None
        if files:
            file_select_label = f"Escolha um arquivo CSV do SFTP ({hostname}, {username})"
            selected_file = st.sidebar.selectbox(file_select_label, files, index=None, placeholder=remote_path)

    else:
        st.sidebar.header("Escolha o Arquivo Local")
        uploaded_file = st.sidebar.file_uploader("Escolha um arquivo CSV", type="csv")

    file_content = None
    if source_option == "SFTP" and selected_file:
        remote_file_path = os.path.join(remote_path, selected_file)
        file_content = get_file_content_from_sftp(hostname, port, username, password, remote_file_path)
    elif source_option == "Local" and uploaded_file is not None:
        file_content = uploaded_file.getvalue().decode('utf-8')

    if file_content:
        full_df = pd.read_csv(StringIO(file_content), sep=';')
        full_df['Datetime'] = pd.to_datetime(full_df['Timestamp'], format="%Y.%m.%d_%H.%M.%S", errors='coerce')

        min_timestamp = full_df['Datetime'].min()
        max_timestamp = full_df['Datetime'].max()

        st.write("Filtrar por intervalo de tempo")
        
        col1, col2 = st.columns(2)
        with col1:
            start_time = st.time_input("Hora de Início", value=min_timestamp.time())
        with col2:
            end_time = st.time_input("Hora de Fim", value=max_timestamp.time())

        velocidade = st.number_input(label="Informe a Velocidade da esteira em Metros por minuto", value=confVelEsteira)

        start_datetime = pd.to_datetime(min_timestamp.date().strftime('%Y-%m-%d') + ' ' + start_time.strftime('%H:%M:%S'))
        end_datetime = pd.to_datetime(max_timestamp.date().strftime('%Y-%m-%d') + ' ' + end_time.strftime('%H:%M:%S'))

        if st.button("Confirmar"):
            filtered_df = full_df[(full_df['Datetime'] >= start_datetime) & (full_df['Datetime'] <= end_datetime)]
            filtered_df['Percentual Bloqueado'] = pd.to_numeric(filtered_df['Percentual Bloqueado'], errors='coerce')
            largura = filtered_df['Largura']

            if velocidade > 0:
                area = calcular_area(velocidade, filtered_df)

            media_percentual_bloqueado = filtered_df['Percentual Bloqueado'].mean()
            peças = calcular_quantidade_pecas(filtered_df)

            with st.expander("Dados do CSV"):
                st.write(filtered_df)

            col1, col2, col3 = st.columns(3)

            with col1:
                st.markdown(
                    f"""
                    <div style="background-color: #262730; padding: 20px; border-radius: 8px; text-align: center;">
                        <h4 style="color: #FFFFFF; font-size: 24px;">Média % Bloqueado</h4>
                        <p style="font-size: 50px; font-weight: bold; color: #FFFFFF;">{media_percentual_bloqueado:.2f}%</p>
                    </div>
                    """, 
                    unsafe_allow_html=True
                )

            with col2:
                st.markdown(
                    f"""
                    <div style="background-color: #262730; padding: 20px; border-radius: 8px; text-align: center;">
                        <h4 style="color: #FFFFFF; font-size: 24px;">Área Total (m²)</h4>
                        <p style="font-size: 50px; font-weight: bold; color: #FFFFFF;">{area:.2f}</p>
                    </div>
                    """, 
                    unsafe_allow_html=True
                )     

            with col3:
                st.markdown(
                    f"""
                    <div style="background-color: #262730; padding: 20px; border-radius: 8px; text-align: center;">
                        <h4 style="color: #FFFFFF; font-size: 24px;">Quantidade Peças</h4>
                        <p style="font-size: 50px; font-weight: bold; color: #FFFFFF;">{peças}</p>
                    </div>
                    """, 
                    unsafe_allow_html=True
                )         

            st.markdown("<br><br>", unsafe_allow_html=True)

            st.title("Gráficos")
          
            #gerar_sombra_plotly(filtered_df, start_datetime, end_datetime)

            st.markdown("<br><br>", unsafe_allow_html=True)

            col1, col2 = st.columns([2, 0.8])

            with col1:
            
                grafico_percentual_bloqueado(filtered_df, start_datetime, end_datetime)

            with col2:
                grafico_de_rosca(media_percentual_bloqueado)

    else:
        st.write("Escolha um arquivo para continuar.")
        
if __name__ == "__main__":
    main()

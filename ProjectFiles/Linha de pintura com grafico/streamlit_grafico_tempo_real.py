import mysql.connector
import math
import sys
import streamlit as st
import pandas as pd
from time import sleep,time
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from streamlit_autorefresh import st_autorefresh
from datetime import datetime, timedelta
import pandas as pd
from datetime import datetime
from threading import Thread
from queue import Queue


st.set_page_config(layout='wide')
placeholder_graph = st.empty()

option_theme = st.get_option("theme.base")
if option_theme == 'dark':
    text_color = 'white'
else:    
    text_color = 'black'



def encontrar_intervalos_de_zeros(vetor,datas=[]):
    intervalos = []
    inicio = None
    #print('\n\n##############')

    for i, valor in enumerate(vetor):
        if valor <= 2:
            if ((i and (datas[i] - datas[i-1]).total_seconds() <= 1 ) or inicio is None):
                #print(f'\t\t{i} ({(datas[i] - datas[i-1]).total_seconds()}) {datas[i]} {(i and (datas[i] - datas[i-1]).total_seconds() <= 1 )} {inicio }')
                if inicio is None:
                    #print(f'\nABRINDO EM {i}')#(f'DIF DATAS: {datas[i]} - {datas[i-1]} {(datas[i] - datas[i-1]).total_seconds()}')
                    inicio = i  # Marca o início de uma sequência de zeros
            elif inicio is not None:
                add_time = timedelta(milliseconds=500)
                intervalos.append([datas[inicio] -add_time, datas[i - 1] + add_time])  # Fim da sequência de zeros
                inicio = i
                #print(f'\n\tFECHANDO EM {i} {datas[i - 1] + add_time}')

        else:
            if inicio is not None:
                add_time = timedelta(milliseconds=500)
                intervalos.append([datas[inicio] -add_time, datas[i - 1] + add_time])  # Fim da sequência de zeros
                inicio = None
                #print(f'\n\tFECHANDO EM {i} {datas[i - 1] + add_time}')
                #exit()

    # Verifica se há uma sequência de zeros no final do vetor
    if inicio is not None:
        add_time = timedelta(seconds=0)
        if datas[inicio] == datas[len(vetor) - 1]:
            add_time = timedelta(milliseconds=500)
        intervalos.append([datas[inicio], datas[len(vetor) - 1]])
    return intervalos

def detectar_intervalos_faltante(x,porcentagem=[]):
    intervalos = []
    
    # Iterar sobre o vetor para encontrar os intervalos
    for i in range(1, len(x)):
        # Calcular a diferença entre a data i e a data anterior (i-1)
        diff = (x[i] - x[i-1]).total_seconds()
        
        # Se a diferença for maior que 1 segundo, adicionar ao intervalo
        if diff > 1: # or porcentagem[i-1] <= 2 or porcentagem[i] <= 2:
            intervalos.append((x[i-1] + timedelta(seconds=0.5), x[i] - timedelta(seconds=0.5)))

    return intervalos

### Para variável last_read['LinhaPinturaUtilizacaoParada'].to_list()
def encontrar_intervalos_de_uns(vetor):
    intervalos = []
    inicio = None

    for i, valor in enumerate(vetor):
        if valor == 1:
            if inicio is None:
                inicio = i  # Marca o início de uma sequência de zeros
        else:
            if inicio is not None:
                intervalos.append([inicio, i - 1])  # Fim da sequência de zeros
                inicio = None

    # Verifica se há uma sequência de zeros no final do vetor
    if inicio is not None:
        intervalos.append([inicio, len(vetor) - 1])
    return intervalos

def merge_intervals(intervals):
    if not intervals:
        return []

    # Ordena os intervalos pelo início
    intervals.sort(key=lambda x: x[0])
    
    merged = [intervals[0]]

    for start, end in intervals[1:]:
        last_start, last_end = merged[-1]

        # Se houver sobreposição ou contenção, mesclar intervalos
        if start <= last_end:
            merged[-1] = (last_start, max(last_end, end))
        else:
            merged.append((start, end))

    return merged

def calcular_media_porcentagem_por_tempo_trabalhando(display_data):
    somatorio = 0
    tempo_total = 0
    for perOcup in display_data['perOcup']:
        if perOcup > 2:
            somatorio += perOcup
            tempo_total += 1
    return somatorio / (minutos_trabalhados * 60)

def create_graph(display_data):
    # INTERVALOS DE ZEROS (UNITÁRIOS são 0.5 maiores)
    intervalos_inativo = encontrar_intervalos_de_zeros(display_data['perOcup'],display_data['date'])#, display_data['perOcup'])

    # INTERVALOS DE PERIODOS SEM DADOS (TODOS SÃO 0.5 anterior ao dado do intervalo)
    intervalos_desativado = detectar_intervalos_faltante(display_data['date'])#, display_data['perOcup'])

    ############# CONTINUAR >>>>>
    #print(intervalos_desativado)
    #Adicionar zeros nas posições desses intervalos
    for x1,x2 in intervalos_desativado:
        first = True
        #print(f'PROCESSANDO {x1} e {x2}')
        for indt,dt in enumerate(display_data['date']):
            if first and dt > x1:
                # print(f'\tPROCESSANDO {x1} > que {dt}')
                display_data['date'].insert(indt,x1)
                display_data['perOcup'].insert(indt,0)
                # print(f'\t\tInserirI  em [{indt}]')
                first = False
            elif not first and dt > x2:
                # print(f'\tPROCESSANDO {x2} < {dt}')
                display_data['date'].insert(indt,x2)
                display_data['perOcup'].insert(indt,0)
                # print(f'\t\tInserirF em [{indt}]')
                break

    # Converte dados em dataframe
    display_data = pd.DataFrame(display_data)

    percentPerHoraTrab = calcular_media_porcentagem_por_tempo_trabalhando(display_data)

    # TEMPO PARA REFRESH DO CÓDIGO Número de * segundos * mili
    count = st_autorefresh(interval= 15 * 1 * 1000, key="dataframerefresh")
    #st.markdown(f'Contador Updates: {count}')
    
    # MESCLA INTERVALOS
    #intervalos_inativo = merge_intervals(intervalos_inativo)

    # Criar gráfico
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=display_data['date'], y=display_data['perOcup'], mode='lines', name='Linha principal'))

    # Adicionar áreas marcadas dados ~= 0%
    for x1,x2 in intervalos_inativo:
        fig.add_vrect(x0=x1, x1=x2, fillcolor="yellow", opacity=0.3, layer="below", line_width=0)

    for x1,x2 in intervalos_desativado:
        fig.add_vrect(x0=x1,x1=x2,fillcolor="red", opacity=0.3, layer="below", line_width=0)

    # Definir tamanho do y
    fig.update_layout(
        yaxis=dict(range=[0, 100]),
        template="plotly_dark" if st.get_option("theme.base") == "dark" else "plotly",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="white" if st.get_option("theme.base") == "dark" else "black")
  # Define o eixo Y de 0 a 50
    )
    return fig, percentPerHoraTrab, count, display_data

def create_bar_graph(display_data):
    display_data = pd.DataFrame(display_data)
    display_data['ativo'] = display_data['perOcup'] > 2
    display_data['hour'] = display_data['date'].dt.floor('h')

    grouped = display_data.groupby('hour')

    # Total de segundos em uma hora
    segundos_por_hora = 3600

    # Crie um DataFrame com as métricas
    result = pd.DataFrame()

    # Número de registros por hora (tempo ativo em segundos)
    result['tempo_ativo_seg'] = grouped.size()

    # Tempo inativo em segundos (segundos totais - segundos ativos)
    result['tempo_inativo_seg'] = segundos_por_hora - result['tempo_ativo_seg']
    result['percent_tempo_inativo_seg'] = (result['tempo_inativo_seg'] / 36) 

    # media porcentagem ativa por hora 
    result['media_perOcup_ativo'] = grouped['perOcup'].apply(lambda x: x[x > 2].mean())

    # tempo ativo menor que 2 segundos por hora
    result['tempo_ativo_menor_2_seg'] = grouped['perOcup'].apply(lambda x: (x <= 2).sum())
    result['percent_tempo_ativo_menor_2_seg'] = (result['tempo_ativo_menor_2_seg'] / 36) 

    fig_bar = go.Figure() # make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.1) #
    bar_width = 1000000

    fig_bar.add_trace(go.Bar(
        x = result.index,
        y=-result['media_perOcup_ativo'],
        base=0,
        name='Média % Ocupação Ativa',
        marker_color='green',
        offset=-1000000,
        width=bar_width*2,
        opacity=0.3#,
        
    ))#,row=2,col=1)

    # Adicione as barras para o tempo inativo
    fig_bar.add_trace(go.Bar(
        x=result.index,
        y=result['percent_tempo_inativo_seg'],
        name='Tempo Inativo (% de hora)',
        marker_color='red',
        #offset=0,
        offset=-1000000,
        opacity=0.3,#,
        width=bar_width
    ))#,row=1,col=1)

    # Adicione as barras para o tempo ativo com ocupação < 2%
    fig_bar.add_trace(go.Bar(
        x=result.index,
        y=result['percent_tempo_ativo_menor_2_seg'],
        name='Tempo Ativo <2% (% de hora)',
        marker_color='yellow',

        offset=-0.2,
        opacity=0.3,
        width=bar_width
    ))#,row=1,col=1)

    fig_bar.update_layout(
        #title="Gráfico de Barras ",
        yaxis=dict(
            zeroline=True,
            zerolinewidth=1,
            zerolinecolor='grey'
        ),
        template="plotly_dark" if st.get_option("theme.base") == "dark" else "plotly",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="white" if st.get_option("theme.base") == "dark" else "black")
        #barmode='stack'  # Para que as posições definidas sejam respeitadas
    )
    return fig_bar

def create_graph_wrapper(display_data, q):
    fig, percentPerHoraTrab, count, display_data = create_graph(display_data)
    q.put((fig, percentPerHoraTrab, count, display_data))

def create_bar_graph_wrapper(display_data, q):
    fig_bar = create_bar_graph(display_data)
    q.put(fig_bar)

# Conectar ao MySQL
conn = mysql.connector.connect(
    host="192.168.100.74",
    user="root",
    password="f4c1l",
    database="tegacepp"
)

# Definir período de análise
datetime.today()
periodo_inicio = "2025-03-14 13:00:00"
periodo_fim = "2025-03-14 14:00:00"

read_date_ini = 'current_date()'
read_date_fin = 'current_date()'

if 'periodo_tempo' not in st.session_state:
    st.session_state['periodo_tempo'] = (datetime.today(),datetime.today())

read_datas = st.session_state.get('periodo_tempo',(datetime.today().date(),))

# if not isinstance(read_datas,tuple):
#     read_datas = (read_datas,)

if len(read_datas)>1:
    read_date_ini,read_date_fin = read_datas
else:
    read_date_ini = read_datas[0]
    read_date_fin = read_datas[0]

read_date_ini = read_date_ini
read_date_fin = read_date_fin + timedelta(days=1)

# start = time()

query_hr_ini = f'''
    select min(l.LinhaPinturaUtilizacaoDtHr) from linhapinturautilizacao l 
    where l.LinhaPinturaUtilizacaoDtHr >= '{read_date_ini}' AND l.LinhaPinturaUtilizacaoDtHr <= '{read_date_fin}' '''
periodo_inicio = pd.read_sql(query_hr_ini, conn)
periodo_inicio = periodo_inicio.iloc[0, 0]



if periodo_inicio:
    print(periodo_inicio,type(periodo_inicio))
    periodo_fim = periodo_inicio.replace(hour=23,minute=59,second=59,microsecond=0)

    # Ajustar o período final se for maior que a hora atual
    # agora = datetime.now()
    # if pd.to_datetime(periodo_fim) > agora:
    #     periodo_fim = agora.strftime("%Y-%m-%d %H:%M:%S")

    # Executar SELECT para pegar os registros reais
    if read_date_fin - read_date_ini > timedelta(days=1):
        periodo_inicio = read_date_ini
        periodo_fim = read_date_fin

    

    query = f"""
        SELECT LinhaPinturaUtilizacaoDtHr, LinhaPinturaUtilizacaoPerOcup, LinhaPinturaUtilizacaoParada
        FROM linhapinturautilizacao
        WHERE LinhaPinturaUtilizacaoDtHr BETWEEN '{periodo_inicio}' AND '{periodo_fim}'
        ORDER BY LinhaPinturaUtilizacaoDtHr;
    """
    last_read = pd.read_sql(query, conn)

    

    # Fechar conexão
    # Converter para datetime
    last_read["LinhaPinturaUtilizacaoDtHr"] = pd.to_datetime(last_read["LinhaPinturaUtilizacaoDtHr"])

    # Criar range completo de minutos
    todos_minutos = pd.date_range(start=periodo_inicio, end=periodo_fim, freq='T')


    # Criar DataFrame com todos os minutos
    df_todos = pd.DataFrame({"LinhaPinturaUtilizacaoDtHr": todos_minutos})

    # Fazer merge para preencher minutos sem registro como NaN
    df_final = df_todos.merge(last_read, on="LinhaPinturaUtilizacaoDtHr", how="left")

    # Preencher valores NaN em 'LinhaPinturaUtilizacaoParada' com 1 (sem registro = parada)
    df_final["LinhaPinturaUtilizacaoParada"].fillna(1, inplace=True)

    # Contar minutos trabalhados e parados
    minutos_trabalhados = (df_final["LinhaPinturaUtilizacaoParada"] == 0).sum()
    minutos_parados = (df_final["LinhaPinturaUtilizacaoParada"] == 1).sum()


    # query_dados = f"""
    #     SELECT LinhaPinturaUtilizacaoDtHr, LinhaPinturaUtilizacaoPerOcup, LinhaPinturaUtilizacaoParada
    #     FROM linhapinturautilizacao
    #     WHERE LinhaPinturaUtilizacaoDtHr BETWEEN '{periodo_inicio}' AND '{periodo_fim}'
    #     ORDER BY LinhaPinturaUtilizacaoDtHr;"""
    # last_read = pd.read_sql(query_dados, conn)

    # Converter para dicionário de listas
    display_data = {'date': last_read['LinhaPinturaUtilizacaoDtHr'].to_list(),'perOcup': last_read['LinhaPinturaUtilizacaoPerOcup'].to_list()}

    conn.close()

    # st.markdown(f'TEMPO LEVADO DEPOIS QUERY {time() - start}')

    # REMOVER DUPLICATAS (mantém maior)
    # duplicatas = []
    # for date in display_data['date']:
    #     if date not in duplicatas and display_data['date'].count(date) > 1:
    #         duplicatas.append(date)
    #         index_duplicada = display_data['date'].index(date)
    #         index_duplicada2 = index_duplicada + 1
    #         if display_data['perOcup'][index_duplicada] > display_data['perOcup'][index_duplicada2]:
    #             display_data['date'].pop(index_duplicada2)
    #             display_data['perOcup'].pop(index_duplicada2)
    #         else:
    #             display_data['date'].pop(index_duplicada)
    #             display_data['perOcup'].pop(index_duplicada)

    # st.markdown(f'TEMPO LEVADO ANTES THREADS {time() - start}')

    q_graph = Queue()
    q_bar = Queue()
    thread_graph = Thread(target=create_graph_wrapper, args=(display_data, q_graph))
    thread_bar = Thread(target=create_bar_graph_wrapper, args=(display_data, q_bar))

    # Iniciar as threads
    thread_graph.start()
    thread_bar.start()

    # Esperar que ambas terminem
    thread_graph.join()
    thread_bar.join()

    print('TERMINADA EXECUÇÃO ??')

    # st.markdown(f'TEMPO LEVADO THREADS {time() - start}')

    fig, percentPerHoraTrab, count, display_data = q_graph.get()
    fig_bar = q_bar.get()

    print('DADO ADQUIRIDO\n\n')
    
    col1,col2 = st.columns([2,10])
    with col1:
        with st.container(border=True):
            st.markdown('**Total de Tempo:**')
            st.markdown(f"<h1 style='text-align: center;'>{math.floor(len(df_final) / 60)}:{len(df_final) % 60:02}</h1>",unsafe_allow_html=True)
            #:red[Texto Exemplo]
        with st.container(border=True):
            st.markdown('**Tempo Trabalhando:**')
            st.markdown(f"<h1 style='text-align: center;'>{math.floor(minutos_trabalhados / 60)}:{minutos_trabalhados % 60:02}</h1>",unsafe_allow_html=True)
        with st.container(border=True):
            st.markdown('**Ocupação média por Tempo trabalhando:**')
            st.markdown(f"<h1 style='text-align: center;'>{percentPerHoraTrab:.2f}%</h1>",unsafe_allow_html=True)
        with st.container(border=True):
            st.markdown('**Tempo Parado:**')
            st.markdown(f"<h1 style='text-align: center;'>{math.floor(minutos_parados / 60)}:{minutos_parados % 60:02}</h1>",unsafe_allow_html=True)
    with col2:
        
        st.markdown('## Indicativo de uso da linha de pintura da esteira no dia {} até {}'.format(read_date_ini.strftime('%d/%m/%Y'),(read_date_fin-timedelta(days=1)).strftime('%d/%m/%Y')))
        st.date_input('Filtro de Data de Leitura',key='periodo_tempo')

        with st.container(border=True):
            st.plotly_chart(fig,key='gráfico')
        with st.container(border=True):
            st.plotly_chart(fig_bar,key='gráfico_bar')
        #color: {text_color};
        st.markdown(f"<p style='text-align: right; '>Última consulta feita em {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}</h1>", unsafe_allow_html=True)
    # st.markdown(f'TEMPO LEVADO TOTAL {time() - start}')
else:
    st.markdown(f'''
        ## Sem Dados disponíveis entre {read_date_ini.strftime('%d/%m/%Y')} até {(read_date_fin -  timedelta(days=1)).strftime('%d/%m/%Y')}
    ''')
    st.date_input('Filtro Leitura',key='periodo_tempo')
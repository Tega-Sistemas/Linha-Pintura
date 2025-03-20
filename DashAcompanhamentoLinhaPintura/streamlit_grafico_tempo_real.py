import mysql.connector
import math
import sys
import streamlit as st
import pandas as pd
from time import sleep, time
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from streamlit_autorefresh import st_autorefresh
from datetime import datetime, timedelta
import pandas as pd
from datetime import datetime
from threading import Thread
from queue import Queue
import copy


st.set_page_config(layout='wide')

placeholder_graph = st.empty()

option_theme = st.get_option("theme.base")
if option_theme == 'dark':
    text_color = 'white'
else:    
    text_color = 'black'


def retorna_dia_da_semana(data): # começando no domingo
    """
    Retorna o dia da semana começando no domingo (domingo = 1, segunda = 2, ..., sábado = 7).
    """
    dia_iso = data.isoweekday()  # Segunda = 1, Domingo = 7
    # Mapeia para: Domingo = 1, Segunda = 2, ..., Sábado = 7
    return (dia_iso % 7) + 1

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
        if diff > 1 and x[i].day - x[i-1].day == 0: # or porcentagem[i-1] <= 2 or porcentagem[i] <= 2:
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

def create_graph(display_data,show_date_start,show_date_end):
    # INTERVALOS DE ZEROS (UNITÁRIOS são 0.5 maiores)
    intervalos_inativo = encontrar_intervalos_de_zeros(display_data['perOcup'],display_data['date'])#, display_data['perOcup'])

    # INTERVALOS DE PERIODOS SEM DADOS (TODOS SÃO 0.5 anterior ao dado do intervalo)
    intervalos_desativado = detectar_intervalos_faltante(display_data['date'])#, display_data['perOcup'])
    #print('INICIANDO OPERACAO {}'.format(len(display_data['date'])))

    #####################
    # Pegar ínicio e fim do período de cada dia
    #   Pegar dias
    dias_periodo = []

    # calcular os minutos decorridos nos intervalos de trabalho até o instante de tempo atual caso não seja domingo e a última data seja o dia atual
    if DIA_SEM_ATUAL != 1 and show_date_end - timedelta(days=1) == datetime.now():
        dias_periodo.append(show_date_start - timedelta(days=1))
    else:
        extra_day = 1

    dias_atras = ((show_date_end - timedelta(days=1)) - show_date_start).days + extra_day
    
    
    if dias_atras:
        for i in range(dias_atras):
            process_date = show_date_end - timedelta(days=1) - timedelta(days=i+1 - extra_day)
            if retorna_dia_da_semana(process_date) != 1:
                dias_periodo.append(process_date)
    ########### CONTINUAR ABAIXO

    


    #Adicionar zeros nas posições desses intervalos desativados
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
    #print('OPERACAO CONCLUIDA {}'.format(len(display_data['date'])))
    # Converte dados em dataframe

    display_data = pd.DataFrame(display_data)

    print(f'INDEX : {display_data.index}')

    ###############
    #   Pegar periodo
    print(f'DIAS EXISTENTES: {dias_periodo}')

    datas_inicio = []
    datas_final = []
    # SISTEMA PARA ADICIONAR HORAS VAZIAS
    for dia_trab_periodo in dias_periodo[::-1]:
        print(f'\tPROCESSANDO {dia_trab_periodo}')
        # result['percent_tempo_inativo_seg'] [hora_falta] = 100

        dia_semana_process = retorna_dia_da_semana(dia_trab_periodo)
        inicio_trab_dia = dados_intervalos[dia_semana_process]['TurnoProdutivoHrEntrada']
        fim_trab_dia = dados_intervalos[dia_semana_process]['TurnoProdutivoHrSaida']

        # Não adicionar para sábado
        if dia_semana_process != 7:
            data_inicial = datetime(year=dia_trab_periodo.year,month=dia_trab_periodo.month,day=dia_trab_periodo.day).replace(hour=inicio_trab_dia.hour,minute=inicio_trab_dia.minute)
            if data_inicial not in display_data['date'].values:
                display_data.loc[len(display_data)] = [data_inicial,0]
                datas_inicio.append(data_inicial)

            data_final = datetime(year=dia_trab_periodo.year,month=dia_trab_periodo.month,day=dia_trab_periodo.day).replace(hour=fim_trab_dia.hour,minute=fim_trab_dia.minute)
            if data_final not in display_data['date'].values:
                display_data.loc[len(display_data)] = [data_final,0]
                datas_final.append(data_final)

            print(f'\t{data_inicial} até {data_final}')
        #REPLACE POIS NÃO CONSEGUE CRIAR DATE_RANGE PARA VALORES MAIS ANTIGOS QUE 1677 ?
        #horarios_desejados = pd.date_range(start=inicio_trab_dia.replace(year=2025), end=fim_trab_dia.replace(year=2025) + timedelta(hours=1), freq='h')
                #print(f'\t\t{dia_hora_trab} /\n\t\t\t {}')
    
    display_data = display_data.sort_values(by='date').reset_index(drop=True)

    for dtini in datas_inicio:
        indice_ini = display_data.index[display_data['date'] == dtini]
        if retorna_dia_da_semana(dtini) != 7:
            new_interval = [pd.Timestamp(dtini), display_data.loc[indice_ini + 1,'date'].iloc[0]]

            print('\t-1>>>{}'.format(new_interval))
            intervalos_desativado.append(new_interval)
    
    
    for dtfim in datas_final:
        indice_fim = display_data.index[display_data['date'] == dtfim]
        #if len(indice_fim) > 1:
            #indice_fim = indice_fim[0]
        print(indice_fim,type(indice_fim))
        #if indice_fim > 0: # POR QUE RETORNA DOIS VALORES? REGISTROS DUPLICADOS ?
        if indice_fim[0] > 0:
            new_interval = [display_data.loc[indice_fim - 1,'date'].iloc[0], pd.Timestamp(dtfim)]

            print('\t-2>>>{}'.format(new_interval))
            if new_interval not in intervalos_desativado:
                intervalos_desativado.append(new_interval)
    
    
    #print(intervalos_desativado)
    #####################    

    percentPerHoraTrab = calcular_media_porcentagem_por_tempo_trabalhando(display_data)
    
    # MESCLA INTERVALOS
    #intervalos_inativo = merge_intervals(intervalos_inativo)

    # Criar gráfico
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=display_data['date'], y=display_data['perOcup'], mode='lines', name='Linha principal'))
    
    #Criar retângulos para intervalos inativos
    shapes = [
        {
            "type": "rect",
            "x0": x1, "x1": x2,
            "y0": -100, "y1": 300,
            "fillcolor": "yellow",
            "opacity": 0.3,
            "layer": "below",
            "line": {"width": 0}
        }
        for x1, x2 in intervalos_inativo
    ]
    
    #Criar retângulos para intervalos desativado
    shapes += [
        {
            "type": "rect",
            "x0": x1, "x1": x2,
            "y0": -100, "y1": 300,
            "fillcolor": "red",
            "opacity": 0.3,
            "layer": "below",
            "line": {"width": 0}
        }
        for x1, x2 in intervalos_desativado
    ]

    print(f'TEMPO INICIO GRAFICO 1 {time() - START}')

    # Definir tamanho do y
    fig.update_layout(
        shapes= shapes,
        yaxis=dict(range=[0, 100]),
        # xaxis=dict(
        #     tickmode="linear",
        #     dtick=3600000/4#, # INTERVALO ENTRE DADOS em ms
        #     #tickformat="%Y-%m-%d %H:%M"
        # ),
        template="plotly_dark" if st.get_option("theme.base") == "dark" else "plotly",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="white" if st.get_option("theme.base") == "dark" else "black")
  # Define o eixo Y de 0 a 50
    )
    return fig, percentPerHoraTrab, display_data

def create_bar_graph(display_data,show_date_start,show_date_end):
    # while True:
    #     try:
    #         print('TENTATIVA CONVERT ({}, {})'.format(len(display_data['date']), len(display_data['perOcup'])))
    display_data = pd.DataFrame(display_data)
        #     print('SUCESSO')
        #     break
        # except Exception as e:
        #     print('ERRO: {}, {} > {}'.format(len(display_data['date']), len(display_data['perOcup']),e))
        #     continue
            #print(display_data['perOcup'])
            #print('ERRO: dados para dataframe: {} ({}, {}), ERRO {} >>'.format(display_data.keys(), len(display_data['date']), len(display_data['perOcup']), e))

    display_data['ativo'] = display_data['perOcup'] > 2
    #print(display_data['date'])
    display_data['hour'] = display_data['date'].dt.floor('h')
    #display_data['date'].max()
    
    min_total = 0 # minutos_total_dia_semana
    
    # VALOR FICA ALTERNANDO ENTRE DATE E DATETIME
    ######### CONTINUAR
    #if datetime.now().date() >= show_date_start.date() and datetime.now().date() <= show_date_end.date():
        #intervalo_total = (datetime.now() - datetime.today().replace(hour=5,minute=0,second=0))#display_data['date'].min())
        #min_total = intervalo_total.seconds / 60# + intervalo_total.days * 60* (18 - 5)
    #print(dados_intervalos)
    
    #variável para talvez considerar o último dia no processamento caso ele não seja igual ao dial atual
    extra_day = 0

    dias_periodo = []

    # calcular os minutos decorridos nos intervalos de trabalho até o instante de tempo atual caso não seja domingo e a última data seja o dia atual
    if DIA_SEM_ATUAL != 1 and show_date_end - timedelta(days=1) == datetime.now():
        segundos_atual = 0
        horario_atual = datetime.now()

        inicio = dados_intervalos[DIA_SEM_ATUAL]['TurnoProdutivoHrEntrada'].replace(year=horario_atual.year,month=horario_atual.month,day=horario_atual.day)
        ini_interv_1 = dados_intervalos[DIA_SEM_ATUAL]['TurnoProdutivoHrSaiIntervalo1'].replace(year=horario_atual.year,month=horario_atual.month,day=horario_atual.day)
        fim_interv_1 = dados_intervalos[DIA_SEM_ATUAL]['TurnoProdutivoHrEntIntervalo1'].replace(year=horario_atual.year,month=horario_atual.month,day=horario_atual.day)
        ini_interv_2 = dados_intervalos[DIA_SEM_ATUAL]['TurnoProdutivoHrSaiIntervalo2'].replace(year=horario_atual.year,month=horario_atual.month,day=horario_atual.day)
        fim_interv_2 = dados_intervalos[DIA_SEM_ATUAL]['TurnoProdutivoHrEntIntervalo2'].replace(year=horario_atual.year,month=horario_atual.month,day=horario_atual.day)
        fim = dados_intervalos[DIA_SEM_ATUAL]['TurnoProdutivoHrSaida'].replace(year=horario_atual.year,month=horario_atual.month,day=horario_atual.day)
        
        periodos_trabalho = [
            (inicio, ini_interv_1),      # Antes do primeiro intervalo
            (fim_interv_1, ini_interv_2), # Entre os intervalos
            (fim_interv_2, fim)          # Após o segundo intervalo
        ]

        segundos_atual = sum(
            max(0, (min(horario_atual, end) - start).total_seconds())
            for start, end in periodos_trabalho
        )

        # if horario_atual <= inicio:
        #     pass # Fora de horário? Começar na meia noite? Ou utilizar primeiro registro existente
        # elif horario_atual > inicio and horario_atual < ini_interv_1:
        #     #calcular do inicio até atual
        #     print('1')
        #     segundos_atual = (horario_atual - inicio).total_seconds()
        # elif horario_atual >= ini_interv_1 and horario_atual <= fim_interv_1:
        #     print('2')
        #     # utilizar fixo do inicio até intervalo
        #     segundos_atual = (ini_interv_1 - inicio).total_seconds()
        # elif horario_atual > fim_interv_1 and horario_atual < ini_interv_2:
        #     print('3')
        #     segundos_atual = (horario_atual - fim_interv_1).total_seconds() + (ini_interv_1 - inicio).total_seconds()
        # elif horario_atual >= ini_interv_2 and horario_atual <= fim_interv_2:
        #     print('4')
        #     segundos_atual = (ini_interv_2 - fim_interv_1).total_seconds() + (ini_interv_1 - inicio).total_seconds()
        # elif horario_atual > fim_interv_2 and horario_atual < fim:
        #     print('5')
        #     segundos_atual = (horario_atual - fim_interv_2).total_seconds() + (ini_interv_2 - fim_interv_1).total_seconds() + (ini_interv_1 - inicio).total_seconds()
        # else:
        #     print('6')
        #     segundos_atual = (fim - fim_interv_2).total_seconds() + (ini_interv_2 - fim_interv_1).total_seconds() + (ini_interv_1 - inicio).total_seconds()
        min_total += segundos_atual/60
        #print(f'COMPARANDO COM {horario_atual} == {fim}')
        dias_periodo.append(show_date_start - timedelta(days=1))
    else:
        extra_day = 1
    # print(f'MINUTOS TOTAIS: {min_total} min')
    
    dias_atras = ((show_date_end - timedelta(days=1)) - show_date_start).days + extra_day
    
    if dias_atras:
        for i in range(dias_atras):
            process_date = show_date_end - timedelta(days=1) - timedelta(days=i+1 - extra_day)
            if retorna_dia_da_semana(process_date) != 1:
                dias_periodo.append(process_date)
            
            dia_semana = retorna_dia_da_semana(process_date)
            if dia_semana != 1: # ignora domingo
                min_total += minutos_total_dia_semana[dia_semana]
            #min_total += 60 * (18 - 5)
    min_trab = 0
    percent_trab_geral = 0
    min_parado = 0
    minutos_ligados = 0

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

    result['tempo_ativo_maior_2_seg'] = grouped['perOcup'].apply(lambda x: (x > 2).sum())
    result['percent_tempo_ativo_maior_2_seg'] = (result['tempo_ativo_maior_2_seg'] / 36) 

    fig_bar = go.Figure() # make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.1) #
    bar_width = 1000000

    #print(f'\n\nDATAS DISPONíveis em horas:{result}\n{type(result)}\n')

    #dias = #pd.unique(result.index.date)#.date.unique()

    #print(f'DIAS EXISTENTES: {dias_periodo}')

    #print(result)
    # SISTEMA PARA ADICIONAR HORAS VAZIAS
    for dia_trab_periodo in dias_periodo[::-1]:
        #print(f'\tPROCESSANDO {dia_trab_periodo}')
        # result['percent_tempo_inativo_seg'] [hora_falta] = 100

        dia_semana_process = retorna_dia_da_semana(dia_trab_periodo)
        inicio_trab_dia = dados_intervalos[dia_semana_process]['TurnoProdutivoHrEntrada']
        fim_trab_dia = dados_intervalos[dia_semana_process]['TurnoProdutivoHrSaida']
        #print(f'\t{inicio_trab_dia} até {fim_trab_dia}')

        # REPLACE POIS NÃO CONSEGUE CRIAR DATE_RANGE PARA VALORES MAIS ANTIGOS QUE 1677 ?
        horarios_desejados = pd.date_range(start=inicio_trab_dia.replace(year=2025), end=fim_trab_dia.replace(year=2025) + timedelta(hours=1), freq='h')
        for hr_desej in horarios_desejados:
            dia_hora_trab = datetime(year=dia_trab_periodo.year,month=dia_trab_periodo.month,day=dia_trab_periodo.day).replace(hour=hr_desej.hour,minute=0)
            if dia_hora_trab not in result.index:
                result.loc[dia_hora_trab] = [0,3600,100,-0,0,0,0,0]
            #else:
                 #print(f'\t\t\t{result.loc[dia_hora_trab]} /// {type(result.loc[dia_hora_trab])}')
                #print(f'\t\t{dia_hora_trab} /\n\t\t\t {}')

    result = result.sort_index()
            #result.iloc[dia_trab_periodo.replace]
    fig_bar.add_trace(go.Bar(
        x= result.index,
        y= -result['media_perOcup_ativo'],
        base=0,
        name='Média % Ocupação Ativa',
        marker_color='blue',
        offset=-1000000,
        width=bar_width*3,
        customdata=[abs(y) for y in -result['media_perOcup_ativo']],
        hovertemplate='%{customdata:.0f} % (%{x})   <extra></extra>',  # Exibe o valor sem o sinal negativo
        opacity=0.3#,
        
    ))#,row=2,col=1)

    #offset_inativo = [ if val != 100 else -1000000 for val in result['percent_tempo_inativo_seg']]
    width_inativo = [bar_width if val != 100 else bar_width*3 for val in result['percent_tempo_inativo_seg']]
    # Adicione as barras para o tempo inativo
    fig_bar.add_trace(go.Bar(
        x=result.index,
        y=result['percent_tempo_inativo_seg'],
        name='Tempo Inativo (% de hora)',
        marker_color='red',
        #offset=0,
        offset=-1000000,
        opacity=0.3,#,
        hovertemplate='%{y:.0f} % (%{x})   <extra></extra>',
        width=width_inativo
    ))#,row=1,col=1)

    # Adicione as barras para o tempo ativo com ocupação < 2%
    fig_bar.add_trace(go.Bar(
        x=result.index,
        y=result['percent_tempo_ativo_menor_2_seg'],
        name='Tempo Ativo <2% (% de hora)',
        marker_color='yellow',
        hovertemplate='%{y:.0f} % (%{x})   <extra></extra>',
        offset=-0,
        opacity=0.3,
        width=bar_width
    ))#,row=1,col=1)

    fig_bar.add_trace(go.Bar(
        x=result.index,
        y=result['percent_tempo_ativo_maior_2_seg'],
        name='Tempo Ativo >2% (% de hora)',
        marker_color='green',
        hovertemplate='%{y:.0f} % (%{x})   <extra></extra>',
        offset=1000000,
        opacity=0.3,
        width=bar_width
    ))#,row=1,col=1)

    fig_bar.update_layout(
        #title="Gráfico de Barras ",
        yaxis=dict(
            zeroline=True,
            range=[-100, 100],
            zerolinewidth=1,
            zerolinecolor='grey'
        ),
        xaxis=dict(
            tickmode="linear",
            dtick=3600000#,
            #tickformat="%Y-%m-%d %H:%M"
        ),
        #yaxis_tickformat=',.0f',
        template="plotly_dark" if st.get_option("theme.base") == "dark" else "plotly",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="white" if st.get_option("theme.base") == "dark" else "black")
        #barmode='stack'  # Para que as posições definidas sejam respeitadas
    )
    return fig_bar, min_total, min_trab, percent_trab_geral, min_parado, minutos_ligados

def create_graph_wrapper(display_data,show_date_start,show_date_end, q):
    fig, percentPerHoraTrab, display_data = create_graph(display_data,show_date_start,show_date_end)
    q.put((fig, percentPerHoraTrab, display_data))
    print(f'TEMPO LEVADO GRAFICO 1 {time() - START}')

def create_bar_graph_wrapper(display_data,show_date_start,show_date_end, q):
    fig_bar,min_total,min_trab,percent_trab_geral,min_parado,minutos_ligados = create_bar_graph(display_data,show_date_start,show_date_end)
    q.put((fig_bar,min_total,min_trab,percent_trab_geral,min_parado,minutos_ligados))
    print(f'TEMPO LEVADO GRAFICO BARRA {time() - START}')

# Conectar ao MySQL
# conn = mysql.connector.connect(
#     host="192.168.100.74",
#     user="root",
#     password="f4c1l",
#     database="tegacepp"
# )

conn = mysql.connector.connect(
    host="192.168.100.30",
    user="root",
    password="f4c1l",
    database="tegacepp_guido"
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

START = time()

###### CONTINUAR >>
# ,TurnoProdutivoHrEntrada,
# TurnoProdutivoHrSaiIntervalo1, TurnoProdutivoHrEntIntervalo1, 
# TurnoProdutivoHrSaiIntervalo2, TurnoProdutivoHrEntIntervalo2,
# TurnoProdutivoHrSaida,
# TurnoProdutivoQtdeMinutosAlmoco 
query_turno = f'''SELECT 
TIME_FORMAT(t.TurnoProdutivoHrEntrada, '%H:%i') AS HoraMinuto,
t.TurnoProdutivoHrEntrada,
t.TurnoProdutivoHrSaiIntervalo1, t.TurnoProdutivoHrEntIntervalo1, 
t.TurnoProdutivoHrSaiIntervalo2, t.TurnoProdutivoHrEntIntervalo2,
t.TurnoProdutivoHrSaida,
t.TurnoProdutivoQtdeMinutosAlmoco,
t.TurnoProdutivoDiaSemana
FROM turnoprodutivo t 
group by t.TurnoProdutivoDiaSemana
order by t.TurnoProdutivoDiaSemana
limit 7;'''#
    
#where t.TurnoProdutivoDiaSemana >= dayofweek('{read_date_ini}') AND t.TurnoProdutivoDiaSemana <= dayofweek('{read_date_fin}')


turno_semanda_dados = pd.read_sql(query_turno, conn)
# st.dataframe(turno_semanda_dados)
periodo_inicio = turno_semanda_dados[turno_semanda_dados['TurnoProdutivoDiaSemana'] == retorna_dia_da_semana(datetime.now())]['HoraMinuto']

#st.markdown(minutos_total_dia_semana)

######## CONTINUAR CHECANDO SE TurnoProdutivoQtdeMinutos é atualizado dinâmicamente
if periodo_inicio.empty:
    #st.markdown('Não foi encontrado')
    query_hr_ini = f'''
        select min(l.LinhaPinturaUtilizacaoDtHr) from linhapinturautilizacao l 
        where l.LinhaPinturaUtilizacaoDtHr >= '{read_date_ini}' AND l.LinhaPinturaUtilizacaoDtHr <= '{read_date_fin}' '''
    periodo_inicio = pd.read_sql(query_hr_ini, conn)
    periodo_inicio = periodo_inicio.iloc[0, 0]
else:
    horario = datetime.strptime(periodo_inicio.iloc[0],'%H:%M')
    #st.markdown(f'{horario} / {type(horario)}')

    hora, minuto = horario.hour,horario.minute
    #st.markdown(f'{read_date_ini} / {type(read_date_ini)}')
    periodo_inicio = datetime.combine(read_date_ini, datetime.min.time()).replace(hour = hora, minute = minuto, second = 0)
#st.markdown(f'{periodo_inicio}/{type(periodo_inicio)}')

dados_intervalos = {}
DIA_SEM_ATUAL = retorna_dia_da_semana(read_date_fin - timedelta(days=1))

minutos_total_dia_semana = {}
for index, row in turno_semanda_dados.iterrows():
    #print('{} == {} ????'.format(row['TurnoProdutivoDiaSemana'],DIA_SEM_ATUAL))
    #if row['TurnoProdutivoDiaSemana'] == DIA_SEM_ATUAL:
    dia_semana_respectivo = row['TurnoProdutivoDiaSemana']
    dados_intervalos[dia_semana_respectivo] = {}
    dados_intervalos[dia_semana_respectivo]['TurnoProdutivoHrEntrada'] = row['TurnoProdutivoHrEntrada']
    dados_intervalos[dia_semana_respectivo]['TurnoProdutivoHrSaiIntervalo1'] = row['TurnoProdutivoHrSaiIntervalo1']
    dados_intervalos[dia_semana_respectivo]['TurnoProdutivoHrEntIntervalo1'] = row['TurnoProdutivoHrEntIntervalo1']
    dados_intervalos[dia_semana_respectivo]['TurnoProdutivoHrSaiIntervalo2'] = row['TurnoProdutivoHrSaiIntervalo2']
    dados_intervalos[dia_semana_respectivo]['TurnoProdutivoHrEntIntervalo2'] = row['TurnoProdutivoHrEntIntervalo2']
    dados_intervalos[dia_semana_respectivo]['TurnoProdutivoHrSaida'] = row['TurnoProdutivoHrSaida']
        

    inicio = row['TurnoProdutivoHrEntrada']
    ini_interv_1 = row['TurnoProdutivoHrSaiIntervalo1']
    fim_interv_1 = row['TurnoProdutivoHrEntIntervalo1']
    ini_interv_2 = row['TurnoProdutivoHrSaiIntervalo2']
    fim_interv_2 = row['TurnoProdutivoHrEntIntervalo2']
    fim = row['TurnoProdutivoHrSaida']
    #minut_almoco = row['TurnoProdutivoQtdeMinutosAlmoco']

    tempo_intervalo_geral = (fim - inicio).total_seconds() / 60
    tempo_interv1 = (fim_interv_1 - ini_interv_1).total_seconds() / 60
    tempo_interv2 = (fim_interv_2 - ini_interv_2).total_seconds() / 60

    print(tempo_intervalo_geral, tempo_interv1, tempo_interv2)

    minutos_dia_sem = tempo_intervalo_geral - (tempo_interv1 + tempo_interv2)# - minut_almoco
    if minutos_dia_sem >= 0:
        minutos_total_dia_semana[row['TurnoProdutivoDiaSemana']] = minutos_dia_sem
    else:
        minutos_total_dia_semana[row['TurnoProdutivoDiaSemana']] = 0

def display_no_data():
    st.markdown(f'''
        ## Sem Dados disponíveis entre {read_date_ini.strftime('%d/%m/%Y')} até {(read_date_fin -  timedelta(days=1)).strftime('%d/%m/%Y')}
    ''')
    st.date_input('Filtro Leitura',key='periodo_tempo')


if periodo_inicio:
    print(periodo_inicio,type(periodo_inicio))
    periodo_fim = datetime.combine(read_date_ini, datetime.min.time()).replace(hour=23,minute=59,second=59,microsecond=0)

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

    minutos_parados = (df_final["LinhaPinturaUtilizacaoPerOcup"] <= 2).sum()
    
    # Preencher valores NaN em 'LinhaPinturaUtilizacaoParada' com 1 (sem registro = parada)
    df_final["LinhaPinturaUtilizacaoParada"].fillna(1, inplace=True)

    # Contar minutos trabalhados e parados
    minutos_trabalhados = (df_final["LinhaPinturaUtilizacaoParada"] == 0).sum()
    
    # minutos_parados = len(df_final["LinhaPinturaUtilizacaoParada"])

    # Converter para dicionário de listas
    display_data = {'date': last_read['LinhaPinturaUtilizacaoDtHr'].to_list(),'perOcup': last_read['LinhaPinturaUtilizacaoPerOcup'].to_list()}

    conn.close()

    st.markdown(f'TEMPO LEVADO DEPOIS QUERY {time() - START}')

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
    if display_data['date']:
        q_graph = Queue()
        q_bar = Queue()
        
        thread_bar = Thread(target=create_bar_graph_wrapper, args=(copy.deepcopy(display_data),read_date_ini,read_date_fin, q_bar))
        thread_graph = Thread(target=create_graph_wrapper, args=(display_data,read_date_ini,read_date_fin, q_graph))
        

        st.markdown(f'TEMPO LEVADO ANTES THREAD {time() - START}')
        # Iniciar as threads
        thread_graph.start()
        thread_bar.start()

        # Esperar que ambas terminem
        thread_graph.join()
        thread_bar.join()
        # st.markdown(f'TEMPO LEVADO THREADS {time() - start}')

        fig, percentPerHoraTrab, display_data = q_graph.get()
        fig_bar, min_total, min_trab, percent_trab_geral, min_parado, minutos_ligados = q_bar.get()

        st.markdown(f'TEMPO LEVADO DEPOIS THREAD {time() - START}')
        col1,col2 = st.columns([2,10])
        with col1:
            minutos_desativados = int(min_total - minutos_parados - minutos_trabalhados)
            #minutos_parados = int((datetime.now() - datetime.today().replace(hour=5,minute=0,second=0)).total_seconds() / 60)
            with st.container(border=True):
                st.markdown('**Total de Tempo:**')
                #minutos_total = len(df_final[df_final['LinhaPinturaUtilizacaoParada'] == 0])
                # old_total_min = len(df_final)
                #min_total
                st.markdown(f"<h1 style='text-align: center;'>{math.floor(min_total/60)}:{int(min_total % 60):02}</h1>",unsafe_allow_html=True)
                #:red[Texto Exemplo]
            with st.container(border=True):
                st.markdown('**Tempo Trabalhando:**')
                st.markdown(f"<h1 style='text-align: center;'>{math.floor(minutos_trabalhados / 60)}:{minutos_trabalhados % 60:02}</h1>",unsafe_allow_html=True)
                #minutos_parados -= minutos_trabalhados
            with st.container(border=True):
                st.markdown('**Ocupação média durante Tempo trabalhando:**')
                st.markdown(f"<h1 style='text-align: center;'>{percentPerHoraTrab:.2f}%</h1>",unsafe_allow_html=True)
            with st.container(border=True):
                st.markdown('**Tempo Parado:**')
                minutos_parados += minutos_desativados
                st.markdown(f"<h1 style='text-align: center;'>{math.floor(minutos_parados / 60)}:{minutos_parados % 60:02}</h1>",unsafe_allow_html=True)
            with st.container(border=True):
                st.markdown('**Tempo Ligado:**')
                #st.markdown(f'{min_total} - {minutos_desativados}')
                minutos_ligados = int(min_total - minutos_desativados)
                st.markdown(f"<h1 style='text-align: center;'>{math.floor(minutos_ligados / 60)}:{minutos_ligados % 60:02}</h1>",unsafe_allow_html=True)
            with st.container(border=True):
                st.markdown('**Tempo Desativado:**') # color: red; background-color:powderblue;
                st.markdown(f"<h1 style='text-align: center; color: red; background-color:lightgray;'>{math.floor(minutos_desativados / 60)}:{minutos_desativados % 60:02}</h1>",unsafe_allow_html=True)
                # f'''
                # <div style="width: 300px; padding: 20px; border: 2px solid black; background-color: powderblue; text-align: center;">
                #     <h1 style="color: red;">Olá</h1>
                #     <p style="color: white; font-size: 18px;">Mundo</p>
                # </div>''',unsafe_allow_html=True)
        with col2:
            st.markdown('## Indicativo de uso da linha de pintura da esteira no dia {} até {}'.format(read_date_ini.strftime('%d/%m/%Y'),(read_date_fin-timedelta(days=1)).strftime('%d/%m/%Y')))
            st.date_input('Filtro de Data de Leitura',key='periodo_tempo')

            with st.container(border=True):
                st.plotly_chart(fig,key='gráfico')
            with st.container(border=True):
                st.plotly_chart(fig_bar,key='gráfico_bar')
            #color: {text_color};
            # TEMPO PARA REFRESH DO CÓDIGO Número de * segundos * mili
            count = st_autorefresh(interval= 5 * 1 * 1000, key="dataframerefresh")
            # st.markdown(f'Contador Updates: {count}')
            st.markdown(f"<p style='text-align: right; '>Última consulta feita em {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}</h1>", unsafe_allow_html=True)
        # st.markdown(f'TEMPO LEVADO TOTAL {time() - start}')
    else:
        display_no_data()
else:
    display_no_data()

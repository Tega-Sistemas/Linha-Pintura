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

# def get_back_days(show_date_start,show_date_end):
#     dias_periodo = []
#     if DIA_SEM_ATUAL != 1 and show_date_end - timedelta(days=1) == datetime.now():
#         dias_periodo.append(show_date_start - timedelta(days=1))
#     else:
#         extra_day = 1

#     dias_atras = ((show_date_end - timedelta(days=1)) - show_date_start).days + extra_day
#     if dias_atras:
#         for i in range(dias_atras):
#             process_date = show_date_end - timedelta(days=1) - timedelta(days=i+1 - extra_day)
#             if retorna_dia_da_semana(process_date) != 1:
#                 dias_periodo.append(process_date)
#     return dias_periodo

def subtract_intervals(interval, subtract_list):
    """
    Subtrai uma lista de intervalos (subtract_list) de um intervalo (interval),
    retornando os pedaços restantes fora dos intervalos subtraídos.
    Cada intervalo é uma lista [inicio, fim] com objetos datetime.
    """
    remaining = [interval]  # Lista inicial com o intervalo a ser ajustado

    for sub in subtract_list:
        new_remaining = []
        for rem in remaining:
            # Sem sobreposição
            if rem[1] <= sub[0] or rem[0] >= sub[1]:
                new_remaining.append(rem)
            # Intervalo completamente dentro do intervalo de pausa (removido)
            elif sub[0] <= rem[0] and rem[1] <= sub[1]:
                continue
            # Sobreposição à direita: ajustar o fim para o início da pausa
            elif rem[0] < sub[0] <= rem[1] <= sub[1]:
                new_remaining.append([rem[0], sub[0]])
            # Sobreposição à esquerda: ajustar o início para o fim da pausa
            elif sub[0] <= rem[0] < sub[1] <= rem[1]:
                new_remaining.append([sub[1], rem[1]])
            # Intervalo de zeros atravessa a pausa: dividir em dois
            elif rem[0] < sub[0] < sub[1] < rem[1]:
                new_remaining.append([rem[0], sub[0]])  # Antes da pausa
                new_remaining.append([sub[1], rem[1]])  # Depois da pausa
        remaining = new_remaining
    
    return remaining

def get_inicio_fim_turno(day):
    dia_semana = retorna_dia_da_semana(day)
    inicio_trab_dia = dados_intervalos[dia_semana]['TurnoProdutivoHrEntrada'].replace(
            year=day.year, month=day.month, day=day.day
        )
    fim_trab_dia = dados_intervalos[dia_semana]['TurnoProdutivoHrSaida'].replace(
            year=day.year, month=day.month, day=day.day
        )
    return inicio_trab_dia, fim_trab_dia

def get_dados_turno(day):
    dia_semana = retorna_dia_da_semana(day)
    inicio_trab_dia = dados_intervalos[dia_semana]['TurnoProdutivoHrEntrada'].replace(
            year=day.year, month=day.month, day=day.day
        )
    fim_trab_dia = dados_intervalos[dia_semana]['TurnoProdutivoHrSaida'].replace(
            year=day.year, month=day.month, day=day.day
        )
    ini_interv_1 = dados_intervalos[dia_semana]['TurnoProdutivoHrSaiIntervalo1'].replace(
            year=day.year, month=day.month, day=day.day
        )
    fim_interv_1 = dados_intervalos[dia_semana]['TurnoProdutivoHrEntIntervalo1'].replace(
            year=day.year, month=day.month, day=day.day
        )
    ini_interv_2 = dados_intervalos[dia_semana]['TurnoProdutivoHrSaiIntervalo2'].replace(
            year=day.year, month=day.month, day=day.day
        )
    fim_interv_2 = dados_intervalos[dia_semana]['TurnoProdutivoHrEntIntervalo2'].replace(
            year=day.year, month=day.month, day=day.day
        )
    return inicio_trab_dia, fim_trab_dia, ini_interv_1, fim_interv_1, ini_interv_2, fim_interv_2

def get_pause_intervals(datas):
    unique_days = sorted(set(d.date() for d in datas))  # Dias únicos em ordem
    pause_intervals = []

    for day in unique_days:
        dia_semana = retorna_dia_da_semana(day)
        ini_interv_1 = dados_intervalos[dia_semana]['TurnoProdutivoHrSaiIntervalo1'].replace(
            year=day.year, month=day.month, day=day.day
        )
        fim_interv_1 = dados_intervalos[dia_semana]['TurnoProdutivoHrEntIntervalo1'].replace(
            year=day.year, month=day.month, day=day.day
        )
        ini_interv_2 = dados_intervalos[dia_semana]['TurnoProdutivoHrSaiIntervalo2'].replace(
            year=day.year, month=day.month, day=day.day
        )
        fim_interv_2 = dados_intervalos[dia_semana]['TurnoProdutivoHrEntIntervalo2'].replace(
            year=day.year, month=day.month, day=day.day
        )

        # Adicionar intervalos de pausa
        pause_intervals.append([ini_interv_1, fim_interv_1])
        pause_intervals.append([ini_interv_2, fim_interv_2])

    return pause_intervals


def encontrar_intervalos_de_zeros(vetor,datas=[]):
    intervalos_brutos = []
    inicio = None

    for i, valor in enumerate(vetor):
        if valor <= 2:
            if ((i and (datas[i] - datas[i-1]).total_seconds() <= 1 ) or inicio is None):
                if inicio is None:
                    inicio = i  # Marca o início de uma sequência de zeros
            elif inicio is not None:
                add_time = timedelta(milliseconds=500)
                intervalos_brutos.append([datas[inicio] -add_time, datas[i - 1] + add_time])  # Fim da sequência de zeros
                inicio = i

        else:
            if inicio is not None:
                add_time = timedelta(milliseconds=500)
                intervalos_brutos.append([datas[inicio] - add_time, datas[i - 1] + add_time])  # Fim da sequência de zeros
                inicio = None

    # Verifica se há uma sequência de zeros no final do vetor
    if inicio is not None:
        add_time = timedelta(seconds=0)
        if datas[inicio] == datas[len(vetor) - 1]:
            add_time = timedelta(milliseconds=500)
        intervalos_brutos.append([datas[inicio] - add_time, datas[len(vetor) - 1] + add_time])


    ################ REMOVER INTERVALOS EM PAUSAS
    # Passo 2:
    pause_intervals = get_pause_intervals(datas)
    
    # Passo 3: Ajustar os intervalos de zeros em relação às pausas
    intervalos_ajustados = []
    for intervalo in intervalos_brutos:
        ajustados = subtract_intervals(intervalo, pause_intervals)
        intervalos_ajustados.extend(ajustados)

    #intervalos_ajustados = intervalos_brutos

    return intervalos_ajustados

def detectar_intervalos_faltante(datas,porcentagem=[]):
    intervalos_brutos = []
    
    # Iterar sobre o vetor para encontrar os intervalos
    for i in range(1, len(datas)):
        # Calcular a diferença entre a data i e a data anterior (i-1)
        diff = (datas[i] - datas[i-1]).total_seconds()
        
        # Se a diferença for maior que 1 segundo, adicionar ao intervalo
        if diff > 1 and datas[i].day - datas[i-1].day == 0: # or porcentagem[i-1] <= 2 or porcentagem[i] <= 2:
            intervalos_brutos.append((datas[i-1] + timedelta(seconds=0.5), datas[i] - timedelta(seconds=0.5)))

    # Passo 2
    pause_intervals = get_pause_intervals(datas)

    # Passo 3
    intervalos_ajustados = []
    for intervalo in intervalos_brutos:
        ajustados = subtract_intervals(intervalo, pause_intervals)
        intervalos_ajustados.extend(ajustados)

    return intervalos_ajustados

def get_ultimo_do_dia(dia,registros):
    data = dia.date()
    registros_data = registros[registros['date'].dt.date == data]

    # Pegar o registro mais recente (último)
    ultimo_do_dia = registros_data.sort_values(by='date').iloc[-1][0]

    return pd.Timestamp(ultimo_do_dia)

def get_primeiro_do_dia(dia,registros):
    data = dia.date()
    registros_data = registros[registros['date'].dt.date == data]

    # Pegar o registro mais recente (último)
    primeiro_do_dia = registros_data.sort_values(by='date').iloc[0][0]

    return pd.Timestamp(primeiro_do_dia)#pd.Timestamp(primeiro_do_dia)


# Função para encontrar subintervalos onde perOcup > 2
def find_intervals_above_threshold(df, threshold=2):
    occupied_intervals = []
    empty_intervals = []
    in_occupied = False
    in_empty = False
    start_occupied = None
    start_empty = None

    first_processed = False

    for i in range(len(df)):
        
        current_time = df['date'].iloc[i]
        current_perOcup = df['perOcup'].iloc[i]
        # Transição para intervalo ocupado (perOcup > 2)
        last_time = df['date'].iloc[i-1] if i > 0 else current_time
        print(type(last_time),type(current_time),type(timedelta(seconds=1)))
        if current_perOcup > threshold and current_time - last_time <= timedelta(seconds=1):
            
            if not in_occupied:
                print(f'{i} - 1')
                # Fechar intervalo vazio anterior, se existir e atender à duração mínima
                if in_empty and start_empty is not None:
                    #duration = (current_time - start_empty).total_seconds()
                    #if duration > min_duration:
                    empty_intervals.append((start_empty, current_time - timedelta(seconds=0.5)))
                in_empty = False
                in_occupied = True
                start_occupied = current_time - timedelta(seconds=0.5) if i != 0 else current_time
        # Transição para intervalo vazio (perOcup <= 2)
        else:
            
            if in_occupied:
                # Fechar intervalo ocupado

                add_time = timedelta(seconds=-0.5)
                if start_occupied == current_time or i == len(df) - 1: # TRATAR DUPLICATA
                    add_time = timedelta(seconds=0.5)
                occupied_intervals.append((start_occupied, current_time + add_time))
                in_occupied = False
            if not in_empty:
                print(f'{i} - 2')
                in_empty = True
                start_empty = current_time - timedelta(seconds=0.5) if i != 0 else current_time
        #print(current_time - last_time)
    # Fechar o último intervalo, se ainda estiver aberto
    last_time = df['date'].iloc[-1]
    if in_occupied:
        occupied_intervals.append((start_occupied - timedelta(seconds=0.5), last_time))
    elif in_empty and start_empty is not None:
        #duration = (last_time - start_empty).total_seconds(
        empty_intervals.append((start_empty, last_time))

    return occupied_intervals, empty_intervals

def get_intervalos_positivos_saidas(registros):
    datas = registros['date']
    print(registros)

    unique_days = sorted(set(datetime.fromtimestamp(d.timestamp()).date() for d in datas))
    
    all_occupied_intervals = []
    all_empty_intervals = []

    for day in unique_days:
        print(f'PROCESSANDO DIA {day}')
        #get_pause_intervals(dt)
        
        inicio_turno_dia, fim_turno_dia,iInterv1,fInterv1,iInterv2,fInterv2 = get_dados_turno(day)
        inicio_dia = datetime(year=day.year,month=day.month,day=day.day,hour=0,minute=0,second=0)
        fim_dia = datetime(year=day.year,month=day.month,day=day.day,hour=23,minute=59,second=59)
        print(inicio_dia, inicio_turno_dia,iInterv1,fInterv1,iInterv2,fInterv2,fim_turno_dia, fim_dia)

        intervals_of_interest = [
            (inicio_dia, inicio_turno_dia),  # Começo do dia até inicio_turno_dia
            (iInterv1, fInterv1),                                    # iInterv1 até fInterv1
            (iInterv2, fInterv2),                                    # iInterv2 até fInterv2
            (fim_turno_dia, fim_dia)     # fim_turno_dia até fim do dia
        ]
        for start, end in intervals_of_interest:
            # Filtrar dados dentro do intervalo atual
            mask = (registros['date'] >= start) & (registros['date'] <= end)
            df_interval = registros[mask]
            
            if not df_interval.empty:
                # Encontrar subintervalos onde perOcup > 2 e perOcup <= 2
                occupied, empty = find_intervals_above_threshold(df_interval)
                all_occupied_intervals.extend(occupied)
                all_empty_intervals.extend(empty)
            else:
                # Se não há dados no intervalo, verificar duração e adicionar como vazio
                duration = (end - start).total_seconds()
                if duration > 1:
                    all_empty_intervals.append((start, end))
    
    return all_occupied_intervals, all_empty_intervals
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
    #####################


    #Adicionar zeros nas posições desses intervalos desativados
    for x1, x2 in intervalos_desativado:
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

    # Adicionar intervalo 
    for dtini in datas_inicio:
        indice_ini = display_data.index[display_data['date'] == dtini]
        inicio_turno_dia, fim_turno_dia = get_inicio_fim_turno(dtini)

        data_ini = pd.Timestamp(dtini)
        if retorna_dia_da_semana(dtini) != 7 and inicio_turno_dia >= get_primeiro_do_dia(dtini,display_data):
            
            modfy_time = timedelta(seconds=0)
            if get_primeiro_do_dia(dtini,display_data) < inicio_turno_dia:
               modfy_time = timedelta(seconds=0.5)
            data_fim = display_data.loc[indice_ini + 1,'date'].iloc[0] - modfy_time

            new_interval = [data_ini, data_fim]
            #print('\t-1>>>{}'.format(new_interval))
            intervalos_desativado.append(new_interval)
            display_data.loc[len(display_data)] = [data_fim,0]
    
    display_data = display_data.sort_values(by='date').reset_index(drop=True)
    for dtfim in datas_final:
        indice_fim = display_data.index[display_data['date'] == dtfim]
        inicio_turno_dia, fim_turno_dia = get_inicio_fim_turno(dtfim)

        #print(indice_fim,type(indice_fim))
        data_fim = pd.Timestamp(dtfim)
        #print(f'COMPARANDO DIA: {get_ultimo_do_dia(dtfim,display_data)} com {fim_turno_dia}')
        if indice_fim[0] > 0 and get_ultimo_do_dia(dtfim,display_data) <= fim_turno_dia:

            modfy_time = timedelta(seconds=0)
            #print(f'\tULTIMO DO DIA {dtfim} >> {get_ultimo_do_dia(dtfim,display_data)}')
            if get_ultimo_do_dia(dtfim,display_data) > fim_turno_dia:
                modfy_time = timedelta(seconds=0.5)
            data_inicio = display_data.loc[indice_fim - 1,'date'].iloc[0] + modfy_time
            
            new_interval = [data_inicio, data_fim]

            #print('\t-2>>>{}'.format(new_interval))
            if new_interval not in intervalos_desativado:
                intervalos_desativado.append(new_interval)
                display_data.loc[len(display_data)] = [data_inicio,0]
    display_data = display_data.sort_values(by='date').reset_index(drop=True)
    #####################    

    intervalo_ativado_extra, intervalos_inativo_extra = get_intervalos_positivos_saidas(display_data)

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

    # Criar retângulos para intervalos ativados em intervalos
    shapes += [
        {
            "type": "rect",
            "x0": x1, "x1": x2,
            "y0": -100, "y1": 300,
            "fillcolor": "mediumpurple",
            "opacity": 0.3,
            "layer": "below",
            "line": {"width": 0}
        }
        for x1, x2 in intervalo_ativado_extra
    ]

    shapes += [
        {
            "type": "rect",
            "x0": x1, "x1": x2,
            "y0": -100, "y1": 300,
            "fillcolor": "lightblue",
            "opacity": 0.3,
            "layer": "below",
            "line": {"width": 0}
        }
        for x1, x2 in intervalos_inativo_extra
    ]
    

    #print(f'TEMPO INICIO GRAFICO 1 {time() - START}')

    fig.update_xaxes(
        tickmode='auto',  # Modo automático para ajustar os ticks
        dtick=3600000,   # Intervalo de 1 hora (em milissegundos)
        #tickformat='%H:%M',  # Formato de exibição das horas
        rangeslider_visible=True  # Adiciona um rangeslider para facilitar o zoom
    )


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
    #print(f'TEMPO LEVADO GRAFICO 1 {time() - START}')

def create_bar_graph_wrapper(display_data,show_date_start,show_date_end, q):
    fig_bar,min_total,min_trab,percent_trab_geral,min_parado,minutos_ligados = create_bar_graph(display_data,show_date_start,show_date_end)
    q.put((fig_bar,min_total,min_trab,percent_trab_geral,min_parado,minutos_ligados))
    #print(f'TEMPO LEVADO GRAFICO BARRA {time() - START}')

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


#st.json(dados_intervalos)

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
    todos_minutos = pd.date_range(start=periodo_inicio, end=periodo_fim, freq='min')

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

    #st.markdown(f'TEMPO LEVADO DEPOIS QUERY {time() - START}')

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
        

        #st.markdown(f'TEMPO LEVADO ANTES THREAD {time() - START}')
        # Iniciar as threads
        thread_graph.start()
        thread_bar.start()

        # Esperar que ambas terminem
        thread_graph.join()
        thread_bar.join()
        # st.markdown(f'TEMPO LEVADO THREADS {time() - start}')

        fig, percentPerHoraTrab, display_data = q_graph.get()
        fig_bar, min_total, min_trab, percent_trab_geral, min_parado, minutos_ligados = q_bar.get()

        # st.markdown(f'TEMPO LEVADO DEPOIS THREAD {time() - START}')
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
                # Talvez utilizar:
                #  :blue[texto]  :red-background[texto exemplo].
                # Container não se adapta:
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

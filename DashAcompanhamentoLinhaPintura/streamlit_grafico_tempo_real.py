#import mysql.connector
import os
import sys
import copy
import math
import numpy as np
import pandas as pd
import streamlit as st
from queue import Queue
from urllib.parse import quote
from sqlalchemy import create_engine
from time import sleep, time
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from streamlit_autorefresh import st_autorefresh
from dotenv import load_dotenv,find_dotenv
from datetime import datetime, timedelta
from threading import Thread
import streamlit.components.v1 as components

load_dotenv(find_dotenv())

#from streamlit_plotly_mapbox_events import plotly_mapbox_events
st.set_page_config(layout='wide')
TOLERANCIA_ATIVO = float(os.getenv('TOLERANCIA_ATIVO'))
#st.markdown(f'TOLERÂNCIA {TOLERANCIA_ATIVO}')

_component_func = components.declare_component(
    "my_component",
    url="http://localhost:3001",
)

def my_component(fig):
    return _component_func(spec=fig.to_json(), default="",key='Gráfico') # Default para evitar None enquanto carrega


#placeholder_graph = st.empty() # se for utilizar while invés de st_autorefresh

option_theme = st.get_option("theme.base")
# if option_theme == 'dark':
#     text_color = 'white'
# else:    
#     text_color = 'black'

def retorna_dia_da_semana(data): # começando no domingo
    """
    Retorna o dia da semana começando no domingo (domingo = 1, segunda = 2, ..., sábado = 7).
    """
    dia_iso = data.isoweekday()  # Segunda = 1 -> Domingo = 7
    return (dia_iso % 7) + 1

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
        inicio_trab_dia, fim_trab_dia, ini_interv_1, fim_interv_1, ini_interv_2, fim_interv_2 = get_dados_turno(day)
        # Adicionar intervalos de pausa
        start_day = datetime(year=day.year,month=day.month,day=day.day, hour=0,minute=0,second = 0)
        end_day = datetime(year=day.year,month=day.month,day=day.day, hour=23,minute=59,second = 59)

        pause_intervals.append([start_day, inicio_trab_dia])
        if retorna_dia_da_semana(day) != 7:  pause_intervals.append([ini_interv_1, fim_interv_1])
        if retorna_dia_da_semana(day) != 7: pause_intervals.append([ini_interv_2, fim_interv_2])
        if retorna_dia_da_semana(day) != 7: pause_intervals.append([fim_trab_dia, end_day])

        if retorna_dia_da_semana(day) == 7:  pause_intervals.append([fim_interv_1, end_day])

    #print(f'intervalos pausa : {pause_intervals}')

    return pause_intervals

def encontrar_intervalos_ativos(vetor, datas = []):
    intervalos_brutos = []
    inicio = None

    for i, valor in enumerate(vetor):
        if valor > TOLERANCIA_ATIVO:
            # print(f'1) {i}')
            # print(f'{datas[i]} {datas[i-1]}')
            if ((i and (datas[i] - datas[i-1]).total_seconds() <= 1) or inicio is None):
                # print('\t>1.1')
                if inicio is None:
                    # print('\t\t-1.1.1')
                    inicio = i  # Marca o início de uma sequência de zeros
            elif inicio is not None:
                # print('\t>1.2')
                add_time = timedelta(seconds=0.5)
                new_intervalo = [datas[inicio] - add_time, datas[i - 1] + add_time]
                intervalos_brutos.append(new_intervalo)  # Fim da sequência de zeros
                inicio = i

        else:
            # print(f'2) {i}')
            if inicio is not None:
                # print('\t>2.1')
                add_time = timedelta(seconds=0.5)
                new_intervalo = [datas[inicio] - add_time, datas[i - 1] + add_time]
                intervalos_brutos.append(new_intervalo)  # Fim da sequência de zeros
                inicio = None

    # Verifica se há uma sequência de zeros no final do vetor
    if inicio is not None:
        add_time = timedelta(seconds=0.5)
        if datas[inicio] == datas[0]:
             add_time = timedelta(milliseconds=0)
        
        add_time2 = timedelta(seconds=0.5)
        if datas[inicio] == datas[len(vetor) - 1]:
            add_time2 = timedelta(seconds=0)

        intervalos_brutos.append([datas[inicio] - add_time, datas[len(vetor) - 1] + add_time2])

    ################ REMOVER INTERVALOS EM PAUSAS
    # Passo 2:
    pause_intervals = get_pause_intervals(datas)
    
    #print(f'intervalos brutos: {intervalos_brutos}')

    # Passo 3: Ajustar os intervalos de zeros em relação às pausas
    #print(f'intervalos pausados: {pause_intervals}')

    intervalos_ajustados = []
    for intervalo in intervalos_brutos:
        ajustados = subtract_intervals(intervalo, pause_intervals)
        intervalos_ajustados.extend(ajustados)

    #print(f'intervalos ajustados: {intervalos_ajustados}')

    #intervalos_ajustados = intervalos_brutos

    return intervalos_ajustados
 
def encontrar_intervalos_de_zeros(vetor, datas = []):
    intervalos_brutos = []
    inicio = None

    for i, valor in enumerate(vetor):
        if valor <= TOLERANCIA_ATIVO:
            if ((i and (datas[i] - datas[i-1]).total_seconds() <= 1) or inicio is None):
                if inicio is None:
                    #print(f'\tABRINDO INTERVALO EM {i}')
                    inicio = i  # Marca o início de uma sequência de zeros
            elif inicio is not None:
                add_time = timedelta(seconds=0.5)
                intervalos_brutos.append([datas[inicio] - add_time, datas[i - 1] + add_time])  # Fim da sequência de zeros
                #print(f'\tFECHANDO INTERVALO EM {datas[inicio], datas[i - 1]}')
                #print(f'\t - ABRINDO INTERVALO EM {i}')
                inicio = i
        else:
            if inicio is not None:
                add_time = timedelta(seconds=0.5)
                intervalos_brutos.append([datas[inicio] - add_time, datas[i - 1]+ add_time])  # Fim da sequência de zeros
                #print(f'\t - FECHANDO INTERVALO EM {[datas[inicio], datas[i - 1] ]}')
                inicio = None
    # Verifica se há uma sequência de zeros no final do vetor
    if inicio is not None:
        # add_time2 = timedelta(seconds=0)
        # if datas[inicio] == datas[len(vetor) - 1]: # datas[len(vetor) - 1] == ultimo_dt_turno or 
        add_time2 = timedelta(seconds=0.5)
        add_time = timedelta(seconds=0.5)
        intervalos_brutos.append([datas[inicio] - add_time, datas[len(vetor) - 1] + add_time2])


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
 
def detectar_intervalos_faltante(datas, porcentagem = []):
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
    ultimo_do_dia = registros_data.sort_values(by='date').iloc[-1, 0]

    return pd.Timestamp(ultimo_do_dia)

def get_primeiro_do_dia(data,registros):
    #print(data,type(data))
    #print(registros)
    if type(data) is datetime:
        data = data.date()
    registros_data = registros[registros['date'].dt.date == data]

    # Pegar o registro mais recente (último)
    primeiro_do_dia = registros_data.sort_values(by='date').iloc[0, 0]

    return pd.Timestamp(primeiro_do_dia)#pd.Timestamp(primeiro_do_dia)

# Função para encontrar subintervalos onde perOcup > 2
def find_intervals_above_threshold(df):
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
        #Ocupado
        if current_perOcup > TOLERANCIA_ATIVO:
            # print('1) Ocupado')
            # anterior era vazio ou está iniciando agora
            if in_empty or i == 0:
                # print('\t1.1')
                # Fechar intervalo vazio anterior, se existir
                if start_empty is not None:
                    # print('\t\tFechar Vazio')
                    empty_intervals.append((start_empty, current_time - timedelta(seconds=0.5)))
                    #print(f'CRIANDO INTERVALO VAZIO: {(start_empty, current_time - timedelta(seconds=0.5))}\n\tPróximo ínicio = {start_occupied}')
                in_empty = False

                # inicializa novo intervalo ocupado
                in_occupied = True
                start_occupied = current_time - timedelta(seconds=0.5) if i != 0 else current_time
            
            # anterior era ocupado mas está distante
            elif current_time - last_time > timedelta(seconds=1):
                # print('\t1.2')
                # Fechar anterior ocup
                add_time = timedelta(seconds=0.5)
                occupied_intervals.append((start_occupied, last_time + add_time))
                # Criar vazio entre o anterior e atual
                empty_intervals.append((last_time + add_time, current_time - timedelta(seconds=0.5)))
                in_empty = False
                # Começar novo no atual
                in_occupied = True
                start_occupied = current_time - timedelta(seconds=0.5)# if i != 0 else current_time
                
            # são ocupados e estão próximos
            else:
                # Continuar ocupado
                # print('\t1.3')
                pass

        # Está vazio ou desligado
        else:
            # print('2) Vazio')
            # Primeiro registro
            if i == 0:
                # print('\t2.1')
                in_empty = True
                start_empty = current_time
                # Iniciar vazio no ínicio
            # Estava ocupado
            elif in_occupied:
                # print('\t2.2')
                # Fechar anterior
                add_time = timedelta(seconds=0.5)
                occupied_intervals.append((start_occupied, last_time + add_time))
                in_occupied = False

                # Iniciar novo vazio no fim do anterior
                in_empty = True
                start_empty = last_time + timedelta(seconds=0.5)# if i != 0 else last_time
            # Estava vazio
            else:
                # print('\t2.3')
                # Continuar Vazio
                pass
            
            # if not in_empty:
            #     #print(f'{i} - 2')
            #     in_empty = True
            #     start_empty = current_time - timedelta(seconds=0.5) if i != 0 else current_time

    # Fechar o último intervalo, se ainda estiver aberto
    last_time = df['date'].iloc[-1]
    if in_occupied:
        # Estava ocupado?
        # Estava vazio?
        # Faz mais de um segundo desde o anterior ?
        occupied_intervals.append((start_occupied, last_time))
    elif in_empty:
        # Estava ocupado ?
        # Estava vaio ?
        #start_empty is not None
        empty_intervals.append((start_empty, last_time))


    # print(f'\tOCUPADO: {occupied_intervals}')
    # print(f'\tVAZIO: {empty_intervals}')
    # print(f'\tPROCESSADOS: {df}')
    return occupied_intervals, empty_intervals, last_time

def get_intervalos_positivos_saidas(registros):
    datas = registros['date']

    unique_days = sorted(set(datetime.fromtimestamp(d.timestamp()).date() for d in datas))
    #print(f'DATAS UNICAS INTERVALOS POSITIVOS SAIDAS {unique_days}')
    all_occupied_intervals = []
    all_empty_intervals = []
    new_last_values = []
    new_first_values = []

    for day in unique_days:        
        inicio_turno_dia, fim_turno_dia,iInterv1,fInterv1,iInterv2,fInterv2 = get_dados_turno(day)
        inicio_dia = datetime(year=day.year,month=day.month,day=day.day,hour=0,minute=0,second=0)
        fim_dia = datetime(year=day.year,month=day.month,day=day.day,hour=23,minute=59,second=59)

        intervals_of_interest = [(inicio_dia, inicio_turno_dia)]  # Começo do dia até inicio_turno_dia
        if retorna_dia_da_semana(day) != 7:
            intervals_of_interest.append((iInterv1, fInterv1))            # iInterv1 até fInterv1
            intervals_of_interest.append((iInterv2, fInterv2))            # iInterv2 até fInterv2
            intervals_of_interest.append((fim_turno_dia, fim_dia))     # fim_turno_dia até fim do dia
        else:
            intervals_of_interest.append((fInterv1,fim_dia))

        last_value = ''
        for start, end in intervals_of_interest:
            #print(f'COMPARANDO {datetime.now()} >= {end} ({datetime.now() >= end}) and {end > start} ???')
            if datetime.now() >= end and end > start:
                
                # Filtrar dados dentro do intervalo atual
                mask = (registros['date'] >= start) & (registros['date'] <= end)
                df_interval = registros[mask]

                # print(f'De {start} até {end}')
                if not df_interval.empty and get_primeiro_do_dia(day,df_interval) < inicio_turno_dia:
                    #print(f'SALVANDO first: {get_primeiro_do_dia(day,df_interval)}')
                    new_first_values.append(get_primeiro_do_dia(day,df_interval) - timedelta(seconds=0.1))

                ############## CONTINUAR AQUI
                if len(df_interval) > TOLERANCIA_ATIVO:
                    # print(f'DADOS {len(df_interval)} PARA: {start} - {end}')
                    # Encontrar subintervalos onde perOcup > 2 e perOcup <= 2
                    occupied, empty, last_value = find_intervals_above_threshold(df_interval)
                    all_occupied_intervals.extend(occupied)
                    all_empty_intervals.extend(empty)
                elif start != inicio_dia and end != fim_dia:
                    # print(f'VAZIO PARA: {start} - {end}')
                    # Se não há dados no intervalo, verificar duração e adicionar como vazio
                    duration = (end - start).total_seconds()
                    if duration > 1:
                        all_empty_intervals.append((start, end))
        
        new_last_value = ''
        if last_value and last_value > fim_turno_dia:
            new_last_value = last_value + timedelta(seconds=0.1)
            new_last_values.append(new_last_value)

        #print(f'LAST EMPTY PARA {day}: {last_value} > {fim_turno_dia} ? ->{new_last_value}')
    return all_occupied_intervals, all_empty_intervals, new_last_values, new_first_values

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
        if perOcup > TOLERANCIA_ATIVO:
            somatorio += perOcup
            tempo_total += 1
    return somatorio / tempo_total#(minutos_trabalhados * 60)

def adicionar_intervalos(df, intervalos):
    """
    Adiciona intervalos desativados (com perOcup=0) ao DataFrame.
    
    Parâmetros:
    df - DataFrame original com colunas 'date' e 'perOcup'
    intervalos_desativado - Lista de tuplas com intervalos (início, fim)
    
    Retorna:
    Novo DataFrame com os intervalos adicionados, ordenado por data
    """
    # Criar lista para armazenar os novos registros
    novos_registros = []
    datas_existentes = set(df['date'])

    for x1, x2 in intervalos:
        # Adicionar os novos registros se não existirem
        if x1 not in datas_existentes:
            novos_registros.append({'date': x1, 'perOcup': 0})
        if x2 not in datas_existentes:
            novos_registros.append({'date': x2, 'perOcup': 0})
    
    # Criar DataFrame com os novos registros
    if novos_registros:
        df_novos = pd.DataFrame(novos_registros)
        # Concatenar e ordenar
        df_resultado = pd.concat([df, df_novos]).sort_values('date').reset_index(drop=True)
    else:
        df_resultado = df.copy()
    
    return df_resultado

def calcula_barras_intervalos(intervalos):
    interval_bars_x = []
    interval_bars_y = []
    interval_bars_x2 = []
    interval_bars_offset = []
    for i_inax1,i_inax2 in intervalos:
        interval_bars_x.append(i_inax1)
        interval_bars_y.append(100)
        #print(i_inax2,i_inax1,type(i_inax2),type(i_inax1))
        interval_bars_x2.append((max(i_inax2-i_inax1,timedelta(seconds=0))).total_seconds() * 1000 )
        interval_bars_offset.append(0)# (i_inax2-i_inax1).total_seconds() * 0 )
        #interval_bars_y.append(100)
    return pd.DataFrame({'from':interval_bars_x,'to':interval_bars_x2,'size':interval_bars_y,'offset':interval_bars_offset})

def create_graph(display_data,show_date_start,show_date_end):
    print(f'TEMPO INICIO GRAFICO 1 {time() - START}')
    # INTERVALOS DE ZEROS (UNITÁRIOS são 0.5 maiores)
    
    intervalos_inativo = encontrar_intervalos_de_zeros(display_data['perOcup'],display_data['date'])#, display_data['perOcup'])
    print(f'TEMPO INICIO GRAFICO 1 PT - 1 >{time() - START}')
    # INTERVALOS DE PERIODOS SEM DADOS (TODOS SÃO 0.5 anterior ao dado do intervalo)
    intervalos_desativado = detectar_intervalos_faltante(display_data['date'])#, display_data['perOcup'])
    print(f'TEMPO INICIO GRAFICO 1 PT - 2 >{time() - START}')
    #print(f'INTERVALOS DESATIVADOS {intervalos_desativado}')


    intervalos_ativos = encontrar_intervalos_ativos(display_data['perOcup'],display_data['date'])
    print(f'TEMPO INICIO GRAFICO 1 PT 0 >{time() - START}')
    #print('INICIANDO OPERACAO {}'.format(len(display_data['date'])))

    #####################
    # Pegar ínicio e fim do período de cada dia
    #   Pegar dias
    dias_periodo = []

    extra_day = 0
    # adicioanr dia atual se não for domingo e for o último para exibição
    # if DIA_SEM_ATUAL != 1 and show_date_end - timedelta(days=1) == datetime.now().date():
    #     dias_periodo.append(show_date_start - timedelta(days=1))
    # else:
    extra_day = 1

    dias_atras = ((show_date_end - timedelta(days= 1)) - show_date_start).days + extra_day
    
    if dias_atras:
        for i in range(dias_atras):
            process_date = show_date_end - timedelta(days= 1) - timedelta(days= i + 1 - extra_day)
            dia_semana = retorna_dia_da_semana(process_date)
            if dia_semana != 1 and dia_semana != 7:
                dias_periodo.append(process_date)
    #####################


    #print('OPERACAO CONCLUIDA {}'.format(len(display_data['date'])))
    # Converte dados em dataframe

    display_data = pd.DataFrame(display_data)

    

    # print(f'INDEX : {display_data.index}')

    ###############
    #   Pegar periodo
    # print(f'DIAS EXISTENTES: {dias_periodo}')
    datas_inicio = []
    datas_final = []

    print(f'TEMPO INICIO GRAFICO 1 PT 0.1 >{time() - START}')

    # SISTEMA PARA ADICIONAR HORAS VAZIAS
    for dia_trab_periodo in dias_periodo[::-1]:
        # print(f'\tPROCESSANDO {dia_trab_periodo}')
        # result['percent_tempo_inativo_seg'] [hora_falta] = 100

        dia_semana_process = retorna_dia_da_semana(dia_trab_periodo)
        
        if dia_semana_process != 7:
            inicio_trab_dia = dados_intervalos[dia_semana_process]['TurnoProdutivoHrEntrada']
            fim_trab_dia = dados_intervalos[dia_semana_process]['TurnoProdutivoHrSaida']

            # if dia_semana_process == 7: print(f'>> SABADO: {fim_trab_dia}')
            if fim_trab_dia.hour == 0:
                fim_trab_dia = dados_intervalos[dia_semana_process]['TurnoProdutivoHrEntIntervalo2']
                # if dia_semana_process == 7: print(f'\t{fim_trab_dia}')
                if fim_trab_dia.hour == 0:
                    fim_trab_dia = dados_intervalos[dia_semana_process]['TurnoProdutivoHrEntIntervalo1']
                    # if dia_semana_process == 7: print(f'\t\t{fim_trab_dia}')

            # Não adicionar para sábado if dia_semana_process != 7:                
            datas_truncadas = set(display_data['date'].dt.floor('s'))

            data_inicial = datetime(year=dia_trab_periodo.year,month=dia_trab_periodo.month,day=dia_trab_periodo.day).replace(hour=inicio_trab_dia.hour,minute=inicio_trab_dia.minute)
            if data_inicial not in datas_truncadas:
                # print(f'\tADICIONANDO INI {data_inicial}')
                display_data.loc[len(display_data)] = [data_inicial,0]
                datas_inicio.append(data_inicial)

            data_final = datetime(year=dia_trab_periodo.year,month=dia_trab_periodo.month,day=dia_trab_periodo.day).replace(hour=fim_trab_dia.hour,minute=fim_trab_dia.minute)
            if data_final not in datas_truncadas and data_final.date() != datetime.now().date():
                # print(f'\tADICIONANDO FIM {data_final}')
                display_data.loc[len(display_data)] = [data_final,0]
                datas_final.append(data_final)


                # print(f'\tADICIONANDO: {data_inicial} até {data_final}')
            #REPLACE POIS NÃO CONSEGUE CRIAR DATE_RANGE PARA VALORES MAIS ANTIGOS QUE 1677 ?
            #horarios_desejados = pd.date_range(start=inicio_trab_dia.replace(year=2025), end=fim_trab_dia.replace(year=2025) + timedelta(hours=1), freq='h')
                    #print(f'\t\t{dia_hora_trab} /\n\t\t\t {}')
    
    # print(f'LAST VALUE> {display_data.iloc[-1]}')
    
    display_data = display_data.sort_values(by='date').reset_index(drop=True)
    print(f'TEMPO INICIO GRAFICO 1 PT 0.2 >{time() - START}')

    # print(f'\nINTERVALOS DESATIVADOS 1 >>{intervalos_desativado}')
    # Adicionar intervalo para primeiros horários do dia
    for dtini in datas_inicio:
       # print(f'<<<{dtini}>>> ((({get_primeiro_do_dia(dtini,display_data)}))) <<<{get_inicio_fim_turno(dtini)}>>>')
        #inicio_turno_dia, fim_turno_dia = get_inicio_fim_turno(dtini)
 
        if dtini >= get_primeiro_do_dia(dtini,display_data): # retorna_dia_da_semana(dtini) != 7 and 
            indice_ini = display_data.index[display_data['date'] == dtini]
            data_ini = pd.Timestamp(dtini)
            
            data_fim = display_data.loc[indice_ini + 1,'date'].iloc[0]

            inicio_trab_dia, fim_trab_dia, ini_interv_1, fim_interv_1, ini_interv_2, fim_interv_2 = get_dados_turno(data_fim)

            if False and retorna_dia_da_semana(dtini) == 7: fim_trab_dia = ini_interv_1

            modfy_time = timedelta(seconds=0.5)
            if data_fim == ini_interv_1 or data_fim == ini_interv_2 or data_fim == fim_trab_dia:#inicio_turno_dia > get_primeiro_do_dia(dtini,display_data):
                modfy_time = timedelta(seconds=0)
            data_fim = data_fim - modfy_time
            
            #add_time = timedelta(seconds=0.5)
            if data_ini < fim_interv_1 and data_fim > ini_interv_1:
                if data_fim > fim_interv_1:
                    # add_time2 = timedelta(seconds=0.5)
                    # print(f'COMPARANDO {data_fim} == {fim_trab_dia} ?')
                    
                    # add_time2 = timedelta(seconds=0.5)
                    # if data_fim != fim_trab_dia:
                    add_time2 = timedelta(seconds=0)
                    
                    # print(f'\t ADICIONAR {data_fim} == {fim_trab_dia}')
                    new_extra_interval = [fim_interv_1, (data_fim - add_time2).to_pydatetime()]
                    # print(f'\tADICIONANDO INTERVALO 1 {new_extra_interval}')
                    intervalos_desativado.append(new_extra_interval)
                    #add_time = timedelta(seconds=0) # não reduzir tempo final quando estiver cortando por conta do intervalo
                data_fim = pd.Timestamp(ini_interv_1)

            #Talvez implementar intervalo 2

            new_interval = [data_ini.to_pydatetime(), (data_fim).to_pydatetime()]
            if new_interval not in intervalos_desativado:
                # print(f'\tADICIONANDO INTERVALO 2 {new_interval}')
                intervalos_desativado.append(new_interval)

            if not (display_data['date'] == data_fim).any():
                display_data.loc[len(display_data)] = [data_fim,0]
    
    print(f'TEMPO INICIO GRAFICO 1 PT 0.3 >{time() - START}')
    display_data = display_data.sort_values(by='date').reset_index(drop=True)
    # print(f'INTERVALOS DESATIVADOS 2 >>{intervalos_desativado}')
    for dtfim in datas_final:
        # IGNORAR DATA DE HOJE
        if dtfim.date() == datetime.now().date(): continue
        #print(f'COMPARAR DATA FINAL: {dtfim} e {datetime.now().date}')
        indice_fim = display_data.index[display_data['date'] == dtfim]
        inicio_turno_dia, fim_turno_dia = get_inicio_fim_turno(dtfim)
        inicio_trab_dia, fim_trab_dia, ini_interv_1, fim_interv_1, ini_interv_2, fim_interv_2 = get_dados_turno(dtfim)

        if False and retorna_dia_da_semana(dtfim) == 7: fim_turno_dia = dtfim

        #print(indice_fim,type(indice_fim))
        data_fim = pd.Timestamp(dtfim)

        #print(f'COMPARANDO DIA: {get_ultimo_do_dia(dtfim,display_data)} com {fim_turno_dia}')
        #print(f'datas finais: {fim_turno_dia} // {get_ultimo_do_dia(dtfim,display_data)}')
        if indice_fim[0] > 0 and get_ultimo_do_dia(dtfim,display_data) <= fim_turno_dia:
            
            data_inicio = display_data.loc[indice_fim - 1,'date'].iloc[0]

            modfy_time = timedelta(seconds=0)
            #print(f'\tULTIMO DO DIA {dtfim} >> {get_ultimo_do_dia(dtfim,display_data)}')
            if data_inicio != inicio_trab_dia and data_inicio != ini_interv_1 and data_inicio != ini_interv_2: #get_ultimo_do_dia(dtfim,display_data) > fim_turno_dia or :
                modfy_time = timedelta(seconds=0.5)
            data_inicio = data_inicio + modfy_time
            
            inicio_trab_dia, fim_trab_dia, ini_interv_1, fim_interv_1, ini_interv_2, fim_interv_2 = get_dados_turno(data_fim)

            if data_inicio >= ini_interv_1 and data_inicio < fim_interv_1: # TALVEZ TRATAR CASO DE data_fim menor que fim do intervalo 1
                data_inicio = pd.Timestamp(fim_interv_1)
                # POSSÍVEL ERRO: INICIO ANTES E FIM DEPOIS ? Ou já tratado no for anterior ?
            # Talvez implementar intervalo 2

            new_interval = [data_inicio.to_pydatetime(), data_fim.to_pydatetime()]

            if new_interval not in intervalos_desativado:
                #print(f'\tADICIONANDO INTERVALO 3 {new_interval}')
                intervalos_desativado.append(new_interval)
                if not (display_data['date'] == data_inicio).any():# [data_inicio,0] not in display_data:
                    display_data.loc[len(display_data)] = [data_inicio,0]
    # print(f'INTERVALOS DESATIVADOS 3 >>{intervalos_desativado}')
    
    display_data = display_data.sort_values(by='date').reset_index(drop=True)
    #####################
    print(f'TEMPO INICIO GRAFICO 1 PT1 >{time() - START}')
    # intervalos fora dos limites e dentro dos intervalos
    intervalo_ativado_extra, intervalos_inativo_extra, new_last_values, new_first_values = get_intervalos_positivos_saidas(display_data)
    print(f'TEMPO INICIO GRAFICO 1 PT2 >{time() - START}')
    #print(f'new_first_values: {new_first_values}')

    if new_last_values:
        for new_last_value in new_last_values:
            #print(f'Inserir last {new_last_value}')
            display_data.loc[len(display_data)] = [new_last_value,0]
    display_data = display_data.sort_values(by='date').reset_index(drop=True)

    if new_first_values:
        for new_first_value in new_first_values:
            #print(f'Inserir last {new_first_value}')
            display_data.loc[len(display_data)] = [new_first_value,0]
    display_data = display_data.sort_values(by='date').reset_index(drop=True)

    
    display_data = adicionar_intervalos(display_data,intervalos_inativo_extra)

    print(f'TEMPO INICIO GRAFICO 1 PT3 >{time() - START}')
    display_data = adicionar_intervalos(display_data,intervalos_desativado)

    print(f'TEMPO INICIO GRAFICO 1 PT4 >{time() - START}')

        #Adicionar zeros nas posições desses intervalos desativados
    # for x1, x2 in intervalos_desativado:
    #     print('INTERVALOS DESATIVADOS')
    #     first = True
    #     #print(f'PROCESSANDO {x1} e {x2}')
    #     for indt,dt in enumerate(display_data['date']):
    #         if first and dt > x1:
    #             # print(f'\tPROCESSANDO {x1} > que {dt}')
    #             display_data['date'].insert(indt,x1)
    #             display_data['perOcup'].insert(indt,0)
    #             # print(f'\t\tInserirI  em [{indt}]')
    #             first = False
    #         elif not first and dt > x2:
    #             # print(f'\tPROCESSANDO {x2} < {dt}')
    #             display_data['date'].insert(indt,x2)
    #             display_data['perOcup'].insert(indt,0)
    #             # print(f'\t\tInserirF em [{indt}]')
    #             break

    # Já sendo calculado em outra parte do código
    percentPerHoraTrab = calcular_media_porcentagem_por_tempo_trabalhando(display_data)

    # MESCLA INTERVALOS
    #intervalos_inativo = merge_intervals(intervalos_inativo)

    # inicio_trab_dia, fim_trab_dia, ini_interv_1, fim_interv_1, ini_interv_2, fim_interv_2 = get_dados_turno(data_fim)
    # if not (display_data['date'] == ini_interv_1).any():
    #     display_data.loc[len(display_data)] = [ini_interv_1,0]
    # if not (display_data['date'] == fim_trab_dia).any():
    #     display_data.loc[len(display_data)] = [fim_trab_dia,0]
    # if not (display_data['date'] == ini_interv_2).any():
    #     display_data.loc[len(display_data)] = [ini_interv_2,0]
    # if not (display_data['date'] == fim_interv_2).any():
    #     display_data.loc[len(display_data)] = [fim_interv_2,0]

    # Criar gráfico
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=display_data['date'], 
        y=display_data['perOcup'], 
        mode='lines', # +markers
        name='Linha principal'))
    
    df_yellow_bar = calcula_barras_intervalos(intervalos_inativo)
    #print(db_yellow_bar['to']-db_yellow_bar['from'],type(db_yellow_bar['to']-db_yellow_bar['from']))
    
    fig.add_trace(go.Bar(
        x=df_yellow_bar['from'],
        y=df_yellow_bar['size'],
        width=df_yellow_bar['to'],
        offset=df_yellow_bar['offset'],#-db_yellow_bar['from']
        marker_color="yellow",
        hoverinfo='skip',#hovertemplate='<extra></extra>',
        name='Leitura < 2%',
        opacity=0.3
    ))

    #shapes = []
    #Criar retângulos para intervalos inativos
    # shapes = [
    #     {
    #         "type": "rect",
    #         "x0": x1, "x1": x2,
    #         "y0": -100, "y1": 300,
    #         "fillcolor": "yellow",
    #         "opacity": 0.3,
    #         "layer": "between",
    #         #"legendgroup":"Leitura < 2%",
    #         #"name": f'Leitura < 2% {ind}',
    #         #"showlegend": True,#True if ind == 0 else False,
    #         "line": {"width": 0}
    #     }
    #     for ind, (x1, x2) in enumerate(intervalos_inativo)
    # ]
    
    df_red_bar = calcula_barras_intervalos(intervalos_desativado)
    #print(db_yellow_bar['to']-db_yellow_bar['from'],type(db_yellow_bar['to']-db_yellow_bar['from']))
    
    fig.add_trace(go.Bar(
        x=df_red_bar['from'],
        y=df_red_bar['size'],
        width=df_red_bar['to'],
        offset=df_red_bar['offset'],#-db_yellow_bar['from']
        marker_color="red",
        name='Desligado',
        hoverinfo='skip',#hovertemplate='<extra></extra>',
        opacity=0.3
    ))
    #Criar retângulos para intervalos desativado
    # shapes += [
    #     {
    #         "type": "rect",
    #         "x0": x1, "x1": x2,
    #         "y0": -100, "y1": 300,
    #         "fillcolor": "red",
    #         "opacity": 0.3,
    #         "layer": "between",
    #         "line": {"width": 0}
    #     }
    #     for x1, x2 in intervalos_desativado
    # ]

    # # Criar retângulos para intervalos ativados em intervalos pausa
    df_purple_bar = calcula_barras_intervalos(intervalo_ativado_extra)
    #print(db_yellow_bar['to']-db_yellow_bar['from'],type(db_yellow_bar['to']-db_yellow_bar['from']))
    
    fig.add_trace(go.Bar(
        x=df_purple_bar['from'],
        y=df_purple_bar['size'],
        width=df_purple_bar['to'],
        offset=df_purple_bar['offset'],
        marker_color="mediumpurple",
        name='Ativo Extra',
        hoverinfo='skip',#hovertemplate='<extra></extra>',
        opacity=0.3
    ))
    # shapes += [
    #     {
    #         "type": "rect",
    #         "x0": x1, "x1": x2,
    #         "y0": -100, "y1": 300,
    #         "fillcolor": "mediumpurple",
    #         "opacity": 0.3,
    #         "layer": "between",
    #         "line": {"width": 0}
    #     }
    #     for x1, x2 in intervalo_ativado_extra
    # ]

    # # Criar retângulos para intervalos desativados nos intervalos pausa ou fora 
    df_lightblue_bar = calcula_barras_intervalos(intervalos_inativo_extra)
    #print(db_yellow_bar['to']-db_yellow_bar['from'],type(db_yellow_bar['to']-db_yellow_bar['from']))
    
    fig.add_trace(go.Bar(
        x=df_lightblue_bar['from'],
        y=df_lightblue_bar['size'],
        width=df_lightblue_bar['to'],
        offset=df_lightblue_bar['offset'],
        marker_color="lightblue",
        name='Vazio Extra',
        hoverinfo='skip',#hovertemplate='<extra></extra>',
        opacity=0.3
    ))
    # shapes += [
    #     {
    #         "type": "rect",
    #         "x0": x1, "x1": x2,
    #         "y0": -100, "y1": 300,
    #         "fillcolor": "lightblue",
    #         "opacity": 0.3,
    #         "layer": "between",
    #         #"showlegend": True,
    #         "line": {"width": 0}
    #     }
    #     for x1, x2 in intervalos_inativo_extra
    # ]

    # # Criar retângulos para intervalos ativos
    df_green_bar = calcula_barras_intervalos(intervalos_ativos)
    #print(db_yellow_bar['to']-db_yellow_bar['from'],type(db_yellow_bar['to']-db_yellow_bar['from']))
    
    fig.add_trace(go.Bar(
        x=df_green_bar['from'],
        y=df_green_bar['size'],
        width=df_green_bar['to'],
        offset=df_green_bar['offset'],
        marker_color="green",
        name='Ativo',
        hoverinfo='skip',#hovertemplate='<extra></extra>',
        opacity=0.3
    ))
    # shapes += [
    #     {
    #         "type": "rect",
    #         "x0": x1, "x1": x2,
    #         "y0": -100, "y1": 300,
    #         "fillcolor": "green",
    #         "opacity": 0.3,
    #         "layer": "between",
    #         #"showlegend": True,
    #         "line": {"width": 0}
    #     }
    #     for x1, x2 in intervalos_ativos
    # ]

    #LEGENDAS Para simular legenda dos shapes
    # fig.add_trace(go.Scatter(
    #     x= [None],  # Sem dados reais
    #     y= [None],
    #     mode='markers',
    #     marker=dict(color='yellow', size=16),
    #     # legendgroup = "Leitura < 2%",
    #     name='Leitura < 2%',  # Nome da legenda
    #     showlegend=True
    # ))
    # fig.add_trace(go.Scatter(
    #     x= [None],  # Sem dados reais
    #     y= [None],
    #     mode='markers',
    #     marker=dict(color='red', size=16),
    #     name='Desligado',  # Nome da legenda
    #     showlegend=True
    # ))
    # fig.add_trace(go.Scatter(
    #     x= [None],  # Sem dados reais
    #     y= [None],
    #     mode='markers',
    #     marker=dict(color='mediumpurple', size=16),
    #     name='Ativo Extra',  # Nome da legenda
    #     showlegend=True
    # ))
    # fig.add_trace(go.Scatter(
    #     x= [None],  # Sem dados reais
    #     y= [None],
    #     mode='markers',
    #     marker=dict(color='lightblue', size=16),
    #     name='Vazio Extra',  # Nome da legenda
    #     showlegend=True
    # ))
    # fig.add_trace(go.Scatter(
    #     x= [None],  # Sem dados reais
    #     y= [None],
    #     mode='markers',
    #     marker=dict(color='lightgreen', size=16),
    #     name='Ativo',  # Nome da legenda
    #     showlegend=True
    # ))

    # Definir tamanho do y
    fig.update_traces(
        marker_line_width=0
    )
    fig.update_xaxes(
        tickmode='auto',  # Modo automático para ajustar os ticks
        dtick=3600000,   # Intervalo de 1 hora (em milissegundos)
        #tickformat='%H:%M',  # Formato de exibição das horas
        rangeslider_visible=True  # Adiciona um rangeslider para facilitar o zoom
    )
    fig.update_layout(
        uirevision= "keep-zoom", # foo
        #shapes= shapes,
        barmode='overlay',
        showlegend=True,
        yaxis=dict(range=[0, 100]),
        # xaxis=dict(
        #     tickmode="linear",
        #     dtick=3600000/4#, # INTERVALO ENTRE DADOS em ms
        #     #tickformat="%Y-%m-%d %H:%M"
        # ),
        template="plotly_dark" if st.get_option("theme.base") == "dark" else "plotly",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="white" if st.get_option("theme.base") == "dark" else "black"),
        legend=dict(
                font=dict(
                    size=18,  # Tamanho da fonte
                    family="Arial"#,  # Família da fonte (opcional)
                )
            )#,
        #overwrite=True
  # Define o eixo Y de 0 a 50
    )
    return fig, percentPerHoraTrab, display_data

def create_bar_graph(display_data,show_date_start,show_date_end):
    # while True:
    #     try:
    #         print('TENTATIVA CONVERT ({}, {})'.format(len(display_data['date']), len(display_data['perOcup'])))
    minutos_extras = 0
    # minutos_extras += (display_data['date'].iloc[-1] - fim).total_seconds()

    display_data = pd.DataFrame(display_data)
        #     print('SUCESSO')
        #     break
        # except Exception as e:
        #     print('ERRO: {}, {} > {}'.format(len(display_data['date']), len(display_data['perOcup']),e))
        #     continue
        # print(display_data['perOcup'])
        # print('ERRO: dados para dataframe: {} ({}, {}), ERRO {} >>'.format(display_data.keys(), len(display_data['date']), len(display_data['perOcup']), e))

    display_data['ativo'] = display_data['perOcup'] > TOLERANCIA_ATIVO
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
    if DIA_SEM_ATUAL != 1 and show_date_end - timedelta(days=1) == datetime.now().date():
        segundos_atual = 0
        horario_atual = datetime.now()

        inicio = dados_intervalos[DIA_SEM_ATUAL]['TurnoProdutivoHrEntrada'].replace(year=horario_atual.year,month=horario_atual.month,day=horario_atual.day)
        ini_interv_1 = dados_intervalos[DIA_SEM_ATUAL]['TurnoProdutivoHrSaiIntervalo1'].replace(year=horario_atual.year,month=horario_atual.month,day=horario_atual.day)
        fim_interv_1 = dados_intervalos[DIA_SEM_ATUAL]['TurnoProdutivoHrEntIntervalo1'].replace(year=horario_atual.year,month=horario_atual.month,day=horario_atual.day)
        ini_interv_2 = dados_intervalos[DIA_SEM_ATUAL]['TurnoProdutivoHrSaiIntervalo2'].replace(year=horario_atual.year,month=horario_atual.month,day=horario_atual.day)
        fim_interv_2 = dados_intervalos[DIA_SEM_ATUAL]['TurnoProdutivoHrEntIntervalo2'].replace(year=horario_atual.year,month=horario_atual.month,day=horario_atual.day)
        fim = dados_intervalos[DIA_SEM_ATUAL]['TurnoProdutivoHrSaida'].replace(year=horario_atual.year,month=horario_atual.month,day=horario_atual.day)
        
        periodos_trabalho = []
        if ini_interv_1.hour == 0 and ini_interv_2.hour == 0:
            periodos_trabalho.append((inicio,fim))
        if ini_interv_1.hour > 0:
            periodos_trabalho.append((inicio, ini_interv_1))
        if ini_interv_2.hour > 0 and fim_interv_2.hour > 0:
            periodos_trabalho.append((fim_interv_1, ini_interv_2))# Entre os intervalos
            periodos_trabalho.append((fim_interv_2, fim))          # Após o segundo intervalo
        elif fim.hour == 0:
            periodos_trabalho.append((fim_interv_1,fim))
        
        #print(f'ANALISANDO O TEMPO PERIODO: {periodos_trabalho}')

        segundos_atual = sum(
            max(0, (min(horario_atual, end) - start).total_seconds())
            for start, end in periodos_trabalho
        )
        #print(f'\tSEG_ATUAL: {segundos_atual}')

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
        dias_periodo.append(show_date_start)
    else:
        extra_day = 1
    # print(f'MINUTOS TOTAIS: {min_total} min')
    
    dias_atras = ((show_date_end - timedelta(days=1)) - show_date_start).days + extra_day
    
    if dias_atras:
        for i in range(dias_atras):
            process_date = show_date_end - timedelta(days=1) - timedelta(days=i+1 - extra_day)
            dia_semana = retorna_dia_da_semana(process_date)
            
            if dia_semana != 1 and dia_semana != 7:
                dias_periodo.append(process_date)
                #  if dia_semana != 1 and dia_semana != 7: # ignora domingo
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
    result['media_perOcup_ativo'] = grouped['perOcup'].apply(lambda x: x[x > TOLERANCIA_ATIVO].mean())

    # tempo ativo menor que 2 segundos por hora
    result['tempo_ativo_menor_2_seg'] = grouped['perOcup'].apply(lambda x: (x <= TOLERANCIA_ATIVO).sum())
    result['percent_tempo_ativo_menor_2_seg'] = (result['tempo_ativo_menor_2_seg'] / 36) 

    result['tempo_ativo_maior_2_seg'] = grouped['perOcup'].apply(lambda x: (x > TOLERANCIA_ATIVO).sum())
    result['percent_tempo_ativo_maior_2_seg'] = (result['tempo_ativo_maior_2_seg'] / 36) 

    fig_bar = go.Figure() # make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.1) #
    bar_width = 1000000

    #print(f'\n\nDATAS DISPONíveis em horas:{result}\n{type(result)}\n')
    #dias = #pd.unique(result.index.date)#.date.unique()
    #print(f'DIAS EXISTENTES: {dias_periodo}')

    #print(result)

    #print(f'RESULTADO CALCULO BARRAS {result}')
    ########## ADICIONAR HORAS FALTANTES DESDE O ÚLTIMO ATÉ O FINAL ?

    # SISTEMA PARA ADICIONAR HORAS VAZIAS
    for dia_trab_periodo in dias_periodo[::-1]:
        #print(f'\tPROCESSANDO {dia_trab_periodo}')
        # result['percent_tempo_inativo_seg'] [hora_falta] = 100

        dia_semana_process = retorna_dia_da_semana(dia_trab_periodo)
        if dia_semana_process != 7 and dia_semana_process != 1:
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
            #result.iloc[dia_trab_periodo.replace

    #print(f'RESULTADO CALCULO BARRAS {result}')
        ########## ADICIONAR HORAS FALTANTES DESDE O ÚLTIMO ATÉ O FINAL ?

    # média na ocupação ativa
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

    # TEMPO ATIVO
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
        font=dict(color="white" if st.get_option("theme.base") == "dark" else "black"),
        legend=dict(
                font=dict(
                    size=18,  # Tamanho da fonte
                    family="Arial",  # Família da fonte (opcional)
                )
            )
        #barmode='stack'  # Para que as posições definidas sejam respeitadas
    )
    return fig_bar, min_total, min_trab, percent_trab_geral, min_parado, minutos_ligados, minutos_extras

def create_graph_wrapper(display_data,show_date_start,show_date_end, q):
    fig, percentPerHoraTrab, display_data = create_graph(display_data,show_date_start,show_date_end)
    q.put((fig, percentPerHoraTrab, display_data))
    print(f'TEMPO LEVADO GRAFICO 1 {time() - START}')

def create_bar_graph_wrapper(display_data,show_date_start,show_date_end, q):
    fig_bar,min_total,min_trab,percent_trab_geral,min_parado,minutos_ligados,minutos_extras = create_bar_graph(display_data,show_date_start,show_date_end)
    q.put((fig_bar,min_total,min_trab,percent_trab_geral,min_parado,minutos_ligados,minutos_extras))
    print(f'TEMPO LEVADO GRAFICO BARRA {time() - START}')

def change_pause_state(var_pause):
    var_pause = 1 - var_pause
    st.session_state['var_pause'] = var_pause

def show_pause_button():
    var_pause = st.session_state.get('var_pause',1)
    text_pause = f'⏸️ Pausar' if var_pause else f'▶️ RECARREGAR'
    container_pause_bt = st.empty()
    if container_pause_bt.button(text_pause,on_click=change_pause_state,args=(var_pause,)):
        container_pause_bt.empty()

        # CRIAR BotÃO COM TEXTO ATUALIZADO
        text_pause = f'⏸️ Pausar' if not var_pause else f'▶️ RECARREGAR'
        container_pause_bt.button(text_pause,on_click=change_pause_state,args=(1 - var_pause,))
        
# Conectar ao MySQL
# conn = mysql.connector.connect(
#     host="192.168.100.74",
#     user="root",
#     password="f4c1l",
#     database="tegacepp"
# )

######### LOCAL DE TESTE
# host = "192.168.100.30"
# user = "root"
# password = "f4c1l"
# database = "tegacepp_guido"
#########

######### PRECISA DO VPN
host = "192.168.2.6"
user = "tega"
password = "yQPL2}X4K@y5H5@4(wWd"
database = "produx"

conn_args = {
    "user": user,
    "password": password,
    "host":host,
    "database": database
}
############

print(password)
engine = create_engine(f"mysql+mysqlconnector://",connect_args=conn_args)#{user}:{password}@{host}/{database}")# # (f"mysql+mysqlconnector://",connect_args=conn_args) 

# Definir período de análise
datetime.today()
periodo_inicio = "2025-03-14 13:00:00"
periodo_fim = "2025-03-14 14:00:00"

read_date_ini = 'current_date()'
read_date_fin = 'current_date()'

if 'periodo_tempo' not in st.session_state:
    st.session_state['periodo_tempo'] = (datetime.today().date(),datetime.today().date())

read_datas = st.session_state.get('periodo_tempo',(datetime.today().date(),))

# if not isinstance(read_datas,tuple):
#     read_datas = (read_datas,)

if len(read_datas) > 1:
    read_date_ini, read_date_fin = read_datas
else:
    read_date_ini = read_datas[0]
    read_date_fin = read_datas[0]

read_date_ini = read_date_ini
read_date_fin = read_date_fin + timedelta(days=1)

START = time() # DEBUG TEMPO PROCESSAMENTO

###### CONTINUAR >>
# ,TurnoProdutivoHrEntrada,
# TurnoProdutivoHrSaiIntervalo1, TurnoProdutivoHrEntIntervalo1, 
# TurnoProdutivoHrSaiIntervalo2, TurnoProdutivoHrEntIntervalo2,
# TurnoProdutivoHrSaida,
# TurnoProdutivoQtdeMinutosAlmoco

print(f'TEMPO ANTES query 1: {time() - START}')

if not 'turno_semana_dados' in st.session_state:
    query_turno = f'''SELECT 
    TIME_FORMAT(t.TurnoProdutivoHrEntrada, '%H:%i') AS HoraMinuto,
    t.TurnoProdutivoHrEntrada,
    t.TurnoProdutivoHrSaiIntervalo1, t.TurnoProdutivoHrEntIntervalo1, 
    t.TurnoProdutivoHrSaiIntervalo2, t.TurnoProdutivoHrEntIntervalo2,
    t.TurnoProdutivoHrSaida,
    t.TurnoProdutivoQtdeMinutosAlmoco,
    t.TurnoProdutivoDiaSemana
    FROM turnoprodutivo t 
    WHERE TurnoProdutivoTurno = {2}
    group by t.TurnoProdutivoDiaSemana
    order by t.TurnoProdutivoDiaSemana
    limit 7;'''#
        
    #where t.TurnoProdutivoDiaSemana >= dayofweek('{read_date_ini}') AND t.TurnoProdutivoDiaSemana <= dayofweek('{read_date_fin}')

    turno_semana_dados = pd.read_sql(query_turno, engine)
    st.session_state['turno_semana_dados'] = turno_semana_dados
turno_semana_dados = st.session_state.get('turno_semana_dados')
# st.dataframe(turno_semana_dados)
periodo_inicio = turno_semana_dados[turno_semana_dados['TurnoProdutivoDiaSemana'] == retorna_dia_da_semana(datetime.now())]['HoraMinuto']

#st.markdown(minutos_total_dia_semana)

print(f'periodo_inicio>>>> {periodo_inicio}')
print(f'TEMPO ANTES query 2: {time() - START}')

######## CONTINUAR CHECANDO SE TurnoProdutivoQtdeMinutos é atualizado dinâmicamente
if periodo_inicio.empty:
    #st.markdown('Não foi encontrado')
    query_hr_ini = f'''
        select min(l.LinhaPinturaUtilizacaoDtHr) from linhapinturautilizacao l 
        where l.LinhaPinturaUtilizacaoDtHr >= '{read_date_ini}' AND l.LinhaPinturaUtilizacaoDtHr <= '{read_date_fin}' '''
    periodo_inicio = pd.read_sql(query_hr_ini, engine)
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
for index, row in turno_semana_dados.iterrows():
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

    if dia_semana_respectivo == 7:
        tempo_intervalo_geral = (ini_interv_1 - inicio).total_seconds() / 60
    minutos_dia_sem = tempo_intervalo_geral - (tempo_interv1 + tempo_interv2)# - minut_almoco
    if minutos_dia_sem >= 0:
        minutos_total_dia_semana[row['TurnoProdutivoDiaSemana']] = minutos_dia_sem
    else:
        minutos_total_dia_semana[row['TurnoProdutivoDiaSemana']] = 0

#print(f'MINUTOS dos Dias da semana: {minutos_total_dia_semana}')

def display_no_data(key='periodo_tempo'):
    st.markdown(f'''
        ## Sem Dados disponíveis entre {periodo_inicio.strftime('%d/%m/%Y')} até {(periodo_fim -  timedelta(days=1)).strftime('%d/%m/%Y')}
    ''')
    st.date_input('Filtro Leitura',key='periodo_tempo')

#st.json(dados_intervalos)
if periodo_inicio:
    print(f'\nTEMPO INICIALIZANDO: {time() - START}')
    #print(periodo_inicio,type(periodo_inicio))
    #periodo_fim = datetime.combine(read_date_ini, datetime.min.time()).replace(hour=23,minute=59,second=59,microsecond=0)

    # Ajustar o período final se for maior que a hora atual
    # agora = datetime.now()
    # if pd.to_datetime(periodo_fim) > agora:
    #     periodo_fim = agora.strftime("%Y-%m-%d %H:%M:%S")

    # Executar SELECT para pegar os registros reais
    #if read_date_fin - read_date_ini > timedelta(days=1):
    periodo_inicio = read_date_ini
    periodo_fim = read_date_fin

    print(F'\nPERIODO FIM INICIAL {periodo_fim}')

    if periodo_inicio > datetime.now().date():
        periodo_inicio = datetime.now().date()
    if periodo_fim > datetime.now().date() + timedelta(days=1):
        periodo_fim = datetime.now().date() + timedelta(days=1)

    print(F'PERIODO FIM APÓS {periodo_fim}\n')

    if 'last_read' not in st.session_state or st.session_state.get('last_dates',[]) != [periodo_inicio, periodo_fim]: 
        print('OP Q1')
        query = f"""
            SELECT LinhaPinturaUtilizacaoDtHr, LinhaPinturaUtilizacaoPerOcup, LinhaPinturaUtilizacaoParada
            FROM linhapinturautilizacao
            WHERE LinhaPinturaUtilizacaoDtHr BETWEEN '{periodo_inicio}' AND '{periodo_fim}'
            GROUP BY LinhaPinturaUtilizacaoDtHr
            ORDER BY LinhaPinturaUtilizacaoDtHr;
        """
        #print(f'TEMPO PERIODO INICIAL {periodo_inicio}')

        last_read = pd.read_sql(query, engine)
        if not last_read.empty:
            st.session_state['last_read'] = last_read
            #print(last_read['LinhaPinturaUtilizacaoDtHr'].iloc[-1])
            st.session_state['last_dates'] = [periodo_inicio, periodo_fim]
            st.session_state['last_read_time'] = last_read['LinhaPinturaUtilizacaoDtHr'].iloc[-1]
        else:
            print(f'QUERY RETORNOU VAZIO >> {query}')
    else:
        print('OP Q2')
        print(f'TEMPO ANTES CARREGAR: {time() - START}')
        last_read = st.session_state.get('last_read')
    
    
    print(f'\nTEMPO QUERY 3: {time() - START}')

    # Fechar conexão
    # Converter para datetime
    last_read["LinhaPinturaUtilizacaoDtHr"] = pd.to_datetime(last_read["LinhaPinturaUtilizacaoDtHr"])

    # Criar range completo de minutos
    todos_minutos = pd.date_range(start= periodo_inicio, end= periodo_fim, freq='min')

    # Criar DataFrame com todos os minutos
    df_todos = pd.DataFrame({"LinhaPinturaUtilizacaoDtHr": todos_minutos})

    # Fazer merge para preencher minutos sem registro como NaN
    df_final = df_todos.merge(last_read, on="LinhaPinturaUtilizacaoDtHr", how="left")

    minutos_parados = (df_final["LinhaPinturaUtilizacaoPerOcup"] <= TOLERANCIA_ATIVO).sum()
    
    # Preencher valores NaN em 'LinhaPinturaUtilizacaoParada' com 1 (sem registro = parada)
    #print('ANTES {}'.format(df_final["LinhaPinturaUtilizacaoParada"]))
    df_final["LinhaPinturaUtilizacaoParada"] = df_final["LinhaPinturaUtilizacaoParada"].infer_objects(copy=False).fillna(1)
    #print('DEPOIS {}'.format(df_final["LinhaPinturaUtilizacaoParada"]))

    # Contar minutos trabalhados e parados
    minutos_trabalhados = (df_final["LinhaPinturaUtilizacaoParada"] == 0).sum()
    
    # minutos_parados = len(df_final["LinhaPinturaUtilizacaoParada"])

    # Converter para dicionário de listas
    display_data = {'date': last_read['LinhaPinturaUtilizacaoDtHr'].to_list(),'perOcup': last_read['LinhaPinturaUtilizacaoPerOcup'].to_list()}

    engine.dispose()

    #################### INSERIDOS PARA TESTES
    #   Só funcionam no final do dia marcado pois não estou reordenando perOcup
            # ANTES
    # display_data['date'].append(datetime(year=2025,month=3,day=22,hour=6,minute=59,second=51))
    # display_data['perOcup'].append(20)
    # display_data['date'].append(datetime(year=2025,month=3,day=22,hour=6,minute=59,second=54))
    # display_data['perOcup'].append(50)
    # display_data['date'].append(datetime(year=2025,month=3,day=22,hour=6,minute=59,second=55))
    # display_data['perOcup'].append(20)
    # display_data['date'].append(datetime(year=2025,month=3,day=22,hour=6,minute=59,second=59))
    # display_data['perOcup'].append(2)
            # DURANTE
    # display_data['date'].append(datetime(year=2025,month=3,day=22,hour=7,minute=59,second=56))
    # display_data['perOcup'].append(2)
    # display_data['date'].append(datetime(year=2025,month=3,day=22,hour=7,minute=59,second=58))
    # display_data['perOcup'].append(60)
            # DEPOIS
    # display_data['date'].append(datetime(year=2025,month=3,day=22,hour=8,minute=0,second=1))
    # display_data['perOcup'].append(60)
    # display_data['date'].append(datetime(year=2025,month=3,day=22,hour=8,minute=59,second=1))
    # display_data['perOcup'].append(60)
    # display_data['date'].append(datetime(year=2025,month=3,day=22,hour=9,minute=0,second=2))
    # display_data['perOcup'].append(50)
    # display_data['date'].append(datetime(year=2025,month=3,day=22,hour=9,minute=0,second=3))
    # display_data['perOcup'].append(2)
    # display_data['date'].append(datetime(year=2025,month=3,day=22,hour=9,minute=0,second=15))
    # display_data['perOcup'].append(10)
    # display_data['date'].append(datetime(year=2025,month=3,day=22,hour=9,minute=0,second=20))
    # display_data['perOcup'].append(5)
    # display_data['date'].append(datetime(year=2025,month=3,day=22,hour=9,minute=0,second=21))
    # display_data['perOcup'].append(2)

    # display_data['date'].append(datetime(year=2025,month=3,day=12,hour=17,minute=30,second=5))
    # display_data['perOcup'].append(2)
    # display_data['date'].append(datetime(year=2025,month=3,day=12,hour=17,minute=30,second=6))
    # display_data['perOcup'].append(2)

    #display_data['date'] = sorted(display_data['date'])
    ####################
    media_ocupacao = 0

    if display_data['date']:
        q_graph = Queue()
        q_bar = Queue()

        media_ocupacao = sum([x for x in display_data['perOcup'] if x > TOLERANCIA_ATIVO]) / len([x for x in display_data['perOcup'] if x > TOLERANCIA_ATIVO])
        #st.markdown(media_ocupacao)

        print(f'TEMPO ANTES CÓPIA {time() - START}')
        copia_dp_data = copy.deepcopy(display_data)
        
        print(f'TEMPO ANTES THREAD 1 {time() - START}')
        thread_bar = Thread(target=create_bar_graph_wrapper, args=(copia_dp_data,periodo_inicio,periodo_fim, q_bar))
        
        print(f'TEMPO ANTES THREAD 2 {time() - START}')
        thread_graph = Thread(target=create_graph_wrapper, args=(display_data,periodo_inicio,periodo_fim, q_graph))

        same_data = st.session_state.get('last_process',[]) == display_data
        st.session_state['last_process'] = display_data
        #st.markdown(f'TEMPO LEVADO ANTES THREAD {time() - START}')
        #st.markdown(f'TEMPO LEVADO ANTES THREAD {time() - START}')
        # Iniciar as threads
        if not same_data or 'fig1' not in st.session_state or 'figbar' not in st.session_state:
            thread_graph.start()
            thread_bar.start()

            # Esperar que ambas terminem
            thread_graph.join()
            thread_bar.join()
            # st.markdown(f'TEMPO LEVADO THREADS {time() - START}')
            print((f'TEMPO LEVADO THREADS {time() - START}'))

            fig, percentPerHoraTrab, display_data = q_graph.get()
            fig_bar, min_total, min_trab, percent_trab_geral, min_parado, minutos_ligados, minutos_extras = q_bar.get()

            st.session_state['fig1'] = (fig, percentPerHoraTrab, display_data)
            st.session_state['figbar'] = (fig_bar, min_total, min_trab, percent_trab_geral, min_parado, minutos_ligados, minutos_extras)
        else:
            fig, percentPerHoraTrab, display_data = st.session_state.get('fig1')
            fig_bar, min_total, min_trab, percent_trab_geral, min_parado, minutos_ligados, minutos_extras = st.session_state.get('figbar')
        last_layout = st.session_state.get('layout',[])
        print(f'LAYOUT ?? {last_layout}')
        if last_layout: # not same_data and 
            last_value_y = display_data['date'].iloc[-1]
            print(f'xaxis: {last_layout.xaxis.range} <{last_layout.xaxis.range[1]} > {last_value_y}> ({type(last_layout.xaxis.range[1])} > {type(last_value_y)})')
            if pd.Timestamp(last_layout.xaxis.range[1]) > last_value_y:
                # ativar de novo automaticamente atualizar
                #st.session_state['show_last'] = True
                last_layout.xaxis.range = (last_layout.xaxis.range[0], last_value_y)
            else:
                #st.session_state['show_last'] = False
                pass
            fig.update_layout(
                xaxis=dict(range=last_layout.xaxis.range),
            )
        else:
            print('Sem Layout')

        # st.markdown(f'TEMPO LEVADO DEPOIS THREAD {time() - START}')
        #st.markdown(f'Tempo Processamento: {time() - START}')
    else:
        fig, percentPerHoraTrab = None, 0
        fig_bar, min_total, min_trab, percent_trab_geral, min_parado, minutos_ligados, minutos_extras = (None,0,0,0,0,0,0)
        #display_no_data()

    show_pause_button()
    #count = st_autorefresh(interval= 5 * 1 * 1000, key="dataframerefresh")

    col1,col2 = st.columns([2,10])
    with col1:
        #if min_total is not None and minutos_parados is not None  and minutos_trabalhados is not None: 
        minutos_desativados = int(min_total - minutos_parados - minutos_trabalhados)
        minutos_ligados = int(min_total - minutos_desativados)
        minutos_parados += minutos_desativados

        #minutos_parados = int((datetime.now() - datetime.today().replace(hour=5,minute=0,second=0)).total_seconds() / 60)
        with st.container(border=True):
            st.markdown('**Total de Tempo:**')
            #minutos_total = len(df_final[df_final['LinhaPinturaUtilizacaoParada'] == 0])
            # old_total_min = len(df_final)
            st.markdown(f"<h1 style='text-align: center;'>{math.floor(min_total/60)}:{int(min_total % 60):02}</h1>",unsafe_allow_html=True)
            #:red[Texto Exemplo]
        with st.container(border=True):
            st.markdown('**Tempo Trabalhando:**')
            st.markdown(f"<h1 style='text-align: center;'>{math.floor(minutos_trabalhados / 60)}:{minutos_trabalhados % 60:02}</h1>",unsafe_allow_html=True)
            #minutos_parados -= minutos_trabalhados
        with st.container(border=True):
            st.markdown('**Ocupação média durante Tempo trabalhando:**')
            # percentPerHoraTrab media_ocupacao 
            st.markdown(f"<h1 style='text-align: center;'>{media_ocupacao:.2f}%</h1>",unsafe_allow_html=True)
        with st.container(border=True):
            st.markdown('**Tempo Parado:**')
            st.markdown(f"<h1 style='text-align: center;'>{math.floor(minutos_parados / 60)}:{minutos_parados % 60:02}</h1>",unsafe_allow_html=True)
        with st.container(border=True):
            st.markdown('**Tempo Ligado:**')
            #st.markdown(f'{min_total} - {minutos_desativados}')
            
            st.markdown(f"<h1 style='text-align: center;'>{math.floor(minutos_ligados / 60)}:{minutos_ligados % 60:02}</h1>",unsafe_allow_html=True)
        with st.container(border=True):
            st.markdown('**Tempo Desativado:**') # color: red; background-color:powderblue;
            #color: red; background-color:lightgray;
            st.markdown(f"<h1 style='text-align: center;'>{math.floor(minutos_desativados / 60)}:{minutos_desativados % 60:02}</h1>",unsafe_allow_html=True)
        with st.container(border=True):
            st.markdown('**Tempo Excedente**') # minutos_extras
            st.markdown(f"<h1 style='text-align: center;'>{math.floor(minutos_extras / 60)}:{minutos_extras % 60:02}</h1>",unsafe_allow_html=True)
            # Talvez utilizar:
            #  :blue[texto]  :red-background[texto exemplo].
            # Container não se adapta:
            # f'''
            # <div style="width: 300px; padding: 20px; border: 2px solid black; background-color: powderblue; text-align: center;">
            #     <h1 style="color: red;">Olá</h1>
            #     <p style="color: white; font-size: 18px;">Mundo</p>
            # </div>''',unsafe_allow_html=True)
    with col2:
        st.markdown('## Indicativo de uso da linha de pintura da esteira no dia {} até {}'.format(periodo_inicio.strftime('%d/%m/%Y'),(periodo_fim-timedelta(days=1)).strftime('%d/%m/%Y')))
        st.date_input('Filtro de Data de Leitura',key='periodo_tempo')

        if fig is None: # MOSTRAR FIGURA VAZIA
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=[periodo_inicio, periodo_fim], 
                y=[0, 0], 
                mode='markers', #
                name='Linha principal'))
            fig.update_layout(
                showlegend=True,
                yaxis=dict(range=[0, 100]),
                # xaxis=dict(
                #     tickmode="linear",
                #     dtick=3600000/4#, # INTERVALO ENTRE DADOS em ms
                #     #tickformat="%Y-%m-%d %H:%M"
                # ),
                template="plotly_dark" if st.get_option("theme.base") == "dark" else "plotly",
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font=dict(color="white" if st.get_option("theme.base") == "dark" else "black"),
                legend=dict(
                        font=dict(
                            size=18,  # Tamanho da fonte
                            family="Arial",  # Família da fonte (opcional)
                        )
                    )
        # Define o eixo Y de 0 a 50
            )
        
        with st.container(border=True):
            #graf_event = plotly_mapbox_events(fig, click_event=True, select_event=True, hover_event=True, relayout_event=True)#, relayout_event=True)
            #st.markdown(f'EVENTO: {graf_event}')
            st.markdown(f'Tempo ANTES gráfico 1: {time() - START}')

            v = my_component(fig)
            st.markdown(f'RECEBIDO> {v}')
            if v and v != 'reset':
                new_layout = go.Layout(
                    # yaxis=dict(
                    #     range=[0, 100]
                    # ),
                    xaxis=dict(
                        range=[v[0], v[1]]
                    )
                )

                if 'layout' not in st.session_state or new_layout != st.session_state.get('layout'):
                    print(f'LAYOUT SALVAR {new_layout}')
                    st.session_state['layout'] = new_layout
                    st.rerun()
                else:
                    print('Não salvar layout {} or {}'.format('layout' not in st.session_state, new_layout != st.session_state.get('layout')))
                    print(st.session_state.get('layout'))
            else:
                if 'layout' in st.session_state:
                    del st.session_state['layout']
                    st.rerun()
            st.markdown(f'RECEBIDO1 > {v}')

            st.plotly_chart(fig,key='gráfico')
        #st.markdown(f'Tempo Carregar gráfico 1: {time() - START}')
        if fig_bar is None: # MOSTRAR FIG BARRA VAZIA
            fig_bar = go.Figure()
            
            fig_bar.add_trace(go.Bar(
                x= [periodo_inicio, periodo_fim],
                y= [0, 0],
                base=0,
                name='Sem dados',
                #marker_color='blue',
                #offset=-1000000,
                #width=bar_width*3,
                #customdata=[abs(y) for y in -result['media_perOcup_ativo']],
                #hovertemplate='%{customdata:.0f} % (%{x})   <extra></extra>',  # Exibe o valor sem o sinal negativo
                opacity=0.3#,
                
            ))
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
                    font=dict(color="white" if st.get_option("theme.base") == "dark" else "black"),
                    legend=dict(
                            font=dict(
                                size=18,  # Tamanho da fonte
                                family="Arial",  # Família da fonte (opcional)
                            )
                        )
                    #barmode='stack'  # Para que as posições definidas sejam respeitadas
                )
        with st.container(border=True):
            st.plotly_chart(fig_bar,key='gráfico_bar')

        #st.markdown(f'Tempo Carregar gráfico Barras: {time() - START}')
        #color: {text_color};
        # TEMPO PARA REFRESH DO CÓDIGO Número de * segundos * mili
        # st.markdown(f'Contador Updates: {count}')
        
        st.markdown(f"<p style='text-align: right; '>Última consulta feita em {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}</h1>", unsafe_allow_html=True)
            
        # st.markdown(f'TEMPO LEVADO TOTAL {time() - start}')
else:
    display_no_data()


# RECARREGAR CASO NÃO ESTEJA PAUSADO
print(f'TIPOS: {type(periodo_fim)} e {type(periodo_inicio)}\n\t {periodo_inicio} -> {periodo_fim-timedelta(days=1)} /  {datetime.now().date()}')
if st.session_state.get('var_pause',1) and (datetime.now().date() <= periodo_fim-timedelta(days=1) or datetime.now().date() == periodo_inicio):
    count = st_autorefresh(interval= 5 * 1 * 1000, key="dataframerefresh")
    st.markdown('RECARREGAR')
else:
    st.markdown('PAUSADO')


if 'last_read' not in st.session_state or st.session_state.get('last_dates',[]) != [periodo_inicio, periodo_fim]: 
        query = f"""
            SELECT LinhaPinturaUtilizacaoDtHr, LinhaPinturaUtilizacaoPerOcup, LinhaPinturaUtilizacaoParada
            FROM linhapinturautilizacao
            WHERE LinhaPinturaUtilizacaoDtHr BETWEEN '{periodo_inicio}' AND '{periodo_fim}'
            GROUP BY LinhaPinturaUtilizacaoDtHr
            ORDER BY LinhaPinturaUtilizacaoDtHr;
        """
        #print(f'TEMPO PERIODO INICIAL {periodo_inicio}')

        last_read = pd.read_sql(query, engine)
        if not last_read.empty:
            st.session_state['last_read'] = last_read
            print(last_read['LinhaPinturaUtilizacaoDtHr'].iloc[-1])
            st.session_state['last_dates'] = [periodo_inicio, periodo_fim]
            st.session_state['last_read_time'] = last_read['LinhaPinturaUtilizacaoDtHr'].iloc[-1]
elif periodo_inicio <= datetime.now().date() <= periodo_fim - timedelta(days=1):
        print(f'TEMPO ANTES CARREGAR: {time() - START}')
        last_read = st.session_state.get('last_read')
        last_read_time = st.session_state.get('last_read_time')

        print(f'LAST READ ANTERIOR: {last_read_time} {type(last_read_time)}')

        print(f'TEMPO ANTES QUERY 3: {time() - START}')
        query = f"""
            SELECT LinhaPinturaUtilizacaoDtHr, LinhaPinturaUtilizacaoPerOcup, LinhaPinturaUtilizacaoParada
            FROM linhapinturautilizacao
            WHERE LinhaPinturaUtilizacaoDtHr > '{last_read_time}'
            ORDER BY LinhaPinturaUtilizacaoDtHr ASC
            LIMIT 100;
        """ # GROUP BY LinhaPinturaUtilizacaoDtHr
        newest_read = pd.read_sql(query, engine)
        
        #print(f'NOVA READ {newest_read}')
        if not newest_read.empty:
            last_read = pd.concat([last_read, newest_read], ignore_index=True)

        st.session_state['last_read'] = last_read
        st.session_state['last_read_time'] = last_read['LinhaPinturaUtilizacaoDtHr'].iloc[-1]

print('\nCONCLUÍDO\n')
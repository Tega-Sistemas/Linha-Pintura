import os
import sys
import copy
import math
import random
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
#from streamlit_theme import st_theme

load_dotenv(find_dotenv())
st.set_page_config(layout='wide')
espaco_vazio = st.empty()

# ESCONDER HEADER/BARRA do streamlit e link âncora dos títulos, também diminuído tamanho do container onde fica o site
with espaco_vazio:
    #theme_info = st_theme(adjust=False)
    st.markdown('''<style>
                header {visibility: hidden;}
                .block-container {
                    padding-top: 1rem;
                    padding-bottom: 0rem;
                    padding-left: 5rem;
                    padding-right: 5rem;
                }
                [data-testid='stHeaderActionElements'] {display: none;}
                </style>''',
                unsafe_allow_html=True) 

# Checar se estava processando dia atual mas passou para outra data

#print('ANALISANDO SE HOJE ESTÁ INCLUSOP E DATA MUDOU:','periodo_tempo' in st.session_state, st.session_state.get('processing_today',False), st.session_state.get('last_dates',()), st.session_state.get('periodo_tempo',(0)),datetime.today().date())
if 'periodo_tempo' in st.session_state and st.session_state.get('processing_today',False) and st.session_state.get('last_dates',()) == st.session_state.get('periodo_tempo',(0)) and st.session_state.get('periodo_tempo',(0))[-1] != datetime.today().date():
    print('COMPARANDO DATAS PARA RESET AO MUDAR DIA {} com {}'.format(st.session_state.get('periodo_tempo')[-1],datetime.today().date()))
    st.session_state['periodo_tempo'] = (st.session_state['periodo_tempo'][0], datetime.today().date())

# Sistema para exibir e fechar licenças
if st.session_state.get('show_licenses',False):
    fechar1 = st.button('FECHAR',key='bt1_fecharlicenca')
    with open('licenses/plotly_mit.txt','r',encoding='utf-8') as f:
        licenca_plotly =f.read()
    with open('licenses/streamlit_apache2.txt','r',encoding='utf-8') as f:
        licenca_streamlit =f.read()

    st.markdown(f'''# LICENÇAS
                
### PLOTLY: [LINK](https://github.com/plotly/plotly.py/blob/main/LICENSE.txt)
''')
    st.code(licenca_plotly, language='text')
    st.markdown('### STREAMLIT: [LINK](https://github.com/streamlit/streamlit/blob/develop/LICENSE)')
    st.code(licenca_streamlit, language='text')

    if st.button('FECHAR',key='bt2_fecharlicenca') or fechar1:
        st.session_state['show_licenses'] = False
        st.rerun()
    else:
        st.stop()

# Porcentagem para considerar esteira como em uso ou não
TOLERANCIA_ATIVO = float(os.getenv('TOLERANCIA_ATIVO'))

# Criar componente customizado
parent_dir = os.path.dirname(os.path.abspath(__file__))
build_dir = os.path.join(parent_dir, "build")
_component_func = components.declare_component(
    "my_component",
    path=build_dir
)
def reactGraph(fig, change_flag, rangeslider=True, key='Gráfico'):
    # print(f'ENVIANDO FLAG MUDANÇA {change_flag}')
    return _component_func(spec=fig.to_json(), change_flag=change_flag, rangeslider=rangeslider, default="", key=key) # Default para evitar None enquanto carrega

def retorna_dia_da_semana(data): 
    """Retorna o dia da semana começando no domingo (domingo = 1, segunda = 2, ..., sábado = 7)."""
    dia_iso = data.isoweekday()
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
    inicio_trab_dia = dados_intervalos[dia_semana]['TurnoProdutivoHrEntrada'].replace(year=day.year, month=day.month, day=day.day)
    fim_trab_dia = dados_intervalos[dia_semana]['TurnoProdutivoHrSaida'].replace(year=day.year, month=day.month, day=day.day)
    return inicio_trab_dia, fim_trab_dia

def get_dados_turno(day):
    dia_semana = retorna_dia_da_semana(day)
    inicio_trab_dia = dados_intervalos[dia_semana]['TurnoProdutivoHrEntrada'].replace(year=day.year, month=day.month, day=day.day)
    fim_trab_dia = dados_intervalos[dia_semana]['TurnoProdutivoHrSaida'].replace(year=day.year, month=day.month, day=day.day)
    ini_interv_1 = dados_intervalos[dia_semana]['TurnoProdutivoHrSaiIntervalo1'].replace(year=day.year, month=day.month, day=day.day)
    fim_interv_1 = dados_intervalos[dia_semana]['TurnoProdutivoHrEntIntervalo1'].replace(year=day.year, month=day.month, day=day.day)
    ini_interv_2 = dados_intervalos[dia_semana]['TurnoProdutivoHrSaiIntervalo2'].replace(year=day.year, month=day.month, day=day.day)
    fim_interv_2 = dados_intervalos[dia_semana]['TurnoProdutivoHrEntIntervalo2'].replace(year=day.year, month=day.month, day=day.day)
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
        # Não é sábado
        if retorna_dia_da_semana(day) != 7:  
            pause_intervals.append([ini_interv_1, fim_interv_1])
            pause_intervals.append([ini_interv_2, fim_interv_2])
            pause_intervals.append([fim_trab_dia, end_day])

        # Sábado
        else:
            pause_intervals.append([fim_interv_1, end_day])
    return pause_intervals

def encontrar_intervalos_ativos(vetor, datas = [], new_data = False):
    intervalos_brutos = []
    inicio = None

    for i, valor in enumerate(vetor):
        if valor > TOLERANCIA_ATIVO:
            if ((i and (datas[i] - datas[i-1]).total_seconds() <= 1) or inicio is None):
                if inicio is None:
                    inicio = i  # Marca o início de uma sequência de zeros
            elif inicio is not None:
                add_time = timedelta(seconds=0.5)
                new_intervalo = [datas[inicio] - add_time, datas[i - 1] + add_time]
                intervalos_brutos.append(new_intervalo)  # Fim da sequência de zeros
                inicio = i

        else:
            if inicio is not None:
                add_time = timedelta(seconds=0.5)
                new_intervalo = [datas[inicio] - add_time, datas[i - 1] + add_time]
                intervalos_brutos.append(new_intervalo)  # Fim da sequência de zeros
                inicio = None

    # Verifica se há uma sequência de zeros no final do vetor
    if inicio is not None:
        add_time = timedelta(seconds=0.5)
        if datas[inicio] == datas[0] and not new_data:
             add_time = timedelta(milliseconds=0)
        
        add_time2 = timedelta(seconds=0.5)
        if datas[inicio] == datas[len(vetor) - 1] and not new_data:
            add_time2 = timedelta(seconds=0)

        intervalos_brutos.append([datas[inicio] - add_time, datas[len(vetor) - 1] + add_time2])

    # REMOVER INTERVALOS EM PAUSAS
    pause_intervals = get_pause_intervals(datas)

    # Ajustar os intervalos de zeros em relação às pausas
    intervalos_ajustados = []
    for intervalo in intervalos_brutos:
        ajustados = subtract_intervals(intervalo, pause_intervals)
        intervalos_ajustados.extend(ajustados)

    return intervalos_ajustados
 
def encontrar_intervalos_de_zeros(vetor, datas = []):
    intervalos_brutos = []
    inicio = None

    for i, valor in enumerate(vetor):
        if valor <= TOLERANCIA_ATIVO:
            if ((i and (datas[i] - datas[i-1]).total_seconds() <= 1) or inicio is None):
                if inicio is None:
                    inicio = i  # Marca o início de uma sequência de zeros
            elif inicio is not None:
                add_time = timedelta(seconds=0.5)
                intervalos_brutos.append([datas[inicio] - add_time, datas[i - 1] + add_time])  # Fim da sequência de zeros
                inicio = i
        else:
            if inicio is not None:
                add_time = timedelta(seconds=0.5)
                intervalos_brutos.append([datas[inicio] - add_time, datas[i - 1]+ add_time])  # Fim da sequência de zeros
                inicio = None

    # Verifica se há uma sequência de zeros no final do vetor
    if inicio is not None:
        add_time2 = timedelta(seconds=0.5)
        add_time = timedelta(seconds=0.5)
        intervalos_brutos.append([datas[inicio] - add_time, datas[len(vetor) - 1] + add_time2])

    # REMOVER INTERVALOS EM PAUSAS
    pause_intervals = get_pause_intervals(datas)
    
    # Ajustar os intervalos de zeros em relação às pausas
    intervalos_ajustados = []
    for intervalo in intervalos_brutos:
        ajustados = subtract_intervals(intervalo, pause_intervals)
        intervalos_ajustados.extend(ajustados)

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

    # REMOVER INTERVALOS EM PAUSAS
    pause_intervals = get_pause_intervals(datas)

    # Ajustar os intervalos de zeros em relação às pausas
    intervalos_ajustados = []
    for intervalo in intervalos_brutos:
        ajustados = subtract_intervals(intervalo, pause_intervals)
        intervalos_ajustados.extend(ajustados)

    return intervalos_ajustados

# Pegar o registro mais recente
def get_ultimo_do_dia(data,registros):
    if type(data) is datetime: data = data.date()
    registros_data = registros[registros['date'].dt.date == data]
    ultimo_do_dia = registros_data.sort_values(by='date').iloc[-1, 0]
    return pd.Timestamp(ultimo_do_dia)

# Pegar o registro mais antigo do dia
def get_primeiro_do_dia(data,registros):
    if type(data) is datetime: data = data.date()
    registros_data = registros[registros['date'].dt.date == data]
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

    for i in range(len(df)):
        current_time = df['date'].iloc[i]
        current_perOcup = df['perOcup'].iloc[i]
        # Transição para intervalo ocupado (perOcup > 2)
        last_time = df['date'].iloc[i-1] if i > 0 else current_time
        # Esteira ocupada
        if current_perOcup > TOLERANCIA_ATIVO:
            # anterior era vazio ou está iniciando agora
            if in_empty or i == 0:
                # Fechar intervalo vazio anterior, se existir
                if start_empty is not None:
                    empty_intervals.append((start_empty, current_time - timedelta(seconds=0.5)))
                in_empty = False

                # inicializa novo intervalo ocupado
                in_occupied = True
                start_occupied = current_time - timedelta(seconds=0.5) if i != 0 else current_time
            
            # anterior era ocupado mas está distante
            elif current_time - last_time > timedelta(seconds=1):
                # Fechar anterior ocup
                add_time = timedelta(seconds=0.5)
                occupied_intervals.append((start_occupied, last_time + add_time))
                # Criar vazio entre o anterior e atual
                empty_intervals.append((last_time + add_time, current_time - timedelta(seconds=0.5)))
                in_empty = False
                # Começar novo intervalo ocupado
                in_occupied = True
                start_occupied = current_time - timedelta(seconds=0.5)# if i != 0 else current_time
                
            # são ocupados e estão próximos
            else:
                # Continuar ocupado
                pass

        # Está vazio ou desligado
        else:
            # Primeiro registro Iniciar vazio no ínicio
            if i == 0:
                in_empty = True
                start_empty = current_time
            # Estava ocupado Fechar anterior
            elif in_occupied:
                add_time = timedelta(seconds=0.5)
                occupied_intervals.append((start_occupied, last_time + add_time))
                in_occupied = False

                # Iniciar novo vazio no fim do anterior
                in_empty = True
                start_empty = last_time + timedelta(seconds=0.5)# if i != 0 else last_time
            # Estava vazio
            else:
                # Continuar Vazio
                pass
            
    # Fechar o último intervalo, se ainda estiver aberto
    last_time = df['date'].iloc[-1]
    if in_occupied:
        occupied_intervals.append((start_occupied, last_time))

        # Implementar para caso? Faz mais de um segundo desde o anterior ?
    elif in_empty:
        empty_intervals.append((start_empty, last_time))

        # Implementar para caso? start_empty is not None
    return occupied_intervals, empty_intervals, last_time

def get_intervalos_positivos_saidas(registros):
    datas = registros['date']

    unique_days = sorted(set(datetime.fromtimestamp(d.timestamp()).date() for d in datas))
    all_occupied_intervals = []
    all_empty_intervals = []
    new_last_values = []
    new_first_values = []

    for day in unique_days:
        inicio_turno_dia, fim_turno_dia,iInterv1, fInterv1, iInterv2, fInterv2 = get_dados_turno(day)
        inicio_dia = datetime(year=day.year, month=day.month, day=day.day, hour=0, minute=0, second=0)
        fim_dia = datetime(year=day.year, month=day.month, day=day.day, hour=23, minute=59, second=59)

        intervals_of_interest = [(inicio_dia, inicio_turno_dia)]  # Começo do dia até inicio_turno_dia
        if retorna_dia_da_semana(day) != 7:
            intervals_of_interest.append((iInterv1, fInterv1))
            intervals_of_interest.append((iInterv2, fInterv2)) 
            intervals_of_interest.append((fim_turno_dia, fim_dia)) 
        else:
            intervals_of_interest.append((fInterv1,fim_dia))

        last_value = ''
        for start, end in intervals_of_interest:
            if datetime.now() >= end and end > start:
                # Filtrar dados dentro do intervalo atual
                mask = (registros['date'] >= start) & (registros['date'] <= end)
                df_interval = registros[mask]

                if not df_interval.empty and get_primeiro_do_dia(day,df_interval) < inicio_turno_dia:
                    new_first_values.append(get_primeiro_do_dia(day,df_interval) - timedelta(seconds=0.1))

                # Ao menos dois valores no intervalo
                if len(df_interval) > 2:
                    # Encontrar subintervalos onde perOcup > {TOLERANCIA_ATIVO} e perOcup <= {TOLERANCIA_ATIVO}
                    occupied, empty, last_value = find_intervals_above_threshold(df_interval)
                    all_occupied_intervals.extend(occupied)
                    all_empty_intervals.extend(empty)
                elif start != inicio_dia and end != fim_dia:
                    # Se não há dados no intervalo, verificar duração e adicionar como vazio
                    duration = (end - start).total_seconds()
                    if duration > 1:
                        all_empty_intervals.append((start, end))
        
        new_last_value = ''
        if last_value and last_value > fim_turno_dia:
            new_last_value = last_value + timedelta(seconds=0.1)
            new_last_values.append(new_last_value)

    return all_occupied_intervals, all_empty_intervals, new_last_values, new_first_values

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
    
    return somatorio / tempo_total if tempo_total else 0

def adicionar_intervalos(df, intervalos):
    """
    Adiciona intervalos desativados (com perOcup=0) ao DataFrame.
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

def calcula_barras_intervalos(intervalos, new = False):
    # extra = 0
    # if new:
    #     extra = 500
    interval_bars_x = []
    interval_bars_y = []
    interval_bars_x2 = []
    interval_bars_offset = []
    for i_inax1,i_inax2 in intervalos:
        interval_bars_x.append(i_inax1)
        interval_bars_y.append(100)
        interval_bars_x2.append((max(i_inax2-i_inax1,timedelta(seconds=0))).total_seconds() * 1000)
        interval_bars_offset.append(0)# (i_inax2-i_inax1).total_seconds() * 0 )
    return pd.DataFrame({'from':interval_bars_x,'to':interval_bars_x2,'size':interval_bars_y,'offset':interval_bars_offset})

def process_part(display_data, show_date_start, show_date_end, last_data_old, last_data_new):
    last_data_old = pd.Timestamp(last_data_old).to_pydatetime() + timedelta(seconds=0.5)

    # display_data[0].insert(0,last_data_old)
    # display_data[1].insert(0,0)
    intervalos_inativo = encontrar_intervalos_de_zeros(display_data[1], display_data[0])
    intervalos_desativado = detectar_intervalos_faltante(display_data[0])
    intervalos_ativos = encontrar_intervalos_ativos(display_data[1], display_data[0],True)
    
    # if (display_data[0][0] - last_data_old + timedelta(seconds=0.5)).total_seconds() > 0.5:
    #     intervalos_desativado.append([last_data_old + timedelta(seconds=0.5),display_data[0][0]])


    display_data = pd.DataFrame({'date':display_data[0],'perOcup':display_data[1]})


    datas_inicio = []
    datas_final = []
    dia_trab_periodo = datetime.today()
    # result['percent_tempo_inativo_seg'] [hora_falta] = 100

    dia_semana_process = retorna_dia_da_semana(dia_trab_periodo)
    
    inicio_trab_dia = last_data_old #dados_intervalos[dia_semana_process]['TurnoProdutivoHrEntrada']
    fim_trab_dia = last_data_new #dados_intervalos[dia_semana_process]['TurnoProdutivoHrSaida']

    #ADICIONARIA A DATA ATUAL ao gráfico
    # if dia_semana_process == 7: print(f'>> SABADO: {fim_trab_dia}')
    # if fim_trab_dia.hour == 0 and fim_trab_dia.minute == 0:
    #     fim_trab_dia = dados_intervalos[dia_semana_process]['TurnoProdutivoHrEntIntervalo2']
    #     # if dia_semana_process == 7: print(f'\t{fim_trab_dia}')
    #     if fim_trab_dia.hour == 0 and fim_trab_dia.minute == 0:
    #         fim_trab_dia = dados_intervalos[dia_semana_process]['TurnoProdutivoHrEntIntervalo1']

    data_inicial = inicio_trab_dia #datetime(year=dia_trab_periodo.year,month=dia_trab_periodo.month,day=dia_trab_periodo.day).replace(hour=inicio_trab_dia.hour,minute=inicio_trab_dia.minute,second=inicio_trab_dia.second,microsecond=inicio_trab_dia.microsecond)
    
    # print('> {} not in  {}?'.format(data_inicial,display_data['date'].values))
    # print('> {} - {}?'.format(display_data.loc[0, 'date'], data_inicial))
    if data_inicial not in display_data['date'].values and display_data.loc[0, 'date'] - data_inicial >= timedelta(seconds=1):# and data_inicial != inicio_trab_dia:
        display_data.loc[len(display_data)] = [data_inicial,0]
        datas_inicio.append(data_inicial)
    

    # Não era pra ser data inicial ?
    # data_final = last_data_new#datetime(year=dia_trab_periodo.year,month=dia_trab_periodo.month,day=dia_trab_periodo.day).replace(hour=fim_trab_dia.hour,minute=fim_trab_dia.minute)
    # if data_final not in display_data['date'].values:# and data_final.date() != datetime.now().date():
    #     print(f'\tADICIONANDO FIM {data_final}')
    #     display_data.loc[len(display_data)] = [data_final,0]
    #     datas_final.append(data_final)

    display_data = display_data.sort_values(by='date').reset_index(drop=True)

    # print(f'\nINTERVALOS DESATIVADOS 1 >>{intervalos_desativado}')
    # Adicionar intervalo para primeiro horário do dia
    if datas_inicio:
        dtini = datas_inicio[0]
        if dtini >= get_primeiro_do_dia(dtini, display_data): # retorna_dia_da_semana(dtini) != 7 and 
            indice_ini = display_data.index[display_data['date'] == dtini]
            data_ini = pd.Timestamp(dtini)

            data_fim = display_data.loc[indice_ini + 1,'date'].iloc[0] if indice_ini + 1 < len(display_data) else dtini + timedelta(seconds=0.5)

            inicio_trab_dia, fim_trab_dia, ini_interv_1, fim_interv_1, ini_interv_2, fim_interv_2 = get_dados_turno(data_fim)

            inicio_trab_dia = last_data_old
            fim_trab_dia = last_data_new

            modfy_time = timedelta(seconds=0.5)
            if data_fim == ini_interv_1 or data_fim == ini_interv_2 or data_fim == fim_trab_dia:#inicio_turno_dia > get_primeiro_do_dia(dtini,display_data):
                modfy_time = timedelta(seconds=0)
            data_fim = data_fim - modfy_time
            
            if data_ini < fim_interv_1 and data_fim > ini_interv_1:
                if data_fim > fim_interv_1:
                    add_time2 = timedelta(seconds=0)
                    new_extra_interval = [fim_interv_1, (data_fim - add_time2).to_pydatetime()]
                    intervalos_desativado.append(new_extra_interval)
                data_fim = pd.Timestamp(ini_interv_1)

            #Talvez implementar intervalo 2

            new_interval = [data_ini.to_pydatetime(), (data_fim).to_pydatetime()]
            if new_interval not in intervalos_desativado and new_interval[1] - new_interval[0] >= timedelta(seconds=1):
                # ADICIONANDO INTERVALO 2
                intervalos_desativado.append(new_interval)

                if not (display_data['date'] == data_fim).any():
                    # print(f'ADICIONANDO DATA FINAL: {data_fim}')
                    display_data.loc[len(display_data)] = [data_fim,0]
        

    display_data = display_data.sort_values(by='date').reset_index(drop=True)
    
    # print(f'INTERVALOS DESATIVADOS 2 >>{intervalos_desativado}')

    # ANTIGO FOR 2 (Por agora não é usado e datas_final está vazio)
    
    # for dtfim in datas_final:
    #     # IGNORAR DATA DE HOJE #if dtfim.date() == datetime.now().date(): continue
        
    #     indice_fim = display_data.index[display_data['date'] == dtfim]
    #     inicio_turno_dia, fim_turno_dia = get_inicio_fim_turno(dtfim)
    #     inicio_trab_dia, fim_trab_dia, ini_interv_1, fim_interv_1, ini_interv_2, fim_interv_2 = get_dados_turno(dtfim)

    #     inicio_trab_dia = last_data_old
    #     fim_trab_dia = last_data_new

    #     #if False and retorna_dia_da_semana(dtfim) == 7: fim_turno_dia = dtfim

    #     data_fim = pd.Timestamp(dtfim)

    #     if indice_fim[0] > 0 and get_ultimo_do_dia(dtfim,display_data) <= fim_turno_dia:
            
    #         data_inicio = display_data.loc[indice_fim - 1,'date'].iloc[0]
    #         modfy_time = timedelta(seconds=0)
    #         #print(f'\tULTIMO DO DIA {dtfim} >> {get_ultimo_do_dia(dtfim,display_data)}')
    #         if data_inicio != inicio_trab_dia and data_inicio != ini_interv_1 and data_inicio != ini_interv_2: #get_ultimo_do_dia(dtfim,display_data) > fim_turno_dia or :
    #             modfy_time = timedelta(seconds=0.5)
    #         data_inicio = data_inicio + modfy_time
            
    #         inicio_trab_dia, fim_trab_dia, ini_interv_1, fim_interv_1, ini_interv_2, fim_interv_2 = get_dados_turno(data_fim)

    #         if data_inicio >= ini_interv_1 and data_inicio < fim_interv_1: # TALVEZ TRATAR CASO DE data_fim menor que fim do intervalo 1
    #             data_inicio = pd.Timestamp(fim_interv_1)
    #             # POSSÍVEL ERRO: INICIO ANTES E FIM DEPOIS ? Ou já tratado no for anterior ?
    #         # Talvez implementar intervalo 2

    #         new_interval = [data_inicio.to_pydatetime(), data_fim.to_pydatetime()]

    #         if new_interval not in intervalos_desativado:
    #             #print(f'\tADICIONANDO INTERVALO 3 {new_interval}')
    #             intervalos_desativado.append(new_interval)
    #             if not (display_data['date'] == data_inicio).any():# [data_inicio,0] not in display_data:
    #                 display_data.loc[len(display_data)] = [data_inicio,0]
    #                 print(f'ADICIONANDO dt inicio {data_inicio}')
    # print(f'INTERVALOS DESATIVADOS 3 >>{intervalos_desativado}')
    
    #display_data = display_data.sort_values(by='date').reset_index(drop=True)

    intervalo_ativado_extra, intervalos_inativo_extra, new_last_values, new_first_values = get_intervalos_positivos_saidas(display_data)
    if new_last_values:
        for new_last_value in new_last_values:
            # print(f'Inserir last {new_last_value}')
            display_data.loc[len(display_data)] = [new_last_value,0]
    display_data = display_data.sort_values(by='date').reset_index(drop=True)

    if new_first_values:
        for new_first_value in new_first_values:
            # print(f'Inserir first {new_first_value}')
            display_data.loc[len(display_data)] = [new_first_value,0]
    display_data = display_data.sort_values(by='date').reset_index(drop=True)
    # print(f'ANTES DE INATIVOS EXTRA {display_data}')
    display_data = adicionar_intervalos(display_data,intervalos_inativo_extra)
    # print(f'ADICIONADOS INTERVALOS INATIVOS EXTRA {display_data}')
    display_data = adicionar_intervalos(display_data,intervalos_desativado)
    # print(f'ADICIONADOS INTERVALOS DESATIVADOS {display_data}')

    df_yellow_bar = calcula_barras_intervalos(intervalos_inativo,True)
    df_red_bar = calcula_barras_intervalos(intervalos_desativado,True)
    df_purple_bar = calcula_barras_intervalos(intervalo_ativado_extra,True)
    df_lightblue_bar = calcula_barras_intervalos(intervalos_inativo_extra,True)
    df_green_bar = calcula_barras_intervalos(intervalos_ativos,True)

    return display_data, intervalos_inativo, intervalos_desativado, intervalos_ativos, intervalo_ativado_extra, intervalos_inativo_extra, df_yellow_bar, df_red_bar, df_purple_bar, df_lightblue_bar, df_green_bar

def create_graph(display_data,show_date_start,show_date_end):
    # INTERVALOS DE ZEROS SEGUIDOS POR MENOS DE 1 SEGUNDO ENTRE CADA (UNITÁRIOS são 0.5 maiores)    
    intervalos_inativo = encontrar_intervalos_de_zeros(display_data['perOcup'],display_data['date'])#, display_data['perOcup'])

    # INTERVALOS DE PERIODOS SEM DADOS (TODOS SÃO 0.5 anterior ao dado do intervalo)
    intervalos_desativado = detectar_intervalos_faltante(display_data['date'])#, display_data['perOcup'])

    # INTERVALOS COM LEITURAS MAIORES QUE TOLERÂNCIA SEGUIDOS POR MENOS DE 1 SEGUNDO ENTRE CADA
    intervalos_ativos = encontrar_intervalos_ativos(display_data['perOcup'],display_data['date'])


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

    # Converte dados em dataframe
    display_data = pd.DataFrame(display_data)

    #   Pegar periodo
    datas_inicio = []
    datas_final = []

    # print(f'TEMPO INICIO GRAFICO 1 PT 0.1 >{time() - START}')

    # SISTEMA PARA ADICIONAR HORAS VAZIAS
    for dia_trab_periodo in dias_periodo[::-1]:

        dia_semana_process = retorna_dia_da_semana(dia_trab_periodo)
        
        if dia_semana_process != 7:
            inicio_trab_dia = dados_intervalos[dia_semana_process]['TurnoProdutivoHrEntrada']
            fim_trab_dia = dados_intervalos[dia_semana_process]['TurnoProdutivoHrSaida']

            if fim_trab_dia.hour == 0:
                fim_trab_dia = dados_intervalos[dia_semana_process]['TurnoProdutivoHrEntIntervalo2']
                if fim_trab_dia.hour == 0:
                    fim_trab_dia = dados_intervalos[dia_semana_process]['TurnoProdutivoHrEntIntervalo1']

            # Não adicionar para sábado if dia_semana_process != 7:                
            datas_truncadas = set(display_data['date'].dt.floor('s'))

            data_inicial = datetime(year=dia_trab_periodo.year,month=dia_trab_periodo.month,day=dia_trab_periodo.day).replace(hour=inicio_trab_dia.hour,minute=inicio_trab_dia.minute)
            if data_inicial not in datas_truncadas:
                display_data.loc[len(display_data)] = [data_inicial,0]
                datas_inicio.append(data_inicial)

            data_final = datetime(year=dia_trab_periodo.year,month=dia_trab_periodo.month,day=dia_trab_periodo.day).replace(hour=fim_trab_dia.hour,minute=fim_trab_dia.minute)
            if data_final not in datas_truncadas and data_final.date() != datetime.now().date():
                display_data.loc[len(display_data)] = [data_final,0]
                datas_final.append(data_final)


            #REPLACE POIS NÃO CONSEGUE CRIAR DATE_RANGE PARA VALORES MAIS ANTIGOS QUE 1677 ?
            #horarios_desejados = pd.date_range(start=inicio_trab_dia.replace(year=2025), end=fim_trab_dia.replace(year=2025) + timedelta(hours=1), freq='h')
    
    display_data = display_data.sort_values(by='date').reset_index(drop=True)
    # print(f'TEMPO INICIO GRAFICO 1 PT 0.2 >{time() - START}')

    # Adicionar intervalo para primeiros horários do dia
    for dtini in datas_inicio:
 
        if dtini >= get_primeiro_do_dia(dtini,display_data): # retorna_dia_da_semana(dtini) != 7 and 
            indice_ini = display_data.index[display_data['date'] == dtini]
            data_ini = pd.Timestamp(dtini)
            
            data_fim = display_data.loc[indice_ini + 1,'date'].iloc[0]

            inicio_trab_dia, fim_trab_dia, ini_interv_1, fim_interv_1, ini_interv_2, fim_interv_2 = get_dados_turno(data_fim)

            if False and retorna_dia_da_semana(dtini) == 7: fim_trab_dia = ini_interv_1 # ignoraria sábado

            modfy_time = timedelta(seconds=0.5)
            if data_fim == ini_interv_1 or data_fim == ini_interv_2 or data_fim == fim_trab_dia:
                modfy_time = timedelta(seconds=0)
            data_fim = data_fim - modfy_time
            
            if data_ini < fim_interv_1 and data_fim > ini_interv_1:
                if data_fim > fim_interv_1:
                    add_time2 = timedelta(seconds=0)
                    
                    # print(f'\t ADICIONAR {data_fim} == {fim_trab_dia}')
                    new_extra_interval = [fim_interv_1, (data_fim - add_time2).to_pydatetime()]
                    # print(f'\tADICIONANDO INTERVALO 1 {new_extra_interval}')
                    intervalos_desativado.append(new_extra_interval)
                data_fim = pd.Timestamp(ini_interv_1)

            #Talvez implementar intervalo 2

            new_interval = [data_ini.to_pydatetime(), (data_fim).to_pydatetime()]
            if new_interval not in intervalos_desativado:
                intervalos_desativado.append(new_interval)

            if not (display_data['date'] == data_fim).any():
                display_data.loc[len(display_data)] = [data_fim,0]
    
    # print(f'TEMPO INICIO GRAFICO 1 PT 0.3 >{time() - START}')
    display_data = display_data.sort_values(by='date').reset_index(drop=True)
    for dtfim in datas_final:
        # IGNORAR DATA DE HOJE
        if dtfim.date() == datetime.now().date(): continue

        indice_fim = display_data.index[display_data['date'] == dtfim]
        inicio_turno_dia, fim_turno_dia = get_inicio_fim_turno(dtfim)
        inicio_trab_dia, fim_trab_dia, ini_interv_1, fim_interv_1, ini_interv_2, fim_interv_2 = get_dados_turno(dtfim)

        if False and retorna_dia_da_semana(dtfim) == 7: fim_turno_dia = dtfim # ignoraria sábado

        data_fim = pd.Timestamp(dtfim)

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

    # intervalos fora dos limites e dentro dos intervalos
    intervalo_ativado_extra, intervalos_inativo_extra, new_last_values, new_first_values = get_intervalos_positivos_saidas(display_data)


    if new_last_values:
        for new_last_value in new_last_values:
            display_data.loc[len(display_data)] = [new_last_value,0]
    display_data = display_data.sort_values(by='date').reset_index(drop=True)

    if new_first_values:
        for new_first_value in new_first_values:
            display_data.loc[len(display_data)] = [new_first_value,0]
    display_data = display_data.sort_values(by='date').reset_index(drop=True)
    
    # Adiciona para gráfico valores nulos nas posições dos intervalos inativos e desativados
    display_data = adicionar_intervalos(display_data,intervalos_inativo_extra)
    display_data = adicionar_intervalos(display_data,intervalos_desativado)


    # Já sendo calculado em outra parte do código
    percentPerHoraTrab = calcular_media_porcentagem_por_tempo_trabalhando(display_data)

    # Criar gráfico
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=display_data['date'], 
        y=display_data['perOcup'], 
        mode='lines', # +markers
        name='Leitura Sensores'))
    
    df_yellow_bar = calcula_barras_intervalos(intervalos_inativo)
    
    fig.add_trace(go.Bar(
        x=df_yellow_bar['from'],
        y=df_yellow_bar['size'],
        width=df_yellow_bar['to'],
        offset=df_yellow_bar['offset'],
        marker_color="yellow",
        hoverinfo='skip',
        name=f'Leitura < {TOLERANCIA_ATIVO}%',
        opacity=0.3
    ))

    df_red_bar = calcula_barras_intervalos(intervalos_desativado)

    fig.add_trace(go.Bar(
        x=df_red_bar['from'],
        y=df_red_bar['size'],
        width=df_red_bar['to'],
        offset=df_red_bar['offset'],
        marker_color="red",
        name='Desligado',
        hoverinfo='skip',
        opacity=0.3
    ))
    

    # Criar retângulos para intervalos ativados em intervalos pausa
    df_purple_bar = calcula_barras_intervalos(intervalo_ativado_extra)
    
    fig.add_trace(go.Bar(
        x=df_purple_bar['from'],
        y=df_purple_bar['size'],
        width=df_purple_bar['to'],
        offset=df_purple_bar['offset'],
        marker_color="mediumpurple",
        name='Trabalhando Extra',
        hoverinfo='skip',
        opacity=0.3
    ))

    # Criar retângulos para intervalos desativados nos intervalos pausa ou fora 
    df_lightblue_bar = calcula_barras_intervalos(intervalos_inativo_extra)
    
    fig.add_trace(go.Bar(
        x=df_lightblue_bar['from'],
        y=df_lightblue_bar['size'],
        width=df_lightblue_bar['to'],
        offset=df_lightblue_bar['offset'],
        marker_color="lightblue",
        name='Vazio Extra',
        hoverinfo='skip',
        opacity=0.3
    ))

    # Criar retângulos para intervalos ativos
    df_green_bar = calcula_barras_intervalos(intervalos_ativos)
    
    fig.add_trace(go.Bar(
        x=df_green_bar['from'],
        y=df_green_bar['size'],
        width=df_green_bar['to'],
        offset=df_green_bar['offset'],
        marker_color="green",
        name='Trabalhando',
        hoverinfo='skip',
        opacity=0.3
    ))
    
    # Definir tamanho do y
    fig.update_traces(
        marker_line_width=0
    )
    
    fig.update_layout(
        barmode='overlay',
        showlegend=True,
        yaxis=dict(range=[0, 100]),
        legend=dict(
                font=dict(
                    size=18,  # Tamanho da fonte
                    # family=theme_font#,  # Família da fonte (opcional)
                )
            )
    )

    fig.update_xaxes(
        tickmode='auto',  # Modo automático para ajustar os ticks
        dtick=3600000,   # Intervalo de 1 hora (em milissegundos)
        #tickformat='%H:%M',  # Formato de exibição das horas
        rangeslider={"visible":True}  # Adiciona um rangeslider para facilitar o zoom
    )
    return fig, percentPerHoraTrab, display_data

def create_bar_graph(display_data,show_date_start,show_date_end):
    minutos_extras = 0

    display_data = pd.DataFrame(display_data)

    display_data['ativo'] = display_data['perOcup'] > TOLERANCIA_ATIVO

    display_data['hour'] = display_data['date'].dt.floor('h')

    
    min_total = 0 # minutos_total_dia_semana
    
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

        segundos_atual = sum(
            max(0, (min(horario_atual, end) - start).total_seconds())
            for start, end in periodos_trabalho
        )

        min_total += segundos_atual/60
        dias_periodo.append(show_date_start)
    else:
        extra_day = 1
    
    dias_atras = ((show_date_end - timedelta(days=1)) - show_date_start).days + extra_day
    
    if dias_atras:
        for i in range(dias_atras):
            process_date = show_date_end - timedelta(days=1) - timedelta(days=i+1 - extra_day)
            dia_semana = retorna_dia_da_semana(process_date)
            
            if dia_semana != 1 and dia_semana != 7:
                dias_periodo.append(process_date)
                min_total += minutos_total_dia_semana[dia_semana]
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

    # SISTEMA PARA ADICIONAR HORAS VAZIAS
    for dia_trab_periodo in dias_periodo[::-1]:
        dia_semana_process = retorna_dia_da_semana(dia_trab_periodo)
        if dia_semana_process != 7 and dia_semana_process != 1:
            inicio_trab_dia = dados_intervalos[dia_semana_process]['TurnoProdutivoHrEntrada']
            fim_trab_dia = dados_intervalos[dia_semana_process]['TurnoProdutivoHrSaida']

            # REPLACE POIS NÃO CONSEGUE CRIAR DATE_RANGE PARA VALORES MAIS ANTIGOS QUE 1677 ?
            horarios_desejados = pd.date_range(start=inicio_trab_dia.replace(year=2025), end=fim_trab_dia.replace(year=2025) + timedelta(hours=1), freq='h')
            for hr_desej in horarios_desejados:
                dia_hora_trab = datetime(year=dia_trab_periodo.year,month=dia_trab_periodo.month,day=dia_trab_periodo.day).replace(hour=hr_desej.hour,minute=0)
                if dia_hora_trab not in result.index:
                    result.loc[dia_hora_trab] = [0,3600,100,-0,0,0,0,0]

    result = result.sort_index()

    # média na ocupação ativa
    fig_bar.add_trace(go.Bar(
        x= result.index,
        y= -result['media_perOcup_ativo'],
        base=0,
        name='Média % Ocupação Trabalhando',
        marker_color='blue',
        offset=-1000000,
        width=bar_width*3,
        customdata=[abs(y) for y in -result['media_perOcup_ativo']],
        hovertemplate='%{customdata:.2f} % (%{x})   <extra></extra>',  # Exibe o valor sem o sinal negativo
        opacity=0.3
    ))

    width_inativo = [bar_width if val != 100 else bar_width*3 for val in result['percent_tempo_inativo_seg']]
    # Adicione as barras para o tempo inativo
    fig_bar.add_trace(go.Bar(
        x=result.index,
        y=result['percent_tempo_inativo_seg'],
        name='Tempo Desligado (% de hora)',
        marker_color='red',
        offset=-1000000,
        opacity=0.3,#,
        hovertemplate='%{y:.2f} % (%{x})   <extra></extra>',
        width=width_inativo
    ))

    # Adicione as barras para o tempo ativo com ocupação < {TOLERANCIA_ATIVO}%
    fig_bar.add_trace(go.Bar(
        x=result.index,
        y=result['percent_tempo_ativo_menor_2_seg'],
        name=f'Tempo Ligado < {TOLERANCIA_ATIVO}% (% de hora)',
        marker_color='yellow',
        hovertemplate='%{y:.2f} % (%{x})   <extra></extra>',
        offset=-0,
        opacity=0.3,
        width=bar_width
    ))

    # TEMPO ATIVO
    fig_bar.add_trace(go.Bar(
        x=result.index,
        y=result['percent_tempo_ativo_maior_2_seg'],
        name=f'Tempo Trabalhando > {TOLERANCIA_ATIVO}% (% de hora)',
        marker_color='green',
        hovertemplate='%{y:.2f} % (%{x})   <extra></extra>',
        offset=1000000,
        opacity=0.3,
        width=bar_width
    ))

    fig_bar.update_layout(
        bargap=0,
        bargroupgap=0,
        yaxis=dict(
            zeroline=True,
            range=[-100, 100],
            zerolinewidth=1,
            zerolinecolor='grey'
        ),
        xaxis=dict(
            tickmode="linear",
            dtick=3600000
        ),
        legend=dict(
                font=dict(
                    size=18,  # Tamanho da fonte
                    # family=theme_font,  # Família da fonte (opcional)
                )
            )
    )
    return fig_bar, min_total, min_trab, percent_trab_geral, min_parado, minutos_ligados, minutos_extras

def create_graph_wrapper(display_data,show_date_start,show_date_end, q):
    fig, percentPerHoraTrab, display_data = create_graph(display_data,show_date_start,show_date_end)
    q.put((fig, percentPerHoraTrab, display_data))
    # print(f'TEMPO LEVADO GRAFICO 1 {time() - START}')

def create_bar_graph_wrapper(display_data,show_date_start,show_date_end, q):
    fig_bar,min_total,min_trab,percent_trab_geral,min_parado,minutos_ligados,minutos_extras = create_bar_graph(display_data,show_date_start,show_date_end)
    q.put((fig_bar,min_total,min_trab,percent_trab_geral,min_parado,minutos_ligados,minutos_extras))
    # print(f'TEMPO LEVADO GRAFICO BARRA {time() - START}')

def change_pause_state(var_pause):
    var_pause = 1 - var_pause
    st.session_state['var_pause'] = var_pause

# SISTEMA BOTÃO DE PAUSE (Não está sendo usado)
def show_pause_button():
    var_pause = st.session_state.get('var_pause',1)
    text_pause = f'⏸️ Pausar' if var_pause else f'▶️ RECARREGAR'
    container_pause_bt = st.empty()
    if container_pause_bt.button(text_pause,on_click=change_pause_state,args=(var_pause,)):
        container_pause_bt.empty()

        # CRIAR BOTÃO COM TEXTO ATUALIZADO
        text_pause = f'⏸️ Pausar' if not var_pause else f'▶️ RECARREGAR'
        container_pause_bt.button(text_pause,on_click=change_pause_state,args=(1 - var_pause,))



######### NA TEGA PRECISA LIGAR VPN (SOPHOS CONNECT)
host = os.getenv("host")
user = os.getenv("user")
password = os.getenv("password")
database = os.getenv("database")

conn_args = {
    "user": user,
    "password": password,
    "host":host,
    "database": database
}

# Criar engine da conexão sql
engine = create_engine(f"mysql+mysqlconnector://", connect_args=conn_args)#{user}:{password}@{host}/{database}")# # (f"mysql+mysqlconnector://",connect_args=conn_args) 

# Definir período de análise
datetime.today()
periodo_inicio = ''
periodo_fim = ''

read_date_ini = ''#'current_date()'
read_date_fin = ''#'current_date()'


if 'periodo_tempo' not in st.session_state:
    st.session_state['periodo_tempo'] = (datetime.today().date(),datetime.today().date())

read_datas = st.session_state.get('periodo_tempo',(datetime.today().date(),))

if len(read_datas) > 1:
    read_date_ini, read_date_fin = read_datas
else:
    read_date_ini = read_datas[0]
    read_date_fin = read_datas[0]

read_date_ini = read_date_ini
read_date_fin = read_date_fin + timedelta(days=1)

START = time() # DEBUG TEMPO PROCESSAMENTO

# print(f'TEMPO ANTES query 1: {time() - START}')
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
    limit 7;'''
        
    turno_semana_dados = pd.read_sql(query_turno, engine)
    st.session_state['turno_semana_dados'] = turno_semana_dados
turno_semana_dados = st.session_state.get('turno_semana_dados')

periodo_inicio = turno_semana_dados[turno_semana_dados['TurnoProdutivoDiaSemana'] == retorna_dia_da_semana(datetime.now())]['HoraMinuto']

# CONTINUAR CHECANDO SE TurnoProdutivoQtdeMinutos é atualizado dinâmicamente
if periodo_inicio.empty:
    query_hr_ini = f'''
        select min(l.LinhaPinturaUtilizacaoDtHr) from linhapinturautilizacao l 
        where l.LinhaPinturaUtilizacaoDtHr >= '{read_date_ini}' AND l.LinhaPinturaUtilizacaoDtHr <= '{read_date_fin}' '''
    periodo_inicio = pd.read_sql(query_hr_ini, engine)
    periodo_inicio = periodo_inicio.iloc[0, 0]
else:
    horario = datetime.strptime(periodo_inicio.iloc[0],'%H:%M')
    hora, minuto = horario.hour,horario.minute
    periodo_inicio = datetime.combine(read_date_ini, datetime.min.time()).replace(hour = hora, minute = minuto, second = 0)

dados_intervalos = {}
DIA_SEM_ATUAL = retorna_dia_da_semana(read_date_fin - timedelta(days=1))

# DADOS TURNOS NOS DIAS DA SEMANA (Está pegando o turno 2 no sql mais acima)
minutos_total_dia_semana = {}
for index, row in turno_semana_dados.iterrows():
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

def display_no_data(key='periodo_tempo'):
    st.markdown(f'''
        ## Sem Dados disponíveis entre {periodo_inicio.strftime('%d/%m/%Y')} até {(periodo_fim -  timedelta(days=1)).strftime('%d/%m/%Y')}
    ''')
    st.date_input('Filtro Leitura',key='periodo_tempo',format='DD/MM/YYYY')

TEST_MODE = False #True

if periodo_inicio:
    periodo_inicio = read_date_ini
    periodo_fim = read_date_fin

    if periodo_inicio > datetime.now().date():
        periodo_inicio = datetime.now().date()
    if periodo_fim > datetime.now().date() + timedelta(days=1):
        periodo_fim = datetime.now().date() + timedelta(days=1)

    if periodo_fim == datetime.now().date() + timedelta(days=1):
        st.session_state['processing_today'] = True
    else:
        st.session_state['processing_today'] = False


    # EXECUTA NOVA CONSULTA AO DETECTAR MUDANÇAS NO INTERVALO DE DATAS
    if 'last_read' not in st.session_state or st.session_state.get('last_dates',[]) != [periodo_inicio, periodo_fim]: 
        # print('OP Q1')
        query = f"""
            SELECT LinhaPinturaUtilizacaoDtHr, LinhaPinturaUtilizacaoPerOcup, LinhaPinturaUtilizacaoParada
            FROM linhapinturautilizacao
            WHERE LinhaPinturaUtilizacaoDtHr BETWEEN '{periodo_inicio}' AND '{periodo_fim}'
            GROUP BY LinhaPinturaUtilizacaoDtHr
            ORDER BY LinhaPinturaUtilizacaoDtHr;
        """

        last_read = pd.read_sql(query, engine)
        if not last_read.empty:
            st.session_state['last_read'] = last_read
            st.session_state['last_read_time'] = last_read['LinhaPinturaUtilizacaoDtHr'].iloc[-1]
        else:
            print(f'QUERY RETORNOU VAZIO >> {query}')
    else:
        # print(f'TEMPO ANTES CARREGAR: {time() - START}')
        last_read = st.session_state.get('last_read')
    
    # print(f'\nTEMPO QUERY 3: {time() - START}')

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
    df_final["LinhaPinturaUtilizacaoParada"] = df_final["LinhaPinturaUtilizacaoParada"].infer_objects(copy=False).fillna(1)

    # Contar minutos trabalhados e parados
    minutos_trabalhados = (df_final["LinhaPinturaUtilizacaoParada"] == 0).sum()
    
    # Converter para dicionário de listas
    display_data = {'date': last_read['LinhaPinturaUtilizacaoDtHr'].to_list(),'perOcup': last_read['LinhaPinturaUtilizacaoPerOcup'].to_list()}

    engine.dispose()

    #################### DADOS INSERIDOS PARA TESTES
    if False:
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
        pass
    ####################

    media_ocupacao = 0
    fig, percentPerHoraTrab = None, 0
    fig_bar, min_total, min_trab, percent_trab_geral, min_parado, minutos_ligados, minutos_extras = (None,0,0,0,0,0,0)

    if display_data['date']:
        q_graph = Queue()
        q_bar = Queue()

        media_ocupacao = sum([x for x in display_data['perOcup'] if x > TOLERANCIA_ATIVO]) / len([x for x in display_data['perOcup'] if x > TOLERANCIA_ATIVO])

        copia_dp_data = copy.deepcopy(display_data)
        
        # PERIODO DE TEMPO MUDOU, RECALCULAR E CRIAR GRÁFICOS
        if st.session_state.get('last_dates',[]) != [periodo_inicio, periodo_fim] or 'fig1' not in st.session_state or 'figbar' not in st.session_state: #(not same_data or 'fig1' not in st.session_state or 'figbar' not in st.session_state):
            # print('OP 1')
            thread_bar = Thread(target=create_bar_graph_wrapper, args=(copia_dp_data,periodo_inicio,periodo_fim, q_bar))
            
            thread_graph = Thread(target=create_graph_wrapper, args=(display_data,periodo_inicio,periodo_fim, q_graph))
            
            thread_graph.start()
            thread_bar.start()

            # Esperar que ambas terminem
            thread_graph.join()
            thread_bar.join()
            print((f'TEMPO LEVADO THREADS {time() - START}'))

            fig, percentPerHoraTrab, display_data = q_graph.get()
            fig_bar, min_total, min_trab, percent_trab_geral, min_parado, minutos_ligados, minutos_extras = q_bar.get()

            st.session_state['fig1'] = (fig, percentPerHoraTrab, display_data)
            st.session_state['figbar'] = (fig_bar, min_total, min_trab, percent_trab_geral, min_parado, minutos_ligados, minutos_extras)
            st.session_state['last_dates'] = [periodo_inicio, periodo_fim]
            st.session_state['last_process'] = display_data
            st.session_state['last_processed_read_time'] = st.session_state.get('last_read_time')
        # Periodo de tempo não mudou porém contém data atual, então calcular para novos valores e juntar com gráficos antigos
        elif TEST_MODE or periodo_inicio <= datetime.now().date() <= periodo_fim - timedelta(days=1) and st.session_state.get('last_processed_read_time') != st.session_state.get('last_read_time'):#not st.session_state.get('last_process',pd.DataFrame()).equals(display_data):
            # print('OP 2')
            # Cálcular intervalos não processados e mesclar com antigos
            last_read_time = st.session_state.get('last_processed_read_time')

            # CONSULTAR sql OU JÁ CONSULTAR NO ANTERIOR ?
            query = f"""
                SELECT LinhaPinturaUtilizacaoDtHr, LinhaPinturaUtilizacaoPerOcup, LinhaPinturaUtilizacaoParada
                FROM linhapinturautilizacao
                WHERE LinhaPinturaUtilizacaoDtHr > '{last_read_time}'
                ORDER BY LinhaPinturaUtilizacaoDtHr ASC
                LIMIT 100;
            """ # GROUP BY LinhaPinturaUtilizacaoDtHr
            newest_read = pd.read_sql(query, engine)

            # print(F'CONSULTADA NOVO LAST READ {newest_read}')
            last_read = st.session_state.get('last_read') # PEGA DADOS DO ÚLTIMO PROCESSAMENTO
            if not newest_read.empty:
                last_read = pd.concat([last_read, newest_read], ignore_index=True)
                test_acumulator = [newest_read['LinhaPinturaUtilizacaoDtHr'].to_list(), newest_read['LinhaPinturaUtilizacaoPerOcup'].to_list()]
            elif TEST_MODE:
                test_acumulator = st.session_state.get('test_acumulator')
                last_read = pd.concat([last_read, pd.DataFrame({'LinhaPinturaUtilizacaoDtHr':test_acumulator[0],'LinhaPinturaUtilizacaoPerOcup':test_acumulator[1]})], ignore_index=True)
            else:
                test_acumulator = []

            

            # Caso existam novos valores para serem processados
            if test_acumulator:
                # GRÁFICO DE BARRAS
                display_data = {'date': last_read['LinhaPinturaUtilizacaoDtHr'].to_list(), 'perOcup': last_read['LinhaPinturaUtilizacaoPerOcup'].to_list()}
                thread_bar = Thread(target=create_bar_graph_wrapper, args=(display_data,periodo_inicio,periodo_fim, q_bar))
                thread_bar.start()
                thread_bar.join()
                fig_bar, min_total, min_trab, percent_trab_geral, min_parado, minutos_ligados, minutos_extras = q_bar.get()
                st.session_state['figbar'] = (fig_bar, min_total, min_trab, percent_trab_geral, min_parado, minutos_ligados, minutos_extras)

                st.session_state['last_read'] = last_read # SALVA DADOS CONCATENADOS

                st.session_state['last_read_time'] = last_read['LinhaPinturaUtilizacaoDtHr'].iloc[-1]
                st.session_state['last_processed_read_time'] = st.session_state.get('last_read_time')    
                st.session_state['last_process'] = pd.DataFrame(display_data)

                # PARA GRÁFICO 1
                fig, percentPerHoraTrab, display_data = st.session_state.get('fig1')
                fig_bar, min_total, min_trab, percent_trab_geral, min_parado, minutos_ligados, minutos_extras = st.session_state.get('figbar')

                for i in range(len(test_acumulator[0])):
                    if isinstance(test_acumulator[0][i], pd.Timestamp):
                        test_acumulator[0][i] = test_acumulator[0][i].to_pydatetime()
                    elif isinstance(test_acumulator[0][i], np.datetime64):
                        test_acumulator[0][i] = test_acumulator[0][i].item()

                ### 2 CÁLCULAR TODOS OS INTERVALOS e adicionar a gráfico como barras (NO LUGAR DE TESTES)
                #       Começando sem "- 0.5" para se unir a barras anteriores
                last_data = list(fig.data[0].x)[-1]
                if pd.to_datetime(last_data).date() != datetime.today().date():
                    last_data = dados_intervalos[DIA_SEM_ATUAL]['TurnoProdutivoHrEntrada'].replace(year=datetime.today().date().year,month=datetime.today().date().month,day=datetime.today().date().day,second=0,microsecond=0)
                    
                    if test_acumulator[0][0] < dados_intervalos[DIA_SEM_ATUAL]['TurnoProdutivoHrEntrada']:
                        last_data = test_acumulator[0][0] - timedelta(seconds=0.1)

                display_data, intervalos_inativo, intervalos_desativado, intervalos_ativos, intervalo_ativado_extra, intervalos_inativo_extra, df_yellow_bar, df_red_bar, df_purple_bar, df_lightblue_bar, df_green_bar = process_part(test_acumulator, periodo_inicio, periodo_fim, last_data, datetime.now())
                percentPerHoraTrab = calcular_media_porcentagem_por_tempo_trabalhando(display_data)
                
                menor_valor_new = datetime.max
                lista_origem_new = None
                index_valor_new = None
                for lista in [[intervalos_inativo,1], [intervalos_desativado,2], [intervalos_ativos,5]]:# + intervalo_ativado_extra + intervalos_inativo_extra:
                    index_lista = lista[1]
                    for index, sublista in enumerate(lista[0]):
                        if sublista[0] < menor_valor_new:
                            menor_valor_new = sublista[0]
                            lista_origem_new = index_lista
                            index_valor_new = index
                
                maior_valor_old = np.datetime64(datetime.min)
                lista_origem_old = -1
                
                if len(fig.data[1].x) and maior_valor_old < fig.data[1].x[-1]:
                    maior_valor_old = fig.data[1].x[-1]
                    lista_origem_old = 1
                if len(fig.data[2].x) and maior_valor_old < fig.data[2].x[-1]:
                    maior_valor_old = fig.data[2].x[-1]
                    lista_origem_old = 2
                if len(fig.data[5].x) and maior_valor_old < fig.data[5].x[-1]:
                    maior_valor_old = fig.data[5].x[-1]
                    lista_origem_old = 5

                # MESCLAR PRIMEIRA BARRA COM BARRA ANTERIOR, ver qual temaior e menor x ?
                if lista_origem_old == lista_origem_new:# checar se estão em datas diferentes
                    modfy_df_bar = []
                    if lista_origem_old == 1:
                        modfy_df_bar = df_yellow_bar
                    elif lista_origem_old == 2:
                        modfy_df_bar = df_red_bar
                    elif lista_origem_old == 5:
                        modfy_df_bar = df_green_bar

                    if modfy_df_bar['from'].to_numpy()[0] == fig.data[lista_origem_old].x[-1]:
                        width_atual = list(fig.data[lista_origem_old].width)
                        width_atual[-1] = modfy_df_bar['to'][index_valor_new] + fig.data[lista_origem_old].width[-1]
                        fig.data[lista_origem_old].width = width_atual
                        
                        x_atual = list(fig.data[lista_origem_old].x)

                        x_atual[-1] = fig.data[lista_origem_old].x[-1] + np.timedelta64(int(modfy_df_bar['to'][index_valor_new] / 2), 'us')

                        fig.data[lista_origem_old].x = np.array(x_atual)

                        
                        # REMOVER LINHA DA BARRA MESCLADA
                        modfy_df_bar = modfy_df_bar.drop(index_valor_new)

                # amarelo
                if not df_yellow_bar.empty:
                    fig.data[1].width = np.concatenate([fig.data[1].width, df_yellow_bar['to'].to_numpy()])
                    fig.data[1].x = np.concatenate([fig.data[1].x, df_yellow_bar['from'].to_numpy()])
                    fig.data[1].y = np.concatenate([fig.data[1].y, df_yellow_bar['size'].to_numpy()])
                    fig.data[1].offset = np.concatenate([fig.data[1].offset, df_yellow_bar['offset'].to_numpy()])

                # vermelho
                if not df_red_bar.empty:
                    fig.data[2].width = np.concatenate([fig.data[2].width, df_red_bar['to'].to_numpy()])
                    fig.data[2].x = np.concatenate([fig.data[2].x, df_red_bar['from'].to_numpy()])
                    fig.data[2].y = np.concatenate([fig.data[2].y, df_red_bar['size'].to_numpy()])
                    fig.data[2].offset = np.concatenate([fig.data[2].offset, df_red_bar['offset'].to_numpy()])

                # roxo
                #fig.data[3]

                # azul
                #fig.data[4]

                # verde
                if not df_green_bar.empty:
                    fig.data[5].width = np.concatenate([fig.data[5].width, df_green_bar['to'].to_numpy()])
                    fig.data[5].x = np.concatenate([fig.data[5].x, df_green_bar['from'].to_numpy()])
                    fig.data[5].y = np.concatenate([fig.data[5].y, df_green_bar['size'].to_numpy()])
                    fig.data[5].offset = np.concatenate([fig.data[5].offset, df_green_bar['offset'].to_numpy()])
            
                for i in range(len(display_data['date'])):
                    display_data.loc[i, 'date'] = np.datetime64(display_data.loc[i, 'date'])

                ### ADICIONAR AO GRÁFICO DE LINHAS (NO LUGAR DE TESTES
                fig.data[0].x = np.array(list(fig.data[0].x) + list(display_data['date']),dtype='datetime64[ns]')
                fig.data[0].y = np.array(list(fig.data[0].y) + list(display_data['perOcup']))

                ### mesmo esquema para gráfico de barras? Ou gráfico de barras é rápido e pode ser executado inteiro ?

                st.session_state['fig1'] = (fig, percentPerHoraTrab, display_data)
            # Sem novos valores para serem processados
            else:
                fig, percentPerHoraTrab, display_data = st.session_state.get('fig1')
                fig_bar, min_total, min_trab, percent_trab_geral, min_parado, minutos_ligados, minutos_extras = st.session_state.get('figbar')    
        
        # PERIDO DE TEMPO NÃO MUDOU E NÃO INCLUI DATA ATUAL
        else:
            # print('OP 3', st.session_state.get('last_processed_read_time'),st.session_state.get('last_read_time'))
            fig, percentPerHoraTrab, display_data = st.session_state.get('fig1')
            fig_bar, min_total, min_trab, percent_trab_geral, min_parado, minutos_ligados, minutos_extras = st.session_state.get('figbar')

    else:
        pass

    ####show_pause_button()
    ####count = st_autorefresh(interval= 5 * 1 * 1000, key="dataframerefresh")
    
    col1,col2 = st.columns([2,10])
    # coluna das estatísticas (e botão licenças)
    with col1:
        minutos_desativados = int(min_total - minutos_parados - minutos_trabalhados)
        minutos_ligados = int(min_total - minutos_desativados)
        minutos_parados += minutos_desativados

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
            st.markdown('**Tempo Desligado:**') # color: red; background-color:powderblue;
            #color: red; background-color:lightgray;
            st.markdown(f"<h1 style='text-align: center;'>{math.floor(minutos_desativados / 60)}:{minutos_desativados % 60:02}</h1>",unsafe_allow_html=True)
        with st.container(border=True):
            st.markdown('**Tempo Excedente**') # minutos_extras
            st.markdown(f"<h1 style='text-align: center;'>{math.floor(minutos_extras / 60)}:{minutos_extras % 60:02}</h1>",unsafe_allow_html=True)
           

        if st.button(':blue[?]',help='Visualizar Licenças Utilizadas'):
            st.session_state['show_licenses'] = True
            st.rerun()
            # Talvez utilizar:
            #  :blue[texto]  :red-background[texto exemplo].
            # Container não se adapta:
            # f'''
            # <div style="width: 300px; padding: 20px; border: 2px solid black; background-color: powderblue; text-align: center;">
            #     <h1 style="color: red;">Olá</h1>
            #     <p style="color: white; font-size: 18px;">Mundo</p>
            # </div>''',unsafe_allow_html=True)
    
    # coluna dos gráficos
    with col2:
        st.markdown('## Indicativo de uso da linha de pintura da esteira no dia {} até {}'.format(periodo_inicio.strftime('%d/%m/%Y'),(periodo_fim-timedelta(days=1)).strftime('%d/%m/%Y')))
        st.date_input('Filtro de Data de Leitura',key='periodo_tempo',format='DD/MM/YYYY')

        if fig is None: # MOSTRAR FIGURA VAZIA
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=[periodo_inicio, periodo_fim], 
                y=[0, 0], 
                mode='markers', #
                name='Leitura Sensores'))
            fig.update_layout(
                showlegend=True,
                yaxis=dict(range=[0, 100]),
                legend=dict(
                        font=dict(
                            size=18,  # Tamanho da fonte
                            # family=theme_font,  # Família da fonte (opcional)
                        )
                    )
            )
        
        with st.container(border=True):
            reactGraph(fig, change_flag={'dates': [periodo_inicio.isoformat(), (periodo_fim-timedelta(days=1)).isoformat()]}, key='graf1')

        if fig_bar is None: # MOSTRAR FIG BARRA VAZIA
            fig_bar = go.Figure()
            
            fig_bar.add_trace(go.Bar(
                x= [periodo_inicio, periodo_fim],
                y= [0, 0],
                base=0,
                name='Sem dados',
                opacity=0.3
                
            ))
            fig_bar.update_layout(
                    yaxis=dict(
                        zeroline=True,
                        range=[-100, 100],
                        zerolinewidth=1,
                        zerolinecolor='grey'
                    ),
                    xaxis=dict(
                        tickmode="linear",
                        dtick=3600000
                    ),
                    legend=dict(
                            font=dict(
                                size=18,  # Tamanho da fonte
                                # family=theme_font,  # Família da fonte (opcional)
                            )
                        )
                )
        with st.container(border=True):

            reactGraph(fig_bar, change_flag = {'dates': [periodo_inicio.isoformat(), (periodo_fim-timedelta(days=1)).isoformat()]}, rangeslider=False, key='graf_bar')

        # Texto mostrando momento do último update do site
        st.markdown(f"<p style='text-align: right; '>Última consulta feita em {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}</h1>", unsafe_allow_html=True)

# Sem dados para exibir
else:
    display_no_data()

# SALVAR INSTANTE DE TEMPO DA ÚLTIMA LEITURA?
if periodo_inicio <= datetime.now().date() <= periodo_fim - timedelta(days=1):
        last_read = st.session_state.get('last_read')
        last_read_time = st.session_state.get('last_read_time')

        query = f"""
            SELECT LinhaPinturaUtilizacaoDtHr, LinhaPinturaUtilizacaoPerOcup, LinhaPinturaUtilizacaoParada
            FROM linhapinturautilizacao
            WHERE LinhaPinturaUtilizacaoDtHr > '{last_read_time}'
            ORDER BY LinhaPinturaUtilizacaoDtHr ASC
            LIMIT 100;
        """ # GROUP BY LinhaPinturaUtilizacaoDtHr
        newest_read = pd.read_sql(query, engine)
        
        if not newest_read.empty:
            last_read = pd.concat([last_read, newest_read], ignore_index=True)
#         st.session_state['last_read'] = last_read
        st.session_state['last_read_time'] = last_read['LinhaPinturaUtilizacaoDtHr'].iloc[-1]

# RECARREGAR CASO NÃO ESTEJA PAUSADO e dia atual está incluso no periodo de tempo
if st.session_state.get('var_pause',1) and (datetime.now().date() <= periodo_fim-timedelta(days=1) or datetime.now().date() == periodo_inicio):
    #################### PARA TESTE TEMPO REAL
    if TEST_MODE:
        valores_aleatorios = [random.randint(0, 100) for _ in range(3)]
        agora = datetime.now().replace(microsecond=0)
        datetimes_ultimos_segundos = [np.datetime64(agora - timedelta(seconds=i)) for i in range(3)][::-1]
        st.session_state['test_acumulator'] = [datetimes_ultimos_segundos, valores_aleatorios]

    count = st_autorefresh(interval= 5 * 1 * 1000, key="dataframerefresh")
    # print('RECARREGAR')
else:
    # print('PAUSADO')
    pass

# print('\nCONCLUÍDO\n')
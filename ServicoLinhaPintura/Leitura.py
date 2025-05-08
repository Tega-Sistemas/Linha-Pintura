import threading
import queue
from dotenv import load_dotenv
import os
import serial
import json
import time
from datetime import datetime
import requests
import termios  # Para capturar termios.error

load_dotenv()

# ----------------------- POST -----------------------
def enviar_post(json_data):
    base_url = os.getenv('BASE_URL')
    equipamento_id = os.getenv('EQUIP_ID')
    url = f"{base_url}leituras?id={equipamento_id}"

    try:
        response = requests.post(url, json=json_data, timeout=10)
        if response.status_code == 200:
            print(f"{datetime.now()}: Dados enviados com sucesso!")
            return True
        else:
            print(f"{datetime.now()}: Erro ao enviar! {response.status_code} - {response.text}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"{datetime.now()}: Erro na requisição: {e}")
        return False

# ----------------------- RELE -----------------------
def ligar_rele(ser):
    ser.write(b"ATIVAR_RELE")
    time.sleep(7)

    tentativas = int(os.getenv('SETUP_TENTATIVAS'))
    melhor_leitura = []
    max_zeros = -1
    
    for _ in range(tentativas):
        ser.flushInput()
        leitura = ser.readline().decode('utf-8').strip().split(';')
        leitura = [valor for valor in leitura if valor]
    
        num_zeros = leitura.count('0')
        if num_zeros > max_zeros:
            max_zeros = num_zeros
            melhor_leitura = leitura

    return melhor_leitura 

def desligar_rele(ser):
    ser.write(b"DESATIVAR_RELE")
    print(f"{datetime.now()}: ENVIANDO COMANDO DESATIVAR_RELE")
    time.sleep(7)

    tentativas = int(os.getenv('SETUP_TENTATIVAS'))
    melhor_leitura = []
    max_uns = -1

    for _ in range(tentativas):
        ser.flushInput()
        leitura = ser.readline().decode('utf-8').strip().split(';')
        leitura = [valor for valor in leitura if valor]

        num_uns = leitura.count('1')
        if num_uns > max_uns:
            max_uns = num_uns
            melhor_leitura = leitura

    return melhor_leitura  

def verificar_setup(ligado, desligado):
    erradas_ligado = [i+1 for i, valor in enumerate(ligado) if valor != '0']
    erradas_desligado = [i+1 for i, valor in enumerate(desligado) if valor != '1']

    resultado = []
    if erradas_ligado:
        resultado.append(f"Colunas com valores incorretos em 'ligado': {erradas_ligado}")
    else:
        resultado.append("Todos os valores em 'ligado' estão corretos.")
    if erradas_desligado:
        resultado.append(f"Colunas com valores incorretos em 'desligado': {erradas_desligado}")
    else:
        resultado.append("Todos os valores em 'desligado' estão corretos.")
    
    print(f"{datetime.now()}: Resultado da verificação: {resultado}")
    return '\n'.join(resultado), erradas_ligado, erradas_desligado

# ----------------------- SET UP -----------------------
def set_up():
    ser = conectar_serial()
    if not ser:
        print(f"{datetime.now()}: Falha ao conectar no setup. Abortando.")
        return []

    print(f"{datetime.now()}: COM SERIAL: {os.getenv('COM_SERIAL')}")
    ligado = ligar_rele(ser)
    time.sleep(5)
    desligado = desligar_rele(ser)

    print(f"{datetime.now()}: Dados com luz ligada: {ligado}")
    print(f"{datetime.now()}: Dados com luz desligada: {desligado}")
    resultado, erradas_ligado, erradas_desligado = verificar_setup(ligado, desligado)

    queimadas = list(set(erradas_ligado + erradas_desligado))
    ser.close()
    return queimadas

# ----------------------- FUNÇÃO DE CONEXÃO SERIAL -----------------------
def conectar_serial(max_tentativas=5, intervalo=2):
    porta = os.getenv('COM_SERIAL')
    baud = int(os.getenv('BAUD_SERIAL'))
    
    for tentativa in range(max_tentativas):
        try:
            ser = serial.Serial(porta, baud, timeout=1)
            print(f"{datetime.now()}: Conectado à porta {porta} com sucesso!")
            return ser
        except serial.SerialException as e:
            print(f"{datetime.now()}: Tentativa {tentativa + 1}/{max_tentativas} falhou: {e}")
            if tentativa < max_tentativas - 1:
                time.sleep(intervalo)
    print(f"{datetime.now()}: Não foi possível conectar à porta serial após várias tentativas.")
    return None

# -------------------------- PROCESSAMENTO ---------------------------
def process_blocos(queue_dados, stop_flag, intervalo=5):
    blocos = []
    bloco_atual = []
    tempo_inicio = time.time()
    contador_blocos = 1
    ultimo_timestamp = None

    print(f"{datetime.now()}: Iniciando process_blocos")
    while not stop_flag.is_set() or not queue_dados.empty():
        try:
            dado = queue_dados.get(timeout=1)
            timestamp_atual = dado["timestamp"]

            if ultimo_timestamp is None:
                ultimo_timestamp = timestamp_atual

            if (timestamp_atual != ultimo_timestamp and bloco_atual) or (time.time() - tempo_inicio >= intervalo and bloco_atual):
                sucesso = enviar_post(bloco_atual)
                if sucesso:
                    print(f"{datetime.now()}: Bloco {contador_blocos} enviado com {len(bloco_atual)} leituras")
                else:
                    print(f"{datetime.now()}: Falha ao enviar bloco {contador_blocos}. Salvando localmente.")
                    salvar_blocos_json(bloco_atual)
                    blocos.append(bloco_atual)
                    if len(blocos) > 100:
                        blocos.pop(0)

                contador_blocos += 1
                bloco_atual = []
                tempo_inicio = time.time()

            bloco_atual.append(dado)
            ultimo_timestamp = timestamp_atual

        except queue.Empty:
            # Tenta enviar blocos pendentes mesmo se a fila estiver vazia
            if bloco_atual and time.time() - tempo_inicio >= intervalo:
                sucesso = enviar_post(bloco_atual)
                if sucesso:
                    print(f"{datetime.now()}: Bloco {contador_blocos} enviado com {len(bloco_atual)} leituras")
                else:
                    print(f"{datetime.now()}: Falha ao enviar bloco {contador_blocos}. Salvando localmente.")
                    salvar_blocos_json(bloco_atual)
                    blocos.append(bloco_atual)
                    if len(blocos) > 100:
                        blocos.pop(0)
                contador_blocos += 1
                bloco_atual = []
                tempo_inicio = time.time()
            continue

    if bloco_atual:
        sucesso = enviar_post(bloco_atual)
        if sucesso:
            print(f"{datetime.now()}: Bloco {contador_blocos} enviado com {len(bloco_atual)} leituras")
        else:
            print(f"{datetime.now()}: Falha ao enviar bloco {contador_blocos}. Salvando localmente.")
            salvar_blocos_json(bloco_atual)
            blocos.append(bloco_atual)

    print(f"{datetime.now()}: Finalizando process_blocos. Total de blocos processados: {len(blocos)}")

# ----------------------- SALVAR DADOS NO JSON -----------------------
def salvar_blocos_json(bloco):
    folder_path = "Files"
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)

    timestamp_arq = datetime.now().strftime("%Y.%m.%d_%H.%M.%S")
    json_name = os.path.join(folder_path, f'Leitura_{timestamp_arq}.json')

    dados_existentes = []
    for dado in bloco:
        if isinstance(dado, dict):
            dados_existentes.append(dado)

    with open(json_name, 'w') as file:
        json_str = json.dumps(dados_existentes, separators=(',', ':'), ensure_ascii=False, indent=4)
        json_str = json_str.replace('\n            ', '').replace('\n        ]', ']')
        file.write(json_str)
    print(f"{datetime.now()}: Dados salvos em {json_name}")

# ----------------------- LEITURA -----------------------
def read_data(queue_dados, stop_flag, queimadas, quant_sensor):
    ser = None
    ultimo_dado = time.time()
    while not stop_flag.is_set():
        if ser is None or not ser.is_open:
            ser = conectar_serial()
            if ser is None:
                time.sleep(5)
                continue
            try:
                ser.write(b"ATIVAR_RELE")
                time.sleep(7)
                ser.flushInput()
                print(f"{datetime.now()}: Conexão inicializada com sucesso.")
            except (serial.SerialException, termios.error) as e:
                print(f"{datetime.now()}: Erro ao inicializar conexão: {e}. Tentando reconectar...")
                ser.close()
                ser = None
                continue

        try:
            if ser.in_waiting > 0:
                timestamp = datetime.now().strftime("%Y.%m.%d_%H.%M.%S")
                linha = ser.readline().decode('utf-8').strip()
                print(f"{timestamp}: Dados recebidos: {linha}")
                ultimo_dado = time.time()

                leituras = linha.split(';')
                leituras = [leitura for leitura in leituras if leitura]

                if len(leituras) != quant_sensor:
                    print(f"{timestamp}: Leitura ignorada: {leituras}. Tamanho incorreto, esperado {quant_sensor} leituras.")
                    continue

                largura, percBloq = calculo(leituras, queimadas)
                dado = {
                    "leituras": leituras,
                    "largura": largura,
                    "percentual_bloqueado": percBloq,
                    "timestamp": timestamp
                }
                try:
                    print(f"{timestamp}: Tamanho da fila antes de adicionar: {queue_dados.qsize()}")
                    queue_dados.put(dado, timeout=1)
                except queue.Full:
                    print(f"{timestamp}: Fila cheia! Descartando dado: {dado}")
            elif time.time() - ultimo_dado > 30:
                print(f"{datetime.now()}: Nenhum dado recebido por 30s. Reiniciando conexão.")
                ser.close()
                ser = None

        except serial.SerialException as e:
            print(f"{datetime.now()}: Erro na leitura serial: {e}. Tentando reconectar...")
            ser.close()
            ser = None
        except termios.error as e:
            print(f"{datetime.now()}: Erro de I/O na serial (termios): {e}. Tentando reconectar...")
            ser.close()
            ser = None
        except Exception as e:
            print(f"{datetime.now()}: Erro inesperado na leitura: {e}")
            ser.close()
            ser = None
        time.sleep(0.1)

    if ser and ser.is_open:
        ser.close()
    print(f"{datetime.now()}: Leitura finalizada.")

# ----------------------- INICIALIZAÇÃO -----------------------
def start_reading(queimadas):
    folder_path = "Files"
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)

    quant_sensor = int(os.getenv('QUANT_SENSOR'))
    queue_dados = queue.Queue(maxsize=1000)
    stop_flag = threading.Event()
    
    thread_processamento = threading.Thread(target=process_blocos, args=(queue_dados, stop_flag))
    thread_processamento.start()
    
    try:
        read_data(queue_dados, stop_flag, queimadas, quant_sensor)
    except KeyboardInterrupt:
        print(f"{datetime.now()}: Programa interrompido pelo usuário.")
        stop_flag.set()

    stop_flag.set()
    thread_processamento.join()

# ----------------------- CÁLCULO -----------------------
def calculo(leituras, queimadas):
    largura = 0
    recepBloq = 0
    quant_sensor = int(os.getenv('QUANT_SENSOR'))
    
    for i, leitura in enumerate(leituras):
        if leitura == "1" and (i + 1) not in queimadas:
            largura += float(os.getenv('CALCULO_LARGURA'))
            recepBloq += 1
    percBloq = (recepBloq / quant_sensor) * 100
    return largura, percBloq

# ----------------------- MAIN -----------------------
if __name__ == "__main__":
    queimadas = set_up()
    start_reading(queimadas)
import threading
import queue
from dotenv import load_dotenv
import os
import serial
import json
import time
from datetime import datetime
import requests

load_dotenv()

# ----------------------- POST -----------------------
def enviar_post(json_data):
    base_url = os.getenv('BASE_URL')
    equipamento_id = os.getenv('EQUIP_ID')
    url = f"{base_url}leituras?id={equipamento_id}"

    try:
        response = requests.post(url, json=json_data)
        if response.status_code == 200:
            print("Dados enviados!")
            return True
        else:
            print("Erro ao enviar! {response.status_code} - {response.text}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"Erro na requisição: {e}")
        return False
    
# ----------------------- RELE -----------------------
def ligar_rele(ser):
    ser.write(b"ATIVAR_RELE")
    time.sleep(7)

    tentativas = int(os.getenv('SETUP_TENTATIVAS'))
    melhor_leitura = []
    max_zeros = -1
    
    for _ in range(tentativas):
        ser.flushInput()  # limpa buffer
        leitura = ser.readline().decode('utf-8').strip().split(';')
        leitura = [valor for valor in leitura if valor]
    
        num_zeros = leitura.count('0')
        if num_zeros > max_zeros:
            max_zeros = num_zeros
            melhor_leitura = leitura

    return melhor_leitura 

def desligar_rele(ser):
    ser.write(b"DESATIVAR_RELE")
    print('ENVIANDO COMANDO 2')
    time.sleep(7)

    tentativas = int(os.getenv('SETUP_TENTATIVAS'))
    melhor_leitura = []
    max_uns = -1

    for _ in range(tentativas):
        ser.flushInput()  # limpa buffer
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
    
    print(f"Resultado da verificação: {resultado}")
    return '\n'.join(resultado), erradas_ligado, erradas_desligado

# ----------------------- SET UP -----------------------
def set_up():
    ser = serial.Serial(os.getenv('COM_SERIAL'), int(os.getenv('BAUD_SERIAL')))
    print(f"COM SERIAL: {os.getenv('COM_SERIAL')}")

    ligado = ligar_rele(ser)
    time.sleep(5)
    desligado = desligar_rele(ser)

    print("Dados com luz ligada:", ligado)
    print("Dados com luz desligada:", desligado)
    resultado, erradas_ligado, erradas_desligado = verificar_setup(ligado, desligado)

    queimadas = list(set(erradas_ligado + erradas_desligado))
    ser.close()

    return queimadas

# -------------------------- PROCESSAMENTO ---------------------------

def process_blocos(queue_dados, stop_flag, intervalo=5):
    blocos = []
    bloco_atual = []
    tempo_inicio = time.time()
    contador_blocos = 1
    ultimo_timestamp = None

    while not stop_flag.is_set() or not queue_dados.empty():
        try:
            dado = queue_dados.get(timeout=1)
            timestamp_atual = dado["timestamp"]

            if ultimo_timestamp is None:
                ultimo_timestamp = timestamp_atual

            # Se o timestamp mudou ou o intervalo foi atingido, envia o bloco atual
            if (timestamp_atual != ultimo_timestamp and bloco_atual) or (time.time() - tempo_inicio >= intervalo and bloco_atual):
                sucesso = enviar_post(bloco_atual)
                if sucesso:
                    print(f"Bloco {contador_blocos} enviado com {len(bloco_atual)} leituras")
                else:
                    print(f"Falha ao enviar bloco {contador_blocos}. Mantendo no array.")
                    blocos.append(bloco_atual)

                contador_blocos += 1
                bloco_atual = []
                tempo_inicio = time.time()  # Reinicia o tempo após enviar o bloco

            bloco_atual.append(dado)
            ultimo_timestamp = timestamp_atual  # Atualiza o último timestamp processado

        except queue.Empty:
            continue

    # Enviar o último bloco que restar
    if bloco_atual:
        sucesso = enviar_post(bloco_atual)
        if sucesso:
            print(f"Bloco {contador_blocos} enviado com {len(bloco_atual)} leituras")
        else:
            print(f"Falha ao enviar bloco {contador_blocos}. Mantendo no array.")
            blocos.append(bloco_atual)

    print(f"Total de blocos processados: {len(blocos)}")

# ----------------------- SALVAR DADOS NO JSON -----------------------
def salvar_blocos_json(bloco):
    folder_path = "Files"
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)

    timestamp_arq = datetime.now().strftime("%Y.%m.%d")
    json_name = os.path.join(folder_path, f'Leitura_{timestamp_arq}.json')

    try:
        # Se o arquivo JSON já existe, abre para leitura e adiciona mais dados
        with open(json_name, 'r') as file:
            dados_existentes = json.load(file)
            # Garante que os dados existentes são uma lista
            if not isinstance(dados_existentes, list):
                dados_existentes = []
    except FileNotFoundError:
        # Cria uma lista vazia se o arquivo não existe
        dados_existentes = []

    # Garante que apenas o bloco atual seja adicionado, sem incluir leituras acumuladas
    for dado in bloco:
        if isinstance(dado, dict):
            dados_existentes.append(dado) 

    # Escreve os dados corrigidos no arquivo JSON
    with open(json_name, 'w') as file:
        # Usa indentação apenas para o nível superior, mas mantém o array "leituras" em uma linha
        json_str = json.dumps(dados_existentes, separators=(',', ':'), ensure_ascii=False, indent=4)
        # Remove quebras de linha e espaços dentro do array "leituras"
        json_str = json_str.replace('\n            ', '').replace('\n        ]', ']')
        file.write(json_str)

# ----------------------- LEITURA -----------------------
def read_data(ser, queue_dados, stop_flag, queimadas, quant_sensor):
    try:
        while not stop_flag.is_set():
            if ser.in_waiting > 0:
                timestamp = datetime.now().strftime("%Y.%m.%d_%H.%M.%S")
                linha = ser.readline().decode('utf-8').strip()

                leituras = linha.split(';')
                leituras = [leitura for leitura in leituras if leitura]

                if len(leituras) != quant_sensor:
                    print(f"Leitura ignorada: {leituras}. Tamanho incorreto, esperado {quant_sensor} leituras.")
                    continue

                largura, percBloq = calculo(leituras, queimadas)
                
                dado = {
                    "leituras": leituras,
                    "largura": largura,
                    "percentual_bloqueado": percBloq,
                    "timestamp": timestamp
                }
                queue_dados.put(dado)  # Coloca o dado na fila para processamento
                time.sleep(0.1)  # Pequeno atraso entre leituras

    except KeyboardInterrupt:
        print("Leitura interrompida pelo usuário.")
        stop_flag.set()
    finally:
        ser.close()

# ----------------------- INICIALIZAÇÃO -----------------------
def start_reading(queimadas):
    folder_path = "Files"
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)

    ser = serial.Serial(os.getenv('COM_SERIAL'), int(os.getenv('BAUD_SERIAL')))
    quant_sensor = int(os.getenv('QUANT_SENSOR'))

    # Garante que o relé está ativado (luz ligada)
    ser.write(b"ATIVAR_RELE")
    time.sleep(7)  # Tempo para o relé estabilizar

    # Limpa o buffer da porta serial
    ser.flushInput()

    # Cria uma fila para armazenar os dados lidos e um sinalizador de parada
    queue_dados = queue.Queue()
    stop_flag = threading.Event()
    
    # Inicia uma thread para processar os blocos de dados em paralelo
    thread_processamento = threading.Thread(target=process_blocos, args=(queue_dados, stop_flag))
    thread_processamento.start()
    
    # Inicia a leitura dos dados da serial e os coloca na fila para processamento
    read_data(ser, queue_dados, stop_flag, queimadas, quant_sensor)

    # Após a leitura, sinaliza para a thread de processamento parar e aguarda sua finalização
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
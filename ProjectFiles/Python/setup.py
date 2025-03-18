from dotenv import load_dotenv
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime
import serial
import csv
import time
import paramiko
import tkinter as tk
import threading

load_dotenv()

# ----------------------- INTERFACE -----------------------
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Status")
        self.geometry("500x400")
        self.attributes('-fullscreen',True)
        self.configure(bg='white')

        self.start_button = tk.Button(self, text="Iniciar Setup", command=self.start_setup, font=("Arial", 80))
        self.start_button.pack(pady=250)

        self.status_label = tk.Label(self, text="", font=("Arial", 80), bg=self.cget('bg'))
        self.status_label.pack(pady=10, padx=10, expand=True)

        self.stop_reading = False  # Flag to stop reading

    def start_setup(self):
        self.start_button.pack_forget()
        
        # Ocultar botões de reiniciar e fechar, se visíveis
        if hasattr(self, 'restart_button') and self.restart_button.winfo_ismapped():
            self.restart_button.pack_forget()
        if hasattr(self, 'close_button') and self.close_button.winfo_ismapped():
            self.close_button.pack_forget()

        self.update_status("SetUp", "yellow")
        self.configure(bg='yellow')
        self.update()

        threading.Thread(target=self.run_setup).start()


    def start_reading_thread(self, queimadas):
        thread = threading.Thread(target=self.start_reading, args=(queimadas,))
        thread.start()

    def update_status(self, text, bg):
        self.status_label.config(text=text, background=bg)

    def run_setup(self):
        queimadas = set_up()

        self.update_status("Leitura", "green")
        self.configure(bg='green')
        self.stop_reading = False
        self.create_stop_button()

        self.after(1000, self.start_reading_thread, queimadas)

    def create_stop_button(self):
        self.stop_button = tk.Button(self, text="Finalizar Leitura", command=self.stop_reading_function, font=("Arial", 50))
        self.stop_button.pack(pady=40)

    def stop_reading_function(self):
        self.stop_reading = True
        self.update_status("Leitura Interrompida", "red")
        self.configure(bg='red')

        self.stop_button.pack_forget()

        self.restart_button = tk.Button(self, text="Reiniciar Leitura", command=self.start_setup, font=("Arial", 50))
        self.restart_button.pack(pady=10)

        self.close_button = tk.Button(self, text="Fechar", command=self.close_application, font=("Arial", 50))
        self.close_button.pack(pady=10)

    def close_application(self):
        self.stop_reading = True
        self.destroy()

    def start_reading(self, queimadas):
        folder_path = "Files"
        if not os.path.exists(folder_path):
            os.makedirs(folder_path)

        ser = serial.Serial(os.getenv('COM_SERIAL'), int(os.getenv('BAUD_SERIAL')))

        timestamp_arq = datetime.now().strftime("%Y.%m.%d")
        csvName = os.path.join(folder_path, f'Leitura_{timestamp_arq}.csv')

        quant_sensor = int(os.getenv('QUANT_SENSOR'))

        file_exists = os.path.isfile(csvName)

        with open(csvName, 'a' if file_exists else 'w', newline='') as arqCSV:
            print(f"-------------FIM DO SETUP-------------")
            escritaCSV = csv.writer(arqCSV, delimiter=';')

            if not file_exists:
                cabecalho = [str(i) for i in range(quant_sensor)] + ["Largura", "Percentual Bloqueado", "Timestamp", "Queimados"]
                escritaCSV.writerow(cabecalho)

            ser.write(b"ATIVAR_RELE")
            time.sleep(5)

            try:
                self.read_data(ser, escritaCSV, csvName, queimadas, quant_sensor)
            except KeyboardInterrupt:
                print("Leitura interrompida.")
                ser.write(b"DESATIVAR_RELE")
            finally:
                ser.close()

        # Se a leitura foi finalizada
        enviar_arquivos_sftp(csvName)

        if not self.stop_reading:
            self.update_status("Fim da Leitura", "red")
            self.configure(bg='red')
            self.destroy()


    def read_data(self, ser, escritaCSV, csvName, queimadas, quant_sensor):
        while not self.stop_reading:
            if ser.in_waiting > 0:
                timestamp = datetime.now().strftime("%Y.%m.%d_%H.%M.%S")
                linha = ser.readline().decode('utf-8').strip()

                leituras = linha.split(';')
                leituras = [leitura for leitura in leituras if leitura]

                if len(leituras) != quant_sensor:
                    print(f"Leitura ignorada: {leituras}. Tamanho incorreto, esperado {quant_sensor} leituras.")
                    continue

                largura, percBloq = calculo(leituras, queimadas)

                linha_csv = leituras + [f"{largura}", f"{percBloq:.3f}", timestamp, f"{queimadas}"]
                escritaCSV.writerow(linha_csv)

                print(f"{leituras}, Largura: {largura} cm, Receptores Bloqueados: {percBloq:.2f}%, Timestamp: {timestamp}, Equipamento ID: 1")

# ----------------------- SET UP -----------------------
def set_up():
    ser = serial.Serial(os.getenv('COM_SERIAL'), int(os.getenv('BAUD_SERIAL')))
    print(os.getenv('COM_SERIAL'))

    ligado = ligar_rele(ser)
    time.sleep(5)
    desligado = desligar_rele(ser)

    print("Dados com luz ligada:", ligado)
    print("Dados com luz desligada:", desligado)
    resultado, erradas_ligado, erradas_desligado = verificar_setup(ligado, desligado)

    queimadas = list(set(erradas_ligado + erradas_desligado))

    if queimadas:
        enviar_email_setup(resultado)
    
    ser.close()

    return queimadas

def ligar_rele(ser):
    ser.write(b"ATIVAR_RELE")
    time.sleep(7)

    tentativas = int(os.getenv('SETUP_TENTATIVAS'))
    melhor_leitura = []
    max_zeros = -1

    for _ in range(tentativas):
        leitura = ser.readline().decode('utf-8').strip().split(';')
        leitura = [valor for valor in leitura if valor]

        num_zeros = leitura.count('0')
        if num_zeros > max_zeros:
            max_zeros = num_zeros
            melhor_leitura = leitura
        
    return melhor_leitura 

def desligar_rele(ser):
    ser.write(b"DESATIVAR_RELE")
    time.sleep(7)

    tentativas = int(os.getenv('SETUP_TENTATIVAS'))
    melhor_leitura = []
    max_uns = -1

    for _ in range(tentativas):
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
    
    print(resultado)
    return '\n'.join(resultado), erradas_ligado, erradas_desligado

def enviar_email_setup(resultado):
    REMETENTE = os.getenv('MAIL_SETUP_REMETENTE')
    DESTINATARIO  = os.getenv('MAIL_SETUP_DESTINATARIO')
    PASSWORD = os.getenv('MAIL_SETUP_PASSWORD')
    SERVER = os.getenv('MAIL_SETUP_SERVER')
    PORT = os.getenv('MAIL_SETUP_PORT')

    msg = MIMEMultipart()
    msg['From'] = REMETENTE
    msg['To'] = DESTINATARIO
    msg['Subject'] = "Resultado da Verificação de Sensores"

    msg.attach(MIMEText(resultado, 'plain'))

    try:
        with smtplib.SMTP_SSL(SERVER, PORT) as server:
            server.login(REMETENTE, PASSWORD)
            server.send_message(msg)
        print("E-mail enviado com sucesso.")
    except Exception as e:
        print(f"Erro ao enviar e-mail: {e}")

# ----------------------- LEITURA -----------------------
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

# ----------------------- SFTP -----------------------
def enviar_arquivos_sftp(local_file):
    try:

        sftp_ip = os.getenv('SFTP_IP')
        sftp_user = os.getenv('SFTP_USER')
        sftp_psw = os.getenv('SFTP_PSW')
        sftp_port = int(os.getenv('SFTP_PORT'))
        sftp_remote_path = os.path.join(os.getenv('SFTP_PATH'), os.path.basename(local_file))

        transport = paramiko.Transport((sftp_ip, sftp_port))
        transport.connect(username=sftp_user, password=sftp_psw)
        
        sftp = paramiko.SFTPClient.from_transport(transport)

        try:
            sftp.chdir(os.getenv('SFTP_PATH'))
        except IOError:
            sftp.mkdir(os.getenv('SFTP_PATH'))
            sftp.chdir(os.getenv('SFTP_PATH'))

        # Upload the file
        sftp.put(local_file, sftp_remote_path)
        print(f"Arquivo {local_file} enviado para {sftp_remote_path} com sucesso.")

        sftp.close()
        transport.close()

    except Exception as e:
        print(f"Erro ao enviar o arquivo para o SFTP: {e}")


if __name__ == "__main__":
    app = App()
    app.mainloop()

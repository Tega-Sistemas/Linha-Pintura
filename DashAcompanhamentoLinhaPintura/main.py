import multiprocessing #import threading
import subprocess

def run_streamlit():
    subprocess.run("streamlit run streamlit_grafico_tempo_real.py",shell=True) #  --server.port 8501

def main():
    run_streamlit()

if __name__ == '__main__':
    main()
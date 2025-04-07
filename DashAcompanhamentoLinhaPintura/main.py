import multiprocessing #import threading
import subprocess

# def run_graph():
#     subprocess.run('python -m http.server 3001',shell=True)
# def run_graph2():
#     subprocess.run('python -m http.server 3002',shell=True)


def run_streamlit():
    subprocess.run("streamlit run streamlit_grafico_tempo_real.py",shell=True) #  --server.port 8501

def main():
    
    # t1 = multiprocessing.Process(target=run_graph)
    # t2 = multiprocessing.Process(target=run_graph2)
    # t3 = multiprocessing.Process(target=run_streamlit)
    # t1.start()
    # t2.start()
    # t3.start()

    # t1.join()
    # t2.join()
    # t3.join()
    run_streamlit()
if __name__ == '__main__':
    main()
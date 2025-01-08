import pandas as pd
import os

def verificar_segmentos(coluna, min_segmento=3):
    valores = coluna.values

    count = 1
    segmentos_validos = [False] * len(valores)

    for i in range(1, len(valores)):
        if valores[i] == valores[i-1]:
            count += 1
        else:
            if count >= min_segmento:
                for j in range(i - count, i):
                    segmentos_validos[j] = True
            count = 1

    if count >= min_segmento:
        for j in range(len(valores) - count, len(valores)):
            segmentos_validos[j] = True

    posicoes_invalidas = [i for i, valido in enumerate(segmentos_validos) if not valido]

    return segmentos_validos, posicoes_invalidas

def corrigir_valor(df, coluna, posicao):
    valores = df[coluna].values

    if posicao > 0 and posicao < len(valores) - 1:
        esquerda = valores[posicao - 1]
        direita = valores[posicao + 1]

        if esquerda == direita:
            valores[posicao] = esquerda
        else:
            if posicao < len(valores) - 2:
                abaixo = valores[posicao + 2]
                if esquerda == abaixo:
                    valores[posicao] = esquerda
                elif direita == abaixo:
                    valores[posicao] = direita

    df[coluna] = valores

def particionar_csv(df, indice_linhas_zero, colunas_utilizadas, nome_base, pasta_saida):
    os.makedirs(pasta_saida, exist_ok=True)
    inicio = 0

    for i, linha_zero in enumerate(indice_linhas_zero + [len(df)]):
        parte = df.iloc[inicio:linha_zero][colunas_utilizadas]

        if not parte.empty:
            nome_arquivo = os.path.join(pasta_saida, f"{nome_base}_parte_{i + 1}.csv")
            parte.to_csv(nome_arquivo, sep=';', decimal=',', index=False)

        inicio = linha_zero + 1

def main():
    # Nome do arquivo original
    nome_arquivo = './Arquivos/Leitura_2024.11.14.csv'

    # Carregar o CSV em um DataFrame
    df = pd.read_csv(nome_arquivo, sep=';', decimal=',')

    # Definir colunas para análise e partição
    colunas_para_verificar = df.columns[:44]
    coluna_timestamp = 'Timestamp'

    # Remover colunas desnecessárias para análise matricial
    colunas_removidas = df[['Largura', 'Percentual Bloqueado', 'Timestamp', 'Queimados']]
    df = df.drop(columns=['Largura', 'Percentual Bloqueado', 'Timestamp', 'Queimados'])

    # Transformar colunas inteiramente formadas por 1 em 0
    for coluna in df.columns:
        if df[coluna].sum() == len(df):
            df[coluna] = 0

    # Verificar e corrigir colunas com problemas
    for coluna in df.columns:
        segmentos_validos, posicoes_invalidas = verificar_segmentos(df[coluna])
        if not all(segmentos_validos):
            for posicao in posicoes_invalidas:
                corrigir_valor(df, coluna, posicao)

    # Identificar linhas que possuem 0 em todas as colunas de 0 a 43
    linhas_zero = df.iloc[:, :44].sum(axis=1) == 0
    indice_linhas_zero = linhas_zero[linhas_zero].index.tolist()

    # Adicionar a coluna 'Timestamp' novamente para a partição
    df[coluna_timestamp] = colunas_removidas[coluna_timestamp]

    # Nome do novo arquivo e pasta para os arquivos particionados
    nome_base = os.path.splitext(os.path.basename(nome_arquivo))[0]
    pasta_saida = './Particionados'

    # Particionar o CSV com base nas linhas de zeros
    particionar_csv(df, indice_linhas_zero, colunas_utilizadas=[coluna_timestamp] + list(df.columns[:44]), nome_base=nome_base, pasta_saida=pasta_saida)

    print(f"Arquivos CSV particionados salvos na pasta '{pasta_saida}'")

# Chamar a função main
if __name__ == "__main__":
    main()

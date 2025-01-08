import pandas as pd
import os

# Retira as linhas inteiramente formadas por 0s, de forma a melhorar o calculo d area total

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

def main():
    # Nome do arquivo original
    nome_arquivo = 'Leitura3_160x683_2250.csv'

    # Carregar o CSV em um DataFrame
    df = pd.read_csv(nome_arquivo, sep=';', decimal=',')

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

    # Calcular a nova coluna 'Largura'
    df['Largura'] = df.apply(lambda row: row.sum() * 0.025, axis=1)

    # Adicionar as colunas removidas novamente, exceto a antiga 'Largura'
    df = pd.concat([df, colunas_removidas.drop(columns=['Largura'])], axis=1)

    # Filtrar as linhas que não possuem nenhum valor 1 nas colunas de índice 0 a 44
    colunas_utilizadas = df.columns[:45]  # Seleciona as colunas de 0 a 44
    df = df[df[colunas_utilizadas].sum(axis=1) > 0]

    # Nome do novo arquivo com '+ NOVO' e salvar na pasta Padrao2
    pasta_padrao2 = './Padrao2'
    os.makedirs(pasta_padrao2, exist_ok=True)
    novo_nome_arquivo = os.path.join(pasta_padrao2, os.path.basename(nome_arquivo).replace('.csv', '_padrao.csv'))

    # Salvar o DataFrame corrigido em um novo CSV
    df.to_csv(novo_nome_arquivo, sep=';', decimal=',', index=False)

    print(f"Arquivo CSV corrigido salvo como '{novo_nome_arquivo}'")

# Chamar a função main
if __name__ == "__main__":
    main()

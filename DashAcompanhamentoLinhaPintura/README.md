# main.py
- Para inicializar o aplicativo basta rodar o arquivo main
```
python .\main
```
- Para alterar a porta do Dash adicionar: "--server.port PORTA" ao final do comando "streamlit run Arquivo.py" 

# streamlit_grafico_tempo_real.py
## Dash para Monitoramento de Esteira de Pintura

Aplicação web para monitoramento em tempo real da utilização de uma esteira de pintura industrial, exibindo métricas de produtividade, tempos de atividade/inatividade e gráficos interativos.

## Funcionalidades Principais

- **Monitoramento em Tempo Real:** Atualizações automáticas a cada 5 segundos.
- **Visualização Interativa:**
  - Gráfico temporal com ocupação da esteira, incluindo intervalos coloridos demarcando períodos:
    - Trabalhando.
    - Desligado.
    - Ligado mas com leitura abaixo da tolerância.
    - Trabalhando fora de horário .
  - Gráfico de barras com distribuição por hora dos dados:
    - Tempo trabalhando.
    - Tempo desligado.
    - Tempo ligado com leitura abaixo da tolerância.
    - Média da porcentagem de ocupação durante o tempo trabalhando.
- **Métricas de Desempenho:**
  - Tempo total de operação.
  - Tempo produtivo vs tempo ocioso.
  - Percentual médio de ocupação.
- **Filtragem por Período:** Seleção de datas para cálculo de estátisticas e gráficos.
- **Identificação Visual:**
  - Destaque de períodos de inatividade.
  - Marcação de intervalos de manutenção/desligamento.

## Pré-requisitos

- Python 3.10.11
- Bibliotecas:
  - streamlit
  - streamlit-autorefresh
  - SQLAlchemy
  - python-dotenv
  - st-theme

## Instalação
- Criar enviorement para python 3.10.11
- Instalar bibliotecas em requirements.txt
- Por fim basta colocar os arquivos e pastas abaixo na mesma pasta e rodar o main.py:
    - .streamlit/ (permite modificar atributos padrão do streamlit, contém config.toml com cores para tema)
    - build/ (Arquivos reacjs compilados para serem utilizados pelo streamlit como custom component)
    - licenses/ (Licenças do plotly e streamlit)
    - .env (deve conter:)
        - TOLERANCIA_ATIVO
        - host
        - user
        - password
        - database
    - main.py
    - requirements.txt
    - streamlit_grafico_tempo_real.py (Lógica principal)


# MyComponent.tsx
## Componente de Gráfico Interativo para Streamlit

Componente React para visualização de dados temporais com Plotly.js integrado ao Streamlit, com suporte a interações avançadas e persistência de estado.

## Funcionalidades Principais
- **Visualização Dinâmica:** Gráficos Plotly com opções de zoom, movimento e download do gráfico como png.
- **Integração com Streamlit em tempo Real:** 
  - Detecta mudanças nos intervalos de tempo sendo utilizados para consulta dos dados.
  - Ajustes automático na vizualização de novos dados.
  - Uso das cores do tema ativo.
- **Persistência de Estado:**
  - Intervalo de zoom selecionado e se deve acompanhar o último valor recebido (Ao receber dados em tempo real e ter o rangeslider ativo).
  - Configurações de legenda e botão selecionado na ModeBar.

## Pré-requisitos
- "@types/react-plotly.js": "^2.6.3",
- "plotly.js": "^3.0.1",
- "react": "^16.13.1",
- "react-dom": "^16.13.1",
- "react-plotly.js": "^2.6.0",
- "streamlit-component-lib": "^2.0.0"


# Desenvolvimento Streamlit e Custom Component
Após a instalação já é possível atualizar o site feito em streamlit, porém para modificar os gráficos que são componentes customizados feitos em react js é preciso utilizar os arquivos na pasta **my_component_STREAMLIT**.

Instalar Node.js

Para instalar os node_modules:
- Navegar até my_component_STREAMLIT/frontend
- Executar: **npm install**

Para criar e utilizar nova build do projeto:
- Navegar até my_component_STREAMLIT/frontend
- Executar: **npm run build**
- Copiar build para pasta "DashAcompanhamentoLinhaPintura"
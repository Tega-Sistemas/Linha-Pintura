import random
import streamlit as st
import streamlit.components.v1 as components
from streamlit_autorefresh import st_autorefresh
import plotly.graph_objects as go

_component_func = components.declare_component(
    "my_component",
    url="http://localhost:3001",
)

def my_component(fig):
    return _component_func(spec=fig.to_json(), default="",key='Gráfico') # Default para evitar None enquanto carrega

# @st.cache_data
# def random_data():
#     return random.sample(range(100), 50), random.sample(range(100), 50)


st.subheader("My Component")

if st.button('ADICIONAR VALORES ANTES'):
    x,y = st.session_state.get('x_y')
    x.append(x[-1] + 1)
    y.append(20)
    st.session_state['x_y'] = [x,y]
    st.rerun()

if 'x_y' not in st.session_state:
    st.session_state['x_y'] = [[1,2,3,4,5],[1,3,7,12,40]]

x,y = st.session_state.get('x_y')



fig = go.Figure(go.Scatter(x=x,y=y,mode='lines+markers'))

if 'layout' in st.session_state:
    layout = st.session_state.get('layout')
    # layout = go.Layout(
    #         # yaxis=dict(
    #         #     range=[0, 100]
    #         # ),
    #         xaxis=dict(
    #             range=[0, 120]
    #         )
    #     )

    fig.layout = layout

fig.update_xaxes(
    rangeslider_visible=True
    )

fig.update_layout(
    title="Gráfico Teste"
    )
v = my_component(fig)


if v:
    new_layout = go.Layout(
        # yaxis=dict(
        #     range=[0, 100]
        # ),
        xaxis=dict(
            range=[v[0], v[1]]
        )
    )

    if 'layout' not in st.session_state or new_layout != st.session_state.get('layout'):
        st.session_state['layout'] = go.Layout(
            # yaxis=dict(
            #     range=[0, 100]
            # ),
            xaxis=dict(
                range=[v[0], v[1]]
            )
        )
        st.rerun()

st.markdown(f'RECEBIDO> {v}')

if st.button('ADICIONAR VALORES DEPOIS'):
    x,y = st.session_state.get('x_y')
    
    x.insert(0,x[0] - 1)
    y.insert(0,10)
    st.session_state['x_y'] = [x,y]
    st.rerun()

st.markdown(len(st.session_state.get('x_y')[0]))

count = st_autorefresh(1 * 5 * 1000)
st.markdown(count)


# x,y = st.session_state.get('x_y')
# x.append(x[-1] + 1)
# y.append(20)
# st.session_state['x_y'] = [x,y]
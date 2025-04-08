import React, { useState,useEffect } from "react"
import { withStreamlitConnection, Streamlit, ComponentProps, Theme } from "streamlit-component-lib"
import Plot from "react-plotly.js"


function MyComponent(props: ComponentProps) {
  const [forceUpdate, setForceUpdate] = useState(0);

  //Inicializar
  useEffect(() => {
    Streamlit.setFrameHeight();
    Streamlit.setComponentReady();
    localStorage.setItem('xaxis_autorange','true');
  }, []);

  const { data, layout, frames, config } = JSON.parse(props.args.spec);
  const [ plotLayout, setPlotLayout ] = useState(layout);

  let change_flag = props.args.change_flag['dates'];
  const theme = props.theme;
  const theme_base = theme?.base || 'light';
  const show_rangeslider = props.args.rangeslider;


    console.log('=========Recebida flag de mudança', change_flag);
    if (typeof change_flag[0] === 'string'){
      change_flag[0] = new Date(`${change_flag[0]}T00:00:00`);
      change_flag[1] = new Date(`${change_flag[1]}T23:59:59`);
    } else {
      console.log('Não convertida', typeof change_flag[0]);
    }

    let storedData = localStorage.getItem('last_dates');
    let saved_lastDates = storedData ? JSON.parse(storedData) : null;
    
    if (saved_lastDates != null && saved_lastDates[0] != null){
      saved_lastDates[0] = new Date(saved_lastDates[0]);
      saved_lastDates[1] = new Date(saved_lastDates[1]);
    } else {
      console.log('Não convertida last dates', saved_lastDates);
      saved_lastDates = change_flag;
    }

    // Caso datas mudaram
    storedData = localStorage.getItem('xaxis_range');
    const saved_Range = storedData ? JSON.parse(storedData) : null;
    const saved_autoRange = localStorage.getItem('xaxis_autorange') === 'true';
    const saved_update_last = localStorage.getItem('update_last') === 'true';
    const saved_dragmode = localStorage.getItem('dragmode');
    
  //Processar Array com visibilidades das legendas caso esteja vazio, tenha tamanho diferente dos dados recebidos ou periodo de tempo mudou
  const saved_showLegend = JSON.parse(localStorage.getItem('showLegend') || '[]');
  // if (saved_showLegend.length === 0 
  //   || data.length !== saved_showLegend.length 
  //   || (saved_lastDates[0] !== -1 && (
  //     saved_lastDates[0].getTime() !== change_flag[0].getTime() 
  //     || saved_lastDates[1].getTime() !== change_flag[1].getTime()
  //   ))
  // ){
  //   const novo_array = data.map((traceData: any) => {
  //       if (!('visible' in traceData)) return false;
  //       return traceData.visible === 'legendonly' ? 'legendonly' : traceData.visible;
  //   });
  // }else{
  //    console.log('Array já existe',saved_showLegend);
  // }

  // Caso datas mudaram  Remover 
  if (saved_lastDates[0] !== -1 && (saved_lastDates[0].getTime() !== change_flag[0].getTime() || saved_lastDates[1].getTime() !== change_flag[1].getTime())){
      localStorage.setItem('last_dates',JSON.stringify(change_flag));
      localStorage.setItem('xaxis_autorange','true');
      plotLayout.xaxis = { ...plotLayout.xaxis,'autorange':saved_autoRange,'rangeslider':{'visible':show_rangeslider}};

  // Se está na data de hpje e variável saved_update_last está True
  } else if (!saved_autoRange && saved_update_last && (saved_lastDates[0] <= new Date() && new Date() <= saved_lastDates[1])){
      if (saved_Range[0] >= data[0]['x'][data[0]['x'].length - 1]){
        saved_Range[0] = data[0]['x'][data[0]['x'].length - 1]
      }
      plotLayout.xaxis = { ...plotLayout.xaxis,'range':[saved_Range[0],data[0]['x'][data[0]['x'].length - 1]],'rangeslider':{'visible':show_rangeslider}}
  
  // Atualizar com último range
  } else if (saved_lastDates[0] !== -1) {
      if(!saved_autoRange){
        plotLayout.xaxis = { ...plotLayout.xaxis,'range':saved_Range,'rangeslider':{'visible':show_rangeslider}};
      } else {
        plotLayout.xaxis = { ...plotLayout.xaxis,'autorange':saved_autoRange,'rangeslider':{'visible':show_rangeslider}};
      }
  }

  plotLayout['dragmode'] = saved_dragmode

//////////// handleLegendClick
const handleLegendClick = (eventData: any) => {
  console.log('INTERAÇÃO LEGENDA', eventData.curveNumber);
  
  const last_a = JSON.parse(localStorage.getItem('showLegend') || '[]')
  if (last_a.length === 0){
      const novo_array = data.map((traceData: any, index: number) => {
        if (eventData.curveNumber === index) {
          return traceData.visible === 'legendonly' ? true : 'legendonly';
        }
        if ('visible' in traceData) {
          return traceData.visible === 'legendonly'
            ? 'legendonly'
            : traceData.visible === true
            ? true
            : false;
        }
        return false;
      });
      localStorage.setItem('showLegend',JSON.stringify(novo_array));
  } else {
      last_a[eventData.curveNumber] = last_a[eventData.curveNumber] === 'legendonly'
      ? true
      : 'legendonly';
      localStorage.setItem('showLegend',JSON.stringify(last_a));
  }

    setForceUpdate((prev: number) => 1 - prev);
  return false;
  };
  // Não deve funcionar por legendclick retornar false 
  const handleLegendDoubleClick = (eventData: any) => {
    // console.log('INTERAÇÃO LEGENDA double', eventData.curveNumber);

    return false;
  };

//////////// handleRelayout
  const handleRelayout = (eventData: any) => {
      const data_atual = new Date();
      const savedRange = localStorage.getItem('xaxis_range');

      // botão reset e autoscale
      if (eventData['xaxis.showspikes'] || eventData['xaxis.autorange']){
          //Streamlit.setComponentValue('reset')
          layout['xaxis'] = {...layout.xaxis,'autorange':true,'rangeslider':{'visible':show_rangeslider}};
          localStorage.setItem('xaxis_autorange','true');
          localStorage.setItem('update_last','false');
          setPlotLayout(layout);
      } else if (eventData['xaxis.range[0]'] && eventData['xaxis.range[1]']) {
          //Streamlit.setComponentValue([eventData['xaxis.range[0]'], eventData['xaxis.range[1]']])
          const last_x = [eventData['xaxis.range[0]'], eventData['xaxis.range[1]']];
          
          // SE HOJE ESTÁ NO INTERVALO CHECAR SE ÚLTIMO X ESTÁ ACIMA DO LIMITE 
          const last_date = new Date(data[0]['x'][data[0]['x'].length - 1]);
          if ( saved_lastDates[0] <= data_atual && data_atual <= saved_lastDates[1]){
            if (new Date(last_x[1]) >= last_date && show_rangeslider){
              console.log('ACOMPANHAR X');
              localStorage.setItem('update_last','true');
              last_x[1] = data[0]['x'][data[0]['x'].length - 1];
            } else {
              console.log('FIXAR X');
              localStorage.setItem('update_last','false');
            }
          } else {
            console.log('HOJE NÃO ESTÁ CONTIDO NO INTERVALO DE TEMPO',saved_lastDates[0],data_atual,saved_lastDates[1]);
            // REMOVER update_last
            localStorage.removeItem('update_last');
          }

          localStorage.setItem('xaxis_range', JSON.stringify(last_x));
          layout['xaxis'] = {...layout.xaxis,'range':last_x,'autorange':false,'rangeslider':{'visible':show_rangeslider}};
          
          localStorage.setItem('xaxis_autorange','false');
          
          setPlotLayout(layout);
      } else if (eventData['xaxis.range'] && eventData['xaxis.range'][0] && eventData['xaxis.range'][1] && show_rangeslider){
          //Streamlit.setComponentValue([eventData['xaxis.range'][0], eventData['xaxis.range'][1]])
          const last_x = [eventData['xaxis.range'][0], eventData['xaxis.range'][1]];
          
          // SE HOJE ESTÁ NO INTERVALO CHECAR SE ÚLTIMO X ESTÁ ACIMA DO LIMITE 
          const last_date = new Date(data[0]['x'][data[0]['x'].length - 1]);
          if ( saved_lastDates[0] <= data_atual && data_atual <= saved_lastDates[1]){
            if (new Date(last_x[1]) > last_date){
              localStorage.setItem('update_last','true');
              last_x[1] = data[0]['x'][data[0]['x'].length - 1];
            } else {
              localStorage.setItem('update_last','false');
            }
          } else {
            // REMOVER update_last
            localStorage.removeItem('update_last');
          }

          localStorage.setItem('xaxis_range', JSON.stringify(last_x));
          layout['xaxis'] = {...layout.xaxis,'range':last_x,'autorange':false,'rangeslider':{'visible':show_rangeslider}};
          
          localStorage.setItem('xaxis_autorange','false');
      } else if('dragmode' in eventData){
        localStorage.setItem('dragmode', eventData['dragmode']);
      }
    };

    //SISTEMA PARA TRATAR X0 maior que X1
    if ('xaxis' in plotLayout && 'range' in plotLayout['xaxis'] && plotLayout['xaxis']['range'] !== null && new Date(plotLayout['xaxis']['range'][0]) > new Date(plotLayout['xaxis']['range'][1])){
      const aux = plotLayout['xaxis']['range'][0];
      plotLayout['xaxis']['range'][0] = plotLayout['xaxis']['range'][1];
      plotLayout['xaxis']['range'][1] = aux;
    }

    //SISTEMA PARA ATUALIZAR BACKGROUND (já ajusto no python)
    plotLayout['plot_bgcolor'] = 'rgba(240, 240, 240, 0)'
    
    const saved_showLegend_load = JSON.parse(localStorage.getItem('showLegend') || '[]');
    console.log('CARREGAR LEGENDA: ',saved_showLegend_load)
    if (data.length > 1){
      saved_showLegend_load.forEach((legendVisible:any, index:number) => {
          if (data[index] && (legendVisible === true || legendVisible === 'legendonly')){
            if ('visible' in data[index]){
              data[index]['visible'] = legendVisible
            } else {
              data[index] = {...data[index], 'visible':legendVisible}
            }
          }/* else {
            console.log('Op 3', index)
          }*/
      })
    }
    
    
    // if (theme_base === 'light'){
    if (theme){
      const backgroundColor = theme['backgroundColor'];
      const bodyFont = theme['bodyFont' as keyof Theme];
      const primaryColor = theme['primaryColor'];
      const secondaryBackgroundColor = theme['secondaryBackgroundColor'];
      const textColor = theme['textColor']
      
      plotLayout['paper_bgcolor'] = backgroundColor;//'rgba(255, 255, 255, 0.9)';
      plotLayout['template'] = 'plotly';
      if ('font' in plotLayout){
        plotLayout['font']['color'] = textColor//'black';
        plotLayout['font']['family'] = bodyFont
      } else {
        plotLayout['font'] = {'color': textColor, 'family': bodyFont}//'black'}
      }
    }

    //   //plotLayout['modebar'] = { color: 'lightgray', activecolor: 'white',bgcolor: 'rgba(0, 0, 0, 0.7)' };
    plotLayout['modebar'] = { color: 'darkgray', activecolor: 'white' ,bgcolor: 'rgba(0 0, 0, 0.7)'};
    plotLayout['legend'] = {...plotLayout.legend, 'itemdoubleclick':false} 
    console.log('layout', plotLayout)
    console.log('data', data)
    // console.log('ARRAY DAS LEGENDAS', saved_showLegend_load)

    return (
      <Plot
        data={data}
        layout={plotLayout}
        onRelayout={handleRelayout}
        onLegendClick={handleLegendClick}
        // onLegendDoubleClick={handleLegendDoubleClick}
        style={{ width: "100%", height: "100%" }}
        //useResizeHandler={true}
        frames={frames}
        // onUpdate={handleUpdate}
        useResizeHandler={true}
        config={{
          'showLink': false,
          'displaylogo': false,
          'showTips':false,
          'modeBarButtonsToRemove': ['resetScale2d','lasso2d','select2d'],
          'toImageButtonOptions': {
            'filename': 'grafico_leituras',
            'format': 'png', // one of png, svg, jpeg, webp
            // 'height': 500,
            // 'width': 700,
            'scale': 2 // Multiply title/legend/axis/canvas sizes by this factor
          }
        }}
      />
    )
}

export default withStreamlitConnection(MyComponent)
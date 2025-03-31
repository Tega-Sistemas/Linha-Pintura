import React, { useState,useEffect } from "react"
import { withStreamlitConnection, Streamlit, ComponentProps } from "streamlit-component-lib"
import Plot from "react-plotly.js"

// let isMouseDown = false;
// let last_read_time = Date.now();
// let last_x: number[] = []


// function liberarMouseLIsten(){
//   document.removeEventListener('mousedown', handleMouseDown);
//   document.removeEventListener('mouseup', handleMouseUp);
//   document.removeEventListener('mouseleave', handleMouseLeave);
//   isMouseDown = false
// }

// function handleMouseDown(){
//   isMouseDown = true;
//   console.log("Mouse pressionado");
// }

// function Enviarlastx(){
//   isMouseDown = false;
//   console.log('Esperar para enviar')
//   last_read_time = Date.now();
//   setTimeout(() => {
//     if (Date.now() - last_read_time >= 50) {  // Confirma que o tempo passou
//         if (last_x) {
//             console.log("Enviar", last_x);
//             Streamlit.setComponentValue(last_x);
//             last_x = [];
//             liberarMouseLIsten();
//         }
//     }
// }, 1000);
// }

// function handleMouseUp(){
//   //if (isMouseDown) {
//   console.log("Mouse liberado");
//   Enviarlastx()
//   //}
// }
// function handleMouseLeave(){
//   // if (isMouseDown) {
//   console.log("Mouse saiu da janela (clicado)");
//   Enviarlastx()
//   // }
// }

function MyComponent(props: ComponentProps) {
  //  const [plotSpec, setPlotSpec] = useState(() => JSON.parse(props.args.spec));
    useEffect(() => {
      // Set the component height and notify Streamlit we're ready
      Streamlit.setFrameHeight();
      Streamlit.setComponentReady();
    }, []);
    
    const { data, layout, frames, config } = JSON.parse(props.args.spec);

    const [plotLayout, setPlotLayout] = useState(layout);

    // const [testLayout,updateTestLayout] = useState(layout)

    let change_flag = props.args.change_flag['dates'];
    console.log('=========Recebida flag de mudança', change_flag);
    if (typeof change_flag[0] === 'string'){
      change_flag[0] = new Date(`${change_flag[0]}T00:00:00`);
      change_flag[1] = new Date(`${change_flag[1]}T23:59:59`);
      console.log('Convertida flag de mudança', change_flag);
    } else {
      console.log('Não convertida', typeof change_flag[0]);
    }

    let storedData = localStorage.getItem('last_dates');
    let saved_lastDates = storedData ? JSON.parse(storedData) : null;
    
    console.log('Carregado lastDates', saved_lastDates)
    if (saved_lastDates != null && saved_lastDates[0] != null){
      saved_lastDates[0] = new Date(saved_lastDates[0]);
      saved_lastDates[1] = new Date(saved_lastDates[1]);
      console.log('Convertida last dates', saved_lastDates);
    } else {
      console.log('Não convertida last dates', saved_lastDates);
      saved_lastDates = [-1,-1];
    }

    // Caso datas mudaram
    

    storedData = localStorage.getItem('xaxis_range');
    const saved_Range = storedData ? JSON.parse(storedData) : null;
    const saved_autoRange = localStorage.getItem('xaxis_autorange') === 'true';
    const saved_update_last = localStorage.getItem('update_last') === 'true';
    const saved_dragmode = localStorage.getItem('dragmode');

    
    console.log('Carregado savedRange', saved_Range);
    console.log('Carregado update_last', saved_update_last);
    console.log('Carregado autoRange', saved_autoRange);

  // ATUALIZAR LAYOUT Tratar caso a caso direto
    // Novos dados recebidos
    
  // Caso datas mudaram  Remover 
  if (saved_lastDates[0].getTime() !== change_flag[0].getTime() || saved_lastDates[1].getTime() !== change_flag[1].getTime()){// && (saved_lastDates[0] > new Date() || new Date() > saved_lastDates[1])){
    //Por que está entrando se são iguais ?
    
    console.log('Opcao 1', saved_autoRange, saved_lastDates[0].getTime() !== change_flag[0].getTime(), saved_lastDates[1].getTime() !== change_flag[1].getTime(),saved_lastDates,change_flag);
      console.log('>>>>',plotLayout['xaxis'])  
      // if ('xaxis' in plotLayout && 'range' in plotLayout['xaxis']){
      //   delete plotLayout['xaxis'].range;
      // }
      // console.log('>>>>',plotLayout['xaxis'])
      localStorage.setItem('last_dates',JSON.stringify(change_flag));
      localStorage.setItem('xaxis_autorange','true');
      plotLayout.xaxis = { ...plotLayout.xaxis,'autorange':saved_autoRange,'rangeslider':{'visible':true}};
      console.log('>>>>',plotLayout['xaxis'])
  
  // Se está na data de hpje e variável saved_update_last está True
    } else if (!saved_autoRange && saved_update_last && (saved_lastDates[0] <= new Date() && new Date() <= saved_lastDates[1])){
      console.log('Opcao 2');
      if (saved_Range[0] >= data[0]['x'][data[0]['x'].length - 1]){ // Caso passe do limite
        saved_Range[0] = data[0]['x'][data[0]['x'].length - 1]
      }
      plotLayout.xaxis = { ...plotLayout.xaxis,'range':[saved_Range[0],data[0]['x'][data[0]['x'].length - 1]],'rangeslider':{'visible':true}}
  
  // Atualizar com último range
    } else {
      console.log('Opcao 3');
      console.log(plotLayout, saved_lastDates[0].getTime() !== change_flag[0].getTime(), saved_lastDates[1].getTime() !== change_flag[1].getTime(),saved_lastDates,change_flag);
      console.log('>>>>',plotLayout['xaxis'])
      if(!saved_autoRange){
        plotLayout.xaxis = { ...plotLayout.xaxis,'range':saved_Range,'rangeslider':{'visible':true}};
      } else {
        plotLayout.xaxis = { ...plotLayout.xaxis,'autorange':saved_autoRange,'rangeslider':{'visible':true}};
      }
      console.log('>>>>',plotLayout['xaxis'])  
  }

plotLayout['dragmode'] = saved_dragmode
//////////// handleRelayout
  const handleRelayout = (eventData: any) => {
      const data_atual = new Date();

      const savedRange = localStorage.getItem('xaxis_range');
      console.log('LAST DATA',savedRange);
      // console.log(layout['xaxis']['range']) //['autorange']
      console.log(eventData);

      // botão reset e autoscale
      if (eventData['xaxis.showspikes'] || eventData['xaxis.autorange']){
          //console.log('Op1')
          //Streamlit.setComponentValue('reset')
          layout['xaxis'] = {...layout.xaxis,'autorange':true,'rangeslider':{'visible':true}};
          localStorage.setItem('xaxis_autorange','true');
          localStorage.setItem('update_last','false');
      } else if (eventData['xaxis.range[0]'] && eventData['xaxis.range[1]']) {
          //console.log('Op2')
          //Streamlit.setComponentValue([eventData['xaxis.range[0]'], eventData['xaxis.range[1]']])
          const last_x = [eventData['xaxis.range[0]'], eventData['xaxis.range[1]']];
          
          // SE HOJE ESTÁ NO INTERVALO CHECAR SE ÚLTIMO X ESTÁ ACIMA DO LIMITE 
          const last_date = new Date(data[0]['x'][data[0]['x'].length - 1]);
          if ( saved_lastDates[0] <= data_atual && data_atual <= saved_lastDates[1]){
            console.log('HOJE CONTIDO NO INTERVALO',new Date(last_x[1]),last_date);
            if (new Date(last_x[1]) > last_date){
              console.log('ACOMPANHAR X');
              localStorage.setItem('update_last','true');
              last_x[1] = data[0]['x'][data[0]['x'].length - 1];
            } else {
              console.log('FIXAR X');
              localStorage.setItem('update_last','false');
            }
          } else {
            console.log('HOJE NÃO ESTÁ CONTIDO NO INTERVALO DETEMPO');
            // REMOVER update_last
            localStorage.removeItem('update_last');
          }

          localStorage.setItem('xaxis_range', JSON.stringify(last_x));
          layout['xaxis'] = {...layout.xaxis,'range':last_x,'autorange':false,'rangeslider':{'visible':true}};
          
          localStorage.setItem('xaxis_autorange','false');
          
          console.log('DEFININDO LAYOUT',layout);
          setPlotLayout(layout);
          // setLayout((prev) => ({
        //   ...prev,
        //   xaxis: {
        //     ...prev.xaxis,
        //     range: [eventData['xaxis.range[0]'], eventData['xaxis.range[1]']],
        //   },
        // }));
      } else if (eventData['xaxis.range'] && eventData['xaxis.range'][0] && eventData['xaxis.range'][1]){
          //Streamlit.setComponentValue([eventData['xaxis.range'][0], eventData['xaxis.range'][1]])
          
          // Possível bug no tempo real
          const last_x = [eventData['xaxis.range'][0], eventData['xaxis.range'][1]];
          
          // SE HOJE ESTÁ NO INTERVALO CHECAR SE ÚLTIMO X ESTÁ ACIMA DO LIMITE 
          const last_date = new Date(data[0]['x'][data[0]['x'].length - 1]);
          if ( saved_lastDates[0] <= data_atual && data_atual <= saved_lastDates[1]){
            console.log('HOJE CONTIDO NO INTERVALO',new Date(last_x[1]),last_date);
            if (new Date(last_x[1]) > last_date){
              console.log('ACOMPANHAR X');
              localStorage.setItem('update_last','true');
              last_x[1] = data[0]['x'][data[0]['x'].length - 1];
            } else {
              console.log('FIXAR X');
              localStorage.setItem('update_last','false');
            }
          } else {
            console.log('HOJE NÃO ESTÁ CONTIDO NO INTERVALO DETEMPO');
            // REMOVER update_last
            localStorage.removeItem('update_last');
          }


          localStorage.setItem('xaxis_range', JSON.stringify(last_x));
          layout['xaxis'] = {...layout.xaxis,'range':last_x,'autorange':false,'rangeslider':{'visible':true}};
          
          localStorage.setItem('xaxis_autorange','false');
          // if (!isMouseDown){
          //   document.removeEventListener('mousedown', handleMouseDown);
          //   document.addEventListener('mousedown', handleMouseDown);
            
          //   document.removeEventListener('mouseup', handleMouseUp);
          //   document.addEventListener('mouseup', handleMouseUp);
            
          //   document.removeEventListener('mouseleave', handleMouseLeave);
          //   document.addEventListener('mouseleave', handleMouseLeave);
          // }
      } else if('dragmode' in eventData){
        localStorage.setItem('dragmode', eventData['dragmode']);
      }
    };


    // const handleUpdate = (eventData: any) => {
    //   console.log('Test Updates',eventData)
    // };
    // console.log('RECEBIDO Dados',props.args.spec)

    //console.log(' DADO DE LAYOUT PARA CARREGAR GRÁFICO', layout['xaxis'])
    return (
      <Plot
        data={data}
        layout={plotLayout}
        onRelayout={handleRelayout}
        style={{ width: "100%", height: "100%" }}//useResizeHandler={true}
        frames={frames}
        // onUpdate={handleUpdate}
        config={config}
      />
    )
}

export default withStreamlitConnection(MyComponent)
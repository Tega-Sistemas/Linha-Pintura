import React, { useEffect } from "react"
import { withStreamlitConnection, Streamlit, ComponentProps } from "streamlit-component-lib"
import Plot from "react-plotly.js"

let isMouseDown = false;
let last_read_time = Date.now();
let last_x: number[] = []


function liberarMouseLIsten(){
  document.removeEventListener('mousedown', handleMouseDown);
  document.removeEventListener('mouseup', handleMouseUp);
  document.removeEventListener('mouseleave', handleMouseLeave);
  isMouseDown = false
}

function handleMouseDown(){
  isMouseDown = true;
  console.log("Mouse pressionado");
}

function Enviarlastx(){
  isMouseDown = false;
  console.log('Esperar para enviar')
  last_read_time = Date.now();
  setTimeout(() => {
    if (Date.now() - last_read_time >= 50) {  // Confirma que o tempo passou
        if (last_x) {
            console.log("Enviar", last_x);
            Streamlit.setComponentValue(last_x);
            last_x = [];
            liberarMouseLIsten();
        }
    }
}, 1000);
}

function handleMouseUp(){
  //if (isMouseDown) {
  console.log("Mouse liberado");
  Enviarlastx()
  //}
}

function handleMouseLeave(){
  // if (isMouseDown) {
  console.log("Mouse saiu da janela (clicado)");
  Enviarlastx()
  // }
}

function MyComponent(props: ComponentProps) {
  useEffect(() => {
    // Set the component height and notify Streamlit we're ready
    Streamlit.setFrameHeight();
    Streamlit.setComponentReady();
  }, []);
  
  
  const { data, layout, frames, config } = JSON.parse(props.args.spec)

  // const [layout, setLayout] = useState({
  //   width: 800,
  //   height: 400,
  //   title: 'Gráfico com Zoom Persistente',
  //   xaxis: { rangeslider: { visible: true } },
  //   shapes: [],
  // });


  // useEffect(() => Streamlit.setComponentValue("Tudo Certo"))
  const handleRelayout = (eventData: any) => {
    console.log(eventData)

    // botão reset e autoscale
    if (eventData['xaxis.showspikes'] || eventData['xaxis.autorange']){
        //console.log('Op1')
        Streamlit.setComponentValue('reset')
    } else if (eventData['xaxis.range[0]'] && eventData['xaxis.range[1]']) {
        //console.log('Op2')
        Streamlit.setComponentValue([eventData['xaxis.range[0]'], eventData['xaxis.range[1]']])
        
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
        last_x = [eventData['xaxis.range'][0], eventData['xaxis.range'][1]]
        if (!isMouseDown){
        document.removeEventListener('mousedown', handleMouseDown);
        document.addEventListener('mousedown', handleMouseDown);
        
        document.removeEventListener('mouseup', handleMouseUp);
        document.addEventListener('mouseup', handleMouseUp);
        
        document.removeEventListener('mouseleave', handleMouseLeave);
        document.addEventListener('mouseleave', handleMouseLeave);
        }
        // if (!isMouseDown){
        //   console.log('Não Enviar ABrindo listeners',isMouseDown)
          
        // }
        // else{
        //   console.log("Enviar")
        // }
    }
  };

  // console.log('RECEBIDO Dados',props.args.spec)

  return (
    <Plot
      data={data}
      layout={layout}
      onRelayout={handleRelayout}
      style={{ width: "100%", height: "100%" }}//useResizeHandler={true}
      frames={frames}
      config={config}
    />
  )
  // return <p>Hello world {props.args.text}</p>
}

export default withStreamlitConnection(MyComponent)
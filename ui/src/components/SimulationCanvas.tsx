import React, { useEffect, useState, useRef } from 'react';
import "./SimulationCanvas.css"

interface CanvasProps {
  ws?: WebSocket
  points?: [number, number][]
  children?: React.ReactNode
}

const rndStyle = {
  border: "1px solid red",
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
}

function SimulationCanvas(props: CanvasProps) {
  const canvas = useRef(null);
  const [ctx, setCtx] = useState<CanvasRenderingContext2D | null>(null);
  const [progressIndex, setProgressIndex] = useState(0);
  const [drawnPoints, setDrawnPoints] = useState<[number, number][]>([]);

  // initialize the canvas context
  useEffect(() => {
    if (canvas.current === null) {
      return
    }

    const canvasDiv = document.getElementById("simulation-canvas");

    // dynamically assign the width and height to canvas
    const canvasEle = canvas.current! as HTMLCanvasElement;
    canvasEle.width = canvasDiv?.offsetWidth || 0;
    canvasEle.height = canvasDiv?.offsetHeight || 0;

    // get context of the canvas
    setCtx(canvasEle.getContext("2d"));
    console.info("GOT CANVAS CONTEXT")
  }, []);

  useEffect(() => {
    if (!props.ws) {
      return
    }

    props.ws!.onmessage = (event: MessageEvent) => {
      const update = JSON.parse(event.data);
      const newDrawnPoints = drawnPoints;
      (update.payload as Array<[number, number]>)?.forEach((point) => {
        newDrawnPoints.push(point);
        if (ctx) {
          ctx.strokeRect(point[0], point[1], 1, 1);
        }
      })
      setDrawnPoints(newDrawnPoints);
      setProgressIndex(props.points?.length || 0)
    }
  }, [props.ws])

  return (
    <div className="canvas-container">
      <div id="simulation-canvas" className="canvas">
        <canvas ref={canvas}></canvas>
      </div>
    </div >
  );
}

export default SimulationCanvas;

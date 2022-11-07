import React, { useEffect, useState, useRef, CanvasHTMLAttributes } from 'react';
import "../index.css"
import RangeInput from '../units/RangeInput';
import "./SimulationCanvas.css"

const targetSize = 600;

interface CanvasProps {
  ws?: WebSocket
  cutleft?: boolean
  cutright?: boolean
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
  const [allPaths, setAllPaths] = useState<[[number, number]][]>([]);
  const [windowResizeEvent, setWidowResizeEvent] = useState<any>();

  const getPathIndexFromPointIndex = (pointIndex: number): number => {
    let lastIndex = 0;
    for (let i = 0; i < allPaths.length; i++) {
      lastIndex += allPaths[i].length
      if (lastIndex > pointIndex) {
        return i;
      }
    }

    return -1;
  };

  const ratioedPoint = (point: [number, number], ratio: number): [number, number] => {
    return [point[0]*ratio, point[1]*ratio];
  }
  
  const redraw = () => {
    if (canvas.current === null) {
      return
    }

    const canvasDiv = document.getElementById("simulation-canvas");
    const canvasEle = canvas.current! as HTMLCanvasElement;
    canvasEle.width = canvasDiv?.offsetWidth || 0;
    canvasEle.height = canvasDiv?.offsetWidth || 0;

    if (!ctx) {
      return
    }

    const ratio = (canvas.current! as HTMLCanvasElement).width / targetSize;
    for (let i = 0; i < progressIndex && i < drawnPoints.length; i++) {
      const point = drawnPoints[i];
      ctx.strokeRect(point[0] * ratio, point[1] * ratio, 1, 1);
    }
  }

  // initialize the canvas context
  useEffect(() => {
    if (canvas.current === null) {
      return
    }

    const canvasDiv = document.getElementById("simulation-canvas");

    // dynamically assign the width and height to canvas
    const canvasEle = canvas.current! as HTMLCanvasElement;
    canvasEle.width = canvasDiv?.offsetWidth || 0;
    canvasEle.height = canvasDiv?.offsetWidth || 0;

    // get context of the canvas
    setCtx(canvasEle.getContext("2d"));

    window.addEventListener('resize', (e) => setWidowResizeEvent(e));
  }, []);

  useEffect(() => {
    redraw()
  }, [windowResizeEvent])

  useEffect(() => {
    if (!props.ws) {
      return
    }

    props.ws!.onmessage = (event: MessageEvent) => {
      const update = JSON.parse(event.data);
      const allPaths: [[number, number]][] = update.payload;
      setAllPaths(allPaths)
      let allPoints: [number, number][] = [];
      for(let i = 0; i < allPaths.length; i++) {
        const path = allPaths[i];
        allPoints = allPoints.concat(path)
      }
      
      setDrawnPoints(allPoints);
      setProgressIndex(allPoints.length);
    }
  }, [props.ws])

  useEffect(() => {
    if (!ctx) {
      return
    }

    if (drawnPoints.length === 0) {
      return;
    }

    const currentCanvas = canvas.current! as HTMLCanvasElement;
    ctx.clearRect(0, 0, currentCanvas.width, currentCanvas.height);
    const ratio = currentCanvas.width / targetSize;

    let startPoint = drawnPoints[0];
    ctx.beginPath();
    ctx.moveTo(startPoint[0] * ratio, startPoint[1] * ratio)

    let currentPathIndex = 0;
    let prevPoint = startPoint;
    for (let i = 1; i < progressIndex && i < drawnPoints.length; i++) {
      const point = drawnPoints[i];
      
      const newPathIndex = getPathIndexFromPointIndex(i)
      if (newPathIndex !== currentPathIndex) {
        ctx.moveTo(...ratioedPoint(point, ratio));
        startPoint = point;
        currentPathIndex = newPathIndex;
      } else {
        ctx.lineTo(...ratioedPoint(point, ratio));
      }
      
      // ctx.strokeRect(point[0] * ratio, point[1] * ratio, 1, 1);
      prevPoint = point;
    }
    
    ctx.stroke();

  }, [progressIndex])

  useEffect(() => {
    setDrawnPoints(drawnPoints.slice(progressIndex, drawnPoints.length - 1));
  }, [props.cutleft])

  useEffect(() => {
    setDrawnPoints(drawnPoints.slice(0, progressIndex));
  }, [props.cutright])

  useEffect(() => {
    redraw();
  }, [drawnPoints])

  const handleOnChange = (value: any) => {
    setProgressIndex(value)
  }

  const clearCanvas = () => {
    if (!ctx) {
      return
    }

    const currentCanvas = canvas.current! as HTMLCanvasElement;
    ctx.clearRect(0, 0, currentCanvas.width, currentCanvas.height);
    setDrawnPoints([])
    setProgressIndex(0)
  }

  return (
    <div className="simulation-container">
      <div className="canvas-container">
        <div id="simulation-canvas" className="simulation-canvas">
          <canvas ref={canvas}></canvas>
        </div>
      </div >
      <div className="w-full pt-2 mb-2">
        <RangeInput
          hideValue
          min={0}
          max={drawnPoints.length || 0}
          default={progressIndex}
          onValueChange={handleOnChange}
        ></RangeInput>
      </div>
      <div className="flex content-start">
        <button className="button-base" onClick={clearCanvas}>Clear Canvas</button>
      </div>
    </div >
  );
}

export default SimulationCanvas;

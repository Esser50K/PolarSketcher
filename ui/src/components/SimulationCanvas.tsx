import React, { useEffect, useState, useRef, CanvasHTMLAttributes } from 'react';
import "../index.css"
import "./SimulationCanvas.css"

const targetSize = 600;

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

const debounce = (callback: (...params: any[]) => any, delay: number) => {
  let inDebounce: ReturnType<typeof setTimeout>;

  return function (this: any, ...args: any[]) {
    clearTimeout(inDebounce);
    inDebounce = setTimeout(() => callback.apply(this, args), delay);
  };
};

function SimulationCanvas(props: CanvasProps) {
  const canvas = useRef(null);
  const slider = useRef(null);
  const [ctx, setCtx] = useState<CanvasRenderingContext2D | null>(null);
  const [progressIndex, setProgressIndex] = useState(0);
  const [drawnPoints, setDrawnPoints] = useState<[number, number][]>([]);
  const [windowResizeEvent, setWidowResizeEvent] = useState<any>();


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

    const debouncedRedraw = debounce(() => {
      console.info("REDRAW")
      setProgressIndex(drawnPoints.length)
    }, 10);

    props.ws!.onmessage = (event: MessageEvent) => {
      const update = JSON.parse(event.data);
      const newDrawnPoints = drawnPoints;
      (update.payload as Array<[number, number]>)?.forEach((point) => {
        newDrawnPoints.push(point);
      })
      setDrawnPoints(newDrawnPoints);
      debouncedRedraw();
    }

    props.ws!.onclose = () => {
      setProgressIndex(drawnPoints.length || 0)
    }
  }, [props.ws])

  useEffect(() => {
    if (!ctx) {
      return
    }

    const currentCanvas = canvas.current! as HTMLCanvasElement;
    ctx.clearRect(0, 0, currentCanvas.width, currentCanvas.height);
    const ratio = currentCanvas.width / targetSize;

    for (let i = 0; i < progressIndex && i < drawnPoints.length; i++) {
      const point = drawnPoints[i];
      ctx.strokeRect(point[0] * ratio, point[1] * ratio, 1, 1);
    }

  }, [progressIndex])

  const handleOnChange = (event: any) => {
    if (event?.target?.value) {
      setProgressIndex(event.target.value)
    }
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
      <div className="w-full pt-2">
        <input
          ref={slider}
          onChange={handleOnChange}
          type="range"
          min="0"
          max={String(drawnPoints.length) || "0"}
          value={String(progressIndex)}
          className="slider h-full border-2"></input>
      </div>
      <div className="flex content-start">
        <button className="button-base" onClick={clearCanvas}>Clear Canvas</button>
      </div>
    </div >
  );
}

export default SimulationCanvas;

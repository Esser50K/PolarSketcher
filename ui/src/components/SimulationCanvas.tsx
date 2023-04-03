import React, { useEffect, useState, useRef, CanvasHTMLAttributes } from 'react';
import "../index.css"
import RangeInput from '../units/RangeInput';
import "./SimulationCanvas.css"

interface CanvasProps {
  fullCanvasDimensions: { x: number, y: number }
  canvasDimensions: { x: number, y: number }
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
  const [currentJobPaths, setCurrentJobPaths] = useState<[[number, number]][]>([]);
  const [accumulatedPaths, setAccumulatedPaths] = useState<[[number, number]][]>([]);
  const [currentJobId, setCurrenttJobId] = useState<string>("");
  const [windowResizeEvent, setWidowResizeEvent] = useState<any>();

  const ratioedPoint = (point: [number, number], ratio: number): [number, number] => {
    const reducedModeDiff = props.fullCanvasDimensions.x - props.canvasDimensions.x;
    return [(point[0] - reducedModeDiff) * ratio, point[1] * ratio];
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

    const ratio = (canvas.current! as HTMLCanvasElement).width / props.canvasDimensions.x;
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
      const jobId: string = update.job_id;

      let newAccumulatedPaths = accumulatedPaths;
      if (jobId !== currentJobId) {
        newAccumulatedPaths = accumulatedPaths.concat(currentJobPaths);
        setAccumulatedPaths(newAccumulatedPaths);
      }

      setCurrenttJobId(jobId)
      setCurrentJobPaths(allPaths)

      let allPoints: [number, number][] = [];
      for (let i = 0; i < newAccumulatedPaths.length; i++) {
        const path = newAccumulatedPaths[i];
        allPoints = allPoints.concat(path);
        allPoints.push([-1, -1]);
      }
      for (let i = 0; i < allPaths.length; i++) {
        const path = allPaths[i];
        allPoints = allPoints.concat(path);
        allPoints.push([-1, -1]);
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
    const ratio = currentCanvas.width / props.canvasDimensions.x;

    let startPoint = drawnPoints[0];
    ctx.beginPath();
    ctx.moveTo(startPoint[0] * ratio, startPoint[1] * ratio)

    let moveOnly = false;
    for (let i = 1; i < progressIndex && i < drawnPoints.length; i++) {
      const point = drawnPoints[i];

      if (point[0] === -1 && point[1] === -1) {
        moveOnly = true;
        continue;
      }

      if (moveOnly) {
        ctx.moveTo(...ratioedPoint(point, ratio));
        startPoint = point;
        moveOnly = false;
      } else {
        ctx.lineTo(...ratioedPoint(point, ratio));
      }
    }

    ctx.stroke();

  }, [progressIndex, props.canvasDimensions])

  useEffect(() => {
    setDrawnPoints(drawnPoints.slice(progressIndex, drawnPoints.length - 1));
  }, [props.cutleft])

  useEffect(() => {
    setDrawnPoints(drawnPoints.slice(0, progressIndex));
  }, [props.cutright])

  useEffect(() => {
    redraw();
  }, [drawnPoints])

  let delayedProgressIndexUpdate: NodeJS.Timeout;
  const handleOnChange = (value: any) => {
    clearTimeout(delayedProgressIndexUpdate);

    delayedProgressIndexUpdate = setTimeout(() => {
      setProgressIndex(value);
    }, 5);
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
      </div>
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

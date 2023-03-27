import React, { SVGProps, useEffect, useState } from 'react';
import '../index.css';
import "./PreviewCanvas.css";
import { Rnd } from 'react-rnd';

export interface DrawnSVG {
  svgContent: string,
  position: number[],
  rotation: number,
  dimensions: number[]
}

interface CanvasProps {
  fullCanvasDimensions: { x: number, y: number }
  canvasDimensions: { x: number, y: number }
  svgContent?: string
  rotation?: number
  center?: boolean
  maxout?: boolean
  children?: React.ReactNode
  drawnSVGs: DrawnSVG[]
  inReducedMode: boolean
  onPositionUpdate?: (pos: { x: number, y: number }) => void
  onResizeUpdate?: (width: number, height: number) => void
}

const rndStyle = {
  border: "1px solid red",
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
}

function PreviewCanvas(props: CanvasProps) {
  const [contentDimensions, setContentDimensions] = useState({ width: 0, height: 0 });
  const [contentPosition, setContentPosition] = useState({ x: 0, y: 0 });
  const [vituralCanvasDimensions, setVirtualCanvasDimensions] = useState({ width: 0, height: 0 });
  const [currentSVGContent, setCurrentSVGContent] = useState<HTMLElement>();
  const [windowResizeEvent, setWindowResizeEvent] = useState<any>();


  const resize = (width: number, height: number) => {
    setContentDimensions({ width: width, height: height });

    if (currentSVGContent) {
      currentSVGContent.setAttribute("width", String(width) + "px");
      currentSVGContent.setAttribute("height", String(width) + "px");
      setCurrentSVGContent(currentSVGContent);
    }

    if (props.onResizeUpdate) {
      props.onResizeUpdate(width, width)
    }
  };

  const setNewPos = (x: number, y: number) => {
    setContentPosition({ x: x, y: y })

    if (props.onPositionUpdate) {
      props.onPositionUpdate({ x: x, y: y })
    }
  }

  useEffect(() => {
    if (vituralCanvasDimensions.height === 0) {
      const canvas = document.getElementById("canvas")
      // setting both as width since canvas is always square
      setVirtualCanvasDimensions({ width: canvas?.offsetWidth || 0, height: canvas?.offsetWidth || 0 })
    }

    window.addEventListener('resize', (event) => {
      const canvas = document.getElementById("canvas")
      // setting both as width since canvas is always square
      setVirtualCanvasDimensions({ width: canvas?.offsetWidth || 0, height: canvas?.offsetWidth || 0 })
      setWindowResizeEvent(event)
    })
  }, [])

  useEffect(() => {
    const canvas = document.getElementById("canvas");
    resize(
      Math.min(contentDimensions.width || 0, canvas?.offsetWidth || 0),
      Math.min(contentDimensions.width || 0, canvas?.offsetWidth || 0))
  }, [windowResizeEvent])

  useEffect(() => {
    if (!props.center) {
      return
    }

    const x = (vituralCanvasDimensions.width / 2) - (contentDimensions.width / 2);
    const y = (vituralCanvasDimensions.height / 2) - (contentDimensions.height / 2);
    setNewPos(x, y);
  }, [props.center])

  useEffect(() => {
    if (!props.maxout) {
      return
    }

    let newContentWidth = contentDimensions.width;
    let newContentHeight = contentDimensions.height;
    const vertical = contentDimensions.height > contentDimensions.width;
    if (vertical) {
      newContentHeight = vituralCanvasDimensions.height;
      const increaseRatio = newContentHeight / contentDimensions.height;
      newContentWidth = contentDimensions.width * increaseRatio;
      resize(newContentWidth, newContentHeight);
    } else {
      newContentWidth = vituralCanvasDimensions.width;
      const increaseRatio = newContentWidth / contentDimensions.width;
      newContentHeight = contentDimensions.height * increaseRatio;
      resize(newContentWidth, newContentHeight);
    }

    const x = (vituralCanvasDimensions.width / 2) - (newContentWidth / 2);
    const y = (vituralCanvasDimensions.height / 2) - (newContentHeight / 2);
    setNewPos(x, y);
  }, [props.maxout])

  useEffect(() => {
    if (contentDimensions.height !== 0) {
      return
    }

    const content = document.getElementById("canvas-content");
    let svgContent = content?.firstChild as SVGProps<SVGElement>;
    content?.childNodes?.forEach((value, key) => {
      if (value.nodeName === "svg") {
        svgContent = value as SVGProps<SVGElement>;
      }
    })

    if (svgContent?.width || svgContent?.height) {
      (svgContent as HTMLElement).removeAttribute("width");
      (svgContent as HTMLElement).removeAttribute("height");
    }

    if (svgContent) {
      const viewBoxAny = (svgContent.viewBox as any)
      const dimensions = (viewBoxAny ? viewBoxAny.baseVal : svgContent.bbox) as SVGRect
      const contentDimensionsWidth = Math.min(dimensions.width || 0, vituralCanvasDimensions.width);
      const contentDimensionsHeight = Math.min(dimensions.height || 0, vituralCanvasDimensions.height);
      (svgContent as HTMLElement).setAttribute("width", String(contentDimensionsWidth) + "px");
      (svgContent as HTMLElement).setAttribute("height", String(contentDimensionsWidth) + "px");
      setCurrentSVGContent(svgContent as HTMLElement);
      resize(contentDimensionsWidth, contentDimensionsWidth);
    }
  }, [props.svgContent])

  // calculate where to draw previously drawn SVGs
  let reducedModeDiff = 0;
  if (props.inReducedMode) {
    reducedModeDiff = props.fullCanvasDimensions.x - props.canvasDimensions.x;
  }

  // the side of the base is 30mm out of whatever the canvas currently is
  const widthPercentage = (30 * 100.0) / props.canvasDimensions.x;
  const canvasDimensionsRatio = props.canvasDimensions.x / vituralCanvasDimensions.width;
  return (
    <div className="canvas-container">
      <div id="canvas" className="preview-canvas"
        style={{ backgroundColor: props.inReducedMode ? "white" : "rgba(255, 0, 0, 0.2)" }}>
        {
          !props.inReducedMode ?
            <div id="canvas-limits-round" className="canvas-limits-round"></div> : null
        }
        <div id="canvas-limits-corner" className="canvas-limits-corner"
          style={{ width: `${widthPercentage}%`, height: `${widthPercentage}%` }}>
        </div>
        {props.drawnSVGs.map((drawnSVG: DrawnSVG, idx: number) => {
          return <div key={`drawn_svg_${idx}`} className="canvas-content"
            style={{
              position: "absolute",
              transform: `rotate(${drawnSVG.rotation}deg)`,
              width: drawnSVG.dimensions[0] / canvasDimensionsRatio,
              height: drawnSVG.dimensions[1] / canvasDimensionsRatio,
              left: (drawnSVG.position[0] - reducedModeDiff) / canvasDimensionsRatio,
              top: drawnSVG.position[1] / canvasDimensionsRatio
            }}
            dangerouslySetInnerHTML={{ __html: drawnSVG.svgContent }}>
          </div>
        })}

        {
          vituralCanvasDimensions.width !== 0 ?
            <Rnd
              style={rndStyle}
              size={{ width: contentDimensions.width, height: contentDimensions.height }}
              onResize={(e, direction, ref, delta, position) => {
                resize(parseInt(ref.style.width), parseInt(ref.style.height))
              }}
              onResizeStop={(e, direction, ref, delta, position) => {
                resize(parseInt(ref.style.width), parseInt(ref.style.height));
                ref.style.minWidth = String(contentDimensions.width)
                ref.style.minHeight = String(contentDimensions.height)
              }}
              position={{ x: contentPosition.x, y: contentPosition.y }}
              onDrag={(e, d) => {
                setContentPosition({ x: d.x, y: d.y })
              }}
              onDragStop={(e, d) => {
                if (props.onPositionUpdate) {
                  props.onPositionUpdate({ x: d.x, y: d.y })
                }
                setContentPosition({ x: d.x, y: d.y })
              }}

              lockAspectRatio
              dragAxis="both"
              bounds=".preview-canvas"
            // enableResizing={{ "bottomRight": true }}
            >
              {props.svgContent ?
                <div id="canvas-content-wrapper" className="canvas-content-wrapper">
                  <div id="position-label" className="svg-label" style={{ left: "-55%", top: "50%", rotate: "-90deg" }}>
                    {(contentPosition.x * canvasDimensionsRatio).toFixed(1) + ", " + (contentPosition.y * canvasDimensionsRatio).toFixed(1)}
                  </div>
                  <div id="width-label" className="svg-label" style={{ top: "-10%" }}>
                    {(contentDimensions.width * canvasDimensionsRatio).toFixed(1)}
                  </div>
                  <div id="height-label" className="svg-label" style={{ right: "-55%", top: "50%", rotate: "90deg" }}>
                    {(contentDimensions.height * canvasDimensionsRatio).toFixed(1)}
                  </div>
                  <div id="canvas-content" className="canvas-content"
                    /*style={{ height: contentDimensions.height, width: contentDimensions.width }}*/
                    style={{ transform: `rotate(${props.rotation}deg)` }}
                    dangerouslySetInnerHTML={{ __html: props.svgContent }}>
                  </div>
                </div> : null}
            </Rnd> : null
        }
      </div>
    </div >
  );
}

export default PreviewCanvas;

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
  imageURL?: string
  svgContent?: string
  rotation?: number
  center?: boolean
  maxout?: boolean
  children?: React.ReactNode
  drawnSVGs: DrawnSVG[]
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
    resizeSVGContent(width, height);

    if (props.onResizeUpdate) {
      props.onResizeUpdate(width, height);
      console.info("CONTENT DIMESNIONS:", width, height);
    }
  };

  const resizeSVGContent = (width: number, height: number) => {
    setContentDimensions({ width: width, height: height });

    if (currentSVGContent) {
      currentSVGContent.setAttribute("width", String(width) + "px");
      currentSVGContent.setAttribute("height", String(height) + "px");
      setCurrentSVGContent(currentSVGContent);
    }
  };

  useEffect(() => {
    resize(100, 100);
  }, [props.imageURL])

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
      setVirtualCanvasDimensions({ width: canvas?.offsetWidth || 0, height: canvas?.offsetWidth || 0 });
    }

    window.addEventListener('resize', (event) => {
      const canvas = document.getElementById("canvas")
      // setting both as width since canvas is always square
      setVirtualCanvasDimensions({ width: canvas?.offsetWidth || 0, height: canvas?.offsetWidth || 0 })
      setWindowResizeEvent(event)
    })
  }, [])

  const ensureSameSizeAsCanvas = () => {
    const canvas = document.getElementById("canvas");
    const widthHeightRatio = props.canvasDimensions.y / props.canvasDimensions.x;
    resize(
      Math.min(contentDimensions.width || 0, (canvas?.offsetWidth || 0) * widthHeightRatio),
      Math.min(contentDimensions.height || 0, (canvas?.offsetHeight || 0) * widthHeightRatio)
    )
    setVirtualCanvasDimensions({ width: canvas?.offsetWidth || 0, height: (canvas?.offsetWidth || 0) * widthHeightRatio })
  }

  useEffect(() => {
    ensureSameSizeAsCanvas()
  }, [windowResizeEvent, props.canvasDimensions, props.svgContent])

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

  const limitElementSize = (elementId: string, width: number, height: number) => {
    console.info("GOT IMAGE URL:", !!props.imageURL);
    console.info("GOT SVG:", props.svgContent);
    if (props.imageURL !== null) {
      return;
    }

    const content = document.getElementById(elementId);
    // let svgContent = content?.firstChild as SVGProps<SVGElement>;
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
      // (svgContent as HTMLElement).setAttribute("width", String(width) + "px");
      // (svgContent as HTMLElement).setAttribute("height", String(height) + "px");
      const svgElement = svgContent as any;
      (svgContent as HTMLElement).setAttribute("width", String(svgElement.width.baseVal.value) + "px");
      (svgContent as HTMLElement).setAttribute("height", String(svgElement.height.baseVal.value) + "px");
      return svgContent;
    }
  }

  useEffect(() => {
    props.drawnSVGs.map((drawnSVG: DrawnSVG, idx: number) => {
      limitElementSize(`drawn_svg_${idx}`,
        drawnSVG.dimensions[0] / canvasDimensionsRatio,
        drawnSVG.dimensions[1] / canvasDimensionsRatio)
    })
  })

  // resize the SVG element on the fly
  useEffect(() => {
    if (contentDimensions.height !== 0) {
      return
    }
    const canvas = document.getElementById("canvas")
    const vituralCanvasWidth = canvas?.offsetWidth || 0;
    const vituralCanvasHeight = canvas?.offsetWidth || 0;


    if (vituralCanvasDimensions.height === 0) {
      setVirtualCanvasDimensions({ width: vituralCanvasWidth, height: vituralCanvasHeight });
    }
    resize(vituralCanvasWidth, vituralCanvasHeight);
  }, [props.svgContent])

  useEffect(() => {
    const canvas = document.getElementById("canvas")
    const vituralCanvasWidth = canvas?.offsetWidth || 0;
    const vituralCanvasHeight = canvas?.offsetWidth || 0;

    if (vituralCanvasDimensions.height === 0) {
      setVirtualCanvasDimensions({ width: vituralCanvasWidth, height: vituralCanvasHeight });
    }
    resizeSVGContent(props.canvasDimensions.x, props.canvasDimensions.y)
  }, [props.canvasDimensions])

  // calculate where to draw previously drawn SVGs
  const reducedModeDiff = props.fullCanvasDimensions.x - props.canvasDimensions.x;

  // the side of the base is 35mm out of whatever the canvas currently is
  const widthPercentage = (35 * 100.0) / props.canvasDimensions.x;
  const canvasDimensionsRatio = props.canvasDimensions.x / vituralCanvasDimensions.width;
  return (
    <div className="canvas-container">
      <div id="canvas" className="preview-canvas"
        style={{
          height: vituralCanvasDimensions.height
        }}>
        <div className="canvas-limits-container">
          <div id="canvas-limits-round" className="canvas-limits-round"
            style={{
              width: props.fullCanvasDimensions.x / canvasDimensionsRatio,
              height: props.fullCanvasDimensions.x / canvasDimensionsRatio,
              right: `${(reducedModeDiff * 100) / props.canvasDimensions.x}px`,
            }}
          ></div>
          <div id="canvas-limits-rest" className="canvas-limits-rest"
            style={{
              left: `${100 - ((100 * reducedModeDiff) / props.canvasDimensions.x)}%`,
            }}
          ></div>
          <div id="canvas-limits-corner" className="canvas-limits-corner"
            style={{ width: `${widthPercentage}%` }}>
          </div>
        </div>
        {props.drawnSVGs.map((drawnSVG: DrawnSVG, idx: number) => {
          return <div id={`drawn_svg_${idx}`} className="canvas-content"
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
                console.info("ON RESIZE:", ref.style.width, ref.style.height)
                resizeSVGContent(parseInt(ref.style.width), parseInt(ref.style.height))
              }}
              onResizeStop={(e, direction, ref, delta, position) => {
                resize(parseInt(ref.style.width), parseInt(ref.style.height));
                // resizeSVGContent(parseInt(ref.style.width), parseInt(ref.style.height));
                // ref.style.minWidth = String(contentDimensions.width)
                // ref.style.minHeight = String(contentDimensions.height)
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
              {(props.svgContent || props.imageURL) ?
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

                  {props.svgContent ?
                    <div id="canvas-content" className="canvas-content"
                      /*style={{ height: contentDimensions.height, width: contentDimensions.width }}*/
                      style={{ transform: `rotate(${props.rotation}deg)` }}
                      dangerouslySetInnerHTML={{ __html: props.svgContent }}>
                    </div> :
                    <div>
                      <img src={props.imageURL} style={{ width: "100%", height: "100%" }} onDragStart={(event) => event.preventDefault()}></img>
                    </div>
                  }
                </div> : null}
            </Rnd> : null
        }
      </div>
    </div >
  );
}

export default PreviewCanvas;

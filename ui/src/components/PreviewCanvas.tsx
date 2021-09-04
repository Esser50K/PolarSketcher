import React, { SVGProps, useEffect, useState } from 'react';
import "./PreviewCanvas.css"
import { Rnd } from 'react-rnd';

interface CanvasProps {
  svgContent?: string
  center?: boolean
  children?: React.ReactNode
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
  const [originalSVGDimensions, setOriginalSVGDimensions] = useState({ width: 0, height: 0 });
  const [contentDimensions, setCotentDimensions] = useState({ width: 0, height: 0 });
  const [contentPosition, setContentPosition] = useState({ x: 0, y: 0 });
  const [canvasDimensions, setCanvasDimensions] = useState({ width: 0, height: 0 });

  useEffect(() => {
    if (!props.center) {
      return
    }

    setContentPosition({
      x: (canvasDimensions.width / 2) - (contentDimensions.width / 2),
      y: (canvasDimensions.height / 2) - (contentDimensions.height / 2)
    })
  }, [props.center])

  useEffect(() => {
    if (contentDimensions.height !== 0) {
      return
    }

    const content = document.getElementById("canvas-content");
    let svgContent = content?.firstChild as SVGProps<SVGElement>;
    content?.childNodes?.forEach((value, key) => {
      console.info(key, value, value.nodeName);
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
      setOriginalSVGDimensions({ width: dimensions.width || 0, height: dimensions.height || 0 })
      setCotentDimensions({
        width: Math.min(dimensions.width || 0, canvasDimensions.width),
        height: Math.min(dimensions.height || 0, canvasDimensions.height)
      })
    }
    //setCotentDimensions({ width: content?.offsetWidth || 0, height: content?.offsetHeight || 0 })
    console.info("WIDTH:", content?.offsetWidth)
    console.info("HEIGHT:", content?.offsetHeight)
  }, [props.svgContent, setCotentDimensions])

  useEffect(() => {
    if (canvasDimensions.height === 0) {
      const canvas = document.getElementById("canvas")
      setCanvasDimensions({ width: canvas?.offsetWidth || 0, height: canvas?.offsetHeight || 0 })
      console.info("CANVAS WIDTH:", canvas?.offsetWidth)
      console.info("CANVAS HEIGHT:", canvas?.offsetHeight)
    }

  }, [])

  return (
    <div className="canvas-container">
      <div id="canvas" className="canvas">
        {
          canvasDimensions.width !== 0 ?
            <Rnd
              style={rndStyle}
              size={{ width: contentDimensions.width, height: contentDimensions.height }}
              onResizeStop={(e, direction, ref, delta, position) => {
                if (props.onResizeUpdate) {
                  props.onResizeUpdate(
                    parseInt(ref.style.width), parseInt(ref.style.height))
                  console.info(parseInt(ref.style.width) / originalSVGDimensions.width)
                }

                setCotentDimensions({
                  width: parseInt(ref.style.width),
                  height: parseInt(ref.style.height),
                  ...position,
                })
                ref.style.minWidth = String(contentDimensions.width)
                ref.style.minHeight = String(contentDimensions.width)
              }}
              position={{ x: contentPosition.x, y: contentPosition.y }}
              onDragStop={(e, d) => {
                if (props.onPositionUpdate) {
                  props.onPositionUpdate({ x: d.x, y: d.y })
                }
                setContentPosition({ x: d.x, y: d.y })
              }}

              lockAspectRatio
              dragAxis="both"
              bounds=".canvas"
              enableResizing={{ "bottomRight": true }}
            >
              {props.svgContent ?
                <div id="canvas-content" className="canvas-content" dangerouslySetInnerHTML={{ __html: props.svgContent }}>
                </div> : null}
            </Rnd> : null}

      </div>
    </div >
  );
}

export default PreviewCanvas;

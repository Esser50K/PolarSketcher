import React, { SVGProps, useEffect, useState } from 'react';
import '../index.css';
import "./PreviewCanvas.css";
import { Rnd } from 'react-rnd';

interface CanvasProps {
  svgContent?: string
  center?: boolean
  maxout?: boolean
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
  const [contentDimensions, setContentDimensions] = useState({ width: 0, height: 0 });
  const [contentPosition, setContentPosition] = useState({ x: 0, y: 0 });
  const [canvasDimensions, setCanvasDimensions] = useState({ width: 0, height: 0 });
  const [currentSVGContent, setCurrentSVGContent] = useState<HTMLElement>();
  const [windowResizeEvent, setWidowResizeEvent] = useState<any>();


  const resize = (width: number, height: number) => {
    setContentDimensions({ width: width, height: height });

    if (currentSVGContent) {
      currentSVGContent.setAttribute("width", String(width) + "px");
      currentSVGContent.setAttribute("height", String(height) + "px");
      setCurrentSVGContent(currentSVGContent);
    }

    if (props.onResizeUpdate) {
      props.onResizeUpdate(width, height)
    }
  };

  const setNewPos = (x: number, y: number) => {
    setContentPosition({ x: x, y: y })

    if (props.onPositionUpdate) {
      props.onPositionUpdate({ x: x, y: y })
    }
  }

  useEffect(() => {
    window.addEventListener('resize', (event) => {
      const canvas = document.getElementById("canvas")
      // setting both as width since canvas is always square
      setCanvasDimensions({ width: canvas?.offsetWidth || 0, height: canvas?.offsetWidth || 0 })


      setWidowResizeEvent(event)
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


    const x = (canvasDimensions.width / 2) - (contentDimensions.width / 2);
    const y = (canvasDimensions.height / 2) - (contentDimensions.height / 2);
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
      newContentHeight = canvasDimensions.height;
      const increaseRatio = newContentHeight / contentDimensions.height;
      newContentWidth = contentDimensions.width * increaseRatio;
      resize(newContentWidth, newContentHeight);
    } else {
      newContentWidth = canvasDimensions.width;
      const increaseRatio = newContentWidth / contentDimensions.width;
      newContentHeight = contentDimensions.height * increaseRatio;
      resize(newContentWidth, newContentHeight);
    }

    const x = (canvasDimensions.width / 2) - (newContentWidth / 2);
    const y = (canvasDimensions.height / 2) - (newContentHeight / 2);
    setNewPos(x, y);
  }, [props.maxout])

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
      console.info("ContentDimensions", dimensions.width, canvasDimensions.width, dimensions.height, canvasDimensions.height);
      const contentDimensionsWidth = Math.min(dimensions.width || 0, canvasDimensions.width);
      const contentDimensionsHeight = Math.min(dimensions.height || 0, canvasDimensions.height);
      (svgContent as HTMLElement).setAttribute("width", String(contentDimensionsHeight) + "px");
      (svgContent as HTMLElement).setAttribute("height", String(contentDimensionsWidth) + "px");
      setCurrentSVGContent(svgContent as HTMLElement);
      console.info("RESIZING")
      resize(contentDimensionsWidth, contentDimensionsHeight);
      console.info("RIGHT HERE")
    }
    // resize(content?.offsetWidth || 0, content?.offsetWidth || 0);
    console.info("WIDTH:", content?.offsetWidth)
    console.info("HEIGHT:", content?.offsetHeight)
  }, [props.svgContent])

  useEffect(() => {
    if (canvasDimensions.height === 0) {
      const canvas = document.getElementById("canvas")
      // setting both as width since canvas is always square
      setCanvasDimensions({ width: canvas?.offsetWidth || 0, height: canvas?.offsetWidth || 0 })
      console.info("CANVAS WIDTH:", canvas?.offsetWidth)
      console.info("CANVAS HEIGHT:", canvas?.offsetHeight)
    }
  }, [])

  return (
    <div className="canvas-container">
      <div id="canvas" className="preview-canvas" style={{ height: canvasDimensions.width }}>
        {
          canvasDimensions.width !== 0 ?
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
              onDragStop={(e, d) => {
                if (props.onPositionUpdate) {
                  props.onPositionUpdate({ x: d.x, y: d.y })
                }
                setContentPosition({ x: d.x, y: d.y })
              }}

              lockAspectRatio
              dragAxis="both"
              bounds=".preview-canvas"
              enableResizing={{ "bottomRight": true }}
            >
              {props.svgContent ?
                <div id="canvas-content" className="canvas-content" /*style={{ height: contentDimensions.height, width: contentDimensions.width }}*/ dangerouslySetInnerHTML={{ __html: props.svgContent }}>
                </div> : null}
            </Rnd> : null}
      </div>
    </div >
  );
}

export default PreviewCanvas;

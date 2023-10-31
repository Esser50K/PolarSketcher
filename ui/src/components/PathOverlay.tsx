import React, { useState } from 'react';
import { Stage, Layer, Line, Circle } from 'react-konva';

interface PathOverlayProps {
  imageDimensions: { width: number, height: number };
}

type Line = {
  start?: { x: number; y: number };
  end?: { x: number; y: number };
  controlPoints?: Array<{ x: number; y: number }>;
};

const PathOverlay: React.FC<PathOverlayProps> = ({ imageDimensions }) => {
  const [lines, setLines] = useState<any[]>([]);
  const [currentNewLine, setCurrentNewLine] = useState<Line>({});
  const [selectedLine, setSelectedLine] = useState<number | null>(null);
  const [currentMousePosition, setCurrentMousePosition] = useState<{ x: number; y: number } | null>(null);
  const [dragStartPos, setDragStartPos] = useState<{ x: number, y: number } | null>(null);

  const { width, height } = imageDimensions;

  const handleOnStageClick = (e: any) => {
    setSelectedLine(null);

    const stage = e.target.getStage();
    const relativePos = stage.pointerPos; // This gives the position relative to the canvas
    const clickedPoint = { x: relativePos.x, y: relativePos.y };

    // If there's no currentLine.start, set it.
    if (!currentNewLine.start) {
      setCurrentNewLine({ start: clickedPoint });
      return;
    }

    // If there's a currentLine.start but no currentLine.end, set the end.
    if (currentNewLine.start && !currentNewLine.end) {
      setCurrentNewLine((prevLine: Line) => ({ ...prevLine, end: clickedPoint }));
      setLines(prevLines => [...prevLines, { start: currentNewLine.start, end: clickedPoint }]);
      setCurrentNewLine({});
    }
  };

  const handleSelectLine = (lineIndex: number) => {
    setSelectedLine(lineIndex);
  }

  const getLineColor = (lineIndex: number) => {
    if (lineIndex === selectedLine) {
      return 'green';
    }

    return 'blue';
  }

  return (
    <Stage
      width={width}
      height={height}
      style={{ position: 'absolute', top: 0, left: 0, zIndex: 2 }}
      onClick={handleOnStageClick}
      onMouseMove={e => {
        const stage = e.target.getStage();
        if (!stage) {
          return;
        }

        const mousePos = stage.pointerPos;
        setCurrentMousePosition(mousePos);
      }}
    >
      <Layer>
        {/* Render existing lines and their control points */}
        {lines.map((line, lineIndex) => (
          <React.Fragment key={lineIndex}>
            {line.start && line.end && (
              <Line
                draggable
                points={[line.start.x, line.start.y, line.end.x, line.end.y]}
                stroke={getLineColor(lineIndex)}
                onClick={(e) => {
                  e.cancelBubble = true;
                  handleSelectLine(lineIndex)
                }}
                onContextMenu={(e) => {
                  e.evt.preventDefault(); // prevent the default context menu
                  const newLines = [...lines];
                  newLines.splice(lineIndex, 1);
                  setLines(newLines);
                }}
              />
            )}
            {line.start && (
              <Circle
                x={line.start.x}
                y={line.start.y}
                radius={5}
                fill="red"
                draggable
                onDragMove={(e) => {
                  const newLines = [...lines];
                  newLines[lineIndex].start = e.target.position();
                  setLines(newLines);
                }}
              />
            )}
            {line.end && (
              <Circle
                x={line.end.x}
                y={line.end.y}
                radius={5}
                fill="red"
                draggable
                onDragMove={(e) => {
                  const newLines = [...lines];
                  newLines[lineIndex].end = e.target.position();
                  setLines(newLines);
                }}
              />
            )}
          </React.Fragment>
        ))}

        {/* Render dynamic line that follows the cursor */}
        {currentNewLine.start && currentMousePosition && (
          <Line
            points={[currentNewLine.start.x, currentNewLine.start.y, currentMousePosition.x, currentMousePosition.y]}
            stroke="blue"
          />
        )}
      </Layer>
    </Stage>
  );
};

export default PathOverlay;

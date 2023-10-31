import React from 'react';

interface GridOverlayProps {
  gridSize: number;
  imageDimensions: { width: number, height: number };
}

const GridOverlay: React.FC<GridOverlayProps> = ({ gridSize, imageDimensions }) => {
  const { width, height } = imageDimensions;

  // Calculate the number of vertical and horizontal lines required
  const verticalLines = Math.floor(width / gridSize);
  const horizontalLines = Math.floor(height / gridSize);

  return (
    <svg width={width} height={height} style={{ position: 'absolute', top: 0, left: 0 }}>
      {/* Render vertical lines */}
      {Array.from({ length: verticalLines }).map((_, index) => (
        <line
          key={`v-${index}`}
          x1={index * gridSize}
          y1={0}
          x2={index * gridSize}
          y2={height}
          stroke="black"
          strokeWidth="0.5"
        />
      ))}

      {/* Render horizontal lines */}
      {Array.from({ length: horizontalLines }).map((_, index) => (
        <line
          key={`h-${index}`}
          x1={0}
          y1={index * gridSize}
          x2={width}
          y2={index * gridSize}
          stroke="black"
          strokeWidth="0.5"
        />
      ))}
    </svg>
  );
};

export default GridOverlay;

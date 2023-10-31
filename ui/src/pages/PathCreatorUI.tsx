import React, { useState } from 'react';
import TextInput from '../units/TextInput';
import GridOverlay from '../components/GridOverlay';
import PathOverlay from '../components/PathOverlay';

const PathCreatorUI: React.FC = () => {
    const [image, setImage] = useState<File | null>(null);
    const [gridSize, setGridSize] = useState<number>(10); // default value
    const [imageUrl, setImageUrl] = useState<string | null>(null);
    const [imageDimensions, setImageDimensions] = useState<{ width: number, height: number } | null>(null);

    const handleImageChange = (event: React.ChangeEvent<HTMLInputElement>) => {
        const file = event.target.files ? event.target.files[0] : null;
        setImage(file);

        if (file) {
            const reader = new FileReader();
            reader.onloadend = () => {
                setImageUrl(reader.result as string);
            };
            reader.readAsDataURL(file);
        } else {
            setImageUrl(null);
        }
    };

    return (
        <div className="flex flex-col h-full">
            {/* Top Bar */}
            <div className="flex justify-between items-center bg-gray-800 p-4">
                {/* Image Upload */}
                <div>
                    <label className="text-white mr-2">Upload Image:</label>
                    <input type="file" accept="image/*" onChange={handleImageChange} />
                </div>

                {/* Grid Size Input */}
                <div className="flex items-center">
                    <TextInput
                        title="Drawing Name"
                        placeholder="write drawing name"
                        onValueChange={(value) => { setGridSize(Number(value)) }}
                        buttonText="Save Drawing"
                    // onButtonClick={saveDrawing}
                    ></TextInput>
                </div>
            </div>

            {/* Content Area */}
            <div className="flex-grow bg-gray-200 p-4 relative"> {/* Added 'relative' class for positioning */}
                {imageUrl && <img src={imageUrl} alt="Uploaded preview" className="max-w-full max-h-full" onLoad={(e) => {
                    const img = e.target as HTMLImageElement;
                    setImageDimensions({ width: img.width, height: img.height });
                }} />}
                {image && imageUrl && imageDimensions && (
                    <>
                        <GridOverlay gridSize={gridSize} imageDimensions={imageDimensions} />
                        <PathOverlay imageDimensions={imageDimensions} />
                    </>
                )}
            </div>
        </div>
    );
};

export default PathCreatorUI;

import React, { useEffect, useState } from 'react';
import './Upload.css';
import PreviewCanvas from '../components/PreviewCanvas'

function Upload() {
    const [selectedFile, setSelectedFile] = useState("");
    const [svgContent, setSvgContent] = useState("");
    const [center, setCenter] = useState(false);
    const [contentScale, setCotentScale] = useState(1.0);
    const [contentPosition, setContentPosition] = useState({ x: 0, y: 0 });

    const handleSelectImage = (event: React.ChangeEvent<HTMLInputElement>) => {
        console.info(typeof (event), event.target.files?.item(0));
        const reader = new FileReader();
        reader.onload = () => {
            setSvgContent(String(reader.result))
        }
        if (event.target.files && event.target.files[0]) {
            reader.readAsText(event.target.files[0]);
            setSelectedFile(event.target.files[0].name);
        }
    }

    const handleCenterClick = () => {
        setCenter(true);
    }

    const handleUpload = async () => {
        if (svgContent === "") {
            return
        }

        try {
            const body = {
                position: [contentPosition.x, contentPosition.y],
                scale: contentScale,
                svg: svgContent
            }

            const resp = await fetch(
                "http://" + document.location.hostname + ":9943/upload",
                {
                    method: 'POST',
                    body: JSON.stringify(body)
                })
            if (resp.status !== 200) {
                alert("failed to upload image: " + await resp.text())
            }
        } catch (e) {
            alert("failed to upload image: " + e)
        }
    }

    const onPositionUpdate = (position: { x: number, y: number }) => setContentPosition(position)
    const onResizeUpdate = (scale: number) => setCotentScale(scale)

    useEffect(() => {
        setCenter(false)
    }, [center])

    return (
        <div className="upload-container">
            <div className="actions-bar">
                <div className="image-selection-container">
                    <div className="select-button-container action-button">
                        <input type="file"
                            accept="image/svg+xml"
                            name="image"
                            id="file"
                            style={{ "display": "none" }}
                            onChange={handleSelectImage}>
                        </input>
                        <p><label htmlFor="file" className="upload-button-text">{selectedFile === "" ? "Select Image" : "Selected Image:"}</label></p>
                        {selectedFile !== "" ?
                            <p className="selected-file">{selectedFile}</p> : null}
                    </div>
                    <div className="action-button">
                        <button onClick={handleUpload}>Upload Image</button>
                    </div>
                </div>
                <div className="actions-bar-buttons">
                    <button className="action-button" onClick={handleCenterClick}>Center</button>
                </div>
            </div>
            <div className="preview-container">
                <PreviewCanvas
                    center={center}
                    svgContent={svgContent}
                    onResizeUpdate={onResizeUpdate}
                    onPositionUpdate={onPositionUpdate}>
                </PreviewCanvas>
            </div>
        </div >
    );
}

export default Upload;

import React, { ChangeEvent, SyntheticEvent, useEffect, useState } from 'react';
import logo from '../logo.svg';
import './Upload.css';
import PreviewCanvas from '../components/PreviewCanvas'

function Upload() {
    const [svgContent, setSvgContent] = useState("");
    const [center, setCenter] = useState(false);

    const handleUpload = (event: React.ChangeEvent<HTMLInputElement>) => {
        console.info(typeof (event), event.target.files?.item(0));
        const reader = new FileReader();
        reader.onload = () => {
            setSvgContent(String(reader.result))
        }
        if (event.target.files && event.target.files[0]) {
            reader.readAsText(event.target.files[0]);
        }
    }

    const handleCenterClick = () => {
        setCenter(true);
    }

    useEffect(() => {
        setCenter(false)
    }, [center])

    return (
        <div className="upload-container">
            <div className="actions-bar">
                <div className="actions-bar-buttons">
                    <div className="upload-button-container action-button">
                        <input type="file" accept="image/svg+xml" name="image" id="file" style={{ "display": "none" }} onChange={handleUpload}></input>
                        <p><label htmlFor="file" className="upload-button-text">Upload Image</label></p>
                    </div>
                    <button className="action-button" onClick={handleCenterClick}>Center</button>
                </div>
            </div>
            <div className="preview-container">
                <PreviewCanvas
                    center={center}
                    svgContent={svgContent}>
                </PreviewCanvas>
            </div>
        </div >
    );
}

export default Upload;

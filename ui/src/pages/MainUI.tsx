import React, { useEffect, useState } from 'react';
import '../index.css';
import './MainUI.css';
import PreviewCanvas from '../components/PreviewCanvas'
import SimulationCanvas from '../components/SimulationCanvas'

function MainUI() {
    const [selectedFile, setSelectedFile] = useState("");
    const [svgContent, setSvgContent] = useState("");
    const [center, setCenter] = useState(false);
    const [runningJobId, setRunningJobId] = useState("");
    const [websocket, setWebsocket] = useState<WebSocket>();
    const [drawnPoints, setDrawnPoints] = useState<[number, number][]>([]);
    const [contentSize, setCotentSize] = useState([600, 600]);
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
            const canvasDiv = document.getElementById("simulation-canvas");
            const ratio = canvasDiv!.offsetWidth / 600;

            const body = {
                position: [contentPosition.x / ratio, contentPosition.y / ratio],
                size: [contentSize[0] / ratio, contentSize[1] / ratio],
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
                return
            }

            const jobId = await resp.text()
            setRunningJobId(jobId);
            if (websocket) {
                websocket.close();
            }
            setWebsocket(undefined);
        } catch (e) {
            alert("failed to upload image: " + e)
        }
    }

    useEffect(() => {
        if (runningJobId === "") {
            return
        }
        if (!!websocket) {
            console.info("STILL GOT WS")
            return
        }

        const webSocket = new WebSocket("ws://" + document.location.hostname + ":9943/updates");
        webSocket.onclose = () => {
            setRunningJobId("");
            setWebsocket(undefined);
            console.info("WEBSOCKET DONE");
        }
        webSocket.onerror = () => {
            setRunningJobId("");
            setWebsocket(undefined);
            console.info("WEBSOCKET ERROR");
        }
        webSocket.onmessage = (event: MessageEvent) => {
            const update = JSON.parse(event.data);
            const newDrawnPoints = drawnPoints;
            (update.payload as Array<[number, number]>)?.forEach((val) => {
                newDrawnPoints.push(val);
            })
            setDrawnPoints(newDrawnPoints);
        }
        setWebsocket(webSocket);
    }, [runningJobId, websocket])

    const onPositionUpdate = (position: { x: number, y: number }) => setContentPosition(position)
    const onResizeUpdate = (width: number, height: number) => setCotentSize([width, height])

    useEffect(() => {
        setCenter(false)
    }, [center])

    return (
        <div className="upload-container m-2">
            <div className="flex flex-col items-center justify-center m-8">
                <div className="w-full flex flex-row items-center justify-start">
                    <div>
                        <button
                            className="button-base"
                            onClick={handleUpload}>Upload Image
                        </button>
                    </div>
                    <div className="flex items-center">
                        <input type="file"
                            accept="image/svg+xml"
                            name="image"
                            id="file"
                            style={{ "display": "none" }}
                            onChange={handleSelectImage}>
                        </input>
                        <p className={`ml-5 p-1 text-sm ${selectedFile === '' ? 'border-2 rounded-sm' : ''}`}>
                            <label htmlFor="file">
                                {selectedFile === "" ? "Select Image" : selectedFile}
                            </label>
                        </p>
                    </div>
                </div>
                <div className="w-full mt-1 mb-1 flex flex-row items-center">
                    <div className="mr-4 flex-grow h-1 bg-gray-100"></div>
                    <div className="font-bold">Action Buttons</div>
                    <div className="ml-4 flex-grow h-1 bg-gray-100"></div>
                </div>
                <div className="w-full m-2 flex flex-row">
                    <button className="button-base" onClick={handleCenterClick}>
                        Center
                    </button>
                </div>
            </div>
            <div className="canvas-containers">
                <div className="preview-container mr-2">
                    <PreviewCanvas
                        center={center}
                        svgContent={svgContent}
                        onResizeUpdate={onResizeUpdate}
                        onPositionUpdate={onPositionUpdate}>
                    </PreviewCanvas>
                </div>

                <div className="preview-container ml-2">
                    <SimulationCanvas ws={websocket}>
                    </SimulationCanvas>
                </div>
            </div>
        </div >
    );
}

export default MainUI;

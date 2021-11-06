import React, { useEffect, useState } from 'react';
import '../index.css';
import './MainUI.css';
import PreviewCanvas from '../components/PreviewCanvas'
import SimulationCanvas from '../components/SimulationCanvas'
import Dropdown from '../units/Dropdown';
import Divider from '../units/Divider';
import NumberInput from '../units/NumberInput';
import RangeInput from '../units/RangeInput';
import CheckboxInput from '../units/CheckboxInput';

function MainUI() {
    const [selectedFile, setSelectedFile] = useState("");
    const [svgContent, setSvgContent] = useState("");
    const [runningJobId, setRunningJobId] = useState("");
    const [websocket, setWebsocket] = useState<WebSocket>();
    const [drawnPoints, setDrawnPoints] = useState<[number, number][]>([]);
    const [contentSize, setCotentSize] = useState([600, 600]);
    const [contentPosition, setContentPosition] = useState({ x: 0, y: 0 });
    const [dryrunChecked, setDryrunChecked] = useState(true);

    // edit tools
    const [center, setCenter] = useState(false);
    const [maxout, setMaxout] = useState(false);
    const [cutLeft, setCutLeft] = useState(false);
    const [cutRight, setCutRight] = useState(false);
    const [rotation, setRotation] = useState(0);

    // toolpath algorithm config
    const [toolpathAlgorithm, setToolpathAlgorithm] = useState("");
    const [nToolpathLines, setNToolpathLines] = useState(100);
    const [toolpathAngle, setToolpathAngle] = useState(0);

    // toolpath algorithm config
    const [pathSortingAlgorithm, setPathSortingAlgorithm] = useState("");
    const [searchStartX, setSearchStartX] = useState(0);
    const [searchStartY, setSearchStartY] = useState(0);

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

    const handleUpload = async () => {
        if (svgContent === "") {
            return
        }

        try {
            const canvasDiv = document.getElementById("simulation-canvas");
            const ratio = canvasDiv!.offsetWidth / 600;  // TODO: remove hardcoded arm length

            const body = {
                position: [contentPosition.x / ratio, contentPosition.y / ratio],
                size: [contentSize[0] / ratio, contentSize[1] / ratio],
                dryrun: dryrunChecked,
                rotation: rotation,
                toolpath_config: {
                    algorithm: toolpathAlgorithm,
                    n_lines: nToolpathLines,
                    angle: toolpathAngle,
                },
                pathsort_config: {
                    algorithm: pathSortingAlgorithm,
                    x: searchStartX,
                    y: searchStartY,
                },
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
        }
        webSocket.onerror = () => {
            setRunningJobId("");
            setWebsocket(undefined);
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
        setMaxout(false)
        setCutLeft(false)
        setCutRight(false)
    }, [center, maxout, cutLeft, cutRight])

    return (
        <div className="upload-container m-2">
            <div className="m-8">
                <div className="w-full flex flex-col items-start justify-start">
                    <div>
                        <CheckboxInput
                            label="Use Dryrun"
                            default={true}
                            onValueChange={(val) => { setDryrunChecked(val) }}
                        ></CheckboxInput>
                    </div>
                    <div className="flex flex-row">
                        {selectedFile !== "" ?
                            <div className="button-base mt-2">
                                <button
                                    onClick={handleUpload}>Upload Image
                                </button>
                            </div> : null}
                        <div className="flex items-center">
                            <input type="file"
                                accept="image/svg+xml"
                                name="image"
                                id="file"
                                style={{ "display": "none" }}
                                onChange={handleSelectImage}>
                            </input>
                            <p className={`mt-2 p-1 text-sm ${selectedFile === '' ? 'border-2 rounded-sm' : ''}`}>
                                <label htmlFor="file">
                                    {selectedFile === "" ? "Select Image" : selectedFile}
                                </label>
                            </p>
                        </div>
                    </div>
                </div>
                <Divider title="Edit Tools"></Divider>
                <div className="w-full m-2 flex flex-row items-stretch">
                    <div className="flex">
                        <button className="button-base" onClick={() => setCenter(true)}>
                            center
                        </button>
                    </div>
                    <div className="flex ml-2">
                        <button className="button-base" onClick={() => setMaxout(true)}>
                            max out
                        </button>
                    </div>
                    <div className="flex ml-2">
                        <button className="button-base" onClick={() => setCutLeft(true)}>
                            cut left
                        </button>
                    </div>
                    <div className="flex ml-2">
                        <button className="button-base" onClick={() => setCutRight(true)}>
                            cut right
                        </button>
                    </div>
                    <div className="flex ml-2">
                        <RangeInput title="rotate" max={360} onValueChange={(val) => setRotation(parseInt(val))}></RangeInput>
                    </div>
                </div>
            </div>
            <div className="canvas-containers">
                <div className="preview-container mr-2">
                    <PreviewCanvas
                        rotation={rotation}
                        center={center}
                        maxout={maxout}
                        svgContent={svgContent}
                        onResizeUpdate={onResizeUpdate}
                        onPositionUpdate={onPositionUpdate}>
                    </PreviewCanvas>
                </div>

                <div className="preview-container ml-2">
                    <SimulationCanvas
                        ws={websocket}
                        cutleft={cutLeft}
                        cutright={cutRight}
                    ></SimulationCanvas>
                </div>
            </div>

            {/* Toolpath Generation Algo Config */}
            <div className="m-8">
                <Divider title="Toolpath Generation Algorithm Config"></Divider>
                <div className="flex flex-row justify-start items-stretch">
                    <div className="flex">
                        <Dropdown
                            label="toolpath generation algorithm"
                            options={{
                                "none": "None",
                                "lines": "Lines",
                                "zigzag": "ZigZag",
                                "rectlines": "RectLines",
                            }}
                            onValueChange={(val) => { setToolpathAlgorithm(val) }}
                        ></Dropdown>
                    </div>
                    <div className="ml-5 flex">
                        <NumberInput title="number of Lines" onValueChange={(val) => { setNToolpathLines(parseInt(val)) }}></NumberInput>
                    </div>
                    <div className="ml-5 flex">
                        <RangeInput title="angle" max={360} onValueChange={(val) => { setToolpathAngle(parseInt(val)) }}></RangeInput>
                    </div>
                </div>
            </div>

            {/* Sort Path Algorithm Config*/}
            <div className="m-8">
                <Divider title="Sort Path Algorithm Config"></Divider>
                <div className="flex flex-row justify-start items-stretch">
                    <div className="flex">
                        <Dropdown
                            label="path sorting algorithm"
                            options={{
                                "none": "None",
                                "simple": "Simple",
                                "simple_variant1": "Simple Variant1",
                                "simple_variant2": "Simple Variant2",
                                "radar_scan": "Radar Scan",
                            }}
                            onValueChange={(val) => { setPathSortingAlgorithm(val) }}
                        ></Dropdown>
                    </div>
                    <div className="ml-5 flex">
                        <NumberInput title="Start X" default={0} max={600} onValueChange={(val) => { setSearchStartX(parseInt(val)) }}></NumberInput>
                    </div>
                    <div className="ml-5 flex">
                        <NumberInput title="Start Y" default={0} max={600} onValueChange={(val) => { setSearchStartY(parseInt(val)) }}></NumberInput>
                    </div>
                </div>
            </div>
        </div >
    );
}

export default MainUI;

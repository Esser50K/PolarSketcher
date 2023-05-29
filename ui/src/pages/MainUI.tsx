import React, { useEffect, useState } from 'react';
import '../index.css';
import './MainUI.css';
import PreviewCanvas, { DrawnSVG } from '../components/PreviewCanvas'
import SimulationCanvas from '../components/SimulationCanvas'
import Dropdown from '../units/Dropdown';
import Divider from '../units/Divider';
import NumberInput from '../units/NumberInput';
import RangeInput from '../units/RangeInput';
import CheckboxInput from '../units/CheckboxInput';

const polar2Cartesian = (amplitude: number, angle: number) => {
    // Convert polar to cartesian
    const x = amplitude * Math.cos(angle * (Math.PI / 180));
    const y = amplitude * Math.sin(angle * (Math.PI / 180));
    return { x: x, y: y };
}

// canvasWidth(585)-cariageLength(72)
const FULL_CANVAS_WIDTH = 513;
const FULL_CANVAS_HEIGHT = 513;
const REDUCED_CANVAS_WIDTH = polar2Cartesian(FULL_CANVAS_WIDTH, 45).x;
const REDUCED_CANVAS_HEIGHT = REDUCED_CANVAS_WIDTH;
const A2_CANVAS_WIDTH = 594;
const A2_CANVAS_HEIGHT = 420;
const A3_CANVAS_WIDTH = 420;
const A3_CANVAS_HEIGHT = 297;
const A4_CANVAS_WIDTH = 297;
const A4_CANVAS_HEIGHT = 210;

const CANVAS_DIMENSIONS: { [key: string]: [number, number] } = {
    "full": [FULL_CANVAS_WIDTH, FULL_CANVAS_HEIGHT],
    "reduced": [REDUCED_CANVAS_WIDTH, REDUCED_CANVAS_HEIGHT],
    "A2": [A2_CANVAS_WIDTH, A2_CANVAS_HEIGHT],
    "A3": [A3_CANVAS_WIDTH, A3_CANVAS_HEIGHT],
    "A4": [A4_CANVAS_WIDTH, A4_CANVAS_HEIGHT],
}

function MainUI() {
    const [selectedFile, setSelectedFile] = useState("");
    const [svgContent, setSvgContent] = useState("");
    const [runningJobId, setRunningJobId] = useState("");
    const [websocket, setWebsocket] = useState<WebSocket>();
    const [drawnPoints, setDrawnPoints] = useState<[number, number][]>([]);
    const [contentSize, setCotentSize] = useState([FULL_CANVAS_WIDTH, FULL_CANVAS_HEIGHT])
    const [contentPosition, setContentPosition] = useState({ x: 0, y: 0 });
    const [dryrunChecked, setDryrunChecked] = useState(true);
    const [drawnSVGs, setDrawnSVGs] = useState<DrawnSVG[]>([]);
    const [canvasDimensions, setCanvasDimensions] = useState<{ x: number, y: number }>({ x: FULL_CANVAS_WIDTH, y: FULL_CANVAS_HEIGHT });

    // edit tools
    const [center, setCenter] = useState(false);
    const [maxout, setMaxout] = useState(false);
    const [cutLeft, setCutLeft] = useState(false);
    const [cutRight, setCutRight] = useState(false);
    const [rotation, setRotation] = useState(0);

    // toolpath algorithm config
    const [toolpathAlgorithm, setToolpathAlgorithm] = useState("none");
    const [lineStep, setLineStep] = useState(10);
    const [toolpathAngle, setToolpathAngle] = useState(0);

    // toolpath algorithm config
    const [pathSortingAlgorithm, setPathSortingAlgorithm] = useState("none");
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

    const setRealCanvasDimensions = (val: string) => {
        const dimensions = CANVAS_DIMENSIONS[val];
        setCanvasDimensions({ x: dimensions[0], y: dimensions[1] });
    }

    const drawBoundary = async () => {
        try {
            const body = {
                canvas_size: [canvasDimensions.x, canvasDimensions.y],
                dryrun: dryrunChecked,
            }

            const resp = await fetch(
                "http://" + document.location.hostname + ":9943/draw_boundary",
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

    const handleUpload = async () => {
        if (svgContent === "") {
            return
        }

        try {
            const canvasDiv = document.getElementById("simulation-canvas");
            const realToVirtualRatio = (canvasDiv!.offsetWidth / canvasDimensions.x);

            const sizeInPreviewCanvas = [contentSize[0] / realToVirtualRatio, contentSize[1] / realToVirtualRatio]
            const posInPreviewCanvas = [(contentPosition.x / realToVirtualRatio), (contentPosition.y / realToVirtualRatio)]
            const reducedModeOffset = FULL_CANVAS_WIDTH - canvasDimensions.x;
            const body = {
                position: [
                    posInPreviewCanvas[0] + reducedModeOffset,
                    posInPreviewCanvas[1]],
                size: [sizeInPreviewCanvas[0], sizeInPreviewCanvas[1]],
                dryrun: dryrunChecked,
                rotation: rotation,
                toolpath_config: {
                    algorithm: toolpathAlgorithm,
                    line_step: lineStep,
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

            const newDrawnSVGs = drawnSVGs;
            newDrawnSVGs.push({
                svgContent: svgContent,
                position: body.position,
                rotation: body.rotation,
                dimensions: body.size
            })
            setDrawnSVGs(newDrawnSVGs)
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
                    <div className="flex">
                        <Dropdown
                            label="canvas dimensions"
                            options={{
                                "full": "full",
                                "reduced": "reduced",
                                "A2": "A2",
                                "A3": "A3",
                                "A4": "A4",
                            }}
                            onValueChange={(val) => { setRealCanvasDimensions(val) }}
                        ></Dropdown>
                    </div>
                    <div className="flex ml-2">
                        <button className="button-base" onClick={drawBoundary}>
                            draw boundary
                        </button>
                    </div>
                </div>
            </div>
            <div className="canvas-containers">
                <div className="preview-container mr-2">
                    <PreviewCanvas
                        fullCanvasDimensions={{ x: FULL_CANVAS_WIDTH, y: FULL_CANVAS_HEIGHT }}
                        canvasDimensions={canvasDimensions}
                        rotation={rotation}
                        center={center}
                        maxout={maxout}
                        svgContent={svgContent}
                        drawnSVGs={drawnSVGs}
                        onResizeUpdate={onResizeUpdate}
                        onPositionUpdate={onPositionUpdate}>
                    </PreviewCanvas>
                </div>

                <div className="preview-container ml-2">
                    <SimulationCanvas
                        fullCanvasDimensions={{ x: FULL_CANVAS_WIDTH, y: FULL_CANVAS_HEIGHT }}
                        canvasDimensions={canvasDimensions}
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
                        <NumberInput title="line step" default={10} onValueChange={(val) => { setLineStep(parseInt(val)) }}></NumberInput>
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
                                "closest_path": "Simple",
                                "closest_path_with_reverse": "Simple Variant1",
                                "closest_path_with_start_anywhere": "Simple Variant2",
                                "radar_scan": "Radar Scan",
                            }}
                            onValueChange={(val) => { setPathSortingAlgorithm(val) }}
                        ></Dropdown>
                    </div>
                    <div className="ml-5 flex">
                        <NumberInput title="Start X" default={0} max={canvasDimensions.x} onValueChange={(val) => { setSearchStartX(parseInt(val)) }}></NumberInput>
                    </div>
                    <div className="ml-5 flex">
                        <NumberInput title="Start Y" default={0} max={canvasDimensions.y} onValueChange={(val) => { setSearchStartY(parseInt(val)) }}></NumberInput>
                    </div>
                </div>
            </div>
        </div >
    );
}

export default MainUI;

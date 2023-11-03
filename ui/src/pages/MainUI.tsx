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
import TextInput from '../units/TextInput';
import DropdownInput from '../units/DropdownInput';


interface SavedDrawing {
    name: string,
    drawings: DrawnSVG[],
}

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
    const [imageURL, setImageURL] = useState("");
    const [image, setImage] = useState<File>();
    const [runningJobId, setRunningJobId] = useState("");
    const [websocket, setWebsocket] = useState<WebSocket>();
    const [drawnPoints, setDrawnPoints] = useState<[number, number][]>([]);
    const [contentSize, setCotentSize] = useState([FULL_CANVAS_WIDTH, FULL_CANVAS_HEIGHT])
    const [contentPosition, setContentPosition] = useState({ x: 0, y: 0 });
    const [dryrunChecked, setDryrunChecked] = useState(true);
    const [drawnSVGs, setDrawnSVGs] = useState<DrawnSVG[]>([]);
    const [canvasDimensions, setCanvasDimensions] = useState<{ x: number, y: number }>({ x: FULL_CANVAS_WIDTH, y: FULL_CANVAS_HEIGHT });
    const [drawingName, setDrawingName] = useState("");
    const [savedDrawings, setSavedDrawings] = useState<{ [key: string]: SavedDrawing }>({});
    const [selectedDrawing, setSelectedDrawing] = useState("");

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

    // bitmap image configs
    const [bitmapProcessingAlgorithm, setBitmapProcessingAlgorithm] = useState("ascii");
    // ascii specific configs
    const [asciiWidth, setAsciiWidth] = useState(80);
    // sin wave specific configs
    const [pixelWidth, setPixelWidth] = useState(8);
    const [maxSinAmplitude, setMaxSinAmplitude] = useState(4);
    const [maxSinFrequency, setMaxSinFrequency] = useState(2);
    const [resolution, setResolution] = useState(.25);


    const handleAbort = async () => {
        const resp = await fetch(
            "http://" + document.location.hostname + ":9943/abort",
            {
                method: 'POST'
            })

        if (resp.status !== 200) {
            console.error("failed to abort job: " + await resp.text())
            return
        }

    }

    const handleSelectImage = (event: React.ChangeEvent<HTMLInputElement>) => {
        console.info("GOT FILE:", typeof (event), event.target.files?.item(0));
        const file = event.target.files?.item(0);

        if (!file) {
            console.error("no image uploaded")
            return;
        }

        if (file.name.includes("svg")) {
            const reader = new FileReader();
            reader.onload = () => {
                setSvgContent(String(reader.result))
            }
            reader.readAsText(file);
            setImage(undefined);
        } else {
            const fileURL = URL.createObjectURL(file);
            console.info("FILE URL:", fileURL);
            setImage(file);
            setImageURL(fileURL);
            setSvgContent("");
        }
        setSelectedFile(file.name);
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

    const saveDrawing = async () => {
        if (drawingName === "") {
            alert("missing drawing name")
            return
        }

        if (drawnSVGs.length === 0) {
            alert("missing drawings")
            return
        }

        const body = {
            name: drawingName,
            drawings: drawnSVGs
        }

        const resp = await fetch(
            "http://" + document.location.hostname + ":9943/drawing/save",
            {
                method: 'POST',
                body: JSON.stringify(body)
            }
        )

        if (resp.status !== 200) {
            alert("failed to save drawing: " + await resp.text())
            return
        }
    }

    const loadDrawings = async () => {
        try {
            const resp = await fetch(
                "http://" + document.location.hostname + ":9943/drawing/list",
                { method: 'GET' }
            )

            if (resp.status !== 200) {
                console.error("failed to load drawings: " + await resp.text())
                return
            }

            const newSavedDrawings: SavedDrawing[] = (await resp.json()).svgs;
            const savedDrawingsMap = newSavedDrawings.reduce(
                (acc: { [key: string]: SavedDrawing }, svg: SavedDrawing) => {
                    acc[svg.name] = svg;
                    return acc;
                }, {})

            setSavedDrawings(savedDrawingsMap)
            setSelectedDrawing(newSavedDrawings[0].name)
        } catch (error) {
            console.error("failed to load drawings: " + String(error))
        }
    };

    const loadDrawing = (drawingName: string) => {
        const savedDrawing = savedDrawings[drawingName];
        setDrawnSVGs(savedDrawing.drawings);
    };

    const handleUpload = async () => {
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
            svg: "",
            image: "",
        }

        if (!image) {
            body.svg = svgContent;
            await handleUploadSVG(body);
        } else {
            await handleUploadImage(body);
        }
    }

    const handleUploadImage = async (body: any) => {
        if (!image) {
            return;
        }

        const reader = new FileReader();
        reader.readAsDataURL(image);
        reader.onloadend = async () => {
            const base64data = reader.result as string;
            body.image = base64data?.replace(/^data:image\/[^;]+;base64,/, "");  // need to remove the stupid prefix
            body.image_processor = bitmapProcessingAlgorithm
            body.ascii_processor_args = {
                "ascii_width": asciiWidth
            }
            body.sin_processor_args = {
                "pixel_width": pixelWidth,
                "max_amplitude": maxSinAmplitude,
                "resolution": resolution,
            }

            // Send the Base64 string to the backend
            try {
                const resp = await fetch("http://" + document.location.hostname + ":9943/upload_bitmap", {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify(body)
                })

                if (resp.status !== 200) {
                    alert("failed to upload image: " + await resp.text())
                    return
                }

                const jsonResp = await resp.json()
                handleUploadFinish(jsonResp.jobId, jsonResp.svg, body);
            } catch (error) {
                console.error("failed to upload image");
            }
        }
    }

    const handleUploadSVG = async (body: any) => {
        if (svgContent === "") {
            return
        }

        try {
            const resp = await fetch(
                "http://" + document.location.hostname + ":9943/upload_svg",
                {
                    method: 'POST',
                    body: JSON.stringify(body)
                }
            )

            if (resp.status !== 200) {
                alert("failed to upload image: " + await resp.text())
                return
            }

            const jobId = await resp.text()
            handleUploadFinish(jobId, svgContent, body);
        } catch (e) {
            alert("failed to upload image: " + e)
        }
    }

    const handleUploadFinish = (jobId: string, svgContent: string, body: any) => {
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

    // load drawings on page load
    useEffect(() => {
        loadDrawings();
    }, [])

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
                <div className="m-8 w-full flex flex-row">
                    <div className="flex flex-col items-start justify-start">
                        <div className="w-full">
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
                                    accept="image/svg+xml+png+jpg"
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
                        <div className="w-full">
                            <div className="button-base mt-2">
                                <button
                                    onClick={handleAbort}>Abort Job
                                </button>
                            </div>
                        </div>
                    </div>
                    <div className="flex flex-col items-start justify-start ml-4">
                        <TextInput
                            title="Drawing Name"
                            placeholder="write drawing name"
                            onValueChange={(value) => { setDrawingName(value) }}
                            buttonText="Save Drawing"
                            onButtonClick={saveDrawing}
                        ></TextInput>
                    </div>
                    <div className="flex flex-col items-start justify-start ml-4">
                        <DropdownInput
                            label="Select Drawing"
                            options={savedDrawings}
                            onValueChange={(name) => { setSelectedDrawing(name); }}
                            buttonText="Load Drawing"
                            onButtonClick={() => loadDrawing(selectedDrawing)}
                        ></DropdownInput>
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
                        imageURL={imageURL}
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
            {svgContent !== "" ?
                <>
                    < div className="m-8">
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
                </> : null
            }

            {/* Configs for bitmap images */}
            {!!image ?
                <div className="m-8">
                    <Divider title="Bitmap Transformation Config"></Divider>
                    <div className="flex flex-row justify-start items-stretch">
                        <div className="flex">
                            <Dropdown
                                label="bitmap transformation algorithm"
                                options={{
                                    "ascii": "ascii",
                                    "sin": "sin",
                                }}
                                onValueChange={(val) => { setBitmapProcessingAlgorithm(val) }}
                            ></Dropdown>
                        </div>

                        {bitmapProcessingAlgorithm === "ascii" ?
                            <>
                                <div className="ml-5 flex">
                                    <NumberInput
                                        title="Ascii Width"
                                        default={asciiWidth}
                                        min={10}
                                        max={100}
                                        onValueChange={(val) => { setAsciiWidth(parseInt(val)) }}
                                    ></NumberInput>
                                </div>
                            </>
                            : null}

                        {bitmapProcessingAlgorithm === "sin" ?
                            <>
                                <div className="ml-5 flex">
                                    <NumberInput
                                        title="Pixel Width"
                                        default={pixelWidth}
                                        min={1}
                                        max={100}
                                        onValueChange={(val) => { setPixelWidth(parseFloat(val)) }}
                                    ></NumberInput>
                                </div>
                                <div className="ml-5 flex">
                                    <NumberInput
                                        title="Max Amplitude"
                                        default={maxSinAmplitude}
                                        min={1}
                                        max={100}
                                        onValueChange={(val) => { setMaxSinAmplitude(parseFloat(val)) }}
                                    ></NumberInput>
                                </div>
                                <div className="ml-5 flex">
                                    <NumberInput
                                        title="Max Frequency"
                                        default={maxSinFrequency}
                                        min={1}
                                        max={100}
                                        onValueChange={(val) => { setMaxSinFrequency(parseFloat(val)) }}
                                    ></NumberInput>
                                </div>
                                <div className="ml-5 flex">
                                    <NumberInput
                                        title="Sin Resolution"
                                        default={resolution}
                                        min={0.01}
                                        max={1}
                                        onValueChange={(val) => { setResolution(parseFloat(val)) }}
                                    ></NumberInput>
                                </div>
                            </>
                            : null}
                    </div>
                </div>
                : null

            }
        </div >
    );
}

export default MainUI;

from gevent import monkey
monkey.patch_all()

import sys
import os
import logging
import json
import argparse
from bitmap_processors.ascii_utils import image_to_ascii_svg
from bitmap_processors.sin_wave_utils import image_to_sin_wave
from drawing_job.job_manager import DrawingJobManager
from path_generator import PathGenerator, ToolpathAlgorithm, PathsortAlgorithm
from polar_sketcher_interface import PolarSketcherInterface
from pymongo.collection import Collection
from pymongo import MongoClient
from werkzeug.exceptions import BadRequest
from flask_sockets import Sockets, Rule
from flask_cors import CORS
from flask import Flask, request, jsonify
from gevent import pywsgi
from geventwebsocket.websocket import WebSocket
from geventwebsocket.handler import WebSocketHandler


app = Flask(__name__)
CORS(app)
sockets = Sockets(app)

# Request Types
GET = "GET"
POST = "POST"
DELETE = "DELETE"

PLOTTER_BASE_WIDTH_MM = int(os.getenv("PLOTTER_WIDTH_MM", 35))
PLOTTER_BASE_HEIGHT_MM = int(os.getenv("PLOTTER_HEIGHT_MM", 35))
CANVAS_WIDTH_MM = int(os.getenv("CANVAS_WIDTH_MM", 513))
CANVAS_HEIGHT_MM = int(os.getenv("CANVAS_HEIGHT_MM", 513))

job_manager: DrawingJobManager = None
svg_collection: Collection = None
polar_sketcher: PolarSketcherInterface = None

running_jobs = {}


@app.route("/upload_svg", methods=[POST])
def upload():
    try:
        params = json.loads(request.data)
    except json.JSONDecodeError:
        return BadRequest("could not understand request")

    path_generator = init_path_generator(params)
    path_generator.load_svg(params["svg"])
    job_id = job_manager.start_drawing_job(
        path_generator, params["dryrun"], params["angle_correction"])
    return job_id


@app.route('/upload_bitmap', methods=[POST])
def asciify():
    try:
        params = json.loads(request.data)
    except json.JSONDecodeError:
        return BadRequest("could not understand request")

    imageb64 = params["image"]
    processor = params["image_processor"]
    processor_to_func = {
        "ascii": image_to_ascii_svg,
        "sin": image_to_sin_wave,
    }
    processor_args = params[processor + "_processor_args"]

    if processor not in processor_to_func.keys():
        return BadRequest(f"no processor for '{processor}'")

    image_processor = processor_to_func[processor](imageb64, **processor_args)
    path_generator = init_path_generator(params)
    path_generator.set_path_generator(image_processor)
    job_id = job_manager.start_drawing_job(
        path_generator, params["dryrun"], params["angle_correction"])

    response = {
        "jobId": job_id,
        "svg": params["svg"]
    }
    return jsonify(response)


@sockets.route('/updates', websocket=True)
def get_updates(ws: WebSocket):
    try:
        event = job_manager.add_ws_client(ws)
        event.wait()
    except Exception as e:
        logging.error("failed to decode message:", e)
        ws.close()


@app.route('/abort', methods=[POST])
def draw_boundary():
    job_manager.stop()
    return "OK"


@app.route('/drawing/save', methods=[POST])
def save_drawing():
    if (not db_connected):
        return "db not connected", 400

    try:
        payload = json.loads(request.data)
    except json.JSONDecodeError:
        return BadRequest("could not understand request")

    name = payload['name']
    try:
        result = svg_collection.update_one(
            {'name': name}, {'$set': payload}, upsert=True)
        if result.upserted_id:
            return str(result.upserted_id), 200
        else:
            return 'Entry updated successfully', 200
    except Exception as e:
        return str(e), 500


@app.route('/drawing/list', methods=[GET])
def list_drawings():
    if (not db_connected):
        return "db not connected", 400

    try:
        svgs = list(svg_collection.find({}, {'_id': 0}))
        return {'svgs': svgs}, 200
    except Exception as e:
        return str(e), 500


@app.route('/svg/<name>', methods=[GET])
def get_drawing(name):
    if (not db_connected):
        return "db not connected", 400

    try:
        svg = svg_collection.find_one({'name': name}, {'_id': 0})
        if svg:
            return svg, 200
        else:
            return 'SVG not found', 404
    except Exception as e:
        return str(e), 500


def init_path_generator(params):
    path_generator = PathGenerator()
    path_generator.set_canvas_size((CANVAS_WIDTH_MM, CANVAS_HEIGHT_MM))
    path_generator.set_offset(params["position"])
    path_generator.set_render_size(params["size"])
    path_generator.set_rotation(params["rotation"])
    try:
        toolpath_algorithm = ToolpathAlgorithm(
            params["toolpath_config"]["algorithm"])
        path_generator.set_toolpath_algorithm(toolpath_algorithm)
        path_generator.set_toolpath_line_number(
            params["toolpath_config"]["line_step"])
        path_generator.set_toolpath_angle(params["toolpath_config"]["angle"])
    except Exception as e:
        logging.error("failed to configure toolpath algorithm:", e)

    try:
        pathsort_algorithm = PathsortAlgorithm(
            params["pathsort_config"]["algorithm"])
        path_generator.set_pathsort_algorithm(pathsort_algorithm)
        path_generator.set_pathsort_start_point(
            complex(params["pathsort_config"]["x"], params["pathsort_config"]["y"]))
    except Exception as e:
        logging.error("failed to configure pathsort algorithm:", e)

    return path_generator


def main():
    global polar_sketcher, job_manager, svg_collection, db_connected

    # stubborn fix for this: https://github.com/heroku-python/flask-sockets/issues/81
    sockets.url_map.add(Rule('/updates', endpoint=get_updates, websocket=True))

    parser = argparse.ArgumentParser(description='Polar Sketcher Server')
    parser.add_argument("-d", "--dry-run", type=bool,
                        default=False, help="use dry run drawer")
    parser.add_argument("-db", "--use-db", type=bool,
                        default=False, help="use mongodb")
    parser.add_argument("-s", "--canvas-size",
                        type=tuple,
                        help="use dry run drawer",
                        default=(600, 600))
    args = parser.parse_args()
    job_manager = DrawingJobManager()

    db_connected = False
    if (args.use_db):
        try:
            client = MongoClient('mongodb://localhost:27017/')
            db = client['polar_sketcher']
            svg_collection = db['drawings_in_progress']

            client.admin.command('ismaster')
            db_connected = True
        except Exception as e:
            print("failed to connect to mongo DB:", e)

    try:
        print("Starting WebServer...")
        server = pywsgi.WSGIServer(
            ('', 9943), app, handler_class=WebSocketHandler, spawn=10)
        server.serve_forever()

    except KeyboardInterrupt:
        if job_manager is not None:
            job_manager.stop()

        if server:
            server.stop()
            server.close()
        sys.exit(0)


if __name__ == '__main__':
    main()

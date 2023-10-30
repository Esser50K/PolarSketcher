from gevent import monkey
monkey.patch_all()

from ascii_utils import image_to_ascii_svg
from job_manager import DrawingJobManager
from path_generator import PathGenerator, ToolpathAlgorithm, PathsortAlgorithm, _generate_boundary_path
from polar_sketcher_interface import PolarSketcherInterface
from pymongo.collection import Collection
from pymongo import MongoClient
from werkzeug.exceptions import BadRequest
from geventwebsocket.websocket import WebSocket
from flask_sockets import Sockets, Rule
from flask_cors import CORS
from flask import Flask, request, jsonify
from threading import Event
import sys
import os
import logging
import json
import argparse


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


@app.route("/upload", methods=[POST])
def upload():
    try:
        params = json.loads(request.data)
    except json.JSONDecodeError:
        return BadRequest("could not understand request")

    path_generator = init_path_generator(params)
    job_id = job_manager.start_drawing_job(path_generator, params["dryrun"])
    return job_id


@sockets.route('/updates', websocket=True)
def get_updates(ws: WebSocket):
    try:
        job = job_manager.get_job()
        if job is None:
            ws.close()
            return

        event = Event()
        job.add_web_connection(ws, event)
        event.wait()
    except Exception as e:
        logging.error("failed to decode message:", e)
        ws.close()


@app.route('/draw_boundary', methods=[POST])
def draw_boundary():
    try:
        params = json.loads(request.data)
    except json.JSONDecodeError:
        return BadRequest("could not understand request")

    path_generator = PathGenerator()
    path_generator.set_canvas_size((CANVAS_WIDTH_MM, CANVAS_HEIGHT_MM))
    boundary = _generate_boundary_path((CANVAS_WIDTH_MM, CANVAS_HEIGHT_MM),
                                       params["canvas_size"],
                                       (PLOTTER_BASE_WIDTH_MM, PLOTTER_BASE_HEIGHT_MM))
    path_generator.add_paths([boundary])

    polar_sketcher = None
    if not params["dryrun"]:
        polar_sketcher = PolarSketcherInterface()

    job_id = job_manager.start_drawing_job(path_generator, polar_sketcher)
    return job_id


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


@app.route('/asciify', methods=[POST])
def asciify():
    try:
        params = json.loads(request.data)
    except json.JSONDecodeError:
        return BadRequest("could not understand request")

    imageb64 = params["image"]
    params["svg"] = image_to_ascii_svg(imageb64)

    path_generator = init_path_generator(params)

    polar_sketcher = None
    if not params["dryrun"]:
        polar_sketcher = PolarSketcherInterface()

    job_id = job_manager.start_drawing_job(path_generator, polar_sketcher)

    response = {
        "jobId": job_id,
        "svg": params["svg"]
    }
    return jsonify(response)


def init_path_generator(params):
    path_generator = PathGenerator()
    path_generator.set_canvas_size((CANVAS_WIDTH_MM, CANVAS_HEIGHT_MM))
    path_generator.load_svg(params["svg"])
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
    polar_sketcher = PolarSketcherInterface()
    job_manager = DrawingJobManager(polar_sketcher)

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
        from gevent import pywsgi
        from geventwebsocket.handler import WebSocketHandler

        print("Starting WebServer...")
        server = pywsgi.WSGIServer(
            ('', 9943), app, handler_class=WebSocketHandler)
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

import argparse
import json
import logging
import os
import sys
from threading import Event

from flask import Flask, request
from flask_cors import CORS
from flask_sockets import Sockets
from geventwebsocket.websocket import WebSocket
from svgelements import Length
from werkzeug.exceptions import BadRequest

from polar_sketcher_interface import PolarSketcherInterface
from path_generator import PathGenerator, ToolpathAlgorithm, PathsortAlgorithm
from job_manager import DrawingJobManager

app = Flask(__name__)
CORS(app)
sockets = Sockets(app)

# Request Types
GET = "GET"
POST = "POST"
DELETE = "DELETE"

CANVAS_WIDTH_MM = int(os.getenv("CANVAS_WIDTH_MM", 600))
CANVAS_HEIGHT_MM = int(os.getenv("CANVAS_HEIGHT_MM", 600))

job_manager: DrawingJobManager = None

running_jobs = {}


@app.route("/upload", methods=[POST])
def upload():
    try:
        params = json.loads(request.data)
    except json.JSONDecodeError:
        return BadRequest("could not understand request")

    path_generator = PathGenerator()
    path_generator.set_canvas_size((CANVAS_WIDTH_MM, CANVAS_HEIGHT_MM))
    path_generator.load_svg(params["svg"])
    path_generator.set_offset(params["position"])
    path_generator.set_render_size(params["size"])
    path_generator.set_rotation(params["rotation"])
    try:
        toolpath_algorithm = ToolpathAlgorithm(params["toolpath_config"]["algorithm"])
        path_generator.set_toolpath_algorithm(toolpath_algorithm)
        path_generator.set_toolpath_line_number(params["toolpath_config"]["n_lines"])
        path_generator.set_toolpath_angle(params["toolpath_config"]["angle"])
    except Exception as e:
        logging.error("failed to configure toolpath algorithm:", e)

    try:
        pathsort_algorithm = PathsortAlgorithm(params["pathsort_config"]["algorithm"])
        path_generator.set_pathsort_algorithm(pathsort_algorithm)
        path_generator.set_pathsort_start_point(complex(params["pathsort_config"]["x"], params["pathsort_config"]["y"]))
    except Exception as e:
        logging.error("failed to configure pathsort algorithm:", e)


    polar_sketcher = None
    if not params["dryrun"]:
        polar_sketcher = PolarSketcherInterface()

    job_id = job_manager.start_drawing_job(path_generator, polar_sketcher)
    return job_id


@sockets.route('/updates')
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


def main():
    global job_manager

    from gevent import monkey
    monkey.patch_all()

    parser = argparse.ArgumentParser(description='Polar Sketcher Server')
    parser.add_argument("-d", "--dry-run", type=bool, default=False, help="use dry run drawer")
    parser.add_argument("-s", "--canvas-size",
                        type=tuple,
                        help="use dry run drawer",
                        default=(600, 600))
    args = parser.parse_args()
    job_manager = DrawingJobManager()
    if not args.dry_run:
        # drawer = PolarSketcherDrawer
        pass

    try:
        from gevent import pywsgi
        from geventwebsocket.handler import WebSocketHandler

        print("Starting WebServer...")
        # waitress.serve(sockets, host='0.0.0.0', port=90143)  # port -> polar
        server = pywsgi.WSGIServer(('', 9943), app, handler_class=WebSocketHandler)
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

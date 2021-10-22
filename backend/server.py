import os
import sys
import json
import argparse
import logging
from werkzeug.exceptions import BadRequest
from flask import Flask, request
from flask_cors import CORS
from svgelements import Length
from svg_parser import SVGParser
from dryrun_drawer import DryrunDrawer
from flask_sockets import Sockets
from geventwebsocket.websocket import WebSocket
from threading import Event


app = Flask(__name__)
CORS(app)
sockets = Sockets(app)


# Request Types
GET = "GET"
POST = "POST"
DELETE = "DELETE"

CANVAS_WIDTH_MM = Length("%dmm" % int(os.getenv("CANVAS_WIDTH_MM", 600)))
CANVAS_HEIGHT_MM = Length("%dmm" % int(os.getenv("CANVAS_HEIGHT_MM", 600)))

parser = None
drawer = None

running_jobs = {}


@app.route("/upload", methods=[POST])
def upload():
    try:
        params = json.loads(request.data)
    except json.JSONDecodeError:
        return BadRequest("could not understand request")

    job_id = drawer.draw(params["svg"], params["position"],
                         size=params["size"],
                         rotation=params["rotation"],
                         toolpath_configs=params["toolpath_configs"])
    return job_id


@sockets.route('/updates')
def get_updates(ws: WebSocket):
    try:
        job = drawer.get_job()
        if job is None:
            ws.close()
            return

        event = Event()
        job.add_websocket(ws, event)
        event.wait()
    except Exception as e:
        logging.error("failed to decode message:", e)
        ws.close()


def length_tuple(strings):
    strings = strings.replace("(", "").replace(")", "")
    parsed_length = map(lambda x: Length("%dmm" % x), strings.split(","))
    return tuple(parsed_length)


if __name__ == '__main__':
    from gevent import monkey
    monkey.patch_all()

    parser = argparse.ArgumentParser(description='Polar Sketcher Server')
    parser.add_argument("-d", "--dry-run", type=bool, default=False, help="use dry run drawer")
    parser.add_argument("-s", "--canvas-size",
                        type=length_tuple,
                        help="use dry run drawer",
                        default=(Length("600mm"), Length("600mm")))
    args = parser.parse_args()

    parser = SVGParser(canvas_size=args.canvas_size)
    drawer = DryrunDrawer(parser)
    if not args.dry_run:
        # drawer = PolarSketcherDrawer
        pass

    server = None
    try:
        from gevent import pywsgi
        from geventwebsocket.handler import WebSocketHandler

        print("Starting WebServer...")
        # waitress.serve(sockets, host='0.0.0.0', port=9943)
        server = pywsgi.WSGIServer(('', 9943), app, handler_class=WebSocketHandler)
        server.serve_forever()

    except KeyboardInterrupt:
        # if drawer is not None:
        #     drawer.stop()

        # if server:
        #     server.stop()
        #     server.close()
        sys.exit(0)

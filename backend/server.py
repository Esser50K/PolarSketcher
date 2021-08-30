import os
import sys
import json
import waitress
import argparse
from werkzeug.exceptions import BadRequest
from flask import Flask, request
from flask_cors import CORS
from svgelements import Length
from old_experiments.svg_parser import SVGParser
from dryrun_drawer import DryrunDrawer


app = Flask(__name__)
CORS(app)

# Request Types
GET = "GET"
POST = "POST"
DELETE = "DELETE"

CANVAS_WIDTH_MM = Length("%dmm" % int(os.getenv("CANVAS_WIDTH_MM", 600)))
CANVAS_HEIGHT_MM = Length("%dmm" % int(os.getenv("CANVAS_HEIGHT_MM", 600)))

parser = None
drawer = None


@app.route("/upload", methods=[POST])
def upload():
    try:
        params = json.loads(request.data)
    except json.JSONDecodeError:
        return BadRequest("could not understand request")

    drawer.draw(params["svg"], params["position"], params["scale"])
    return "ok"


def length_tuple(strings):
    strings = strings.replace("(", "").replace(")", "")
    parsed_length = map(lambda x: Length("%dmm" % x), strings.split(","))
    return tuple(parsed_length)


if __name__ == '__main__':
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

    try:
        print("Starting WebServer...")
        waitress.serve(app, host='0.0.0.0', port=9943)
    except KeyboardInterrupt:
        if drawer is not None:
            drawer.stop()

        sys.exit(0)

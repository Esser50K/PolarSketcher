from gevent import monkey, pywsgi
monkey.patch_all()

from geventwebsocket.handler import WebSocketHandler
from geventwebsocket.websocket import WebSocket
from flask import Flask
from flask_cors import CORS
from flask_sock import Sock

app = Flask(__name__)
app.config['SOCK_SERVER_OPTIONS'] = {'ping_interval': 25}
CORS(app)
sock = Sock(app)

@sock.route('/test')
def get_updates(ws: WebSocket):
    try:
        print("HERE")
        print(ws.receive())
    except Exception as e:
        print(e)


def main():
    try:
        print("Starting WebServer...")
        server = pywsgi.WSGIServer(('127.0.0.1', 9943), app)
        server.serve_forever()

    except KeyboardInterrupt:
        pass
    except Exception as e:
        print("ERROR:", e)

if __name__ == '__main__':
    main()

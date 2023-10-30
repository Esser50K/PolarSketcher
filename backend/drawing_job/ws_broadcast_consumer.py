import uuid
import json
from copy import copy
from drawing_job.consumer_models import Consumer, ConsumerPoint
from path_generator import CLOSE_PATH_COMMAND, PATH_END_COMMAND
from typing import Tuple, Dict, List
from threading import Event
from geventwebsocket.websocket import WebSocket


class WebsocketConnection:
    def __init__(self, ws: WebSocket):
        self.ws = ws
        self.done_event = Event()

    def close(self):
        self.ws.close()
        self.done_event.set()


class WSBroadcastConsumer(Consumer):
    def __init__(self):
        self.drawn_paths: List[List[Tuple]] = []
        self.current_path: List[Tuple] = []
        self.websockets: Dict[str, WebsocketConnection] = {}

    def init(self):
        pass

    def shutdown(self):
        self._broadcast(self._msg())
        self._close_all_webconnections()

    def _msg(self) -> str:
        return json.dumps({
            "type": "update",
            "payload": self.drawn_paths
        })

    def add_ws_client(self, ws: WebSocket) -> Event:
        unique_origin = ws.origin + str(uuid.uuid4())
        ws_connection = WebsocketConnection(ws)
        self.websockets[unique_origin] = ws_connection
        self._broadcast(self._msg(), {unique_origin: ws_connection})

        return ws_connection.done_event

    def consume(self, consumer_point: ConsumerPoint):
        point = consumer_point.point
        if type(point) is tuple:
            self.current_path.append(point)
        elif point == CLOSE_PATH_COMMAND:
            pass
        elif point == PATH_END_COMMAND:
            self.drawn_paths.append(copy(self.current_path))
            self.current_path = []
            self._broadcast(self._msg())

    def _broadcast(self, msg: str, clients=None):
        if clients is None:
            clients = self.websockets

        to_delete = []
        for origin, web_conn in clients.items():
            try:
                web_conn.ws.send(msg)
            except Exception as e:
                print("failed sending point to %s:" % origin, type(e), e)
                to_delete.append(origin)

        for ws in to_delete:
            try:
                self.websockets[ws].close()
            finally:
                del self.websockets[ws]

    def _close_all_webconnections(self):
        for _, webconn in self.websockets.items():
            webconn.close()
        self.websockets = {}

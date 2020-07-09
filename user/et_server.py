import socket
import time
import sys
import json
import threading
from talon import eye, ctrl, tap
from talon_plugins.eye_mouse import tracker, menu, config
from talon.track.geom import Point2d, EyeFrame


IP = 'localhost'
PORT = 8324
BUFFER_SIZE = 1024


class EyeTrackingServer:
    def __init__(self):
        self._clients = []
        self._alive = True
        self.lock = threading.RLock()
        self.attached_tracker = None

    def start(self):
        self._alive = True
        with self.lock:
            if self.attached_tracker != tracker:
                try:
                    self.attached_tracker.unregister('gaze', self.on_gaze)
                except Exception: pass
                tracker.register('gaze', self.on_gaze)
                self.attached_tracker = tracker
        threading.Thread(target=self.accept_thread).start()

    def stop(self):
        self._alive = False
        with self.lock:
            if self.attached_tracker is not None:
                try:
                    self.attached_tracker.unregister('gaze', self.on_gaze)
                except Exception: pass
                self.attached_tracker = None

    def accept_thread(self):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.bind((IP, PORT))
            s.listen()
            s.settimeout(1)
            print('Listening', s, self._alive)
            while self._alive:
                try:
                    client_socket, addr = s.accept()
                    print(f'Connected with {addr[0]}:{addr[1]}')
                    self._clients.append(client_socket)
                except socket.timeout:
                    pass
            s.close()
        except OSError as msg:
            print(f'Could not start server thread. Error: {msg}')

    def broadcast(self, data):
        data = json.dumps(data).encode('utf-8')
        for client in self._clients:
            try:
                client.send(data)
            except socket.error:
                client.close()
                self._clients.remove(client)

    def on_gaze(self, b):
        l, r = EyeFrame(b, 'Left'), EyeFrame(b, 'Right')
        ts = time.time()

        # crossed eyes seem more accurate:
        # TODO factor in eye position relative to sensor: ideal is eye looking across the sensor
        weight = lambda x: max(0.25, min((0.25 + (max(x, 0) ** 1.8) / 2), 0.75))
        lw = weight(l.gaze.x)
        rw = 1 - weight(r.gaze.x)
        pos = (l.gaze * lw + r.gaze * rw) / (lw + rw)

        if r and not l: pos = r.gaze.copy()
        elif l and not r: pos = l.gaze.copy()
        pos *= config.size_px

        self.broadcast({
            'x': pos.x,
            'y': pos.y,
            'tstamp': ts,
        })

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, type, value, traceback):
        self.stop()


config.eye_tracking_server = False
server = EyeTrackingServer()


def on_attach(dev):
    sync_tracker()


def on_detach(dev):
    sync_tracker()


def toggle_eye_tracking_server(state):
    config.eye_tracking_server = state
    sync_tracker()


def sync_tracker():
    if tracker and config.eye_tracking_server:
        server.start()
    else:
        server.stop()


eye.register('attach', on_attach)
eye.register('detach', on_detach)

for dev in eye.devices():
    on_attach(dev)

et_server_menu = menu.toggle('Eye Tracking Server', weight=2, cb=toggle_eye_tracking_server)

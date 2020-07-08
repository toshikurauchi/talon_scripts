import threading
import time

from talon import eye, ctrl, tap
from talon_plugins.eye_mouse import tracker, menu, config
from talon.track.geom import Point2d, EyeFrame

MOUSE_MEMORY = 0.2  # seconds
MOUSE_MOV_THRESH = 20  # pixels
MOUSE_GAZE_THRESH = 250  # pixels
ANGLE_THRESH = 90  # degrees

config.magic_pointing = False


class MouseHistory:
    def __init__(self):
        self._reset_history()

    def on_move(self, typ, e):
        self.history.append((e.x, e.y, time.time()))
        self._refresh_history()
        return False

    def direction(self):
        self._refresh_history()
        p0 = self.history[0]
        p1 = self.history[-1]
        return Point2d(p1[0] - p0[0], p1[1] - p0[1])

    def latest(self):
        return Point2d(*self.history[-1][:2])

    def _refresh_history(self):
        now = time.time()
        last = self.history[-1]
        self.history = [d for d in self.history if now - d[2] < MOUSE_MEMORY]
        if not self.history:
            self.history.append(last)

    def _reset_history(self):
        x, y = ctrl.mouse_pos()
        self.history = [(x, y, time.time())]

mouse_history = MouseHistory()
tap.register(tap.MMOVE, mouse_history.on_move)


def on_attach(dev):
    sync_tracker()


def on_detach(dev):
    sync_tracker()


def toggle_magic(state):
    config.magic_pointing = state
    sync_tracker()


def sync_tracker():
    if tracker and config.magic_pointing:
        magic.enable()
    else:
        magic.disable()


class MagicPointing:
    def __init__(self):
        self.lock = threading.RLock()
        self.attached_tracker = None

    def enable(self):
        with self.lock:
            if self.attached_tracker != tracker:
                try:
                    self.attached_tracker.unregister('gaze', self.on_gaze)
                except Exception: pass
                tracker.register('gaze', self.on_gaze)
                self.attached_tracker = tracker

    def disable(self):
        with self.lock:
            if self.attached_tracker is not None:
                try:
                    self.attached_tracker.unregister('gaze', self.on_gaze)
                except Exception: pass
                self.attached_tracker = None

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

        mouse_direction = mouse_history.direction()

        if config.magic_pointing and mouse_direction.len() > MOUSE_MOV_THRESH:
            delta = pos - mouse_history.latest()
            angle_delta = delta.angle() - mouse_direction.angle()
            angle_delta = (angle_delta + 180) % 360 - 180  # [-180, 180]
            if delta.len() > MOUSE_GAZE_THRESH and abs(angle_delta) < ANGLE_THRESH:
                ctrl.mouse_move(pos.x, pos.y)


magic = MagicPointing()

eye.register('attach', on_attach)
eye.register('detach', on_detach)

for dev in eye.devices():
    on_attach(dev)

control_mouse = menu.toggle('MAGIC Pointing', weight=2, cb=toggle_magic)

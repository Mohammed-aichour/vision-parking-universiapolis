"""Geometry and temporal rules, independent of OpenCV and YOLO."""

from dataclasses import dataclass, field
from collections import deque
from math import hypot


def inside_polygon(point: tuple[float, float], polygon: list[list[float]]) -> bool:
    """Ray casting; points on an edge are treated as inside."""
    x, y = point
    if len(polygon) < 3:
        return False
    found = False
    for i, a in enumerate(polygon):
        b = polygon[(i + 1) % len(polygon)]
        ax, ay = a
        bx, by = b
        cross = (x - ax) * (by - ay) - (y - ay) * (bx - ax)
        if abs(cross) < 1e-6 and min(ax, bx) <= x <= max(ax, bx) and min(ay, by) <= y <= max(ay, by):
            return True
        if (ay > y) != (by > y):
            intercept = ax + (y - ay) * (bx - ax) / (by - ay)
            if x < intercept:
                found = not found
    return found


def line_side(point: tuple[float, float], start: list[float], end: list[float]) -> int:
    """Return -1, 0, or +1 relative to a directed line."""
    value = (end[0] - start[0]) * (point[1] - start[1]) - (end[1] - start[1]) * (point[0] - start[0])
    return (value > 0) - (value < 0)


@dataclass
class PlaceState:
    current: str = "inconnue"
    candidate: str | None = None
    candidate_since: float = 0.0

    def update(self, observed: str, time_seconds: float, stable_seconds: float,
               free_stable_seconds: float | None = None,
               observed_since: float | None = None) -> str:
        if observed not in {"libre", "occupée", "inconnue"}:
            raise ValueError(f"État invalide : {observed}")
        if observed == "inconnue":
            self.current = "inconnue"
            self.candidate = None
            return self.current
        if observed != self.candidate:
            self.candidate = observed
            self.candidate_since = observed_since if observed_since is not None else time_seconds
        required = (free_stable_seconds if observed == "libre" and self.current == "occupée"
                    and free_stable_seconds is not None
                    else stable_seconds)
        if time_seconds - self.candidate_since >= required:
            self.current = observed
        return self.current


@dataclass
class PlaceMotion:
    """Report when a detected vehicle first became stationary inside one place."""

    window_seconds: float = 2.0
    points: deque[tuple[float, tuple[float, float]]] = field(default_factory=deque)

    def update(self, anchor: tuple[float, float] | None, time_seconds: float,
               tolerance_pixels: float = 8.0) -> float | None:
        if anchor is None:
            self.points.clear()
            return None
        self.points.append((time_seconds, anchor))
        while self.points and time_seconds - self.points[0][0] > self.window_seconds:
            self.points.popleft()
        if not self.points or time_seconds - self.points[0][0] < self.window_seconds - 0.25:
            return None
        xs = [point[0] for _, point in self.points]
        ys = [point[1] for _, point in self.points]
        if max(xs) - min(xs) > tolerance_pixels or max(ys) - min(ys) > tolerance_pixels:
            return None
        return self.points[0][0]


@dataclass
class PassageCounter:
    start: list[float]
    end: list[float]
    enter_side: int
    cooldown_seconds: float = 2.0
    minimum_distance_pixels: float = 8.0
    entries: int = 0
    exits: int = 0
    last_side: dict[int, int] = field(default_factory=dict)
    last_counted: dict[int, float] = field(default_factory=dict)

    def update(self, track_id: int, point: tuple[float, float], time_seconds: float) -> str | None:
        length = hypot(self.end[0] - self.start[0], self.end[1] - self.start[1])
        if length == 0:
            return None
        distance = ((self.end[0] - self.start[0]) * (point[1] - self.start[1])
                    - (self.end[1] - self.start[1]) * (point[0] - self.start[0])) / length
        if abs(distance) < self.minimum_distance_pixels:
            return None
        side = line_side(point, self.start, self.end)
        if side == 0:
            return None
        previous = self.last_side.get(track_id)
        self.last_side[track_id] = side
        if previous is None or previous == side:
            return None
        if time_seconds - self.last_counted.get(track_id, float("-inf")) < self.cooldown_seconds:
            return None
        self.last_counted[track_id] = time_seconds
        if side == self.enter_side:
            self.entries += 1
            return "entrée"
        self.exits += 1
        return "sortie"

"""Render the configured virtual parking spaces over an IP7 reference frame."""

import json
from pathlib import Path


def run(frame_path: Path, zones_path: Path, output_path: Path) -> None:
    import cv2
    import numpy as np

    frame = cv2.imread(str(frame_path))
    if frame is None:
        raise RuntimeError(f"Image illisible : {frame_path}")
    config = json.loads(zones_path.read_text(encoding="utf-8"))
    height, width = frame.shape[:2]
    sx = width / config["reference_width"]
    sy = height / config["reference_height"]
    overlay = frame.copy()
    for place in config["places"]:
        if place.get("display_polygon", place["polygon"]) is None:
            continue
        polygon = np.asarray([[round(x * sx), round(y * sy)] for x, y in place.get("display_polygon", place["polygon"])], dtype=np.int32)
        color = (190, 137, 30) if place["observable"] else (0, 188, 235)
        cv2.fillPoly(overlay, [polygon], color)
    frame = cv2.addWeighted(overlay, 0.13, frame, 0.87, 0)
    for place in config["places"]:
        if place.get("display_polygon", place["polygon"]) is None:
            continue
        polygon = np.asarray([[round(x * sx), round(y * sy)] for x, y in place.get("display_polygon", place["polygon"])], dtype=np.int32)
        color = (190, 137, 30) if place["observable"] else (0, 188, 235)
        cv2.polylines(frame, [polygon], True, color, 3)
        center = polygon.mean(axis=0).astype(int)
        x, y = int(center[0]), int(center[1])
        cv2.rectangle(frame, (x - 31, y - 17), (x + 31, y + 8), (16, 30, 44), -1)
        cv2.putText(frame, place["id"], (x - 23, y + 1), cv2.FONT_HERSHEY_SIMPLEX, 0.58,
                    (255, 255, 255), 2, cv2.LINE_AA)
    cv2.rectangle(frame, (0, 0), (width, 64), (16, 30, 44), -1)
    cv2.putText(frame, "PLAN : 18 PLACES | A06 = 6E VOITURE", (24, 44),
                cv2.FONT_HERSHEY_SIMPLEX, 1.1, (255, 255, 255), 2, cv2.LINE_AA)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if not cv2.imwrite(str(output_path), frame):
        raise RuntimeError(f"Impossible de créer : {output_path}")

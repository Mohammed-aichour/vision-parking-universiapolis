"""Run YOLO on a recorded video and publish a browser-ready demonstration."""

import json
import os
import shutil
import subprocess
from datetime import datetime
from pathlib import Path

from .core import PassageCounter, PlaceMotion, PlaceState


def load_zones(path: Path, width: int, height: int) -> dict:
    config = json.loads(path.read_text(encoding="utf-8"))
    original_w = int(config["reference_width"])
    original_h = int(config["reference_height"])
    if original_w <= 0 or original_h <= 0:
        raise ValueError("Dimensions de référence invalides")
    if not config.get("places"):
        raise ValueError("Aucune place définie. Lance d'abord la commande annotate.")
    factor_x, factor_y = width / original_w, height / original_h

    def scale(point):
        return [round(point[0] * factor_x), round(point[1] * factor_y)]

    seen = set()
    places = []
    for place in config["places"]:
        name = str(place["id"]).strip()
        polygon = place.get("polygon")
        observable = bool(place.get("observable", True))
        if not name or name in seen or (polygon is None and observable) or (polygon is not None and len(polygon) < 3):
            raise ValueError(f"Place invalide ou doublon : {name}")
        seen.add(name)
        # A display contour may differ from its detection area when needed.
        display_polygon = place.get("display_polygon", polygon)
        if display_polygon is not None and len(display_polygon) < 3:
            raise ValueError(f"Contour affiché invalide : {name}")
        places.append({"id": name, "polygon": [scale(p) for p in polygon] if polygon is not None else None,
                       "display_polygon": [scale(p) for p in display_polygon] if display_polygon is not None else None,
                       "observable": observable})
    passage = config.get("passage")
    if passage:
        passage = {"start": scale(passage["start"]), "end": scale(passage["end"]), "enter_side": passage["enter_side"]}
        if passage["start"] == passage["end"] or passage["enter_side"] not in {"positive", "negative"}:
            raise ValueError("Ligne de passage invalide")
    movement_roi = config.get("movement_roi")
    if movement_roi is not None:
        if len(movement_roi) < 3:
            raise ValueError("Zone de circulation invalide")
        movement_roi = [scale(p) for p in movement_roi]
    return {"places": places, "passage": passage, "movement_roi": movement_roi}


def run(video_path: Path, zones_path: Path, output_dir: Path, model_name: str,
        stride: int = 2, confidence: float = 0.25, stable_seconds: float = 1.5,
        free_stable_seconds: float | None = None,
        recording_start_clock: str | None = None) -> Path:
    import cv2
    import numpy as np
    from ultralytics import YOLO

    if stride < 1 or not (0 < confidence < 1) or stable_seconds < 0 or (free_stable_seconds is not None and free_stable_seconds < 0):
        raise ValueError("Paramètres stride, confidence ou délai de stabilisation invalides")
    if recording_start_clock is not None:
        datetime.strptime(recording_start_clock, "%H:%M:%S")
    source = cv2.VideoCapture(str(video_path))
    if not source.isOpened():
        raise RuntimeError(f"Impossible d'ouvrir la vidéo : {video_path}")
    fps = source.get(cv2.CAP_PROP_FPS)
    width = int(source.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(source.get(cv2.CAP_PROP_FRAME_HEIGHT))
    if fps <= 0 or width <= 0 or height <= 0:
        source.release()
        raise RuntimeError("Fréquence ou dimensions vidéo invalides")
    zones = load_zones(zones_path, width, height)
    polygons = {p["id"]: np.asarray(p["polygon"], dtype=np.int32)
                for p in zones["places"] if p["polygon"] is not None}
    movement_roi = (np.asarray(zones["movement_roi"], dtype=np.int32)
                    if zones["movement_roi"] is not None else None)
    output_dir.mkdir(parents=True, exist_ok=True)
    video_output = output_dir / "video_annotee.mp4"
    temp_video = output_dir / "video_temporaire.mp4"
    writer = cv2.VideoWriter(str(temp_video), cv2.VideoWriter_fourcc(*"mp4v"), fps / stride, (width, height))
    if not writer.isOpened():
        source.release()
        raise RuntimeError("Impossible de créer la vidéo annotée")

    model = YOLO(model_name)
    states = {place["id"]: PlaceState() for place in zones["places"]}
    motion = {place["id"]: PlaceMotion() for place in zones["places"]}
    counter = None
    if zones["passage"]:
        line = zones["passage"]
        counter = PassageCounter(line["start"], line["end"], 1 if line["enter_side"] == "positive" else -1)
    samples = []
    events = []
    frame_index = -1
    processed = 0
    last_sample_second = -1
    try:
        while True:
            ok, frame = source.read()
            if not ok:
                break
            frame_index += 1
            if frame_index % stride:
                continue
            time_seconds = frame_index / fps
            # COCO vehicle classes: bicycle is excluded; car, motorcycle, bus, truck.
            result = model.track(frame, persist=True, tracker="bytetrack.yaml", conf=confidence,
                                 classes=[2, 3, 5, 7], verbose=False)[0]
            detections = []
            for box in result.boxes:
                x1, y1, x2, y2 = (float(v) for v in box.xyxy[0].tolist())
                track_id = int(box.id[0]) if box.id is not None else None
                detections.append({"box": (x1, y1, x2, y2), "anchor": ((x1 + x2) / 2, y2),
                                   "id": track_id, "confidence": float(box.conf[0])})
            # Une détection au bord d'une place (par exemple les bennes à droite)
            # ne suffit pas à déclarer celle-ci occupée.
            for detection in detections:
                detection["places"] = [place["id"] for place in zones["places"]
                                       if place["observable"] and cv2.pointPolygonTest(polygons[place["id"]],
                                                               detection["anchor"], True) > 1.0]
            visible_detections = [d for d in detections if d["places"]]
            # The blue outline represents a vehicle still in the useful aisle.
            # Vehicles already inside a parking polygon, hidden under this
            # camera, or far beyond the monitored rows are not outlined.
            moving_detections = []
            for detection in detections:
                if movement_roi is None or cv2.pointPolygonTest(movement_roi, detection["anchor"], False) < 0:
                    continue
                x1, y1, x2, y2 = detection["box"]
                box_area = max(1.0, (x2 - x1) * (y2 - y1))
                box_poly = np.asarray([[x1, y1], [x2, y1], [x2, y2], [x1, y2]], dtype=np.float32)
                parked = any(
                    cv2.pointPolygonTest(poly, detection["anchor"], False) >= 0
                    or cv2.intersectConvexConvex(poly.astype(np.float32), box_poly)[0] / box_area >= 0.25
                    for poly in polygons.values()
                )
                if not parked:
                    moving_detections.append(detection)
            current = {}
            for place in zones["places"]:
                name = place["id"]
                matches = [d for d in visible_detections if name in d["places"]]
                best = max(matches, key=lambda d: d["confidence"]) if matches else None
                stationary_since = motion[name].update(
                    best["anchor"] if best else None, time_seconds,
                    tolerance_pixels=max(4.0, width / 160.0))
                # A new car must settle in its space before the eight-second
                # occupancy confirmation begins. Already occupied spaces keep
                # their state while a vehicle is detected there.
                occupied_observation = bool(matches) and (
                    processed == 0 or states[name].current == "occupée" or stationary_since is not None)
                observed = ("inconnue" if not place["observable"] else
                            "occupée" if occupied_observation else "libre")
                # The first decoded frame establishes the initial snapshot.
                # Stability delays apply to later changes, not the initial view.
                if processed == 0 and observed != "inconnue":
                    states[name].current = observed
                    states[name].candidate = observed
                    states[name].candidate_since = time_seconds
                before = states[name].current
                current[name] = states[name].update(
                    observed, time_seconds, stable_seconds, free_stable_seconds,
                    stationary_since if observed == "occupée" and before != "occupée" else None)
                if current[name] != before and before != "inconnue":
                    event = {"time": round(time_seconds, 2), "kind": "place", "place": name, "state": current[name]}
                    if current[name] == "occupée":
                        event["parked_at_seconds"] = round(states[name].candidate_since, 2)
                    events.append(event)

            if counter:
                for detection in detections:
                    if detection["id"] is not None:
                        event = counter.update(detection["id"], detection["anchor"], time_seconds)
                        if event:
                            events.append({"time": round(time_seconds, 2), "kind": "passage", "direction": event,
                                           "track_id": detection["id"]})

            zone_colors = {"libre": (65, 185, 85), "occupée": (60, 75, 225), "inconnue": (0, 190, 235)}
            for d in moving_detections:
                x1, y1, x2, y2 = (round(v) for v in d["box"])
                cv2.rectangle(frame, (x1, y1), (x2, y2), (255, 145, 35), 2)
            for place in zones["places"]:
                if place["display_polygon"] is None:
                    continue
                polygon = np.asarray(place["display_polygon"], dtype=np.int32)
                color = zone_colors[current[place["id"]]]
                cv2.polylines(frame, [polygon], True, color, 2)
                x, y = (int(v) for v in polygon[0])
                cv2.rectangle(frame, (x - 1, y - 17), (x + 37, y + 2), (20, 35, 55), -1)
                cv2.putText(frame, place["id"], (x + 2, y - 3),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.42, (255, 255, 255), 1)
            if zones["passage"]:
                line = zones["passage"]
                cv2.line(frame, tuple(line["start"]), tuple(line["end"]), (255, 180, 0), 3)
            counts = {kind: sum(state == kind for state in current.values()) for kind in ("libre", "occupée", "inconnue")}
            cv2.rectangle(frame, (0, 0), (width, 43), (20, 35, 55), -1)
            cv2.putText(frame, f"LIBRES {counts['libre']}  OCCUPEES {counts['occupée']}  INCONNUES {counts['inconnue']}",
                        (13, 29), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            writer.write(frame)
            processed += 1
            whole_second = int(time_seconds)
            if whole_second > last_sample_second:
                last_sample_second = whole_second
                samples.append({"time": round(time_seconds, 2), "states": current.copy(), "counts": counts,
                                "entries": counter.entries if counter else None,
                                "exits": counter.exits if counter else None,
                                "detections": len(moving_detections)})
            if processed % 100 == 0:
                print(f"{processed} images traitées ; vidéo à {time_seconds:.1f} s", flush=True)
    finally:
        source.release()
        writer.release()
    if not processed:
        raise RuntimeError("Aucune image vidéo traitée")
    browser_video = False
    try:
        import imageio_ffmpeg

        command = [imageio_ffmpeg.get_ffmpeg_exe(), "-y", "-loglevel", "error", "-i", str(temp_video),
                   "-c:v", "libx264", "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(video_output)]
        subprocess.run(command, check=True, capture_output=True, text=True)
        temp_video.unlink()
        browser_video = True
    except (ImportError, OSError, subprocess.CalledProcessError) as exc:
        os.replace(temp_video, video_output)
        print(f"Conversion H.264 indisponible ; le MP4 reste lisible dans VLC : {exc}")
    result_data = {"source_name": video_path.name, "recording_start_clock": recording_start_clock,
                   "duration_seconds": round((frame_index + 1) / fps, 2),
                   "processed_frames": processed, "fps_source": fps, "stride": stride,
                   "confidence": confidence, "stable_seconds": stable_seconds,
                   "free_stable_seconds": free_stable_seconds if free_stable_seconds is not None else stable_seconds,
                   "places": [p["id"] for p in zones["places"]], "passage_configured": counter is not None,
                   "browser_video": browser_video,
                   "samples": samples, "events": events,
                   "note": "Démonstration sur vidéo enregistrée : les résultats doivent être vérifiés manuellement."}
    (output_dir / "resultats.json").write_text(json.dumps(result_data, ensure_ascii=False, indent=2), encoding="utf-8")
    shutil.copyfile(Path(__file__).resolve().parents[2] / "04_INTERFACE_WEB" / "index.html", output_dir / "index.html")
    return output_dir

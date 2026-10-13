"""Draw parking places and, optionally, an entrance/exit line on a video frame."""

import json
from pathlib import Path


def run(video_path: Path, output_path: Path, at_seconds: float = 0.0) -> None:
    import cv2

    capture = cv2.VideoCapture(str(video_path))
    if not capture.isOpened():
        raise RuntimeError(f"Impossible d'ouvrir la vidéo : {video_path}")
    capture.set(cv2.CAP_PROP_POS_MSEC, at_seconds * 1000)
    ok, frame = capture.read()
    capture.release()
    if not ok:
        raise RuntimeError("Impossible de lire l'image de référence")

    height, width = frame.shape[:2]
    config = {"reference_width": width, "reference_height": height, "places": [], "passage": None}
    points: list[list[int]] = []
    mode = "places"
    window = "Polygones - voir les touches sur l'image"

    def clicked(event, x, y, _flags, _userdata):
        if event == cv2.EVENT_LBUTTONDOWN:
            points.append([x, y])
        elif event == cv2.EVENT_RBUTTONDOWN and points:
            points.pop()

    cv2.namedWindow(window, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(window, min(width, 1280), min(height, 760))
    cv2.setMouseCallback(window, clicked)
    try:
        while True:
            display = frame.copy()
            for place in config["places"]:
                polygon = place["polygon"]
                cv2.polylines(display, [__import__("numpy").array(polygon, dtype="int32")], True, (0, 180, 0), 2)
                cv2.putText(display, place["id"], tuple(polygon[0]), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            if config["passage"]:
                line = config["passage"]
                cv2.line(display, tuple(line["start"]), tuple(line["end"]), (0, 200, 255), 3)
            for point in points:
                cv2.circle(display, tuple(point), 5, (255, 200, 0), -1)
            if len(points) >= 2:
                for a, b in zip(points, points[1:]):
                    cv2.line(display, tuple(a), tuple(b), (255, 200, 0), 2)
            label = "PLACE: clics, N=nommer, L=ligne, U=annuler, S=sauver, Q=quitter" if mode == "places" else "LIGNE: 2 points + 1 clic cote entree, P=places, U=annuler, S=sauver"
            cv2.rectangle(display, (0, 0), (min(width, 1100), 36), (20, 30, 45), -1)
            cv2.putText(display, label, (12, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.52, (255, 255, 255), 1)
            cv2.imshow(window, display)
            key = cv2.waitKey(50) & 0xFF
            if key == ord("u") and points:
                points.pop()
            elif key == ord("l"):
                points.clear()
                mode = "ligne"
            elif key == ord("p"):
                points.clear()
                mode = "places"
            elif key == ord("n") and mode == "places" and len(points) >= 3:
                name = input("Nom de cette place (exemple A01) : ").strip().upper()
                if name and name not in {p["id"] for p in config["places"]}:
                    config["places"].append({"id": name, "polygon": points.copy(), "observable": True})
                    points.clear()
                else:
                    print("Nom vide ou déjà utilisé ; recommence.")
            elif mode == "ligne" and len(points) == 3:
                from .core import line_side

                side = line_side(tuple(points[2]), points[0], points[1])
                if side:
                    config["passage"] = {"start": points[0], "end": points[1], "enter_side": "positive" if side > 0 else "negative"}
                    print("Ligne de passage enregistrée. Le troisième clic indique le côté d'entrée.")
                    points.clear()
                    mode = "places"
                else:
                    points.pop()
                    print("Le côté d'entrée doit être en dehors de la ligne.")
            elif key == ord("s"):
                output_path.parent.mkdir(parents=True, exist_ok=True)
                output_path.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")
                print(f"Configuration enregistrée : {output_path}")
            elif key == ord("q"):
                break
    finally:
        cv2.destroyAllWindows()

"""Desktop workbench for inspecting IP7 detections and editing virtual spaces."""

from __future__ import annotations

import json
import copy
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

import cv2
from PIL import Image, ImageTk


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_VIDEO = ROOT / "01_VIDEO_SOURCE" / "video_ip7_10_minutes.mp4"
DEFAULT_ZONES = ROOT / "02_POLYGONES" / "places_18.json"
MANUAL_ZONES = ROOT / "02_POLYGONES" / "places_18_essai_manuel.json"
MODEL = ROOT / "07_MODELE_YOLO" / "yolo26n.pt"
VEHICLE_CLASSES = [2, 3, 5, 7]


class ManualLab:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        root.title("Atelier visuel | Parking Universiapolis - IP7 | édition")
        root.geometry("1500x920")
        root.minsize(1100, 720)
        self.video_path = DEFAULT_VIDEO
        self.zone_path = MANUAL_ZONES if MANUAL_ZONES.exists() else DEFAULT_ZONES
        self.config = json.loads(self.zone_path.read_text(encoding="utf-8"))
        self.capture = None
        self.frame = None
        self.photo = None
        self.model = None
        self.detections = []
        self.drag_index = None
        self.drawing = False
        self.draft = []
        self.undo_stack = []
        self.scale = 1.0
        self.offset_x = 0
        self.offset_y = 0
        self.view_x = 0
        self.view_y = 0
        self.zoom_var = tk.StringVar(value="1×")
        self.line_var = tk.IntVar(value=3)
        self.observable_var = tk.BooleanVar(value=True)
        self.frame_w = 1
        self.frame_h = 1
        self.time_var = tk.DoubleVar(value=0)
        self.place_var = tk.StringVar(value="A04")
        self.polygon_var = tk.StringVar(value="display_polygon")
        self.show_all_var = tk.BooleanVar(value=True)
        self.show_yolo_var = tk.BooleanVar(value=False)
        self.conf_var = tk.DoubleVar(value=0.25)
        self.status_var = tk.StringVar(value="Chargez une image, puis lancez YOLO ou sélectionnez une place.")
        self._build_ui()
        self._open_video(self.video_path)
        root.after(100, self.load_frame)

    def _build_ui(self) -> None:
        self.root.configure(bg="#eaf0f5")
        style = ttk.Style(self.root)
        style.theme_use("clam")
        style.configure("TFrame", background="#eaf0f5")
        style.configure("TLabel", background="#eaf0f5", foreground="#153047", font=("Segoe UI", 10))
        style.configure("Title.TLabel", font=("Segoe UI Semibold", 21), foreground="#102d43")
        style.configure("Sub.TLabel", font=("Segoe UI", 10), foreground="#4c6575")
        style.configure("TButton", padding=(10, 7), font=("Segoe UI", 10))
        style.configure("Accent.TButton", foreground="white", background="#136994")
        style.map("Accent.TButton", background=[("active", "#0b547c")])

        outer = ttk.Frame(self.root, padding=16)
        outer.pack(fill="both", expand=True)
        ttk.Label(outer, text="ATELIER DE DÉTECTION ET DE CALIBRAGE", style="Title.TLabel").pack(anchor="w")
        ttk.Label(outer, text="Caméra IP7  •  OpenCV + YOLO  •  18 places virtuelles  •  essais enregistrés séparément", style="Sub.TLabel").pack(anchor="w", pady=(2, 12))

        main = ttk.Frame(outer)
        main.pack(fill="both", expand=True)
        main.columnconfigure(0, weight=1)
        main.columnconfigure(1, weight=0)
        main.rowconfigure(0, weight=1)

        image_panel = ttk.Frame(main)
        image_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 14))
        self.canvas = tk.Canvas(image_panel, bg="#10222e", highlightthickness=0, cursor="crosshair")
        self.canvas.pack(fill="both", expand=True)
        self.canvas.bind("<Configure>", lambda _event: self.draw())
        self.canvas.bind("<Button-1>", self.on_down)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_up)
        self.canvas.bind("<Double-Button-1>", self.on_double)
        self.canvas.bind("<Button-3>", self.on_right)

        sidebar = ttk.Frame(main, width=340)
        sidebar.grid(row=0, column=1, sticky="ns")
        sidebar.grid_propagate(False)
        ttk.Label(sidebar, text="1  VIDÉO", font=("Segoe UI Semibold", 13)).pack(anchor="w", pady=(0, 7))
        ttk.Button(sidebar, text="Choisir une vidéo...", command=self.choose_video).pack(fill="x", pady=3)
        self.video_label = ttk.Label(sidebar, text=DEFAULT_VIDEO.name, wraplength=320)
        self.video_label.pack(anchor="w", pady=(2, 6))
        self.time_label = ttk.Label(sidebar, text="00:00 / 10:00")
        self.time_label.pack(anchor="w")
        self.slider = ttk.Scale(sidebar, from_=0, to=600, variable=self.time_var)
        self.slider.pack(fill="x", pady=(2, 3))
        self.slider.bind("<ButtonRelease-1>", lambda _event: self.load_frame())
        row = ttk.Frame(sidebar)
        row.pack(fill="x", pady=(0, 12))
        ttk.Button(row, text="− 10 s", command=lambda: self.step(-10)).pack(side="left", expand=True, fill="x", padx=(0, 3))
        ttk.Button(row, text="Afficher l'image", command=self.load_frame).pack(side="left", expand=True, fill="x", padx=3)
        ttk.Button(row, text="+ 10 s", command=lambda: self.step(10)).pack(side="left", expand=True, fill="x", padx=(3, 0))

        ttk.Separator(sidebar).pack(fill="x", pady=8)
        ttk.Label(sidebar, text="2  TESTER YOLO", font=("Segoe UI Semibold", 13)).pack(anchor="w", pady=(5, 7))
        ttk.Label(sidebar, text="Seuil de confiance (0,10 à 0,90)").pack(anchor="w")
        ttk.Spinbox(sidebar, from_=0.1, to=0.9, increment=0.05, textvariable=self.conf_var, width=8).pack(anchor="w", pady=(2, 5))
        ttk.Button(sidebar, text="Détecter les véhicules sur cette image", style="Accent.TButton", command=self.detect).pack(fill="x", pady=3)
        ttk.Checkbutton(sidebar, text="Afficher les rectangles bleus", variable=self.show_yolo_var, command=self.draw).pack(anchor="w", pady=3)
        self.count_label = ttk.Label(sidebar, text="YOLO : aucun test lancé", wraplength=320)
        self.count_label.pack(anchor="w", pady=(0, 8))

        ttk.Separator(sidebar).pack(fill="x", pady=8)
        ttk.Label(sidebar, text="3  POLYGONES DES PLACES", font=("Segoe UI Semibold", 13)).pack(anchor="w", pady=(5, 7))
        ttk.Label(sidebar, text="Place à modifier").pack(anchor="w")
        place_names = [p["id"] for p in self.config["places"]]
        self.place_combo = ttk.Combobox(sidebar, textvariable=self.place_var, values=place_names, state="readonly")
        self.place_combo.pack(fill="x", pady=(2, 5))
        self.place_combo.bind("<<ComboboxSelected>>", lambda _event: self.on_place_selected())
        ttk.Radiobutton(sidebar, text="Contour visible sur la vidéo", variable=self.polygon_var, value="display_polygon", command=self.draw).pack(anchor="w")
        ttk.Radiobutton(sidebar, text="Zone utilisée pour l'occupation", variable=self.polygon_var, value="polygon", command=self.draw).pack(anchor="w")
        ttk.Checkbutton(sidebar, text="Afficher les 18 places", variable=self.show_all_var, command=self.draw).pack(anchor="w", pady=(3, 7))
        options = ttk.Frame(sidebar)
        options.pack(fill="x", pady=(0, 7))
        ttk.Label(options, text="Zoom").pack(side="left")
        zoom = ttk.Combobox(options, textvariable=self.zoom_var, values=["1×", "1,5×", "2×", "3×"], state="readonly", width=5)
        zoom.pack(side="left", padx=(7, 13))
        zoom.bind("<<ComboboxSelected>>", lambda _event: self.draw())
        ttk.Label(options, text="Épaisseur").pack(side="left")
        ttk.Spinbox(options, from_=1, to=8, textvariable=self.line_var, width=4, command=self.draw).pack(side="left", padx=(7, 0))
        ttk.Checkbutton(sidebar, text="Place visible / observable", variable=self.observable_var, command=self.toggle_observable).pack(anchor="w", pady=(0, 5))
        ttk.Label(sidebar, text="Glisser un point pour le déplacer. Double clic sur un bord pour ajouter un point. Clic droit sur un point pour le retirer.", wraplength=320).pack(anchor="w", pady=(0, 6))
        row2 = ttk.Frame(sidebar)
        row2.pack(fill="x")
        ttk.Button(row2, text="Redessiner", command=self.begin_redraw).pack(side="left", expand=True, fill="x", padx=(0, 4))
        ttk.Button(row2, text="Terminer le contour", command=self.finish_redraw).pack(side="left", expand=True, fill="x")
        row3 = ttk.Frame(sidebar)
        row3.pack(fill="x", pady=(5, 0))
        ttk.Button(row3, text="Annuler la modification", command=self.undo).pack(side="left", expand=True, fill="x", padx=(0, 4))
        ttk.Button(row3, text="Rétablir cette place", command=self.reset_place).pack(side="left", expand=True, fill="x")
        ttk.Button(sidebar, text="Enregistrer l'essai des polygones", style="Accent.TButton", command=self.save).pack(fill="x", pady=(9, 3))
        ttk.Button(sidebar, text="Ouvrir un fichier de polygones...", command=self.choose_zones).pack(fill="x", pady=3)
        self.zone_label = ttk.Label(sidebar, text=self.zone_path.name, wraplength=320)
        self.zone_label.pack(anchor="w", pady=(2, 3))

        status = ttk.Label(outer, textvariable=self.status_var, style="Sub.TLabel", wraplength=1350)
        status.pack(fill="x", pady=(9, 0))

    def _open_video(self, path: Path) -> None:
        cap = cv2.VideoCapture(str(path))
        if not cap.isOpened():
            messagebox.showerror("Vidéo introuvable", f"Impossible d'ouvrir :\n{path}")
            return
        if self.capture is not None:
            self.capture.release()
        self.capture = cap
        self.video_path = path
        self.video_label.configure(text=path.name)
        fps = cap.get(cv2.CAP_PROP_FPS) or 1
        count = cap.get(cv2.CAP_PROP_FRAME_COUNT)
        self.duration = max(0, count / fps)
        self.slider.configure(to=self.duration)
        self.time_var.set(0)

    def choose_video(self) -> None:
        path = filedialog.askopenfilename(title="Choisir une vidéo", filetypes=[("Vidéos", "*.mp4 *.avi *.mkv *.mov"), ("Tous", "*.*")])
        if path:
            self._open_video(Path(path))
            self.load_frame()

    def choose_zones(self) -> None:
        path = filedialog.askopenfilename(title="Choisir les polygones", filetypes=[("JSON", "*.json")])
        if not path:
            return
        try:
            data = json.loads(Path(path).read_text(encoding="utf-8"))
            if not data.get("places") or not data.get("reference_width") or not data.get("reference_height"):
                raise ValueError("Ce fichier ne contient pas une configuration de places valide.")
        except (OSError, ValueError) as exc:
            messagebox.showerror("Configuration invalide", str(exc))
            return
        self.config = data
        self.zone_path = Path(path)
        self.zone_label.configure(text=self.zone_path.name)
        names = [p["id"] for p in data["places"]]
        self.place_combo.configure(values=names)
        self.place_var.set(names[0])
        self.on_place_selected()
        self.draw()

    def load_frame(self) -> None:
        if self.capture is None:
            return
        seconds = min(max(0, float(self.time_var.get())), self.duration)
        self.capture.set(cv2.CAP_PROP_POS_MSEC, seconds * 1000)
        ok, frame = self.capture.read()
        if not ok:
            self.status_var.set("Impossible de lire cette image. Choisissez un instant légèrement plus tôt.")
            return
        self.frame = frame
        self.frame_h, self.frame_w = frame.shape[:2]
        self.detections = []
        self.show_yolo_var.set(False)
        self.count_label.configure(text="YOLO : lancer le test sur cette image")
        self.time_label.configure(text=f"{int(seconds//60):02d}:{int(seconds%60):02d} / {int(self.duration//60):02d}:{int(self.duration%60):02d}")
        self.status_var.set("Image affichée. Choisissez une place ou lancez la détection YOLO.")
        self.draw()

    def step(self, delta: float) -> None:
        self.time_var.set(min(max(0, self.time_var.get() + delta), self.duration - 0.25))
        self.load_frame()

    def detect(self) -> None:
        if self.frame is None:
            return
        self.status_var.set("YOLO analyse cette image…")
        self.root.update_idletasks()
        try:
            if self.model is None:
                from ultralytics import YOLO
                self.model = YOLO(str(MODEL))
            confidence = min(0.9, max(0.1, float(self.conf_var.get())))
            result = self.model.predict(self.frame, conf=confidence, classes=VEHICLE_CLASSES, verbose=False)[0]
            self.detections = []
            for box in result.boxes:
                x1, y1, x2, y2 = [float(n) for n in box.xyxy[0].tolist()]
                cls = int(box.cls[0])
                self.detections.append((x1, y1, x2, y2, result.names[cls], float(box.conf[0])))
            self.show_yolo_var.set(True)
            self.count_label.configure(text=f"YOLO : {len(self.detections)} véhicules détectés sur cette image")
            self.status_var.set("Rectangles bleus = détections YOLO, y compris hors des 18 places. Ce test ne calcule pas l'occupation.")
            self.draw()
        except Exception as exc:
            messagebox.showerror("Erreur YOLO", str(exc))
            self.status_var.set("La détection YOLO a échoué.")

    def selected(self) -> dict | None:
        return next((p for p in self.config["places"] if p["id"] == self.place_var.get()), None)

    def on_place_selected(self) -> None:
        place = self.selected()
        if place is not None:
            self.observable_var.set(bool(place.get("observable", True)))
        self.draw()

    def remember(self) -> None:
        self.undo_stack.append(copy.deepcopy(self.config))
        self.undo_stack = self.undo_stack[-30:]

    def undo(self) -> None:
        if not self.undo_stack:
            self.status_var.set("Aucune modification à annuler.")
            return
        self.config = self.undo_stack.pop()
        self.on_place_selected()
        self.status_var.set("Dernière modification annulée. Enregistrez pour conserver cet état.")

    def reset_place(self) -> None:
        place = self.selected()
        if place is None:
            return
        original = json.loads(DEFAULT_ZONES.read_text(encoding="utf-8"))
        source = next((p for p in original["places"] if p["id"] == place["id"]), None)
        if source is None:
            return
        self.remember()
        place.clear()
        place.update(copy.deepcopy(source))
        self.on_place_selected()
        self.status_var.set(f"{place['id']} rétablie depuis la configuration initiale.")

    def toggle_observable(self) -> None:
        place = self.selected()
        if place is not None:
            self.remember()
            place["observable"] = bool(self.observable_var.get())
            self.status_var.set(f"{place['id']} : {'observable' if place['observable'] else 'inconnue si non visible'}. Enregistrez l'essai.")
            self.draw()

    def points(self) -> list:
        place = self.selected()
        if place is None:
            return []
        key = self.polygon_var.get()
        if key == "display_polygon" and key not in place:
            place[key] = [p.copy() for p in place["polygon"]]
        return place[key]

    def to_canvas(self, point: list | tuple) -> tuple[float, float]:
        x = float(point[0]) * self.frame_w / self.config["reference_width"]
        y = float(point[1]) * self.frame_h / self.config["reference_height"]
        return self.offset_x + (x - self.view_x) * self.scale, self.offset_y + (y - self.view_y) * self.scale

    def from_canvas(self, x: float, y: float) -> list[int]:
        px = (x - self.offset_x) / self.scale + self.view_x
        py = (y - self.offset_y) / self.scale + self.view_y
        return [int(max(0, min(self.config["reference_width"] - 1, px * self.config["reference_width"] / self.frame_w))),
                int(max(0, min(self.config["reference_height"] - 1, py * self.config["reference_height"] / self.frame_h)))]

    def draw(self) -> None:
        if self.frame is None:
            return
        canvas = self.canvas
        cw, ch = max(canvas.winfo_width(), 2), max(canvas.winfo_height(), 2)
        zoom = {"1×": 1, "1,5×": 1.5, "2×": 2, "3×": 3}.get(self.zoom_var.get(), 1)
        view_w = max(1, int(self.frame_w / zoom))
        view_h = max(1, int(self.frame_h / zoom))
        place = self.selected()
        if place and zoom > 1:
            polygon = place.get(self.polygon_var.get(), place["polygon"])
            cx = sum(p[0] for p in polygon) / len(polygon) * self.frame_w / self.config["reference_width"]
            cy = sum(p[1] for p in polygon) / len(polygon) * self.frame_h / self.config["reference_height"]
            self.view_x = max(0, min(self.frame_w - view_w, int(cx - view_w / 2)))
            self.view_y = max(0, min(self.frame_h - view_h, int(cy - view_h / 2)))
        else:
            self.view_x = self.view_y = 0
        self.scale = min(cw / view_w, ch / view_h)
        w, h = max(1, round(view_w * self.scale)), max(1, round(view_h * self.scale))
        self.offset_x, self.offset_y = (cw - w) / 2, (ch - h) / 2
        cropped = self.frame[self.view_y:self.view_y + view_h, self.view_x:self.view_x + view_w]
        rgb = cv2.cvtColor(cropped, cv2.COLOR_BGR2RGB)
        img = Image.fromarray(rgb).resize((w, h), Image.Resampling.BILINEAR)
        self.photo = ImageTk.PhotoImage(img)
        canvas.delete("all")
        canvas.create_image(self.offset_x, self.offset_y, image=self.photo, anchor="nw")
        if self.show_yolo_var.get():
            for x1, y1, x2, y2, label, confidence in self.detections:
                a = (self.offset_x + (x1 - self.view_x) * self.scale, self.offset_y + (y1 - self.view_y) * self.scale)
                b = (self.offset_x + (x2 - self.view_x) * self.scale, self.offset_y + (y2 - self.view_y) * self.scale)
                canvas.create_rectangle(*a, *b, outline="#14a7ff", width=2)
                canvas.create_text(a[0] + 3, max(10, a[1] - 8), text=f"{label} {confidence:.2f}", fill="#14a7ff", anchor="w", font=("Segoe UI Semibold", 9))
        key = self.polygon_var.get()
        for place in self.config["places"]:
            chosen = place["id"] == self.place_var.get()
            if not chosen and not self.show_all_var.get():
                continue
            polygon = place.get(key, place["polygon"])
            if len(polygon) < 3:
                continue
            xy = [coord for point in polygon for coord in self.to_canvas(point)]
            color = "#ffd446" if chosen else "#4be299"
            thickness = max(1, min(8, self.line_var.get()))
            canvas.create_polygon(*xy, fill="", outline="#10222e", width=thickness + (4 if chosen else 2))
            canvas.create_polygon(*xy, fill="", outline=color, width=thickness + (1 if chosen else 0))
            x, y = self.to_canvas(polygon[0])
            canvas.create_text(x + 3, y - 7, text=place["id"], anchor="sw", fill=color, font=("Segoe UI Semibold", 10 if chosen else 8))
            if chosen:
                for point in polygon:
                    px, py = self.to_canvas(point)
                    canvas.create_oval(px - 7, py - 7, px + 7, py + 7, fill="#ffd446", outline="#10222e", width=2)
        if self.drawing:
            if len(self.draft) > 1:
                coords = [coord for point in self.draft for coord in self.to_canvas(point)]
                canvas.create_line(*coords, fill="#ffd446", width=3)
            for point in self.draft:
                x, y = self.to_canvas(point)
                canvas.create_oval(x - 5, y - 5, x + 5, y + 5, fill="#ffd446")

    def closest_vertex(self, x: float, y: float) -> int | None:
        for i, point in enumerate(self.points()):
            px, py = self.to_canvas(point)
            if (px - x) ** 2 + (py - y) ** 2 < 13 ** 2:
                return i
        return None

    def on_down(self, event) -> None:
        if self.drawing:
            self.draft.append(self.from_canvas(event.x, event.y))
            self.draw()
            return
        self.drag_index = self.closest_vertex(event.x, event.y)
        if self.drag_index is not None:
            self.remember()

    def on_drag(self, event) -> None:
        if self.drag_index is not None and not self.drawing:
            self.points()[self.drag_index] = self.from_canvas(event.x, event.y)
            self.draw()

    def on_up(self, _event) -> None:
        self.drag_index = None

    def on_double(self, event) -> None:
        if self.drawing or self.closest_vertex(event.x, event.y) is not None:
            return
        points = self.points()
        if len(points) < 2:
            return
        best_index, best_dist = None, 20 ** 2
        for i, a in enumerate(points):
            b = points[(i + 1) % len(points)]
            ax, ay = self.to_canvas(a)
            bx, by = self.to_canvas(b)
            dx, dy = bx - ax, by - ay
            t = max(0, min(1, ((event.x - ax) * dx + (event.y - ay) * dy) / (dx * dx + dy * dy or 1)))
            dist = (event.x - ax - t * dx) ** 2 + (event.y - ay - t * dy) ** 2
            if dist < best_dist:
                best_index, best_dist = i + 1, dist
        if best_index is not None:
            self.remember()
            points.insert(best_index, self.from_canvas(event.x, event.y))
            self.draw()

    def on_right(self, event) -> None:
        if self.drawing:
            if self.draft:
                self.draft.pop()
                self.draw()
            return
        index = self.closest_vertex(event.x, event.y)
        points = self.points()
        if index is not None and len(points) > 3:
            self.remember()
            points.pop(index)
            self.draw()

    def begin_redraw(self) -> None:
        self.drawing = True
        self.draft = []
        self.status_var.set(f"Cliquez au moins 3 points pour {self.place_var.get()}, puis « Terminer le contour ».")
        self.draw()

    def finish_redraw(self) -> None:
        if not self.drawing:
            return
        if len(self.draft) < 3:
            messagebox.showwarning("Contour incomplet", "Il faut au moins 3 points.")
            return
        self.remember()
        self.points()[:] = self.draft
        self.drawing = False
        self.draft = []
        self.status_var.set("Nouveau contour prêt. Enregistrez l'essai pour conserver le changement.")
        self.draw()

    def save(self) -> None:
        MANUAL_ZONES.write_text(json.dumps(self.config, ensure_ascii=False, indent=2), encoding="utf-8")
        self.zone_path = MANUAL_ZONES
        self.zone_label.configure(text=MANUAL_ZONES.name)
        self.status_var.set(f"Essai enregistré : {MANUAL_ZONES}")
        messagebox.showinfo("Polygones enregistrés", f"Copie d'essai créée :\n{MANUAL_ZONES}\n\nLa configuration du tableau de bord reste intacte.")


def main() -> None:
    root = tk.Tk()
    ManualLab(root)
    root.mainloop()


if __name__ == "__main__":
    main()

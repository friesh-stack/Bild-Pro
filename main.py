import os
import re
import io
import csv
import json
import shutil
from pathlib import Path
from datetime import datetime
from tkinter import Tk, StringVar, BooleanVar, IntVar, filedialog, messagebox
from tkinter import ttk

from PIL import Image, ImageOps, ImageEnhance
import pandas as pd


APP_NAME = "Bild-Pro"
APP_VERSION = "1.0.0"


DEFAULT_CONFIG = {
    "objects": {
        "Strandvilla 8a": {
            "prefix": "strandvilla_8a",
            "keywords": ["strandvilla 8a", "8a", "villa 8a"]
        },
        "Strandvilla 8b": {
            "prefix": "strandvilla_8b",
            "keywords": ["strandvilla 8b", "8b", "villa 8b"]
        },
        "Dünenvilla 3": {
            "prefix": "duenenvilla_3",
            "keywords": ["dünenvilla 3", "duenenvilla 3", "fewo 3", "wohnung 3"]
        },
        "Dünenvilla 5": {
            "prefix": "duenenvilla_5",
            "keywords": ["dünenvilla 5", "duenenvilla 5", "fewo 5", "wohnung 5"]
        }
    },
    "categories": {
        "Außenansicht": {
            "folder": "01_Aussenansicht",
            "keywords": ["außen", "aussen", "fassade", "haus", "eingang", "ansicht", "front", "villa"]
        },
        "Stellplatz": {
            "folder": "02_Stellplatz",
            "keywords": ["stellplatz", "parkplatz", "auto", "carport", "garage", "einfahrt", "zufahrt"]
        },
        "Garten": {
            "folder": "03_Garten",
            "keywords": ["garten", "rasen", "terrasse", "grill", "hecke", "pflanzen", "bäume", "baeume"]
        },
        "Wohnzimmer": {
            "folder": "04_Wohnzimmer",
            "keywords": ["wohnzimmer", "sofa", "couch", "sessel", "tv", "fernseher", "kamin", "living"]
        },
        "Küche": {
            "folder": "05_Kueche",
            "keywords": ["küche", "kueche", "kitchen", "herd", "backofen", "spüle", "spuele", "kühlschrank", "kuehlschrank", "geschirrspüler"]
        },
        "Schlafzimmer": {
            "folder": "06_Schlafzimmer",
            "keywords": ["schlafzimmer", "bett", "doppelbett", "kleiderschrank", "bedroom"]
        },
        "Bad 1": {
            "folder": "07_Bad_1",
            "keywords": ["bad 1", "badezimmer 1", "dusche", "waschbecken", "wc", "toilette", "spiegel"]
        },
        "Bad 2": {
            "folder": "08_Bad_2",
            "keywords": ["bad 2", "badezimmer 2", "zweites bad", "gäste wc", "gaeste wc", "wc 2"]
        },
        "Flur": {
            "folder": "09_Flur",
            "keywords": ["flur", "eingang", "garderobe", "treppe", "diele"]
        },
        "Aussicht": {
            "folder": "10_Aussicht",
            "keywords": ["aussicht", "meer", "strand", "ostsee", "blick", "düne", "duene", "umgebung"]
        },
        "Sonstige": {
            "folder": "99_Sonstige",
            "keywords": ["sonstige", "detail", "deko"]
        }
    }
}


def app_dir() -> Path:
    return Path(__file__).resolve().parent


def load_config() -> dict:
    config_path = app_dir() / "config" / "config.json"
    if config_path.exists():
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return DEFAULT_CONFIG


def normalize(text: str) -> str:
    text = text.lower()
    replacements = {"ä": "ae", "ö": "oe", "ü": "ue", "ß": "ss"}
    for a, b in replacements.items():
        text = text.replace(a, b)
    return text


def slugify(text: str) -> str:
    text = normalize(text)
    text = re.sub(r"[^a-z0-9]+", "_", text)
    text = re.sub(r"_+", "_", text).strip("_")
    return text or "bild"


def score_keywords(filename: str, label: str, keywords: list[str]) -> int:
    n = normalize(filename)
    score = 0
    if normalize(label) in n:
        score += 30
    for kw in keywords:
        nkw = normalize(str(kw))
        if nkw and nkw in n:
            score += max(5, len(nkw))
    return score


def detect_object(filename: str, config: dict, fallback: str) -> str:
    best_name, best_score = fallback, 0
    for name, info in config["objects"].items():
        score = score_keywords(filename, name, info.get("keywords", []))
        if score > best_score:
            best_name, best_score = name, score
    return best_name


def detect_category(filename: str, config: dict) -> tuple[str, int]:
    best_name, best_score = "Sonstige", 0
    for name, info in config["categories"].items():
        score = score_keywords(filename, name, info.get("keywords", []))
        if score > best_score:
            best_name, best_score = name, score
    return best_name, best_score


def crop_to_9_16(img: Image.Image) -> Image.Image:
    img = img.convert("RGB")
    target_ratio = 9 / 16
    w, h = img.size
    ratio = w / h
    if ratio > target_ratio:
        new_w = int(h * target_ratio)
        left = (w - new_w) // 2
        return img.crop((left, 0, left + new_w, h))
    if ratio < target_ratio:
        new_h = int(w / target_ratio)
        top = max(0, (h - new_h) // 2)
        return img.crop((0, top, w, top + new_h))
    return img


def fit_to_9_16_white(img: Image.Image) -> Image.Image:
    img = img.convert("RGB")
    target_ratio = 9 / 16
    w, h = img.size
    ratio = w / h
    if ratio > target_ratio:
        new_w = w
        new_h = int(w / target_ratio)
    else:
        new_h = h
        new_w = int(h * target_ratio)
    canvas = Image.new("RGB", (new_w, new_h), "white")
    canvas.paste(img, ((new_w - w) // 2, (new_h - h) // 2))
    return canvas


def resize_long_edge(img: Image.Image, max_edge: int) -> Image.Image:
    img = img.convert("RGB")
    w, h = img.size
    if max(w, h) <= max_edge:
        return img
    if w >= h:
        new_size = (max_edge, int(h * max_edge / w))
    else:
        new_size = (int(w * max_edge / h), max_edge)
    return img.resize(new_size, Image.LANCZOS)


def optimize_image(img: Image.Image, mode: str, min_kb: int, max_kb: int, max_edge: int, auto_enhance: bool) -> bytes:
    img = ImageOps.exif_transpose(img).convert("RGB")

    if auto_enhance:
        img = ImageEnhance.Contrast(img).enhance(1.08)
        img = ImageEnhance.Sharpness(img).enhance(1.05)

    if mode == "9:16 zuschneiden":
        img = crop_to_9_16(img)
    elif mode == "9:16 mit weißem Rand":
        img = fit_to_9_16_white(img)

    img = resize_long_edge(img, max_edge)

    best_bytes = b""
    best_distance = 10**9
    target = (min_kb + max_kb) / 2

    for edge in [max_edge, 1800, 1600, 1400, 1200, 1000, 900, 800]:
        candidate = resize_long_edge(img, edge)
        for quality in range(95, 34, -5):
            buffer = io.BytesIO()
            candidate.save(buffer, format="JPEG", quality=quality, optimize=True, progressive=True)
            data = buffer.getvalue()
            size_kb = len(data) / 1024
            if min_kb <= size_kb <= max_kb:
                return data
            distance = abs(size_kb - target)
            if distance < best_distance:
                best_distance = distance
                best_bytes = data
            if size_kb < max_kb:
                return data

    return best_bytes


def create_html(rows: list[dict], title: str) -> str:
    cards = []
    for row in rows:
        path = row["relative_path"].replace("\\", "/")
        cards.append(f"""
<div class="card">
  <img src="{path}" alt="{row['new_name']}">
  <h3>{row['category']}</h3>
  <p>{row['title']}</p>
  <small>{row['new_name']} · {row['size_kb']} KB</small>
</div>
""")
    return f"""<!doctype html>
<html lang="de">
<head>
<meta charset="utf-8">
<title>{title}</title>
<style>
body {{ font-family: Arial, sans-serif; margin: 24px; background:#f5f5f5; }}
h1 {{ margin-bottom: 4px; }}
.grid {{ display:grid; grid-template-columns: repeat(auto-fill, minmax(260px, 1fr)); gap:18px; }}
.card {{ background:white; border-radius:12px; padding:12px; box-shadow:0 2px 8px rgba(0,0,0,.12); }}
.card img {{ width:100%; height:260px; object-fit:cover; border-radius:10px; }}
</style>
</head>
<body>
<h1>{title}</h1>
<p>Erstellt mit {APP_NAME} {APP_VERSION} am {datetime.now().strftime('%d.%m.%Y %H:%M')}</p>
<div class="grid">{''.join(cards)}</div>
</body>
</html>"""


class BildProApp:
    def __init__(self, root: Tk):
        self.root = root
        self.root.title(f"{APP_NAME} {APP_VERSION}")
        self.root.geometry("940x680")
        self.config = load_config()
        self.source_dir = StringVar()
        self.output_dir = StringVar()
        self.object_var = StringVar(value=list(self.config["objects"].keys())[0])
        self.mode_var = StringVar(value="9:16 zuschneiden")
        self.min_kb = IntVar(value=150)
        self.max_kb = IntVar(value=300)
        self.max_edge = IntVar(value=1600)
        self.auto_enhance = BooleanVar(value=True)
        self.keep_originals = BooleanVar(value=True)
        self.status_var = StringVar(value="Bereit.")
        self.files = []
        self.build_ui()

    def build_ui(self):
        main = ttk.Frame(self.root, padding=12)
        main.pack(fill="both", expand=True)

        title = ttk.Label(main, text="Bild-Pro – Bildsortierer für Ferienwohnungen", font=("Segoe UI", 16, "bold"))
        title.pack(anchor="w", pady=(0, 12))

        paths = ttk.LabelFrame(main, text="1. Ordner auswählen", padding=10)
        paths.pack(fill="x", pady=6)

        ttk.Label(paths, text="Fotoordner").grid(row=0, column=0, sticky="w")
        ttk.Entry(paths, textvariable=self.source_dir, width=80).grid(row=0, column=1, padx=8)
        ttk.Button(paths, text="Durchsuchen", command=self.pick_source).grid(row=0, column=2)

        ttk.Label(paths, text="Zielordner").grid(row=1, column=0, sticky="w", pady=(8, 0))
        ttk.Entry(paths, textvariable=self.output_dir, width=80).grid(row=1, column=1, padx=8, pady=(8, 0))
        ttk.Button(paths, text="Durchsuchen", command=self.pick_output).grid(row=1, column=2, pady=(8, 0))

        settings = ttk.LabelFrame(main, text="2. Einstellungen", padding=10)
        settings.pack(fill="x", pady=6)

        ttk.Label(settings, text="Objekt").grid(row=0, column=0, sticky="w")
        ttk.Combobox(settings, textvariable=self.object_var, values=list(self.config["objects"].keys()), width=28, state="readonly").grid(row=0, column=1, sticky="w", padx=8)

        ttk.Label(settings, text="Format").grid(row=0, column=2, sticky="w")
        ttk.Combobox(settings, textvariable=self.mode_var, values=["Originalformat", "9:16 zuschneiden", "9:16 mit weißem Rand"], width=26, state="readonly").grid(row=0, column=3, sticky="w", padx=8)

        ttk.Label(settings, text="Min KB").grid(row=1, column=0, sticky="w", pady=(8, 0))
        ttk.Entry(settings, textvariable=self.min_kb, width=8).grid(row=1, column=1, sticky="w", padx=8, pady=(8, 0))

        ttk.Label(settings, text="Max KB").grid(row=1, column=2, sticky="w", pady=(8, 0))
        ttk.Entry(settings, textvariable=self.max_kb, width=8).grid(row=1, column=3, sticky="w", padx=8, pady=(8, 0))

        ttk.Label(settings, text="Lange Kante").grid(row=2, column=0, sticky="w", pady=(8, 0))
        ttk.Combobox(settings, textvariable=self.max_edge, values=[900, 1200, 1600, 2000, 2400], width=8, state="readonly").grid(row=2, column=1, sticky="w", padx=8, pady=(8, 0))

        ttk.Checkbutton(settings, text="Helligkeit/Kontrast leicht verbessern", variable=self.auto_enhance).grid(row=2, column=2, sticky="w", pady=(8, 0))
        ttk.Checkbutton(settings, text="Originale sichern", variable=self.keep_originals).grid(row=2, column=3, sticky="w", pady=(8, 0))

        buttons = ttk.Frame(main)
        buttons.pack(fill="x", pady=10)

        ttk.Button(buttons, text="Fotos prüfen", command=self.scan).pack(side="left")
        ttk.Button(buttons, text="START – Bilder sortieren", command=self.process).pack(side="left", padx=8)
        ttk.Button(buttons, text="Zielordner öffnen", command=self.open_output).pack(side="left", padx=8)

        preview_frame = ttk.LabelFrame(main, text="3. Erkannte Bilder", padding=8)
        preview_frame.pack(fill="both", expand=True, pady=6)

        columns = ("file", "object", "category", "score")
        self.tree = ttk.Treeview(preview_frame, columns=columns, show="headings", height=15)
        self.tree.heading("file", text="Datei")
        self.tree.heading("object", text="Objekt")
        self.tree.heading("category", text="Kategorie")
        self.tree.heading("score", text="Treffer")
        self.tree.column("file", width=430)
        self.tree.column("object", width=160)
        self.tree.column("category", width=180)
        self.tree.column("score", width=70)
        self.tree.pack(fill="both", expand=True)

        status = ttk.Label(main, textvariable=self.status_var, relief="sunken", anchor="w")
        status.pack(fill="x", pady=(8, 0))

    def pick_source(self):
        path = filedialog.askdirectory(title="Fotoordner auswählen")
        if path:
            self.source_dir.set(path)
            if not self.output_dir.get():
                self.output_dir.set(str(Path(path) / "_Bild-Pro_Ergebnis"))

    def pick_output(self):
        path = filedialog.askdirectory(title="Zielordner auswählen")
        if path:
            self.output_dir.set(path)

    def scan(self):
        source = Path(self.source_dir.get())
        if not source.exists():
            messagebox.showerror("Fehler", "Bitte einen gültigen Fotoordner auswählen.")
            return

        exts = {".jpg", ".jpeg", ".png", ".webp"}
        self.files = [p for p in source.iterdir() if p.suffix.lower() in exts]
        self.tree.delete(*self.tree.get_children())

        for p in self.files:
            obj = detect_object(p.name, self.config, self.object_var.get())
            cat, score = detect_category(p.name, self.config)
            self.tree.insert("", "end", values=(p.name, obj, cat, score))

        self.status_var.set(f"{len(self.files)} Bilder gefunden.")

    def process(self):
        if not self.files:
            self.scan()
        if not self.files:
            return

        source = Path(self.source_dir.get())
        output = Path(self.output_dir.get())
        output.mkdir(parents=True, exist_ok=True)

        if self.keep_originals.get():
            originals = output / "_Originale"
            originals.mkdir(exist_ok=True)

        rows = []
        counters = {}

        for idx, p in enumerate(self.files, start=1):
            obj = detect_object(p.name, self.config, self.object_var.get())
            cat, score = detect_category(p.name, self.config)

            obj_info = self.config["objects"].get(obj, {})
            cat_info = self.config["categories"].get(cat, self.config["categories"]["Sonstige"])
            obj_prefix = obj_info.get("prefix", slugify(obj))
            folder = cat_info.get("folder", slugify(cat))

            counter_key = (obj, cat)
            counters[counter_key] = counters.get(counter_key, 0) + 1

            out_dir = output / slugify(obj) / folder
            out_dir.mkdir(parents=True, exist_ok=True)

            new_name = f"{obj_prefix}_{folder}_{counters[counter_key]:02d}.jpg"
            out_path = out_dir / new_name

            try:
                img = Image.open(p)
                data = optimize_image(
                    img,
                    self.mode_var.get(),
                    int(self.min_kb.get()),
                    int(self.max_kb.get()),
                    int(self.max_edge.get()),
                    self.auto_enhance.get()
                )
                out_path.write_bytes(data)
                if self.keep_originals.get():
                    shutil.copy2(p, output / "_Originale" / p.name)

                rows.append({
                    "Nr": idx,
                    "Objekt": obj,
                    "Kategorie": cat,
                    "Titel": cat,
                    "Originaldatei": p.name,
                    "Neue Datei": new_name,
                    "Ordner": str(out_dir.relative_to(output)),
                    "relative_path": str((out_dir / new_name).relative_to(output)),
                    "new_name": new_name,
                    "category": cat,
                    "size_kb": round(len(data) / 1024, 1),
                    "Treffer": score
                })
            except Exception as exc:
                rows.append({
                    "Nr": idx,
                    "Objekt": obj,
                    "Kategorie": "Fehler",
                    "Titel": str(exc),
                    "Originaldatei": p.name,
                    "Neue Datei": "",
                    "Ordner": "",
                    "relative_path": "",
                    "new_name": "",
                    "category": "Fehler",
                    "size_kb": 0,
                    "Treffer": 0
                })

            self.status_var.set(f"Verarbeitet: {idx}/{len(self.files)}")
            self.root.update_idletasks()

        df = pd.DataFrame(rows)
        df.to_excel(output / "bilduebersicht.xlsx", index=False)
        df.to_csv(output / "bilduebersicht.csv", index=False, sep=";", encoding="utf-8-sig")
        html = create_html([r for r in rows if r["new_name"]], f"Bildübersicht {self.object_var.get()}")
        (output / "index.html").write_text(html, encoding="utf-8")

        messagebox.showinfo("Fertig", f"Die Bilder wurden sortiert.\n\nZielordner:\n{output}")
        self.status_var.set(f"Fertig. Ergebnis: {output}")

    def open_output(self):
        path = Path(self.output_dir.get())
        if path.exists():
            os.startfile(str(path))
        else:
            messagebox.showwarning("Hinweis", "Der Zielordner existiert noch nicht.")


def main():
    root = Tk()
    try:
        root.iconbitmap(str(app_dir() / "assets" / "bild-pro.ico"))
    except Exception:
        pass
    app = BildProApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()

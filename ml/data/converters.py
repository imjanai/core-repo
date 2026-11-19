"""
ml/data/converters.py — Format conversion tools for labeling exports.
Converts CVAT / COCO / Label Studio annotations to YOLO .txt format and VLM JSONL.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from packages.schema import SymbolType

# Mapping from label names to YOLO class indices
LABEL_TO_CLASS_ID: dict[str, int] = {
    "wandcontactdoos": 0,
    "wcd": 0,
    "stopcontact": 0,
    "schakelaar": 1,
    "switch": 1,
    "lichtpunt": 2,
    "lamp": 2,
    "datapunt": 3,
    "data": 3,
    "verdeler": 4,
    "groepenkast": 4,
    "meterkast": 4,
}


def coco_to_yolo(coco_json_path: str | Path, output_labels_dir: str | Path) -> int:
    """
    Converts a COCO annotations JSON export to YOLO txt format.
    """
    with open(coco_json_path, "r", encoding="utf-8") as f:
        coco = json.load(f)

    out_dir = Path(output_labels_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    # Index images by id
    images = {img["id"]: img for img in coco.get("images", [])}
    # Index categories
    categories = {cat["id"]: cat["name"].lower() for cat in coco.get("categories", [])}

    annotations_by_img: dict[int, list[dict[str, Any]]] = {}
    for ann in coco.get("annotations", []):
        img_id = ann["image_id"]
        annotations_by_img.setdefault(img_id, []).append(ann)

    converted_files = 0
    for img_id, img_info in images.items():
        img_w = float(img_info["width"])
        img_h = float(img_info["height"])
        file_stem = Path(img_info["file_name"]).stem
        out_txt = out_dir / f"{file_stem}.txt"

        lines = []
        for ann in annotations_by_img.get(img_id, []):
            cat_name = categories.get(ann["category_id"], "")
            cls_id = LABEL_TO_CLASS_ID.get(cat_name)
            if cls_id is None:
                continue

            # COCO bbox: [x_min, y_min, width, height]
            x_min, y_min, w, h = ann["bbox"]
            x_center = (x_min + w / 2.0) / img_w
            y_center = (y_min + h / 2.0) / img_h
            w_norm = w / img_w
            h_norm = h / img_h

            # Clamp normalized values
            x_center = max(0.0, min(1.0, x_center))
            y_center = max(0.0, min(1.0, y_center))
            w_norm = max(0.0, min(1.0, w_norm))
            h_norm = max(0.0, min(1.0, h_norm))

            lines.append(f"{cls_id} {x_center:.6f} {y_center:.6f} {w_norm:.6f} {h_norm:.6f}")

        with open(out_txt, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + ("\n" if lines else ""))
        converted_files += 1

    return converted_files


def label_studio_to_yolo(ls_json_path: str | Path, output_labels_dir: str | Path) -> int:
    """
    Converts Label Studio JSON export to YOLO txt format.
    """
    with open(ls_json_path, "r", encoding="utf-8") as f:
        tasks = json.load(f)

    out_dir = Path(output_labels_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    converted_files = 0
    for task in tasks:
        # Get filename or id
        data = task.get("data", {})
        image_url = data.get("image", "")
        file_stem = Path(image_url).stem or f"task_{task.get('id', converted_files)}"
        out_txt = out_dir / f"{file_stem}.txt"

        lines = []
        annotations = task.get("annotations", [])
        for ann in annotations:
            for res in ann.get("result", []):
                val = res.get("value", {})
                labels = val.get("rectanglelabels", [])
                if not labels:
                    continue
                label_name = labels[0].lower()
                cls_id = LABEL_TO_CLASS_ID.get(label_name)
                if cls_id is None:
                    continue

                # Label Studio percentages (0-100)
                x_perc = float(val["x"])
                y_perc = float(val["y"])
                w_perc = float(val["width"])
                h_perc = float(val["height"])

                x_center = (x_perc + w_perc / 2.0) / 100.0
                y_center = (y_perc + h_perc / 2.0) / 100.0
                w_norm = w_perc / 100.0
                h_norm = h_perc / 100.0

                lines.append(f"{cls_id} {x_center:.6f} {y_center:.6f} {w_norm:.6f} {h_norm:.6f}")

        with open(out_txt, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + ("\n" if lines else ""))
        converted_files += 1

    return converted_files

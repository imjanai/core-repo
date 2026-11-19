"""
ml/data/synthetic.py — Synthetic blueprint and label generator for electrical schematics.
Produces realistic architectural floor plans with electrical symbols, rooms, and circuits.
Emits DXF files, rendered blueprint images, YOLO label files, and ground truth Project models.
"""

from __future__ import annotations

import json
import math
import random
from pathlib import Path
from typing import Any

import cv2
import numpy as np

from packages.drawing import create_drawing, draw_cable, export_dxf, place_symbol
from packages.materials import compute_materials
from packages.schema import FileType, Project, Room, SourceType, Symbol, SymbolType

SYMBOL_CHOICES = [
    (SymbolType.WANDCONTACTDOOS, 0),
    (SymbolType.SCHAKELAAR, 1),
    (SymbolType.LICHTPUNT, 2),
    (SymbolType.DATAPUNT, 3),
    (SymbolType.VERDELER, 4),
]


def generate_synthetic_blueprint(
    project_id: str = "synth-001",
    num_rooms: int = 4,
    symbols_per_room: int = 6,
    img_size: int = 1024,
    seed: int = 42,
) -> tuple[Project, bytes, list[dict[str, Any]]]:
    """
    Generates a synthetic architectural blueprint:
    Returns (Project, rendered_png_bytes, yolo_boxes_list).
    """
    rng = random.Random(seed)
    scale = 1.0  # 1 px = 10 mm (or 100 px per meter)

    # 1. Create layout canvas
    img = np.ones((img_size, img_size, 3), dtype=np.uint8) * 250  # Off-white blueprint background

    # 2. Draw outer walls and rooms
    margin = 80
    usable_w = img_size - 2 * margin
    usable_h = img_size - 2 * margin

    room_names = ["Woonkamer", "Keuken", "Slaapkamer", "Badkamer", "Hal", "Berging"]
    rng.shuffle(room_names)

    cols = 2
    rows = (num_rooms + 1) // 2
    col_w = usable_w // cols
    row_h = usable_h // rows

    rooms: list[Room] = []
    symbols: list[Symbol] = []
    yolo_boxes: list[dict[str, Any]] = []

    # Distribution board in the first room / hallway
    panel_placed = False

    for r_idx in range(num_rooms):
        c = r_idx % cols
        r = r_idx // cols
        rx1 = margin + c * col_w
        ry1 = margin + r * row_h
        rx2 = rx1 + col_w
        ry2 = ry1 + row_h
        r_name = room_names[r_idx % len(room_names)]

        # Draw room walls
        cv2.rectangle(img, (rx1, ry1), (rx2, ry2), (60, 60, 60), 3)
        cv2.putText(
            img,
            r_name,
            (rx1 + 20, ry1 + 35),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (90, 90, 90),
            2,
        )

        room_obj = Room(
            name=r_name,
            polygon=[
                [rx1 * 10.0, ry1 * 10.0],
                [rx2 * 10.0, ry1 * 10.0],
                [rx2 * 10.0, ry2 * 10.0],
                [rx1 * 10.0, ry2 * 10.0],
            ],
        )
        rooms.append(room_obj)

        circuit_id = f"G{r_idx + 1}"

        # Place symbols in this room
        for s_idx in range(symbols_per_room):
            # Select symbol type
            if not panel_placed:
                st, cls_id = SymbolType.VERDELER, 4
                panel_placed = True
            else:
                st, cls_id = rng.choice(SYMBOL_CHOICES[:4])

            # Random position inside room away from walls
            sx = rng.randint(rx1 + 30, rx2 - 30)
            sy = rng.randint(ry1 + 45, ry2 - 30)

            # Draw symbol representation on canvas
            box_sz = 24
            half = box_sz // 2
            if st == SymbolType.WANDCONTACTDOOS:
                cv2.circle(img, (sx, sy), half - 2, (0, 0, 180), 2)
                cv2.line(img, (sx - half + 2, sy), (sx + half - 2, sy), (0, 0, 180), 2)
            elif st == SymbolType.SCHAKELAAR:
                cv2.circle(img, (sx, sy), half - 4, (180, 0, 0), 2)
                cv2.line(img, (sx, sy), (sx + half, sy - half), (180, 0, 0), 2)
            elif st == SymbolType.LICHTPUNT:
                cv2.line(img, (sx - half, sy - half), (sx + half, sy + half), (0, 140, 0), 2)
                cv2.line(img, (sx - half, sy + half), (sx + half, sy - half), (0, 140, 0), 2)
            elif st == SymbolType.DATAPUNT:
                pts = np.array([[sx, sy - half], [sx - half, sy + half], [sx + half, sy + half]], np.int32)
                cv2.polylines(img, [pts], True, (160, 80, 0), 2)
            elif st == SymbolType.VERDELER:
                cv2.rectangle(img, (sx - half, sy - half * 2), (sx + half, sy + half * 2), (0, 0, 0), 2)
                cv2.line(img, (sx - half, sy - half * 2), (sx + half, sy + half * 2), (0, 0, 0), 2)

            # Symbol object in mm
            sym = Symbol(
                type=st,
                x=float(sx * 10.0),
                y=float(sy * 10.0),
                room_id=room_obj.id,
                circuit=circuit_id,
                confidence=1.0,
                source=SourceType.VECTOR,
                attributes={"synthetic": True},
            )
            symbols.append(sym)

            # Normalized YOLO coordinates
            x_center = sx / img_size
            y_center = sy / img_size
            w_norm = box_sz / img_size
            h_norm = (box_sz * 2 if st == SymbolType.VERDELER else box_sz) / img_size

            yolo_boxes.append({
                "class_id": cls_id,
                "x_center": x_center,
                "y_center": y_center,
                "width": w_norm,
                "height": h_norm,
                "symbol_type": st.value,
            })

    # Draw legend at bottom
    cv2.putText(img, "LEGENDA: O-WCD  /-Schakelaar  X-Lichtpunt  ^-Data  []-Verdeler", (margin, img_size - 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (100, 100, 100), 1)

    project = Project(
        id=project_id,
        name=f"Synthetisch Project {project_id}",
        file_type=FileType.IMAGE,
        scale=10.0,
        rooms=rooms,
        symbols=symbols,
        meta={"synthetic": True, "seed": seed},
    )
    # Compute ground truth materials
    project = compute_materials(project)

    _, png_bytes = cv2.imencode(".png", img)
    return project, png_bytes.tobytes(), yolo_boxes


def write_synthetic_dataset(
    output_dir: str | Path = "ml/data",
    num_train: int = 10,
    num_val: int = 4,
    num_golden: int = 6,
) -> dict[str, int]:
    """
    Populates ml/data with synthetic drawings, labels, VLM conversations, and golden benchmarks.
    """
    base = Path(output_dir)
    det_img_train = base / "detector" / "images" / "train"
    det_img_val = base / "detector" / "images" / "val"
    det_lbl_train = base / "detector" / "labels" / "train"
    det_lbl_val = base / "detector" / "labels" / "val"
    golden_img_dir = base / "golden" / "tekeningen"
    golden_ans_dir = base / "golden" / "antwoorden"
    vlm_dir = base / "vlm"

    for d in (det_img_train, det_img_val, det_lbl_train, det_lbl_val, golden_img_dir, golden_ans_dir, vlm_dir):
        d.mkdir(parents=True, exist_ok=True)

    vlm_train_records: list[dict[str, Any]] = []
    vlm_val_records: list[dict[str, Any]] = []

    # Generate Train
    train_ids = [f"synth-train-{i:03d}" for i in range(1, num_train + 1)]
    for idx, pid in enumerate(train_ids):
        proj, png_bytes, boxes = generate_synthetic_blueprint(pid, seed=100 + idx)
        img_name = f"{pid}.png"
        (det_img_train / img_name).write_bytes(png_bytes)
        lbl_content = "\n".join(
            f"{b['class_id']} {b['x_center']:.6f} {b['y_center']:.6f} {b['width']:.6f} {b['height']:.6f}"
            for b in boxes
        )
        (det_lbl_train / f"{pid}.txt").write_text(lbl_content + "\n", encoding="utf-8")

        # VLM record
        vlm_train_records.append({
            "image": str(det_img_train / img_name),
            "conversations": [
                {"from": "human", "value": "<image>\nWelke ruimtes ziet u op deze tekening? Geef JSON."},
                {"from": "gpt", "value": json.dumps([r.name for r in proj.rooms])},
            ],
        })

    # Generate Val
    val_ids = [f"synth-val-{i:03d}" for i in range(1, num_val + 1)]
    for idx, pid in enumerate(val_ids):
        proj, png_bytes, boxes = generate_synthetic_blueprint(pid, seed=200 + idx)
        img_name = f"{pid}.png"
        (det_img_val / img_name).write_bytes(png_bytes)
        lbl_content = "\n".join(
            f"{b['class_id']} {b['x_center']:.6f} {b['y_center']:.6f} {b['width']:.6f} {b['height']:.6f}"
            for b in boxes
        )
        (det_lbl_val / f"{pid}.txt").write_text(lbl_content + "\n", encoding="utf-8")

        vlm_val_records.append({
            "image": str(det_img_val / img_name),
            "conversations": [
                {"from": "human", "value": "<image>\nWelke ruimtes ziet u op deze tekening? Geef JSON."},
                {"from": "gpt", "value": json.dumps([r.name for r in proj.rooms])},
            ],
        })

    # Write VLM JSONL files
    with open(vlm_dir / "train.jsonl", "w", encoding="utf-8") as f:
        for r in vlm_train_records:
            f.write(json.dumps(r) + "\n")

    with open(vlm_dir / "val.jsonl", "w", encoding="utf-8") as f:
        for r in vlm_val_records:
            f.write(json.dumps(r) + "\n")

    # Generate Golden Set
    golden_ids = [f"synth-golden-{i:03d}" for i in range(1, num_golden + 1)]
    for idx, pid in enumerate(golden_ids):
        proj, png_bytes, _ = generate_synthetic_blueprint(pid, seed=900 + idx)
        (golden_img_dir / f"{pid}.png").write_bytes(png_bytes)
        (golden_ans_dir / f"{pid}.json").write_text(
            proj.model_dump_json(indent=2), encoding="utf-8"
        )

    # Write splitsing.yaml
    from ml.data.split import create_or_update_splits
    create_or_update_splits(train_ids + val_ids, golden_ids, base / "splitsing.yaml")

    return {
        "train": len(train_ids),
        "val": len(val_ids),
        "golden": len(golden_ids),
    }

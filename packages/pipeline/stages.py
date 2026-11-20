"""
packages/pipeline/stages.py — de elf stappen uit het README, als code.

Volgorde (zie doc/031-pipeline-overview.md):

     1  ingest        bestand ophalen uit opslag
     2  classify      formaat bepalen (magic bytes > extensie)
     3  normalize     schaal, tegels, metadata
     4a extract_vector DXF/IFC/PDF-vectordata
     4b detect        symbolen op rasterafbeeldingen
     4c legend_ocr    legenda + bijschriften
     5  vlm           visueel redeneren over de hele tekening
     6  fuse          drie sporen samensmelten tot één Project
     7  validate      AREI/NEN 1010 waarschuwingen
     8  materials     materiaallijst + prijzen
     9  output        exportklaar maken

Ontwerpregel: **stappen 1-3 en 6-9 zijn verplicht, 4a/4b/4c/5 zijn optioneel.**
De parser- en visionpackages zijn nog niet gebouwd; zolang die ontbreken slaan
die stappen over (met een duidelijke reden) en levert de run alsnog een
bruikbare, gevalideerde materiaallijst op. Zodra `packages/parsers` of
`packages/vision` bestaat, licht de bijbehorende stap automatisch op — de
engine hoeft niet gewijzigd te worden.

Verwachte contracten (bouw je later, ondertekening is bindend):

    packages.parsers.dxf.parse_dxf(data: bytes) -> Project
    packages.parsers.ifc.parse_ifc(data: bytes) -> Project
    packages.parsers.pdf.parse_pdf(data: bytes) -> Project
    packages.vision.detector.detect_symbols(data: bytes, project: Project) -> list[Symbol]
    packages.vision.ocr.extract_legend(data: bytes) -> list[dict]
    packages.vision.vlm.reason(project: Project, data: bytes, legend: list) -> Project
"""

from __future__ import annotations

import hashlib
import importlib
import logging
import os
from typing import Any, Callable

from packages.schema import FileType, Project, SourceType, Symbol, ValidationWarning

from packages.pipeline.errors import NotImplementedStage, PermanentStageError, StageSkipped
from packages.pipeline.fusion import FusionConfig, fuse
from packages.pipeline.stage import Stage, StageContext, stage
from packages.pipeline.types import RetryPolicy

logger = logging.getLogger("imjan.pipeline")

#: Eigen retry-policy voor I/O- en modelstappen: snelle eerste herhaling,
#: daarna ruimere backoff (net genoeg om een korte S3/blip op te vangen).
IO_RETRY = RetryPolicy(max_attempts=3, base_delay=1.0, max_delay=30.0)
MODEL_RETRY = RetryPolicy(max_attempts=4, base_delay=2.0, max_delay=60.0)
FAST = RetryPolicy(max_attempts=2, base_delay=0.0, jitter=False)


# ---------------------------------------------------------------------------
# Hulpmiddelen
# ---------------------------------------------------------------------------


def _lazy(module: str, attr: str) -> Callable | None:
    """Import alleen als het bestand bestaat — anders None (stage slaat over)."""
    try:
        mod = importlib.import_module(module)
    except ModuleNotFoundError:
        return None
    fn = getattr(mod, attr, None)
    return fn if callable(fn) else None


def _require(fn: Callable | None, stage_id: str, what: str) -> Callable:
    if fn is None:
        raise NotImplementedStage(f"[{stage_id}] {what} is nog niet geïmplementeerd")
    return fn


def _merge_project(target: Project, source: Project) -> None:
    """Voegt een parser-Project samen in het lopende Project."""
    target.symbols.extend(source.symbols)
    target.rooms.extend(source.rooms)
    if source.scale and source.scale != 1.0 and target.scale == 1.0:
        target.scale = source.scale
    for key, value in (source.meta or {}).items():
        target.meta.setdefault(key, value)


def _looks_like_image(data: bytes) -> bool:
    return (
        data.startswith(b"\x89PNG\r\n\x1a\n")
        or data.startswith(b"\xff\xd8\xff")
        or data[:4] in (b"II*\x00", b"MM\x00*")
        or data[:6] in (b"GIF87a", b"GIF89a")
    )


def detect_file_type(data: bytes, filename: str = "") -> FileType:
    """
    Bepaalt het formaat op de inhoud (magic bytes), met de bestandsnaam als
    terugval. Inhoud wint altijd: een `.pdf` met PNG-inhoud is een afbeelding.
    """
    head = data[:32]
    if head.startswith(b"%PDF"):
        return FileType.PDF
    if head.startswith(b"ISO-10303-21"):
        return FileType.IFC
    if head.startswith(b"AutoCAD Binary DXF"):
        return FileType.DXF
    if _looks_like_image(data):
        return FileType.IMAGE
    # ASCII-DXF: records zijn gescheiden door nieuwe regels; "SECTION" of
    # een commentarieregel (999) in de eerste bytes is vrijwel uniek.
    if head.lstrip().startswith(b"999") or b"SECTION" in data[:256]:
        return FileType.DXF

    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    return {
        "dxf": FileType.DXF,
        "dwg": FileType.DXF,
        "ifc": FileType.IFC,
        "pdf": FileType.PDF,
        "png": FileType.IMAGE,
        "jpg": FileType.IMAGE,
        "jpeg": FileType.IMAGE,
        "tif": FileType.IMAGE,
        "tiff": FileType.IMAGE,
        "bmp": FileType.IMAGE,
    }.get(ext, FileType.UNKNOWN)


def _tile_grid(width: int, height: int, tile: int = 1024, overlap: int = 128) -> list[dict]:
    """Tegelraster voor de detector — puur rekenen, geen beeldbibliotheek nodig."""
    if width <= 0 or height <= 0 or tile <= 0:
        return []
    overlap = min(max(overlap, 0), tile - 1)
    step = tile - overlap
    tiles = []
    for y in range(0, max(1, height - overlap), step):
        for x in range(0, max(1, width - overlap), step):
            tiles.append({"x": x, "y": y, "w": min(tile, width - x), "h": min(tile, height - y)})
    return tiles


# ---------------------------------------------------------------------------
# 1 — Ingest
# ---------------------------------------------------------------------------


@stage(
    id="ingest",
    name="Ingest",
    description="Haalt het bronbestand op uit de opslag en vastlegt integriteit.",
    retry=IO_RETRY,
    timeout_s=120.0,
    replay=True,  # bytes horen niet in het checkpoint → bij hervatten opnieuw
)
def ingest(ctx: StageContext) -> None:
    data = ctx.load_source()
    if not data:
        raise PermanentStageError("Bronbestand is leeg", stage_id="ingest")

    ctx.payload["source_bytes"] = data
    ctx.payload["source_size"] = len(data)
    ctx.payload["source_sha256"] = hashlib.sha256(data).hexdigest()
    ctx.project.meta.setdefault("source", {})
    ctx.project.meta["source"] = {
        "sha256": ctx.payload["source_sha256"],
        "size": len(data),
        "filename": ctx.payload.get("filename", ""),
    }


# ---------------------------------------------------------------------------
# 2 — Classificatie
# ---------------------------------------------------------------------------


@stage(
    id="classify",
    name="Classificatie",
    description="Bepaalt het bestandsformaat op basis van magic bytes.",
    requires=("ingest",),
    retry=FAST,
    timeout_s=30.0,
)
def classify(ctx: StageContext) -> None:
    data = ctx.load_source()
    file_type = detect_file_type(data, str(ctx.payload.get("filename", "")))

    if file_type == FileType.UNKNOWN:
        # Geen fout: de run gaat door en de optionele stappen slaan over.
        # De elektricien ziet "formaat niet herkend" in plaats van een crash.
        logger.warning("Onbekend bestandsformaat voor project %s", ctx.project.id)
        ctx.payload["classify_note"] = "formaat niet herkend"

    ctx.project.file_type = file_type
    ctx.payload["file_type"] = file_type.value


# ---------------------------------------------------------------------------
# 3 — Normalisatie
# ---------------------------------------------------------------------------


@stage(
    id="normalize",
    name="Normalisatie",
    description="Schaal, tegelraster en metadata voor de vervolgstappen.",
    requires=("classify",),
    retry=FAST,
    timeout_s=120.0,
    optional=True,
)
def normalize(ctx: StageContext) -> None:
    project = ctx.project
    payload = ctx.payload

    if project.scale <= 0:
        project.scale = 1.0

    file_type = project.file_type
    if file_type == FileType.IMAGE and "source_bytes" in payload:
        data = payload["source_bytes"]
        size = _image_size(data)
        if size:
            width, height = size
            payload["image_width"] = width
            payload["image_height"] = height
            tile = int(ctx.options.get("tile_size", 1024))
            overlap = int(ctx.options.get("tile_overlap", 128))
            payload["tiles"] = _tile_grid(width, height, tile, overlap)
            project.meta["tiles"] = len(payload["tiles"])

    if "scale_hint" in payload:
        project.scale = float(payload["scale_hint"])

    project.meta["normalized"] = True


def _image_size(data: bytes) -> tuple[int, int] | None:
    """Leest afmetingen zonder beeldbibliotheek (PNG/JPEG/RIFF-header)."""
    try:
        if data.startswith(b"\x89PNG\r\n\x1a\n") and len(data) >= 24:
            return int.from_bytes(data[16:20], "big"), int.from_bytes(data[20:24], "big")
        if data[:4] in (b"RIFF",) and data[8:12] == b"WEBP" and len(data) >= 30:
            return int.from_bytes(data[26:28], "little"), int.from_bytes(data[28:30], "little")
        if data.startswith(b"\xff\xd8\xff"):
            i = 2
            while i + 9 < len(data):
                if data[i] != 0xFF:
                    i += 1
                    continue
                marker = data[i + 1]
                if marker in (0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7,
                              0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF):
                    return (
                        int.from_bytes(data[i + 7 : i + 9], "big"),
                        int.from_bytes(data[i + 5 : i + 7], "big"),
                    )
                if marker in (0xD8, 0x01) or 0xD0 <= marker <= 0xD7:
                    i += 2
                    continue
                seg = int.from_bytes(data[i + 2 : i + 4], "big")
                i += 2 + seg
    except Exception:  # noqa: BLE001 — header lezen is best effort
        return None
    return None


# ---------------------------------------------------------------------------
# 4a — Vector-extractie
# ---------------------------------------------------------------------------


@stage(
    id="extract_vector",
    name="Vector-extractie",
    description="Leest symbolen en ruimtes rechtstreeks uit DXF/IFC/PDF.",
    requires=("normalize",),
    retry=IO_RETRY,
    timeout_s=300.0,
    optional=True,
)
def extract_vector(ctx: StageContext) -> None:
    file_type = ctx.project.file_type
    if file_type not in {FileType.DXF, FileType.IFC, FileType.PDF}:
        ctx.skip(f"geen vectorbron ({file_type.value})")

    parser: Callable | None = {
        FileType.DXF: _lazy("packages.parsers.dxf", "parse_dxf"),
        FileType.IFC: _lazy("packages.parsers.ifc", "parse_ifc"),
        FileType.PDF: _lazy("packages.parsers.pdf", "parse_pdf"),
    }[file_type]

    parse = _require(parser, "extract_vector", f"parser voor {file_type.value}")
    data = ctx.load_source()
    result = parse(data)
    if isinstance(result, Project):
        _merge_project(ctx.project, result)
    else:
        raise PermanentStageError(
            f"parser voor {file_type.value} gaf geen Project terug", stage_id="extract_vector"
        )

    ctx.payload["vector_symbols"] = len(ctx.project.symbols)


# ---------------------------------------------------------------------------
# 4b — Detectie
# ---------------------------------------------------------------------------


@stage(
    id="detect_symbols",
    name="Symbooldetectie",
    description="Objectdetectie op rasterafbeeldingen (YOLO-achtig).",
    requires=("normalize",),
    retry=MODEL_RETRY,
    timeout_s=300.0,
    optional=True,
)
def detect_symbols(ctx: StageContext) -> None:
    if ctx.project.file_type not in {FileType.IMAGE, FileType.PDF}:
        ctx.skip(f"detectie niet van toepassing op {ctx.project.file_type.value}")

    detect = _require(
        _lazy("packages.vision.detector", "detect_symbols"),
        "detect_symbols",
        "detector",
    )
    data = ctx.load_source()
    tiled = ctx.options.get("detector_tiled", os.environ.get("DETECTOR_TILED") == "1")
    tiles = ctx.payload.get("tiles", []) if tiled else []
    found = detect(data, ctx.project, tiles=tiles) if tiles else detect(data, ctx.project)
    _absorb_symbols(ctx, found, source="detector")


# ---------------------------------------------------------------------------
# 4c — Legenda + OCR
# ---------------------------------------------------------------------------


@stage(
    id="legend_ocr",
    name="Legenda + OCR",
    description="Leest de legenda en bijschriften om symbolen te duiden.",
    requires=("normalize",),
    retry=MODEL_RETRY,
    timeout_s=300.0,
    optional=True,
)
def legend_ocr(ctx: StageContext) -> None:
    extract = _require(
        _lazy("packages.vision.ocr", "extract_legend"),
        "legend_ocr",
        "OCR (PaddleOCR)",
    )
    data = ctx.load_source()
    legend = extract(data)
    ctx.project.meta["legend"] = legend or []
    ctx.payload["legend_items"] = len(legend or [])


# ---------------------------------------------------------------------------
# 5 — VLM-redenering
# ---------------------------------------------------------------------------


@stage(
    id="vlm",
    name="VLM-redenering",
    description="Vision-Language-Model redeneert over de hele tekening.",
    requires=("extract_vector", "detect_symbols", "legend_ocr"),
    retry=MODEL_RETRY,
    timeout_s=240.0,
    optional=True,
    when=lambda ctx: bool(ctx.options.get("vlm_enabled", True)),
)
def vlm_reason(ctx: StageContext) -> None:
    reason = _require(
        _lazy("packages.vision.vlm", "reason"),
        "vlm",
        "VLM-client (vLLM/Qwen-VL)",
    )
    data = ctx.load_source()
    ctx.project = reason(ctx.project, data, ctx.project.meta.get("legend", []))


# ---------------------------------------------------------------------------
# 6 — Fusie
# ---------------------------------------------------------------------------


@stage(
    id="fuse",
    name="Fusie",
    description="Smelt de drie sporen samen, filtert ruis en wijst ruimtes toe.",
    requires=("vlm",),
    retry=FAST,
    timeout_s=60.0,
)
def fuse_stage(ctx: StageContext) -> None:
    raw = FusionConfig(**(ctx.options.get("fusion") or {}))
    _, stats = fuse(ctx.project, raw)
    ctx.payload["fusion"] = stats.as_dict()
    classifier = ctx.options.get("symbol_classifier", os.environ.get("SYMBOL_CLASSIFIER_PATH"))
    if classifier and ctx.project.file_type == FileType.IMAGE:
        try:
            from packages.vision.classifier import classify_candidates

            threshold = float(ctx.options.get("classifier_threshold", os.environ.get("SYMBOL_CLASSIFIER_THRESHOLD", "0.65")))
            ctx.project.symbols, summary = classify_candidates(
                ctx.load_source(), ctx.project.symbols, classifier, threshold, ctx.project.scale,
            )
            ctx.project.meta["symbol_classifier"] = {"status": "applied", **summary}
        except (OSError, ValueError, ImportError, KeyError) as error:
            logger.warning("Symbol classifier unavailable: %s", error)
            ctx.project.meta["symbol_classifier"] = {"status": "unavailable"}

    # De ruwe bytes zijn nu overbodig; checkpoint en geheugen blijven klein.
    ctx.forget_source()


# ---------------------------------------------------------------------------
# 7 — Validatie
# ---------------------------------------------------------------------------


@stage(
    id="validate",
    name="AREI-validatie",
    description="Voert de AREI/NEN 1010-regels uit en voegt fusiewaarschuwingen toe.",
    requires=("fuse",),
    retry=FAST,
    timeout_s=60.0,
)
def validate_stage(ctx: StageContext) -> None:
    from packages.rules import validate

    scope = str(ctx.options.get("rules_scope", "residential"))
    ctx.project = validate(ctx.project, scope=scope)

    # Waarschuwingen van vóór de fusie zijn weggegooid door de regelengine
    # (die herschrijft project.warnings); we voegen de onze opnieuw toe.
    fusion_stats = (ctx.project.meta or {}).get("fusion", {})
    dropped = int(fusion_stats.get("dropped_low_confidence", 0))
    if dropped:
        ctx.project.warnings.append(
            ValidationWarning(
                code="FUSION-LAGE-BETROUWBAARHEID",
                severity="warning",
                message=(
                    f"{dropped} symbool(symboolen) onder de betrouwbaarheidsdrempel "
                    "verwijderd — controleer handmatig of er iets mist."
                ),
                symbol_ids=fusion_stats.get("dropped_ids", [])[:50],
            )
        )
    if ctx.payload.get("classify_note"):
        ctx.project.warnings.append(
            ValidationWarning(
                code="FORMAAT-NIET-HERKEND",
                severity="warning",
                message="Het bestandsformaat kon niet herkend worden; "
                "alleen stappen die met de ruwe bytes overweg konden zijn uitgevoerd.",
            )
        )


# ---------------------------------------------------------------------------
# 8 — Materialen
# ---------------------------------------------------------------------------


@stage(
    id="materials",
    name="Materiaalengine",
    description="Zet symbolen om in een geprijsde materiaallijst.",
    requires=("validate",),
    retry=FAST,
    timeout_s=60.0,
)
def materials_stage(ctx: StageContext) -> None:
    from packages.materials import compute_materials

    ctx.project = compute_materials(ctx.project)
    ctx.payload["material_lines"] = len(ctx.project.materials)


# ---------------------------------------------------------------------------
# 9 — Output
# ---------------------------------------------------------------------------


@stage(
    id="output",
    name="Output",
    description="Maakt het resultaat exportklaar (totalen, samenvatting).",
    requires=("materials",),
    retry=FAST,
    timeout_s=120.0,
)
def output_stage(ctx: StageContext) -> None:
    project = ctx.project
    total = sum(m.total_price or 0.0 for m in project.materials)
    errors = [w for w in project.warnings if w.severity == "error"]

    # De status (processing/done/failed) is de verantwoordelijkheid van de
    # worker die de run in de database wegschrijft; deze stap blijft puur.
    project.meta["output"] = {
        "symbols": len(project.symbols),
        "rooms": len(project.rooms),
        "materials": len(project.materials),
        "warnings": len(project.warnings),
        "errors": len(errors),
        "total_price": round(total, 2),
        "ready_for_review": not errors,
    }
    ctx.payload["total_price"] = round(total, 2)

    exporter = ctx.options.get("exporter")
    if callable(exporter):
        exporter(project)


# ---------------------------------------------------------------------------
# Samenstellen
# ---------------------------------------------------------------------------

DEFAULT_STAGES: list[Stage] = [
    ingest,
    classify,
    normalize,
    extract_vector,
    detect_symbols,
    legend_ocr,
    vlm_reason,
    fuse_stage,
    validate_stage,
    materials_stage,
    output_stage,
]


def build_default_pipeline() -> "Pipeline":  # noqa: F821 — type only
    from packages.pipeline.engine import Pipeline

    return Pipeline(
        name="analyse",
        description="Tekening → symbolen → AREI-validatie → materiaallijst",
        stages=list(DEFAULT_STAGES),
    )


def _absorb_symbols(ctx: StageContext, found: Any, *, source: str) -> None:
    """Voegt gevonden symbolen toe en markeert hun herkomst."""
    if not found:
        return
    added = 0
    for item in found:
        if not isinstance(item, Symbol):
            continue
        try:
            item.source = SourceType(source)
        except (ValueError, TypeError):
            item.source = SourceType.DETECTOR
        item.attributes.setdefault("sources", [str(source)])
        ctx.project.symbols.append(item)
        added += 1
    ctx.payload[f"symbols_{source}"] = added

"""
tests/pipeline/test_stages.py — de elf stappen uit het README.

Twee scenario's:
  * **degraded**: de parser-/visionimplementaties zijn verborgen (`_lazy`
    geeft niks terug) → die stappen slaan over en de run levert alsnog een
    gevalideerd project op;
  * **volledig**: met een echte (of ingeplugde) parser → symbolen worden
    gevonden, aan ruimtes gekoppeld, AREI-waarschuwingen gegeven en materialen
    berekend.

Draaien:
    uv run pytest tests/pipeline/test_stages.py -v
"""

from __future__ import annotations

import pytest

from packages.pipeline import (
    EventBus,
    CollectingHandler,
    EventType,
    InMemoryCheckpointStore,
    InMemoryMetrics,
    NO_RETRY,
    PipelineFailed,
    PipelineOptions,
    StageContext,
    StageState,
    RunState,
    build_default_pipeline,
    detect_file_type,
)
from packages.pipeline import stages as stages_mod
from packages.schema import FileType, Project, Room, Symbol, SymbolType

DXF_BYTES = b"0\nSECTION\n2\nHEADER\n0\nENDSEC\n0\nEOF\n"
ROOM = Room(name="Leefruimte", polygon=[[0, 0], [6000, 0], [6000, 4000], [0, 4000]])


def make_ctx(payload: dict | None = None, options: PipelineOptions | None = None) -> StageContext:
    return StageContext(
        project=Project(id="p-stages"),
        payload=payload if payload is not None else {"source_bytes": DXF_BYTES,
                                                     "filename": "plattegrond.dxf"},
        options=options
        or PipelineOptions(default_retry=NO_RETRY, default_timeout_s=30.0),
        events=EventBus(),
        metrics=InMemoryMetrics(),
    )


# ---------------------------------------------------------------------------
# Classificatie
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "data,expected",
    [
        (b"%PDF-1.7\n", FileType.PDF),
        (b"ISO-10303-21;\nHEADER;", FileType.IFC),
        (b"AutoCAD Binary DXF\r\n\x1a\x00", FileType.DXF),
        (DXF_BYTES, FileType.DXF),
        (b"\x89PNG\r\n\x1a\n" + b"\x00" * 40, FileType.IMAGE),
        (b"\xff\xd8\xff\xe0\x00\x10JFIF" + b"\x00" * 40, FileType.IMAGE),
        (b"II*\x00" + b"\x00" * 40, FileType.IMAGE),
        (b"onbekende rommel", FileType.UNKNOWN),
    ],
)
def test_detect_file_type_by_content(data, expected):
    assert detect_file_type(data) == expected


def test_detect_file_type_falls_back_to_extension():
    assert detect_file_type(b"onbekende rommel", "tekening.dxf") == FileType.DXF
    assert detect_file_type(b"onbekende rommel", "foto.png") == FileType.IMAGE


def test_inhoud_wint_van_extensie():
    """Een .png die eigenlijk een PDF is, wordt als PDF herkend."""
    assert detect_file_type(b"%PDF-1.4", "screenshot.png") == FileType.PDF


# ---------------------------------------------------------------------------
# Normalisatie
# ---------------------------------------------------------------------------


def test_tile_grid_covers_image_with_overlap():
    normalize = next(s for s in stages_mod.DEFAULT_STAGES if s.id == "normalize")
    ctx = make_ctx(
        payload={
            "source_bytes": b"\x89PNG\r\n\x1a\n" + (0).to_bytes(4, "big") + b"IHDR"
            + (4000).to_bytes(4, "big") + (2000).to_bytes(4, "big") + b"\x00" * 8,
            "filename": "scan.png",
        }
    )
    ctx.project.file_type = FileType.IMAGE
    normalize.run(ctx)

    tiles = ctx.payload["tiles"]
    assert tiles, "er moeten tegels gegenereerd worden"
    assert ctx.payload["image_width"] == 4000
    assert ctx.payload["image_height"] == 2000
    assert ctx.project.meta["tiles"] == len(tiles)
    # elk vlak valt binnen de afbeelding
    assert all(t["x"] + t["w"] <= 4000 and t["y"] + t["h"] <= 2000 for t in tiles)


def test_normalize_bewaart_scale_hint():
    normalize = next(s for s in stages_mod.DEFAULT_STAGES if s.id == "normalize")
    ctx = make_ctx(payload={"source_bytes": DXF_BYTES, "filename": "a.dxf",
                            "scale_hint": 50.0})
    normalize.run(ctx)
    assert ctx.project.scale == 50.0


# ---------------------------------------------------------------------------
# Ingest
# ---------------------------------------------------------------------------


def test_ingest_berekent_sha256():
    ingest = next(s for s in stages_mod.DEFAULT_STAGES if s.id == "ingest")
    ctx = make_ctx()
    ingest.run(ctx)
    assert ctx.payload["source_size"] == len(DXF_BYTES)
    assert len(ctx.payload["source_sha256"]) == 64
    assert ctx.project.meta["source"]["sha256"] == ctx.payload["source_sha256"]


def test_ingest_met_lege_file_is_permanente_fout():
    ingest = next(s for s in stages_mod.DEFAULT_STAGES if s.id == "ingest")
    ctx = make_ctx(payload={"source_bytes": b"", "filename": "leeg.dxf"})
    from packages.pipeline import PermanentStageError

    with pytest.raises(PermanentStageError):
        ingest.run(ctx)


# ---------------------------------------------------------------------------
# Volledige run — degraded (implementaties verborgen)
# ---------------------------------------------------------------------------


@pytest.fixture
def no_implementations(monkeypatch):
    """
    Verbergt alle parser- en visionimplementaties.

    packages/parsers en packages/vision bestaan inmiddels wel; dit fixture
    boots de wereld van vóór na zodat het degradatiecontract blijft getest:
    ontbrekende implementatie → overslaan, tenzij `strict`.
    """
    monkeypatch.setattr(stages_mod, "_lazy", lambda module, attr: None)


def test_volledige_run_zonder_parsers_levert_resultaat_op(no_implementations):
    pipeline = build_default_pipeline()
    pipeline.validate()

    ctx = make_ctx(payload={"source_bytes": DXF_BYTES, "filename": "plan.dxf"})
    run = pipeline.run(ctx)

    assert run.state == RunState.SUCCEEDED
    assert run.progress == 1.0

    states = {s.stage_id: s.state for s in run.stages}
    # verplichte stappen zijn klaar
    for required in ("ingest", "classify", "fuse", "validate", "materials", "output"):
        assert states[required] == StageState.SUCCEEDED, required
    # ontbrekende implementaties slaan netjes over
    for missing in ("extract_vector", "legend_ocr", "vlm"):
        assert states[missing] == StageState.SKIPPED, missing
        assert "niet geïmplementeerd" in run.stage(missing).error

    assert ctx.project.file_type == FileType.DXF


def test_gefaalde_optionele_stap_gaat_niet_mee_de_grond_in():
    """vLLM dat down is mag de analyse niet platleggen (niet-strict)."""
    pipeline = build_default_pipeline()
    ctx = make_ctx()
    run = pipeline.run(ctx)
    assert run.state == RunState.SUCCEEDED


def test_strict_mode_wel_faal_de_run(no_implementations):
    """CI wil horen dat de parser ontbreekt: strict zet een overslaande stap
    met `NotImplementedStage` om in een gefaalde run."""
    pipeline = build_default_pipeline()
    ctx = make_ctx(options=PipelineOptions(strict=True, default_retry=NO_RETRY,
                                           default_timeout_s=30.0))
    with pytest.raises(PipelineFailed):
        pipeline.run(ctx)


def test_volledige_run_met_echte_pakketten():
    """
    De wereld van nu: packages/parsers en packages/vision zijn aanwezig.

    Vector-extractie draait dus écht mee en geen enkele stap blijft steken op
    "niet geïmplementeerd" — anders zouden we de degradatieconstructie als
    excuus gebruiken om een kapotte integratie te missen.
    """
    pipeline = build_default_pipeline()
    ctx = make_ctx()
    run = pipeline.run(ctx)

    assert run.state == RunState.SUCCEEDED
    states = {s.stage_id: s.state for s in run.stages}
    assert states["extract_vector"] == StageState.SUCCEEDED
    for st in run.stages:
        if st.error:
            assert "niet geïmplementeerd" not in st.error, st.stage_id


# ---------------------------------------------------------------------------
# Volledige run — met een ingeplugde parser
# ---------------------------------------------------------------------------


def fake_parser(data: bytes) -> Project:
    """Simuleert packages.parsers.dxf.parse_dxf (contract uit stages.py)."""
    symbols = [
        Symbol(type=SymbolType.WANDCONTACTDOOS, x=1000, y=1000, circuit="G1"),
        Symbol(type=SymbolType.WANDCONTACTDOOS, x=1400, y=1000, circuit="G1"),
        Symbol(type=SymbolType.LICHTPUNT, x=3000, y=2000, circuit="L1"),
        # detector-ruis: zou gefilterd moeten worden
        Symbol(type=SymbolType.WANDCONTACTDOOS, x=5000, y=3000,
               confidence=0.1, source="detector"),
    ]
    # De vierde komt niet van de parser in de praktijk; we voegen hem toe om
    # te tonen dat fusie ook binnen één spoor ruis verwijdert.
    return Project(symbols=symbols, rooms=[ROOM], scale=1.0)


@pytest.fixture
def plugged_parser(monkeypatch):
    def fake_lazy(module: str, attr: str):
        if module == "packages.parsers.dxf" and attr == "parse_dxf":
            return fake_parser
        return None

    monkeypatch.setattr(stages_mod, "_lazy", fake_lazy)


def test_volledige_run_met_parser(plugged_parser):
    pipeline = build_default_pipeline()
    ctx = make_ctx()
    collector = ctx.events.subscribe(CollectingHandler())
    run = pipeline.run(ctx)

    assert run.state == RunState.SUCCEEDED
    states = {s.stage_id: s.state for s in run.stages}
    assert states["extract_vector"] == StageState.SUCCEEDED
    assert states["detect_symbols"] == StageState.SKIPPED  # geen detector
    assert states["vlm"] == StageState.SKIPPED

    project = ctx.project
    # 4 ingevoerd, 1 als ruis gefilterd → 3 symbolen
    assert len(project.symbols) == 3
    assert project.meta["fusion"]["dropped_low_confidence"] == 1

    # symbolen in de ruimte gekoppeld
    assert all(s.room_id == ROOM.id for s in project.symbols)

    # AREI-waarschuwing: 2 WCD's op één groep is prima, maar we controleren
    # dat de regelengine gedraaid heeft (warnings-lijst bestaat en gevuld kan zijn)
    assert isinstance(project.warnings, list)

    # materialen + output
    assert project.materials, "er moeten materialen berekend zijn"
    assert project.meta["output"]["symbols"] == 3
    assert project.meta["output"]["total_price"] >= 0
    assert ctx.payload["material_lines"] == len(project.materials)

    # laag-betrouwbaarheidswaarschuwing is toegevoegd na de regelengine
    codes = {w.code for w in project.warnings}
    assert "FUSION-LAGE-BETROUWBAARHEID" in codes

    assert collector.stages[-1] == "output"


def test_arei_waarschuwingen_komen_in_resultaat(plugged_parser):
    def parser_met_negen_wcds(data: bytes) -> Project:
        return Project(
            rooms=[ROOM],
            symbols=[
                # 400 mm hart-op-hart: realistische muurafstand en ruim buiten
                # de fusiedrempel van 150 mm, dus dit blijven 9 losse WCD's.
                Symbol(type=SymbolType.WANDCONTACTDOOS, x=1000 + i * 400, y=1000,
                       circuit="G1")
                for i in range(9)
            ],
        )

    monkey = pytest.MonkeyPatch()
    monkey.setattr(
        stages_mod, "_lazy",
        lambda m, a: parser_met_negen_wcds if a == "parse_dxf" else None,
    )
    try:
        pipeline = build_default_pipeline()
        ctx = make_ctx()
        pipeline.run(ctx)
        codes = {w.code for w in ctx.project.warnings}
        assert "AREI-4.4.2-WCD" in codes
    finally:
        monkey.undo()


# ---------------------------------------------------------------------------
# Checkpointing over de hele keten
# ---------------------------------------------------------------------------


def test_run_is_checkpointed_en_hervatbaar():
    store = InMemoryCheckpointStore()
    pipeline = build_default_pipeline()
    ctx = make_ctx()

    run = pipeline.run(ctx, store=store)
    saved = store.load(run.run_id)
    assert saved is not None
    assert saved.state == RunState.SUCCEEDED
    assert saved.project_snapshot["meta"]["output"]["symbols"] == 0

    # Hervatten van een geslaagde run mag niet.
    from packages.pipeline import PipelineError

    with pytest.raises(PipelineError, match="al geslaagd"):
        pipeline.run(make_ctx(), store=store, resume=run.run_id)

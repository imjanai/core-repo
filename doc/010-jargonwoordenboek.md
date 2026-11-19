# 010 — Jargonwoordenboek

Alfabetische lijst van termen die in dit project voorkomen, geschreven voor wie niet uit de elektrotechniek én niet uit ML komt.

---

## A

**Agent** — Een LLM dat niet alleen tekst genereert maar tools mag aanroepen (bv. `place_symbol`). Zie [055-mcp-server](055-mcp-server.md).

**Alembic** — Migratietool voor SQLAlchemy: houdt de databasestructuur bij in versiebeheer. Zie [075](075-fastapi-sqlalchemy-alembic.md).

**AVG / GDPR** — Wet op gegevensbescherming. Relevant omdat tekeningen persoonsgegevens kunnen bevatten (namen, adressen in titelblokken). Zie [084](084-veiligheid-en-avg.md).

## B

**Backward compatible** — Een wijziging die bestaande data of clients niet breekt. Zie [027](027-versiebeheer-van-het-schema.md).

**Bounding box** — Rechthoek rond een herkend object, met coördinaten en confidence. Zie [036](036-stap-4b-detectie.md).

**Broker** — Het tussenstation dat taken verdeelt (hier: Redis). Zie [077](077-redis-en-celery.md).

## C

**Celery** — Python-taakqueue. Doe zware dingen asynchronois zodat de API snel blijft. Zie [054](054-worker-celery.md).

**COCO-formaat** — Standaard indeling voor gelabelde objectdetectiedata (JSON + afbeeldingen). Zie [066](066-datasetstructuur.md).

**Confidence** — Het cijfer (0–1) dat zegt hoe zeker een waarneming is. In `Symbol.confidence`. Zie [023](023-symbol-model.md).

**Conventional Commits** — Gestandaardiseerde commitberichten (`feat:`, `fix:`, `docs:`). Zie [094](094-conventional-commits.md).

## D

**DVC** — Data Version Control: versiebeheer voor datasets, net als git maar voor grote bestanden. Zie [066](066-datasetstructuur.md).

**DXF** — Drawing Exchange Format, het open CAD-formaat van AutoCAD. Tekstgebaseerd, machineleesbaar. Zie [042](042-parsers-dxf.md).

## E

**ETIM** — Europees classificatiesysteem voor bouwproducten; koppelt een artikel aan een gestandaardiseerde productclassificatie. Gebruikt in de materiaalengine.

**Evaluatieset** — Vaste set tekeningen met gouden antwoorden, nooit trainingsdata, altijd de promoveerbaarheidsmaatstaf. Zie [068](068-evaluatieset.md).

**ezdxf** — Python-bibliotheek om DXF te lezen en te schrijven. Zie [042](042-parsers-dxf.md).

## F

**Fine-tuning** — Een voorgebruik model verder trainen op eigen data, zodat het het eigen domein leert. Zie [063](063-finetuning-lora.md).

**Fusie** — Het samenbrengen van waarnemingen uit meerdere bronnen tot één `Project`. Zie [039](039-stap-6-fusie.md).

## G

**Groep** — Een zekeringkring in een woning; in het model het veld `Symbol.circuit` (bv. `"G3"`). Zie [023](023-symbol-model.md).

## I

**IFC** — Industry Foundation Classes, het open BIM-formaat. Zie [043](043-parsers-ifc.md).

**Ingest** — De eerste stap: binnenhalen en vastleggen van een upload. Zie [032](032-stap-1-ingest.md).

## K

**Konva** — JavaScript-tekenbibliotheek voor interactieve overlays op de frontend (symbolen bewerken). Zie [078](078-frontend-stack.md).

## L

**Legenda** — Het blok op een tekening dat uitlegt welk symbool wat betekent. De belangrijkste interpretatiebron voor het VLM. Zie [037](037-stap-4c-tekst-en-legenda.md).

**LoRA / QLoRA** — Techniek om een groot model efficiënt bij te trainen met weinig extra geheugen (trainbare matrices met lage rang). Zie [063](063-finetuning-lora.md).

## M

**mAP** — mean Average Precision, de hoofdmaatstaf voor objectdetectiekwaliteit. Zie [069](069-metrics.md).

**MCP** — Model Context Protocol: open standaard waarmee een LLM tools van een externe server aanroept. Zie [055](055-mcp-server.md).

**MinIO** — S3-compatibele objectopslag die je zelf host; in docker-compose de lokale vervanger van AWS S3. Zie [060](060-opslag-en-s3.md).

## N

**NEN 1010** — Nederlandse norm voor elektrische installaties in gebouwen: dimensionering, beveiliging, belasting. Zie [047](047-rules-nen-1010.md).

## O

**OCR** — Optical Character Recognition: tekst uit afbeeldingen halen (hier: PaddleOCR). Zie [037](037-stap-4c-tekst-en-legenda.md).

## P

**Pipeline** — De reeks stappen van upload tot output, opgesplitst in Celery-taken. Zie [031](031-pipeline-overview.md).

**Preprocessing** — Alles wat je doet vóór de analyse: converteren, tegelen, schaal bepalen. Zie [034](034-stap-3-normalisatie.md).

**Prompt** — De invoer die je aan een taalmodel geeft. Bij VLM-redeneren vaak een afbeelding + instructie. Zie [046](046-vision-vlm-client.md).

## Q

**Qwen-VL** — Het visie-taalmodel dat als basis dient voor het eigen model. Zie [062](062-basismodel-qwen-vl.md).

## R

**Raster / rasterafbeelding** — Pixelbestand (PNG, JPEG, gescande PDF) zonder vectorinformatie. Zie [016](016-hybride-aanpak.md).

**Row-level security (RLS)** — Databasefunctie die per rij controleert of de gebruiker die mag zien; de basis van multi-tenancy. Zie [086](086-multitenant-security.md).

**RT-DETR** — Detectiemodel van de YOLO-familie, transformer-gebaseerd. Zie [065](065-symbooldetectie.md).

## S

**SAHI** — Slicing Assisted Hyperparameter Inference: snijdt grote afbeeldingen in tegels zodat kleine symbolen niet verloren gaan. Zie [036](036-stap-4b-detectie.md).

**Scale / schaal** — mm per tekeningeenheid. Zonder schaal zijn coördinaten betekenisloos. Veld `Project.scale`. Zie [022](022-project-model.md).

**Source** — Herkomst van een waarneming: `vector | detector | vlm | human`. Veld `Symbol.source`. Zie [023](023-symbol-model.md).

## T

**Tiling** — Zie SAHI.

**Type hint / mypy** — Statisch typen in Python; `uv run mypy .` controleert. Zie [082](082-lint-types-format.md).

## U

**uv** — Snelle Python-packagemanager en workspace-tool; vervangt pip/poetry hier. Zie [074](074-python-en-uv.md).

## V

**Vector** — Tekening opgebouwd uit wiskundige lijnen/curves; exact en schaalbaar. Tegenhanger van raster.

**Vector-PDF** — PDF met vectordata (uit CAD geëxporteerd); bruikbaarder dan gescand PDF.

**VLM** — Vision-Language Model: begrijpt zowel afbeeldingen als tekst. Hier Qwen-VL. Zie [062](062-basismodel-qwen-vl.md).

**vLLM** — Snelle inference-server voor LLM's met OpenAI-compatibele API. Zie [071](071-model-serving-vllm.md).

**Validation** — Het van nature controleren van data (Pydantic) versus het controleren op normregels (`rules`). Zie [028](028-validatie-in-het-schema.md).

## W

**WCD** — Wandcontactdoos; `SymbolType.WCD = "wandcontactdoos"`. Zie [025](025-symboltype-enum.md).

**Webhook** — Automatische aanroep van jouw API door een externe partij bij een gebeurtenis.

## Y

**YOLO** — "You Only Look Once", een snel objectdetectiemodel van Ultralytics. Zie [065](065-symbooldetectie.md).

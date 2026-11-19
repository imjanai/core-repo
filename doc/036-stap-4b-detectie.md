# 036 — Stap 4b: Detectie op raster

## Wanneer

Alleen bij rasterinvoer (gescande PDF's, foto's). Bij DXF/IFC optioneel als tegencontrole.

## Wat er gebeurt

Per tegel loopt een objectdetectiemodel (YOLO of RT-DETR) en levert bounding boxes met een klasse en een confidence.

```python
class Detection(BaseModel):
    klasse: str            # SymbolType-waarde
    bbox: tuple[float, float, float, float]   # x1, y1, x2, y2 in tegelcoördinaten
    confidence: float
    tegel_id: int
```

## De tiling-problematiek

Een installatietekening is groot; symbolen zijn klein. Zonder tegelen:

- wordt een A0-tekening geschaald naar 640 × 640,
- is een WCD 4 × 4 pixels,
- ziet het model niets.

SAHI snijdt in overlappende tegels (bv. 1024 px, 20% overlap), draait detectie per tegel, en projecteert de boxes terug naar originele coördinaten. Daarna volgt **non-maximum suppression** over alle tegels heen: hetzelfde symbool dat op twee tegels voorkomt, wordt één waarneming.

## Het NMS-vraagstuk

Standaard NMS werkt op overlap (IoU). Bij tekeningen gaat het soms mis:

- symbolen staan dicht op elkaar (WCD naast schakelaar) — te agressieve NMS gooit er één weg.
- hetzelfde symbool verschijnt op twee tegels met iets verschoven boxes — te lakse NMS telt dubbel.

**Oplossing:** NMS per klasse, met een iets hogere IoU-drempel dan standaard, plus een test op de evaluatieset met handmatig getelde aantallen als maatstaf. Zie [069-metrics](069-metrics.md).

## Waarom niet alleen VLM voor detectie

Een VLM kan "ik zie hier ongeveer twaalf stopcontacten" zeggen, maar:

- het is traag (seconden per tegel in plaats van milliseconden),
- het telt onbetrouwbaar,
- het geeft geen strakke bounding boxes voor de review-UI.

Een detectiemodel is gemaakt voor precies dit: snel, structureel, meetbaar in mAP. Het VLM komt in stap 5 voor wat een detector niet kan: context en interpretatie.

## Het model trainen

Zie [064-train-detector-script](064-train-detector-script.md) voor `ml/train_detector.py` en [065-symbooldetectie](065-symbooldetectie.md) voor de keuze tussen YOLO en RT-DETR.

## Drempelkeuze

De confidence-drempel bepaalt het precisierecall-evenwicht. Te laag: veel valse positieven in de materiaallijst (dure fout, de klant bestelt overbodig materiaal). Te hoog: gemiste punten (ook duur: tekort op de bouw).

**Aanbeveling:** begin conservatief (hoge precisie) en laat de review-UI "zeker gemist" tonen als aparte lijst. Liever een vakman die 5 kandidaten bevestigt dan 5 ontbrekende stopcontacten.

## Output

```python
class DetectieOutput(BaseModel):
    project_id: str
    pagina: int
    detections: list[Detection]
```

## Wat er nu bestaat

Niets. [packages/vision](../packages/vision) is leeg.

# 097 — Prestaties en schaal

## Waar de tijd heen gaat

Terugkijkend op de pipeline ([031](031-pipeline-overview.md)): de VLM-stappen zijn de bottleneck, gevolgd door detectie en OCR. Alles andere is verwaarloosbaar.

| Stap | Bron | Optimalisatie |
|---|---|---|
| 5 VLM | GPU-tokens | Crops i.p.v. pagina's, caching, batching |
| 4b detectie | GPU | Tiling-efficiëntie, TensorRT-export |
| 4c OCR | GPU/CPU | Alleen tekstgebieden, niet de hele pagina |
| 3 normalisatie | I/O + CPU | Parallelle rendering |
| overig | — | Niet optimaliseren |

## De volgorde van optimalisatie

1. **Meten vóór optimaliseren.** Zonder timings gok je. Zie [080-observability](080-observability.md).
2. **Minder werk vóór sneller werk.** Crops in plaats van hele pagina's is een grotere winst dan een sneller model.
3. **Parallelle sporen.** 4a, 4b en 4c naast elkaar — de klok is de langzaamste tak.
4. **Caching.** Dezelfde tekening opnieuw analyseren moet gedeeltelijk gratis zijn.
5. **Pas daarna:** hardware, modellen, exports.

## Begrenzingen

| Begrenzing | Waarde | Waarom |
|---|---|---|
| Upload-grootte | 100 MB | Voorkomt misbruik |
| VLM-timeout | 60 s per aanroep | Voorkomt hangende taken |
| Aanroepen per tekening | bv. 50 crops | Kostencap |
| Tegels per pagina | afhankelijk van formaat | Geheugen |

Elke begrenzing heeft een zichtbare melding, niet een stille afkap.

## Schaalmodellen

### Kortetermijn (Fase 1)

- Eén GPU, één worker-pool.
- Verticale schaal: grotere GPU bij meer aanvragen.
- Vereenvoudiging: vectorpad eerst — geen GPU nodig.

### Middellange termijn (Fase 2–3)

- Meerdere workers op één GPU (batching helpt).
- Aparte queues per taakzwaarte.
- Autoscaling op queue-lengte.

### Langetermijn (Fase 5)

- Multi-regio (EU), als de klantkring groeit.
- Model-versies per tenant mogelijk (premium).

## Kosten van snelheid

| Maatregel | Kosten |
|---|---|
| Grotere GPU | Meer per uur |
| Meerdere replicas | Lineair meer |
| Caching | Opslag, klein |
| Kleiner model | Minder kwaliteit |

Zie [098-kostenraming](098-kostenraming.md).

## Wat er nu bestaat

Niets om te meten. Er is geen pipeline.

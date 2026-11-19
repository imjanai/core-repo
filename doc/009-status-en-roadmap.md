# 009 — Status en roadmap

## De zes fases

Uit de README, in volgorde met de afhankelijkheden die de volgorde verklaren.

### Fase 0 — Fundering 📍 huidige fase

> Dataverzameling, projectmodel, evaluatieset, baseline.

| Onderdeel | Status |
|---|---|
| Projectmodel (`packages/schema`) | ✅ grotendeels |
| Evaluatieset (±50 tekeningen met gouden antwoorden) | 📋 |
| Baseline-metrics | 📋 |
| Datasetverzameling en labeling | 📋 |

**Waarom eerst:** zonder evaluatieset kun je niet zien of een model beter is. Alles wat daarop volgt meet je anders blind ([068](068-evaluatieset.md), principe 6 uit [006](006-ontwerpprincipes.md)).

---

### Fase 1 — MVP 📋

> Upload → analyse → materiaallijst, review-UI, 3–5 pilotklanten.

**Scope:** één pad goed (waarschijnlijk DXF/vector-PDF, de betrouwbare route), materiaallijst als output, review om te corrigeren.

**Niet in scope:** tekenen via MCP, normvalidatie, integraties.

**Succescriterium:** pilotklanten gebruiken wekelijks; percentage tekeningen zonder correctie wordt gemeten ([069-metrics](069-metrics.md)).

---

### Fase 2 — Feedbackloop 📋

> Correcties als trainingsdata, maandelijkse hertraining, prijskoppeling.

**Wat dit verandert:** het systeem stopt met stilstaan. Elke maand een nieuw model dat op de evaluatieset niet mag verslechteren.

**Afhankelijk van:** voldoende correctievolume; te weinig data maakt hertrainen zinloos. Zie [070-feedbackloop](070-feedbackloop.md).

---

### Fase 3 — Tekenen via MCP 📋

> Agent die schema's en installatietekeningen opbouwt.

**Wat:** de MCP-server ([055](055-mcp-server.md)) met tools `create_drawing`, `place_symbol`, `draw_cable`, `add_dimension`, `export_dxf`.

**Waarom nu en niet eerder:** tekenen vraagt om een betrouwbaar begrip van het domein. Eerst lezen, dan schrijven.

---

### Fase 4 — Ontwerp en validatie 📋

> NEN 1010-regelengine, groepsindeling, kabeldimensionering.

**Wat:** de regelset groeit van één regel naar een volwaardige engine; kabeldimensionering koppelt belasting → doorsnede.

**Kritiek:** grenswaarden komen uit de geldende norm en worden door een domeinexpert beheerd, niet door het model bepaald ([047](047-rules-nen-1010.md)).

---

### Fase 5 — Schaal en integraties 📋

> ERP/offerte, BIM/IFC, mobiele opname-app, keuringsrapporten.

Bredere markt, meer kanalen, meer compliance. Zie ook de doelgroepen ([004](004-doelgroepen.md)).

---

## Afhankelijkheden tussen fases

```
Fase 0 (meten)
   └─► Fase 1 (waarde leveren)
          └─► Fase 2 (leren van correcties)
                 ├─► Fase 3 (schrijven met begrip)
                 │      └─► Fase 5 (integraties)
                 └─► Fase 4 (regels aanscherpen)
```

Fase 3 en 4 zijn parallel mogelijk; Fase 5 wacht op beide.

## Kritieke paden

1. **Evaluatieset vóór modelwerk.** Zonder is elke verbetering een mening.
2. **Pilotklanten vóór breedte.** Eén goed werkend pad weegt zwaarder dan vijf halfwerkende.
3. **Review-UI vóór frequente hertraining.** Zonder correctiedata is hertrainen gokken.
4. **Stabiele API vóór integraties.** Externe partijen migreren traag.

## Waar deze repo zich nu bevindt

Tussen Fase 0-begin en Fase 1-voorbereiding: het datamodel staat, de regelengine is begonnen, de afhankelijkheden zijn vastgelegd in [pyproject.toml](../pyproject.toml), en de scripts/apps zijn nog leeg. Zie [002-project-overview](002-project-overview.md#huidige-status-van-de-repo).

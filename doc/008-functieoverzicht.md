# 008 — Functieoverzicht en status

## De zeven functies

Uit de README, met per functie wat het technisch vraagt en wat ervoor gebouwd moet worden.

### 1. Tekeninganalyse — 📋

**Wat:** Herkent symbolen, ruimtes, groepen en legenda's in DXF, IFC, vector-PDF en rasterafbeeldingen.

**Techniek:** drie sporen (vector-parser, detector, VLM) die samenkomen in één `Project`.

**Bouwsteen die al staat:** [packages/schema](../packages/schema) — het doelmodel van de analyse.

**Nodig:** parsers ([042](042-parsers-dxf.md), [043](043-parsers-ifc.md), [044](044-parsers-pdf.md)), detector ([045](045-vision-detector.md)), VLM-client ([046](046-vision-vlm-client.md)), fusie ([039](039-stap-6-fusie.md)).

---

### 2. Materiaallijsten — 📋

**Wat:** Zet symbolen om naar artikelen, hoeveelheden en prijzen (ETIM-gebaseerd).

**Techniek:** pure functie `Project → list[MaterialLine]`; groeperen per artikelnummer, optellen per ruimte of groep.

**Afhankelijk van:** betrouwbare analyse (functie 1) en een artikelcatalogus.

**Nodig:** [packages/materials](../packages/materials) — zie [048](048-materials-engine.md).

---

### 3. Tekenen via MCP — 📋

**Wat:** AI plaatst symbolen, trekt kabelroutes en exporteert DXF/PDF.

**Techniek:** een MCP-server met vijf tools die een agent mag aanroepen; elke tool geeft een `Project`-wijziging terug zodat alles controleerbaar en terug te draaien is.

**Bouwsteen die al staat:** `mcp` staat in [pyproject.toml](../pyproject.toml).

**Nodig:** [apps/mcp_server](../apps/mcp_server) — zie [055](055-mcp-server.md), [056](056-mcp-tools.md).

---

### 4. Normvalidatie — 🚧

**Wat:** Controleert het ontwerp op regels (o.a. NEN 1010).

**Techniek:** een lijst van `Rule`-objecten, elk met een `check: Callable[[Project], list[str]]`.

**Status:** de eerste regel bestaat: `max_wcd_per_group` (maximaal 8 WCD's per groep) in [packages/rules/rules.py](../packages/rules/rules.py). Zie [047](047-rules-nen-1010.md).

---

### 5. Offertegeneratie — 📋

**Wat:** Materiaal, arbeid en marge naar PDF-offerte.

**Techniek:** Jinja2-template → WeasyPrint → PDF; openpyxl voor de Excel-variant.

**Afhankelijk van:** materiaallijsten (functie 2) en arbeidstypen per symbool.

---

### 6. Review-UI — 📋

**Wat:** Elektricien controleert en corrigeert; correcties verbeteren het model.

**Techniek:** tekening tonen met overlappende symbolen (PDF.js/OpenSeadragon + Konva), per symbool bevestigen/wijzigen/verwijderen, `POST /corrections`.

**Waarom kritiek:** zonder review geen correctiedata, zonder correctiedata geen beter model. Zie [070-feedbackloop](070-feedbackloop.md).

**Let op:** [apps/review/README.md](../apps/review/README.md) zegt "Security Reviewer" — dat lijkt een placeholder en moet nog worden bijgesteld naar de bedoelde review-UI. Zie [057](057-review-app.md).

---

### 7. Integraties — 📋

**Wat:** Offerte-/ERP-software, groothandel-feeds, BIM.

**Techniek:** stabiele API-contracten + webhooks; BIM via IFC in- en uitvoer.

**Wacht op:** Fase 5, en op een stabiele API ([018](018-api-grenzen.md)).

---

## Statuslegenda

| Symbool | Betekenis |
|---|---|
| ✅ | Klaar |
| 🚧 | In ontwikkeling |
| 📋 | Gepland |

## Samenvatting

| # | Functie | Status | Kritieke afhankelijkheid |
|---|---|---|---|
| 1 | Tekeninganalyse | 📋 | Schema (✅) |
| 2 | Materiaallijsten | 📋 | Analyse |
| 3 | Tekenen via MCP | 📋 | Schema + drawing-engine |
| 4 | Normvalidatie | 🚧 | Schema (✅) |
| 5 | Offertegeneratie | 📋 | Materiaallijsten |
| 6 | Review-UI | 📋 | Analyse |
| 7 | Integraties | 📋 | Stabiele API |

De afhankelijkheidsketen is duidelijk: **alles hangt aan de analyse**, en die hangt aan de evaluatieset (Fase 0). Vandaar de prioriteiten in [009-status-en-roadmap](009-status-en-roadmap.md).

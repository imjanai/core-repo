# 093 — Een eerste analyse draaien

## De voorbeelden uit de README

```bash
# Upload een DXF en start de pipeline
curl -F "file=@voorbeeld.dxf" http://localhost:8080/projects

# Haal de materiaallijst op
curl http://localhost:8080/projects/<id>/materials?format=xlsx -o materiaal.xlsx
```

## Stap voor stap

### 1. Zorg dat de stack draait

Zie [091-installatie](091-installatie.md). De API moet op `:8080` antwoorden:

```bash
curl http://localhost:8080/healthz
```

### 2. Upload

```bash
curl -F "file=@voorbeeld.dxf" http://localhost:8080/projects
```

Antwoord:

```json
{"id": "0f6b1e2a-...", "status": "queued"}
```

### 3. Volg de voortgang

```bash
watch -n2 "curl -s http://localhost:8080/projects/0f6b1e2a-... | jq ."
```

```json
{"status": "processing", "current_step": 4, "step_name": "Vector-extractie"}
```

### 4. Bekijk het resultaat

```bash
curl -s http://localhost:8080/projects/0f6b1e2a-.../symbols | jq '.[0:3]'
```

```json
[{"id": "s1", "type": "wandcontactdoos", "x": 12450.0, "y": 8300.0,
  "room_id": "r1", "circuit": "G3", "confidence": 1.0, "source": "vector"}]
```

### 5. Waarschuwingen

```bash
curl -s http://localhost:8080/projects/0f6b1e2a-.../warnings | jq
```

```json
[{"rule_id": "grp-wcd", "message": "Groep G3 heeft 12 WCD's (controleer belasting)"}]
```

### 6. Materiaallijst

```bash
curl "http://localhost:8080/projects/0f6b1e2a-.../materials?format=xlsx" -o materiaal.xlsx
```

## Het eerste DXF-bestand

Waar haal je er één? Opties:

1. **Zelf maken met ezdxf.** Bepaald de snelste route naar een test:

```python
import ezdxf

doc = ezdxf.new()
msp = doc.modelspace()
doc.blocks.new(name="WCD")
for x, y in [(0, 0), (3000, 0), (6000, 0)]:
    msp.add_blockref("WCD", insert=(x, y))
doc.saveas("test.dxf")
```

2. **Een openbare voorbeeldtekening.**
3. **Uit de eigen praktijk** — met toestemming en geanonimiseerd. Zie [084-veiligheid-en-avg](084-veiligheid-en-avg.md).

## Wat je nu al kunt leren

Deze oefening is niet alleen een demo: hij levert de eerste observaties op voor

- de werkende import-structuur ([026-schema-export](026-schema-export.md)),
- de eerste bugs in de pipeline,
- de eerste testgevallen ([081-teststrategie](081-teststrategie.md)).

## Wat er nu bestaat

Niets van de flow — de API, worker en exports bestaan nog niet.

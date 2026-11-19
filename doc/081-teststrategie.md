# 081 — Teststrategie

## De lagen

| Laag | Wat | Waar | Snelheid |
|---|---|---|---|
| **Unit** | Functies in packages | `packages/*/tests` | Milliseconden |
| **Integratie** | DB, S3, taken | `apps/*/tests` | Seconden |
| **Evaluatie** | Modelkwaliteit | `ml/eval` | Minuten |
| **End-to-end** | Upload tot output | `tests/e2e` | Minuten |

De README:

> `uv run pytest` # unit- en integratietests

## De eerste tests die geschreven moeten worden

De repo bevat nog geen enkele test. De logische volgorde:

1. **Test voor `packages/rules`** — die bewijst dat de import werkt en de regel juist vuurt. Zie [047-rules-nen-1010](047-rules-nen-1010.md) voor voorbeelden.
2. **Test voor `packages/schema`** — round-trip serialisatie, Enum-gedrag, defaults.
3. **Test voor de fusie** — handgeschreven waarnemingen → verwacht `Project`.

Die drie zijn snel, deterministisch en blokkeren de rest van het werk niet.

## Wat elk package moet testen

### `schema`

- `Project.model_validate(p.model_dump()) == p` (round-trip)
- Ongeldige invoer wordt geweigerd (`confidence=1.5`)
- Enum-gedrag: `SymbolType.WCD == "wandcontactdoos"`

### `rules`

- Per regel: een positief en een negatief geval.
- Een leeg project levert geen waarschuwingen.

### `parsers`

- Een met ezdxf-geschreven test-DXF wordt correct gelezen (deterministisch, geen dataset nodig).
- Randgevallen: lege DXF, onbekende eenheden, beveiligd PDF.

### `vision`

- Tiling-geometrie: tegels bedekken het beeld, overlap klopt.
- NMS: twee overlappende boxes worden één.
- JSON-parsing van VLM-uitvoer (inclusief codeblok-wrappers).

### `materials`

- Eén symbool → één regel; tien symbolen → één regel met aantal 10.
- Onbekend type → fout of expliciete default, niet stil.

### `drawing`

- Een geplaatst symbool is terug te lezen uit de geëxporteerd DXF.

## Testdata

- **Geen afhankelijkheid van netwerk of GPU** in unit-tests.
- **Geen klantdata** in tests; gebruik gegenereerde fixtures.
- **De evaluatieset is geen testset** — die draait alleen in de promotiegate. Zie [068-evaluatieset](068-evaluatieset.md).

## Wat de CI draait

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy .
uv run pytest
```

Zie [083-cicd](083-cicd.md).

## Coverage

Geen percentage nastreven om het percentage. Wél: elke bug die in productie gevonden wordt, krijgt eerst een reproducerende test. Dat is coverage met een reden.

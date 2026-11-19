# 043 — IFC-parsing met ifcopenshell

## Wat IFC toevoegt

IFC (Industry Foundation Classes) is het open BIM-formaat. Waar DXF tekent, beschrijft IFC *wat* het is: een `IfcElectricOutlet` is niet een cirkel op een laag maar een object met een klasse, een ruimte-relatie en een plaatsing in 3D.

**Praktisch gevolg:** bij IFC is een deel van het werk al gedaan — `room_id` komt uit de relatie, niet uit punt-in-polygoon.

## De bibliotheek: ifcopenshell

```python
import ifcopenshell
import ifcopenshell.geom

model = ifcopenshell.open("gebouw.ifc")
outlets = model.by_type("IfcElectricOutlet")
```

## Wat je eruit haalt

| IFC-entiteit | Wordt | Opmerking |
|---|---|---|
| `IfcElectricOutlet` | `Symbol(WCD)` | Inclusief placement |
| `IfcElectricSwitch` | `Symbol(SWITCH)` | |
| `IfcLightFixture` | `Symbol(LIGHT)` | |
| `IfcDistributionElement` (overig) | kandidaat, `UNKNOWN` | |
| `IfcSpace` | `Room` | Met `Name` en polygoon |
| `IfcBuildingStorey` | verdieping | Voor `Room.floor` |
| `IfcCableSegment` | kabelroute | Voedt `Symbol.circuit` |
| `IfcDistributionBoard` | `Symbol(PANEL)` | De verdeler |

## Plaatsing bepalen

IFC-plaatsingen zijn een keten van transform matrices:

```python
import ifcopenshell.util.placement

matrix = ifcopenshell.util.placement.get_local_placement(outlet.ObjectPlacement)
x, y, z = matrix.translation  # in project-eenheden
```

Het resultaat is 3D. Voor een plattegrond-projectie:

- kies X en Y als de bouwrichting (meestal `OwnerHistory`-conventie),
- of projecteer op het bouwlaagvlak via `IfcBuildingStorey`.

Die keuze moet getest worden tegen echte bestanden: IFC-projecten verschillen in oriëntatie-conventie.

## De eenheden

Lees de lengte-eenheid uit:

```python
unit_scale = ifcopenshell.util.unit.calculate_unit_scale(model)
```

Dat levert de factor om naar mm om te rekenen — de input voor `Project.scale`. Zie [034-stap-3-normalisatie](034-stap-3-normalisatie.md).

## Waar IFC in de praktijk wringt

| Probleem | Realiteit | Aanpak |
|---|---|---|
| Incompleet model | Installateur levert soms alleen de architectuur-IFC | Detecteer ontbrekende elektra-objecten en waarschuw |
| Verschillende IFC-versies | IFC2x3 en IFC4 naast elkaar | Test beide; ifcopenshell ondersteunt beide |
| Decomposition | Objecten zitten in assemblies | Traverse `IfcRelContainedInSpatialStructure` |
| Geen kabelroutes | Wordt zelden modellerend | Val terug op het VLM of op circuit-inferentie |
| Plattegrond-projectie | Intersecties met muren | Gebruik de wandgeometrie om kamers te snijden |

## De rol in de hybride aanpak

IFC valt onder het vectorpad ([016-hybride-aanpak](016-hybride-aanpak.md)): geen detector nodig, wel VLM voor de legenda — al is een legenda in een IFC-model zelden nodig omdat de klassen al expliciet zijn.

## Wat er nu bestaat

Niets. [packages/parsers](../packages/parsers) is leeg; `ifcopenshell` staat in [pyproject.toml](../pyproject.toml).

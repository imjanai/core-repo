# 003 — Het probleem dat imjan AI oplost

## De realiteit op de werkvloer

Elektriciens en installatiebedrijven besteden het grootste deel van hun tijd aan werk dat niets met elektriciteit te maken heeft:

- tekeningen doorlezen en symbolen tellen,
- materiaallijsten en offertes uittypen,
- schema's overtekenen in CAD,
- groepsindelingen handmatig controleren.

Dat is repetitief, foutgevoelig en kost vele uren voordat er één kabel getrokken is.

## Waar het misgaat

| Probleem | Gevolg |
|---|---|
| **Handmatig tellen** | Een gemiste wandcontactdoos betekent tekort materiaal op de bouwplaats |
| **Overgetypte lijsten** | Foutieve artikelnummers, verkeerde aantallen, marge die klopt op papier niet in de praktijk |
| **Normkennis verspreid** | NEN 1010-regels zitten in het hoofd van een senior, niet in het proces |
| **Tekentijd** | Elke woning of kantoor vraagt opnieuw hetzelfde symboolwerk |
| **Junior-senior-gat** | De ervaren calculator leest een tekening in seconden; een junior in twintig minuten |

## Waarom bestaande tools niet volstaan

- **CAD-pakketten** tekenen, maar interpreteren niet. Ze weten niet dat een cirkel met een kruis een lichtpunt is.
- **Offertesoftware** rekent, maar moet alles handmatig ingevoerd krijgen.
- **Generieke AI** kan een foto van een tekening beschrijven, maar telt niet betrouwbaar, hallucineert aantallen en kent de norm niet.
- **BIM-tools** werken alleen als de tekening al als IFC is opgeleverd — in de praktijk begint 80% als PDF of DWG.

## De kern van de oplossing

imjan AI combineert drie dingen die elk afzonderlijk al bestaan, maar zelden samen:

1. **Exacte vector-uitlezing** waar het kan (DXF/IFC zijn machineleesbaar — gebruik ze).
2. **Visie-modellen** waar het moet (raster-PDF's en foto's zijn dat niet).
3. **Regelcode** voor alles wat nooit mag variëren (aantallen, belasting, normgrenzen).

De hybride aanpak staat uitgelegd in [016-hybride-aanpak](016-hybride-aanpak.md).

## Het echte product

Niet "een AI die tekeningen leest", maar:

> **Een proces waarin een tekening aan de ene kant en een gecontroleerde offerte met materiaallijst aan de andere kant komt, met een vakman als laatste controlepunt — en waarbij elke correctie het systeem beter maakt.**

De feedbackloop (correcties → trainingsdata → beter model) is daarom minstens belangrijk als het model zelf. Zie [070-feedbackloop](070-feedbackloop.md).

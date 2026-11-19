# 068 — De evaluatieset

## De regel

> De evaluatieset (±50 tekeningen met gouden antwoorden) is heilig: nooit trainen op deze data.

Elke modelversie wordt hierop gemeten vóór promoveren. Zonder dat is elke verbetering een mening.

## Wat erin zit

±50 tekeningen, elk met:

- het bronbestand,
- een **volledige, handmatig gecontroleerde** grondwaarde: elk symbool met type en coördinaat, elke ruimte, elke groepskoppeling,
- de schaal,
- de verwachte materiaallijst (als uitkomstmeting).

## Representativiteit

De set moet de praktijk representeren, niet de gemakkelijke gevallen:

| Dimensie | Waarborg |
|---|---|
| Formaat | DXF, vector-PDF, gescande PDF |
| Tekengewoonte | Verschillende software (AutoCAD, Revit, BricsCAD, Stabicad) |
| Schaal | 1:20 t/m 1:100 |
| Complexeiteit | Van eenvoudig appartement tot utiliteit |
| Kwaliteit | Ook rommelige, gescande, handgeschreven tekeningen |
| Legenda | Met én zonder legenda |

Te makkelijke set = vals vertrouwen. Te zware set = ontmoediging. Mengsel naar praktijkverdeling.

## Data leakage

De meest voorkomende valkuil in ML: data die van train en eval door elkaar loopt.

| Vorm | Ontstaat door | Voorkomen |
|---|---|---|
| Zelfde tekening in tegels in beide splitsingen | Tegelen vóór splitsen | **Splits per tekening**, vóór tegelen |
| Handtekening-stijl herkenbaar | Dezelfde tekener in beide sets | Splits per project/klant |
| Hyperparameters afgestemd op de evalset | Vaak tune-iteraties | Houd een aparte validatieset |
| Gouden set gebruikt als traindata bij "meer data nodig" | Druk van de deadline | Technische blokkade: `golden/` niet in de loader |

## Wat je per versie rapporteert

Uit de README:

- precisie en recall per symbooltype,
- afwijking in totaal aantal per symbool,
- fout in de uiteindelijke materiaallijst (aantal en kosten),
- percentage tekeningen dat zonder correctie door de review komt.

Zie [069-metrics](069-metrics.md) voor de uitwerking.

## Hoe vaak

Bij elke kandidaat-versie: altijd. Bij wijzigingen in de pipeline (niet alleen modellen): ook. Een parser-wijziging kan de materiaalfout verergeren zonder dat er één model gewijzigd is.

## De kosten

50 tekeningen grondwaarde maken is veel werk (ordelijk 50–150 uur). Het is de duurste maar ook de waardevolste investering van Fase 0: alles wat daarna gemeten wordt, rust erop.

## Wat er nu bestaat

[ml/eval](../ml/eval) is leeg. Er is geen gouden set. Dit is het eerste wat gebouwd moet worden — vóór elk modelwerk. Zie [009-status-en-roadmap](009-status-en-roadmap.md).

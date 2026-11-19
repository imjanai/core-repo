# DXF-review

Start de bestaande API, Celery-worker, PostgreSQL, Redis en S3/MinIO. Open
`http://localhost:8080/review/`. Je kunt een bestaand DXF-project openen met
`/review/?project=<project-id>`.

1. Upload een DXF en wacht tot de analyse klaar is.
2. Selecteer een symbool op de tekening of in de lijst. Wijzig het type of de
   positie, verwijder het symbool of voeg een symbool toe.
3. Controleer de bijgewerkte materiaallijst en download Excel of PDF.

De viewer toont 2D-geometrie uit modelspace. Tekst, lay-outs en externe
referenties vallen buiten deze weergave. De originele analyse en correcties
worden apart bewaard. De reviewdownloads gebruiken `review=true`.

## Pilotdata evalueren

Plaats geanonimiseerde DXF-bestanden en handmatig gecontroleerde antwoorden
buiten de repository, bijvoorbeeld in `pilot-golden/tekeningen/plan-01.dxf` en
`pilot-golden/antwoorden/plan-01.json`. Het antwoord gebruikt het
`packages.schema.Project`-model en dezelfde coördinaten in millimeters als de
review. Vul voor prijsvergelijkingen ook de verwachte materialen in.

```sh
uv run python ml/eval/run_eval.py --dataset ../pilot-golden --report ../pilot-eval.md
```

Gebruik de tellingen, materiaalkosten en geschatte correcties voor de pilot.
De huidige Level 1-detectiescores in de runner zijn voorbeeldwaarden.

## Revisie en bestelling

Open de vorige beoordeelde tekening en upload een nieuwe versie onder
**Revisies**. De vergelijking gaat uit van dezelfde oorsprong en schaal.
Vergelijkbare symbolen worden op positie gekoppeld. Duidelijke correcties
kunnen worden overgenomen wanneer ook het DXF-blok en de laag overeenkomen.
De lijst voor handmatige controle bevat onder meer eerder toegevoegde
symbolen en correcties zonder duidelijke match. De review-URL bevat beide
project-ID's zodat je de vergelijking later kunt heropenen.

Onder **Leveranciersbestelling** vul je per materiaal een SKU, aantal per
verpakking en eventueel een prijs per verpakking in. De CSV rondt naar hele
verpakkingen af en gaat uit van de huidige beoordeelde materiaallijst. De
leveranciersinstellingen worden lokaal in de browser bewaard. De CSV heeft
een vaste kolomindeling en kan zo nodig worden aangepast aan de leverancier.

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

Gebruik **Projectbibliotheek** om eerdere DXF-projecten te zoeken op
bestandsnaam of analysestatus. Kies twee afgeronde projecten als vorige
en huidige tekening om ze direct te vergelijken. Bij elke symboolcorrectie
kun je een opmerking opslaan. Je vindt die terug in **Correctiegeschiedenis**.

Bij **Analysestappen** zie je welke stappen klaar, overgeslagen of mislukt
zijn, met eventuele foutmeldingen. Gebruik **Analyse hervatten** bij een
mislukte run met een opgeslagen checkpoint. De worker pakt de analyse op
vanaf dat checkpoint en gebruikt de bestaande upload.

## Offertes en installatie

Gebruik **Offertes** om prijzen, arbeidsuren, uurtarief en vaste kosten
in te vullen. Opslaan maakt een aparte, onveranderlijke offerteversie.
Download die als PDF, of vergelijk twee versies om een wijzigingsstaat op
basis van hun opgeslagen bedragen te downloaden. Als je een revisie hebt
geopend, zijn de offertes van de vorige tekening ook beschikbaar als basis.
Alle bedragen zijn exclusief btw.

De **Installatiechecklist** gebruikt de beoordeelde symbolen. Groepeer op
ruimte of kring en toon desgewenst alleen openstaande punten. Afvinken
wordt per project opgeslagen.

Pas op een bestaande database eerst migratie `0003` toe met
`uv run alembic upgrade head`.

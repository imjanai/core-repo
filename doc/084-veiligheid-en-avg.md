# 084 — Veiligheid en AVG

## De eisen uit de README

- **Data-isolatie.** Multi-tenant met row-level security.
- **AVG.** Tekeningen kunnen persoonsgegevens bevatten. Hosting in de EU, verwerkersovereenkomsten, bewaartermijnen en verwijdering op verzoek.
- **Trainingsdata.** Klantdata wordt alleen voor training gebruikt met expliciete toestemming.

## Waarom tekeningen persoonsgegevens bevatten

Mensen denken bij AVG aan klantendatabases. Installatietekeningen bevatten vaak:

- **titelblokken** met projectnaam, adres, opdrachtgever,
- **plattegronden** van woningen (indirect identificerend in combinatie),
- soms **namen van bewoners** of aannemers in aantekeningen.

Dus: tekeningen vallen wél onder de AVG.

## De maatregelen

### 1. Hosting in de EU

AWS EU-regio (bijv. `eu-central-1` of `eu-west-1`), of een Europese provider. Leg vast waar backups en logs staan — die tellen mee.

### 2. Verwerkersovereenkomst

Met elke onderaannemer: AWS, eventueel Auth0, eventueel een ML-provider. Zonder DPA geen data.

### 3. Bewaartermijnen

| Categorie | Voorstel |
|---|---|
| Bronbestanden | X maanden na projectafsluiting |
| Tussenresultaten | Kort (weken) |
| Correcties/trainingsdata | Alleen met toestemming, met opzegbaarheid |
| Logs en traces | 30 dagen |
| Backups | Volgens retentiebeleid, met expliciete verwijderprocedure |

### 4. Verwijdering op verzoek

Een `DELETE /projects/{id}` die niet alleen de DB-rij weggooit maar ook:

- de S3-objecten,
- de caches,
- de eventuele kopieën in trainingsexports (bij toestemming ingetrokken: markeren en bij de volgende hertraining uitsluiten).

### 5. Encryptie

- In rust: S3 SSE, database-encryptie.
- In transit: TLS overal, ook intern als dat kan.
- Keys beheerd in een secret-manager, niet in `.env` in git. Zie [088-secrets-en-configuratie](088-secrets-en-configuratie.md).

### 6. Toestemming voor training

Los van de dienstverlening: een expliciete, aparte, intrekbare toestemming. Zonder toestemming draait het product wel maar de feedbackloop niet. Zie [070-feedbackloop](070-feedbackloop.md).

## Wat er niet in de README staat maar nodig is

- **Datalekprocedure** — melden binnen 72 uur; wie doet wat.
- **Pentest** vóór brede uitrol.
- **Logging van toegang** tot klantdata — wie bekeek welk project. Zie [089-auditlogging](089-auditlogging.md).
- **Subprocessen-register** (verwerkingsregister, Art. 30 AVG).

## De balans

Te weinig beveiliging is een datalek. Te veel bureaucraat maakt het product onbruikbaar voor de zzp'er. Start met de basis: EU-hosting, RLS, encryptie, bewaartermijnen, toestemmingsregister — dat is 80% van het verhaal.

## Wat er nu bestaat

Niets. Er is geen code, geen configuratie, geen DPA.

# 100 — Productiechecklist

Alles wat af moet voordat echte klantdata in productie draait. Per categorie met een verwijzing naar het detaildocument.

## Fundament

- [ ] Workspace-configuratie met per-pakket-dependencies — [013](013-monorepo-workspace.md)
- [ ] Import-structuur opgelost; `from packages.rules import validate` werkt — [026](026-schema-export.md)
- [ ] `uv.lock` gecommit — [074](074-python-en-uv.md)
- [ ] Eerste tests groen in CI — [081](081-teststrategie.md)
- [ ] `infra/docker-compose.yml` draait de hele stack lokaal — [079](079-docker-infra.md)

## Pipeline

- [ ] Ingest met virusscan en begrenzingen — [032](032-stap-1-ingest.md)
- [ ] Classificatie getest op vier formaat-categorieën — [033](033-stap-2-classificatie.md)
- [ ] Schaalbepaling met sanity-check — [034](034-stap-3-normalisatie.md)
- [ ] Vector-parser getest tegen echte tekeningen — [042](042-parsers-dxf.md), [044](044-parsers-pdf.md)
- [ ] Fusie idempotent — [039](039-stap-6-fusie.md)
- [ ] Elke stap heeft timeout en begrijpelijke foutmelding — [090](090-foutscenario.md)

## ML

- [ ] Evaluatieset bestaat, is gesplitst en gecommit — [068](068-evaluatieset.md)
- [ ] Baseline-metrics vastgelegd — [069](069-metrics.md)
- [ ] Promotiegate draait in CI — [083](083-cicd.md)
- [ ] Modelversies geregistreerd en herleidbaar per analyse — [072](072-mlops-en-registratie.md)
- [ ] Licenties beoordeeld, inclusief AGPL-risico's — [087](087-modellicenties.md)

## Veiligheid

- [ ] Row-level security op elke tabel met klantdata, mét test — [086](086-multitenant-security.md)
- [ ] EU-hosting bevestigd — [084](084-veiligheid-en-avg.md)
- [ ] Verwerkersovereenkomsten getekend — [084](084-veiligheid-en-avg.md)
- [ ] Bewaartermijnen geconfigureerd — [084](084-veiligheid-en-avg.md)
- [ ] Verwijdering op verzoek werkt end-to-end — [084](084-veiligheid-en-avg.md)
- [ ] Secrets in secret-manager, niet in bestanden — [088](088-secrets-en-configuratie.md)
- [ ] Toestemmingsflow voor training — [070](070-feedbackloop.md)
- [ ] Pentest uitgevoerd en bevindingen verwerkt — [084](084-veiligheid-en-avg.md)
- [ ] Auditlogging actief — [089](089-auditlogging.md)
- [ ] Gebruiksvoorwaarden juridisch beoordeeld — [085](085-aansprakelijkheid.md)

## Betrouwbaarheid

- [ ] Backups van database én opslag, met hersteltest — [090](090-foutscenario.md)
- [ ] Monitoring en alarmering actief — [080](080-observability.md)
- [ ] Runbook: wat doe ik bij [scenario] — [090](090-foutscenario.md)
- [ ] Rate limiting per tenant — [052](052-api-server.md)
- [ ] Rollback-procedure voor modelversies — [072](072-mlops-en-registratie.md)

## Product

- [ ] Review-UI werkt op tablet — [057](057-review-app.md)
- [ ] Twijfel-lijst zichtbaar en bruikbaar — [057](057-review-app.md)
- [ ] Materiaalexport klopt handmatig geverifieerd — [048](048-materials-engine.md)
- [ ] Nederlandstalige foutmeldingen — [090](090-foutscenario.md)
- [ ] Onboarding van een pilotklant in < 1 uur — [091](091-installatie.md)

## De vraag vóór livegang

> Kunnen we uitleggen wat er gebeurt als het misgaat — en is er iemand die het kan herstellen?

Zo niet: nog niet live.

---

## Slot

Dit was document 100 van 100. Terug naar de [index](001-index.md).

De documenten beschrijven het project zoals ontworpen in de README en zoals de huidige code is. Waar code nog niet bestaat, is dat per document vermeld. Bij twijfel: de repo is leidend — [030-schema-verschillen-met-readme](030-schema-verschillen-met-readme.md) verzamelt de verschillen.

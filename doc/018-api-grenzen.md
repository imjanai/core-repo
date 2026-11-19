# 018 — API-grenzen (welke diensten praten met welke)

## Het principe

Er is **één** externe ingang: de API. Geen enkele andere dienst luistert op een publiek bereikbaar adres. De worker, de MCP-server en het model zijn interne details.

## De grenzen op een rij

| Grens | Van | Naar | Protocol | Publiek? |
|---|---|---|---|---|
| A | Frontend | API | HTTPS/JSON (REST) | ✅ |
| B | API | PostgreSQL | asyncpg (TCP) | ❌ |
| C | API | Redis | Celery-client | ❌ |
| D | API | S3 | boto3 (HTTP, intern) | ❌ |
| E | Worker | Redis | Celery | ❌ |
| F | Worker | S3 | boto3 | ❌ |
| G | Worker | vLLM | OpenAI-compatibel HTTP | ❌ |
| H | Worker | PostgreSQL | asyncpg | ❌ |
| I | Agent-clients | MCP-server | MCP (stdio of HTTP) | ⚠️ geauthenticeerd |
| J | Frontend | S3 (uploads/downloads) | presigned URL | ⚠️ tijdelijk |

## Waarom presigned URL's voor uploads

Het niet doorsturen van bestanden via de API:

- bestanden gaan direct tussen browser en opslag (sneller, minder geheugen),
- de API blijft licht en hoeft geen gigabytes te bufferen,
- de URL is tijdelijk en per object, wat een natuurlijke authorisatielaag geeft.

Regel: de URL levert alleen `PUT` of `GET` op precies één object en verloopt binnen minuten.

## Waarom het model nooit publiek is

vLLM spreekt OpenAI-compatibel en zou dus zonder meer een API kunnen zijn. Dat mag niet:

- het model is duur per token — elke aanroep moet geauthentificeerd en begrensd zijn;
- prompts bevatten klanttekeningen — die mogen het interne netwerk niet uit;
- alleen de worker mag aanroepen, vanuit de pipeline.

Zie [071-model-serving-vllm](071-model-serving-vllm.md).

## Waarom de MCP-server een eigen grens is

De MCP-server is bedoeld om door een AI-agent (bijv. Claude Desktop of een IDE) te worden aangeroepen — potentieel vanaf een ontwikkelaarsmachine. Dat vraagt:

- een expliciete configuratie-actie (de gebruiker start de server zelf),
- een beperkte toolset (alleen tekenen, geen data-toegang),
- elke tool die een `Project`-wijziging teruggeeft, zodat de API kan auditen wat er gebeurde.

Zie [055-mcp-server](055-mcp-server.md) en [056-mcp-tools](056-mcp-tools.md).

## Versiebeheer van de API

De frontend en eventuele integratiepartners zijn gebonden aan de API. Dus:

- de API is versioneerbaar (`/v1/...`) zodra externe partijen zich aansluiten;
- toevoegen mag altijd; verwijderen of hernoemen pas na een migratieperiode;
- het OpenAPI-schema (`/docs`) is het contract.

## Wat er nu al bestaat

Niets — de API-map bevat alleen een placeholder-README. Zie [052-api-server](052-api-server.md) en [002-project-overview#huidige-status](002-project-overview.md#huidige-status-van-de-repo).

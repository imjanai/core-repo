# 071 — Model-serving met vLLM

## De keuze

> **Model-serving:** vLLM (OpenAI-compatibele API)

## Waarom vLLM

- **Snel.** Continuous batching en paged attention benutten de GPU veel beter dan een naïeve loop.
- **OpenAI-compatibel.** Dezelfde client-code als tegen een externe API — makkelijk te testen en te vervangen.
- **Eenvoudig.** Eén commando, geen eigen serving-code om te onderhouden.

Alternatieven vergeleken: [020-keuzes-en-alternatieven](020-keuzes-en-alternatieven.md).

## Het starten

```bash
uv run vllm serve ./models/elektro-vl \
  --host 0.0.0.0 --port 8000 \
  --max-model-len 8192 \
  --gpu-memory-utilization 0.9
```

De client in [packages/vision](../packages/vision) wijst naar `VLLM_BASE_URL` (zie [046-vision-vlm-client](046-vision-vlm-client.md) en de voorbeeld-`.env` in de README).

## Wat de pipeline ervan vraagt

| Eigenschap | Waarom |
|---|---|
| Determinisme (`temperature=0`) | Reproduceerbare analyses en evaluaties |
| JSON-structuur | De pipeline parseert; zie [038](038-stap-5-vlm-redenering.md) |
| Batches | Meerdere crops tegelijk = hogere doorvoer |
| Begrenzing | Max tokens per aanroep voorkomt uitglijders |

## Operationele aandachtspunten

### 1. Het model is duur

Een GPU-server draait ook als er niets is. Begrenzen:

- autoscaling op queue-lengte (of een minimum van één replica voor de piek),
- caching van herhaalde aanroepen op inhoud-hash,
- crops in plaats van hele tekeningen (minder tokens).

Zie [097-prestaties-en-schaal](097-prestaties-en-schaal.md) en [098-kostenraming](098-kostenraming.md).

### 2. Nooit publiek

De API-server praat niet direct met vLLM; alleen de worker. Zie [018-api-grenzen](018-api-grenzen.md). Klanttekeningen in prompts mogen het interne netwerk niet uit.

### 3. Logging van prompts

Langfuse legt prompts en antwoorden vast voor debugging. Maar: prompts bevatten klanttekeningen (als data-URI). Stel een bewaartermijn in en overweeg het weglaten van de beeld-URI in de log. Zie [080-observability](080-observability.md) en [084-veiligheid-en-avg](084-veiligheid-en-avg.md).

### 4. Versiebeheer

Elke modelversie die geserveerd wordt, heeft een naam (`elektro-vl-v0.3`) en een registratie in MLflow. Zo is herleidbaar welk model een bepaalde analyse produceerde. Zie [072-mlops-en-registratie](072-mlops-en-registratie.md).

## De detector is een ander verhaal

De detector draait niet via vLLM maar als PyTorch/ONNX-model in de worker — laag geheugen, hoge doorvoer, geen server nodig. Zie [045-vision-detector](045-vision-detector.md).

## Wat er nu bestaat

Niets. `openai` en `qwen-vl-utils` staan in [pyproject.toml](../pyproject.toml); er is geen model, geen server en geen config.

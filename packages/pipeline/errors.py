"""
packages/pipeline/errors.py — fouttaxonomie van de pipeline.

De engine maakt onderscheid tussen twee soorten falen:

    Permanent  →  herhalen helpt niet. De run faalt direct.
                  bv. "onbekend bestandsformaat", "schema-validatie mislukt"

    Retryable  →  waarschijnlijk tijdelijk. De stage wordt opnieuw geprobeerd
                  met exponentiële backoff + jitter.
                  bv. "S3 niet bereikbaar", "vLLM gaf 503", "timeout"

Stages mogen die keuze afdwingen door PermanentStageError of
RetryableStageError op te gooien. Elke andere ongevraagde uitzondering wordt
behandeld als retryable (een bug in een stage wordt dus beperkt tot
`max_attempts` pogingen in plaats van de hele run te slopen).
"""

from __future__ import annotations


class PipelineError(Exception):
    """Basis-exception voor alles wat met de pipeline te maken heeft."""

    #: of de engine deze fout opnieuw mag proberen
    retryable: bool = False

    def __init__(self, message: str, *, stage_id: str | None = None) -> None:
        super().__init__(message)
        self.stage_id = stage_id


class PermanentStageError(PipelineError):
    """De stage kan nooit slagen met deze input — niet opnieuw proberen."""

    retryable = False


class RetryableStageError(PipelineError):
    """Waarschijnlijk tijdelijke storing — gerust opnieuw proberen."""

    retryable = True


class StageTimeoutError(RetryableStageError):
    """De stage heeft zijn tijdslimiet overschreden."""


class StageSkipped(Exception):
    """Intern signaal: de stage wil zichzelf als 'overgeslagen' laten boeken."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


class NotImplementedStage(StageSkipped):
    """
    De implementatie van deze optionele stage bestaat (nog) niet.

    Onderscheiden van een gewone skip zodat `PipelineOptions(strict=True)`
    in CI kan zeggen: "hier ontbreekt de parser, dat is een fout" — terwijl
    een productie-run er gewoon mee doorgaat.
    """


class PipelineCancelled(PipelineError):
    """De run is geannuleerd door een mens of door de shutdown-handler."""


class PipelineFailed(PipelineError):
    """De run is definitief mislukt; bevat het laatste stage-foutbericht."""

    def __init__(
        self,
        message: str,
        *,
        stage_id: str | None = None,
        attempts: int = 0,
        cause: BaseException | None = None,
    ) -> None:
        super().__init__(message, stage_id=stage_id)
        self.attempts = attempts
        self.cause = cause


class PipelineAlreadyRunning(PipelineError):
    """
    Er draait al een run voor dit project.

    Dubbele uitvoering voorkomen is belangrijker dan alles: dezelfde tekening
    twee keer analyseren betekent dubbele materialijsten en een review-UI die
    heen en weer springt. De worker behandelt dit als 'niets doen', de API
    vertaalt het naar 409 Conflict.
    """

    def __init__(self, message: str, *, run: "PipelineRun | None" = None) -> None:
        super().__init__(message)
        self.run = run


class DagError(PipelineError):
    """De stage-afhankelijkheden vormen geen geldige (acyclische) graaf."""


def classify_optional_failure(exc: BaseException) -> bool:
    """
    Bepaalt of een mislukte *optionele* stage mag worden overgeslagen.

    Een ontbrekende afhankelijkheid (torch/vLLM/een parser die nog niet
    gebouwd is) is geen storing maar een gemoduleerde functie — de analyse
    gaat door met wat er wel is.
    """
    if isinstance(exc, (NotImplementedError, ImportError, ModuleNotFoundError)):
        return True
    if isinstance(exc, StageSkipped):
        return True
    return False


def is_retryable(exc: BaseException) -> bool:
    """Bepaalt of een uitzoveriging opnieuw geprobeerd mag worden."""
    if isinstance(exc, PipelineError):
        return exc.retryable
    # Onbekende uitzonderingen (bugs, netwerkstacks) behandelen we als
    # tijdelijk: liever drie pogingen dan een half afgebroken project.
    return True

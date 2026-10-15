"""In-process native refusal, never reconstructed from JSON or model arguments."""


class DisabledBeforeDispatch(dict):
    """Browser adapter found a disabled element before beginning any click."""


class MissingBeforeDispatch(dict):
    """Native target resolution returned without beginning any click.

    Not a claim that a control cannot exist elsewhere or appear later.
    JSON/dict copies intentionally lose this in-process provenance.
    """


class AuditPreflightRefused(dict):
    """Native audit adapter returned before starting POST, never reconstructed."""

"""Exact opt-in safeguard for Comms provider requests."""
import pytest
from fastapi import HTTPException

from services.api.comms import require_external_model_release


@pytest.mark.parametrize("value", [None, "", "false", "True", "TRUE", "1", " true "])
def test_comms_disabled_by_default(monkeypatch, value):
    if value is None:
        monkeypatch.delenv("COMMS_EXTERNAL_MODEL_ENABLED", raising=False)
    else:
        monkeypatch.setenv("COMMS_EXTERNAL_MODEL_ENABLED", value)
    with pytest.raises(HTTPException) as error:
        require_external_model_release()
    assert error.value.status_code == 503

def test_comms_explicit_release(monkeypatch):
    monkeypatch.setenv("COMMS_EXTERNAL_MODEL_ENABLED", "true")
    require_external_model_release()

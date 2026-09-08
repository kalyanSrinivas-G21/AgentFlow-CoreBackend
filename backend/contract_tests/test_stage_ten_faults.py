import pytest
from pydantic import ValidationError

from app.events.envelope import EventEnvelope


def test_malformed_event_envelope_is_detectable_for_dead_letter_routing():
    with pytest.raises(ValidationError):
        EventEnvelope.model_validate_json("{not-json}")

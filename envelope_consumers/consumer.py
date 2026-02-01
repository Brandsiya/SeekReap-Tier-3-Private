from tier3.validators import validate_tier2_envelope, EnvelopeValidationError

class EnvelopeConsumer:
    def __init__(self, envelope=None):
        if envelope is not None:
            try:
                validate_tier2_envelope(envelope)
            except EnvelopeValidationError as e:
                raise ValueError(f"Invalid envelope for EnvelopeConsumer: {e}")
        self.envelope = envelope

    def process(self):
        if self.envelope:
            print(f"Processing envelope: {self.envelope}")
        else:
            print("No envelope provided.")

from tier3.validators import validate_tier2_envelope, EnvelopeValidationError

class Processor:
    def __init__(self, envelope=None):
        if envelope is not None:
            try:
                validate_tier2_envelope(envelope)
            except EnvelopeValidationError as e:
                raise ValueError(f"Invalid envelope for Processor: {e}")
        self.envelope = envelope

    def run(self):
        if self.envelope:
            print(f"Processing semantic logic on envelope: {self.envelope}")
        else:
            print("No envelope provided.")

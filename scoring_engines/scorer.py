from tier3.validators import validate_tier2_envelope, EnvelopeValidationError

class Scorer:
    def __init__(self, envelope=None):
        if envelope is not None:
            try:
                validate_tier2_envelope(envelope)
            except EnvelopeValidationError as e:
                raise ValueError(f"Invalid envelope for Scorer: {e}")
        self.envelope = envelope

    def score(self):
        if self.envelope:
            print(f"Scoring envelope: {self.envelope}")
        else:
            print("No envelope provided.")

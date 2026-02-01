import sys
import os

# Add repo root to sys.path
repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

# Add submodules
for subfolder in ["envelope_consumers", "semantic_processors", "scoring_engines", "tier3"]:
    sub_path = os.path.join(repo_root, subfolder)
    if os.path.isdir(sub_path) and sub_path not in sys.path:
        sys.path.insert(0, sub_path)

from envelope_consumers.consumer import EnvelopeConsumer
from semantic_processors.processor import Processor
from scoring_engines.scorer import Scorer
from tier3.validators import validate_tier2_envelope, EnvelopeValidationError

example_env = {
    "behavior_type": "aggressive",
    "intensity": 0.5,
    "duration": 10,
    "premium_indicator": False,
    "_version": "1.0.0",
    "_processed_by": "tier2"
}

# Validate envelope
try:
    validate_tier2_envelope(example_env)
    print("Envelope passed validation ✅")
except EnvelopeValidationError as e:
    print(f"Envelope validation failed ❌: {e}")

# Initialize Tier-3 modules
ec = EnvelopeConsumer(envelope=example_env)
proc = Processor(envelope=example_env)
scorer = Scorer(envelope=example_env)

# Run example methods
ec.process()
proc.run()
scorer.score()
print("All Tier-3 modules loaded successfully ✅")

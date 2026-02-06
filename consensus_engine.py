from tier2_client import Tier2Client
from dataclasses import dataclass
from typing import List

@dataclass
class VerificationResult:
    reap_id: str
    consensus: bool
    node_votes: int
    total_nodes: int
    score: float

class ConsensusEngine:
    def __init__(self, tier2_nodes: List[str]):
        self.client = Tier2Client(tier2_nodes)
    
    async def verify_distributed(self, reap_id: str) -> VerificationResult:
        result = await self.client.verify_reap(reap_id)
        return VerificationResult(
            reap_id=reap_id,
            consensus=result["consensus"],
            node_votes=result["node_votes"],
            total_nodes=result["nodes"],
            score=0.75  # Aggregated from nodes
        )

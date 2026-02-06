import httpx
import asyncio
from typing import List, Dict

class Tier2Client:
    def __init__(self, tier2_urls: List[str]):
        self.tier2_urls = tier2_urls
        self.client = httpx.AsyncClient()
    
    async def create_seeker(self) -> Dict:
        results = await asyncio.gather(*[
            self.client.post(f"{url}/v1/seekers") for url in self.tier2_urls
        ])
        return results[0].json()  # Primary replica
    
    async def verify_reap(self, reap_id: str) -> Dict:
        results = await asyncio.gather(*[
            self.client.post(f"{url}/v1/verify/{reap_id}") for url in self.tier2_urls
        ])
        # Consensus: 2/3 nodes must agree "verified"
        verified_count = sum(1 for r in results if r.json().get("status") == "verified")
        return {"consensus": verified_count >= 2, "nodes": len(results)}

"""
Example usage of the Tier-3 semantic processing system.
"""
import json
import base64

# Import our Tier-3 modules
from envelope_consumers.consumer import create_consumer
from semantic_processors.processor import SemanticProcessor
from scoring_engines.scorer import MonetizationScorer

def create_sample_envelope():
    """Create a sample envelope similar to what Tier-2 would produce."""
    # This is the semantic data that would come from atomic behaviors
    semantic_data = {
        "behavior_type": "deep_research",
        "intensity": 0.85,
        "duration": 180,  # 3 minutes
        "premium_indicator": True,
        "user_segment": "professional",
        "features_used": ["advanced_search", "export", "analytics"]
    }
    
    # Tier-2 would encode this into an opaque envelope
    encoded_payload = base64.b64encode(
        json.dumps(semantic_data).encode('utf-8')
    ).decode('utf-8')
    
    envelope = {
        "envelope_id": "env_12345",
        "timestamp": "2024-01-26T22:30:00Z",
        "payload": encoded_payload,
        "signature": "sig_abc123"  # In production, this would be a real signature
    }
    
    return envelope

def main():
    """Run the complete Tier-3 processing pipeline."""
    print("=== SEEKREAP TIER-3 DEMONSTRATION ===")
    print()
    
    # Step 1: Create sample envelope (simulating Tier-2 output)
    print("1. Creating sample envelope (simulating Tier-2 output)...")
    envelope = create_sample_envelope()
    print(f"   Envelope ID: {envelope['envelope_id']}")
    print(f"   Payload size: {len(envelope['payload'])} chars")
    print()
    
    # Step 2: Consume envelope with Tier-3 consumer
    print("2. Consuming envelope with Tier-3 consumer...")
    consumer = create_consumer()
    semantic_data = consumer.consume_envelope(envelope)
    print(f"   Successfully consumed envelope #{consumer.processed_count}")
    print(f"   Decoded data keys: {list(semantic_data.keys())}")
    print()
    
    # Step 3: Process semantic data
    print("3. Processing semantic data for insights...")
    processor = SemanticProcessor()
    insights = processor.process(semantic_data)
    print(f"   Generated insights #{processor.insights_generated}")
    print(f"   Monetization score: {insights['monetization_score']:.2f}")
    print(f"   Patterns detected: {insights.get('patterns', [])}")
    print(f"   Recommended actions: {insights['recommended_actions'][:2]}")
    print()
    
    # Step 4: Score for monetization
    print("4. Scoring for monetization potential...")
    scorer = MonetizationScorer()
    valuation = scorer.score(insights)
    print(f"   Value score: {valuation['value_score']:.2f}")
    print(f"   Confidence: {valuation['confidence']:.2f}")
    print(f"   Recommended tier: {valuation['pricing_tiers']['tier']}")
    print(f"   Monthly price: ${valuation['pricing_tiers']['monthly_price']}")
    print(f"   Expected revenue: ${valuation['estimated_revenue']['expected']:.2f}")
    print(f"   Risks: {valuation['risk_factors']}")
    print()
    
    # Step 5: Display monetization summary
    print("5. MONETIZATION SUMMARY:")
    print("   " + "=" * 40)
    print(f"   User behavior: {semantic_data.get('behavior_type', 'unknown')}")
    print(f"   Engagement level: {'HIGH' if semantic_data.get('intensity', 0) > 0.7 else 'MODERATE'}")
    print(f"   Recommended action: {valuation['pricing_tiers']['tier']} tier at ${valuation['pricing_tiers']['monthly_price']}/month")
    print(f"   Lifetime value estimate: ${valuation['estimated_revenue']['lifetime_value']:.2f}")
    print(f"   Risk assessment: {len(valuation['risk_factors'])} risk(s) identified")
    print()
    print("=== DEMONSTRATION COMPLETE ===")

if __name__ == "__main__":
    main()

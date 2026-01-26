"""
Semantic processor - extracts business meaning from decoded data.
"""
from typing import Dict, Any, List

class SemanticProcessor:
    """Processes decoded semantic data into business insights."""
    
    def __init__(self):
        self.insights_generated = 0
    
    def process(self, semantic_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process semantic data into monetizable insights.
        
        Args:
            semantic_data: Decoded data from envelope consumer
            
        Returns:
            Business insights with monetization potential
        """
        insights = {
            'raw': semantic_data,
            'insights': [],
            'monetization_score': 0.0,
            'recommended_actions': []
        }
        
        # Extract behavioral patterns
        patterns = self._extract_patterns(semantic_data)
        insights['patterns'] = patterns
        
        # Score monetization potential
        score = self._calculate_monetization_score(semantic_data, patterns)
        insights['monetization_score'] = score
        
        # Generate recommended actions
        actions = self._generate_recommendations(semantic_data, score)
        insights['recommended_actions'] = actions
        
        self.insights_generated += 1
        return insights
    
    def _extract_patterns(self, data: Dict[str, Any]) -> List[str]:
        """Extract behavioral patterns from semantic data."""
        patterns = []
        
        # Proprietary pattern detection logic
        if 'behavior_type' in data:
            patterns.append(f"behavior_{data['behavior_type']}")
        
        if 'intensity' in data and data.get('intensity', 0) > 0.7:
            patterns.append("high_intensity_behavior")
        
        if 'duration' in data and data.get('duration', 0) > 60:
            patterns.append("sustained_engagement")
        
        return patterns
    
    def _calculate_monetization_score(self, data: Dict[str, Any], patterns: List[str]) -> float:
        """Calculate monetization potential score (0.0-1.0)."""
        score = 0.0
        
        # Base score from patterns
        pattern_score = len(patterns) * 0.1
        score += min(pattern_score, 0.3)
        
        # Intensity bonus
        if 'intensity' in data:
            score += data['intensity'] * 0.3
        
        # Duration bonus
        if 'duration' in data:
            duration_norm = min(data['duration'] / 300.0, 1.0)
            score += duration_norm * 0.2
        
        # Proprietary business rules
        if 'premium_indicator' in data and data['premium_indicator']:
            score += 0.2
        
        return min(score, 1.0)
    
    def _generate_recommendations(self, data: Dict[str, Any], score: float) -> List[str]:
        """Generate monetization recommendations based on score."""
        recommendations = []
        
        if score > 0.8:
            recommendations.append("PREMIUM_UPSELL: High-value user detected")
            recommendations.append("PERSONALIZED_OFFER: Create custom bundle")
        elif score > 0.5:
            recommendations.append("CROSS_SELL: Related feature suggestion")
            recommendations.append("LOYALTY_PROGRAM: Invite to join")
        else:
            recommendations.append("BASIC_ENGAGEMENT: Continue free tier")
            recommendations.append("EDUCATION: Share tutorials")
        
        # Context-specific recommendations
        if 'behavior_type' in data:
            recommendations.append(f"CONTEXT_OPTIMIZE: For {data['behavior_type']}")
        
        return recommendations

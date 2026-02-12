from tier3.contract import compute_score

def test_score_calculation_basic():
    score = compute_score(quality_score=1.0, risk_score=0.0)
    assert score == 0.7

def test_score_clamping_lower():
    score = compute_score(quality_score=0.0, risk_score=1.0)
    assert score == 0.0

def test_score_clamping_upper():
    score = compute_score(quality_score=1.0, risk_score=-1.0)
    assert score <= 1.0

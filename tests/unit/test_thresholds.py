from tier3.contract import derive_decision

def test_approve_threshold():
    assert derive_decision(0.75) == "approve"

def test_review_threshold_lower_bound():
    assert derive_decision(0.45) == "review"

def test_reject_below_review():
    assert derive_decision(0.4499) == "reject"

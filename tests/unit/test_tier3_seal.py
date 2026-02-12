from tier3.seal import contract_fingerprint

EXPECTED_FINGERPRINT = "efbc56c95460b1194bf7d9f37e7bd9bb6d2315d28739d77a9cdb170453217b69"


def test_contract_fingerprint_frozen():
    assert contract_fingerprint() == EXPECTED_FINGERPRINT

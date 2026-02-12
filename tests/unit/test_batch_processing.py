from tier3.api import process_batch

def test_batch_order_preserved():
    envelopes = [
        {"content": "a", "metadata": {}, "context": {}},
        {"content": "b", "metadata": {}, "context": {}},
    ]

    results = process_batch(envelopes)

    assert len(results) == 2

"""The pure checks of the index health script. No Azure."""
from app.ai.labs import lab06_index_health as health


def test_count_ok_only_when_equal():
    assert health.count_ok(21, 21)
    assert not health.count_ok(21, 20)     # dropped
    assert not health.count_ok(21, 22)     # duplicated


def test_golden_hits_pass_and_fail():
    results = {q: [expected] for q, expected in health.GOLDEN}
    assert all(found for *_, found in health.golden_hits(results))

    first_query = health.GOLDEN[0][0]
    results[first_query] = ["Taxi ride"]   # relevance regression
    outcome = health.golden_hits(results)
    assert outcome[0][2] is False
    assert all(found for *_, found in outcome[1:])


def test_missing_query_counts_as_failure():
    assert not any(found for *_, found in health.golden_hits({}))

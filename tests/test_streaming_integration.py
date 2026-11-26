import os
import pytest


@pytest.mark.integration
@pytest.mark.spark
def test_real_streaming_duplicate_update_invalid_and_late():
    if os.environ.get("SM_TEST_STREAMING") != "1":
        pytest.skip("Run with a Spark-enabled environment and SM_TEST_STREAMING=1")
    from streaming_scenario import run_scenario
    assert run_scenario()["status"] == "passed"

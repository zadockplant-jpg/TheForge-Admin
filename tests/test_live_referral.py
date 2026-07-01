import os
import time
import pytest

from api_client import AdminApiClient, ApiError

# Opt-in live tests: set RUN_LIVE_TESTS=1 and provide a token via
# SENDFORGE_ADMIN_TEST_API_TOKEN in the environment.
pytestmark = pytest.mark.skipif(
    os.environ.get("RUN_LIVE_TESTS") != "1",
    reason="Run live tests with RUN_LIVE_TESTS=1",
)

EMAIL = "zadockplant@gmail.comsendforge_admin_live_referral_test_lab_0_4_1"


def _get_client_with_token():
    token = os.environ.get("SENDFORGE_ADMIN_TEST_API_TOKEN")
    if not token:
        pytest.skip("Set SENDFORGE_ADMIN_TEST_API_TOKEN to run live tests")
    client = AdminApiClient()
    client.token = token
    return client


def test_upsert_program_create_code_and_list():
    client = _get_client_with_token()

    # Upsert a small test referral program
    program_payload = {
        "productSlug": "tabforge",
        "tiers": [{"requiredPurchases": 1, "rewardAmountCents": 100}],
        "rewardType": "cashapp_manual",
        "status": "active",
    }
    resp = client.upsert_referral_program(program_payload)
    assert resp is not None

    # Create a referral code tied to the provided test email
    code_payload = {
        "email": EMAIL,
        "code": f"test_{int(time.time())}",
        "cashappHandle": "$testhandle",
    }
    created = client.create_referral_code(code_payload)
    assert created is not None

    # Fetch referrals and ensure programs key exists
    data = client.get_referrals()
    assert isinstance(data, dict)
    assert "programs" in data

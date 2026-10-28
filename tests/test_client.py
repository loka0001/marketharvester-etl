from unittest.mock import MagicMock
import pytest
from marketharvester.client import ResilientClient, HarvestRateLimitError, HarvestHTTPError


def test_client_retry_and_success_on_transient_server_error():
    session = MagicMock()
    # First response 503, second response 200 OK
    resp_503 = MagicMock(status_code=503)
    resp_200 = MagicMock(status_code=200, text="<html>Success</html>", apparent_encoding="utf-8")
    session.get.side_effect = [resp_503, resp_200]

    client = ResilientClient(max_retries=2, base_backoff=0.01, rate_limit_delay=0.0, session=session)
    html = client.get_html("http://example.com/test")
    assert html == "<html>Success</html>"
    assert session.get.call_count == 2


def test_client_rate_limit_error():
    session = MagicMock()
    resp_429 = MagicMock(status_code=429, headers={"Retry-After": "0.01"})
    session.get.return_value = resp_429

    client = ResilientClient(max_retries=1, base_backoff=0.01, rate_limit_delay=0.0, session=session)
    with pytest.raises(HarvestRateLimitError):
        client.get_html("http://example.com/test-rate-limit")


def test_client_404_raises_http_error():
    session = MagicMock()
    resp_404 = MagicMock(status_code=404)
    session.get.return_value = resp_404

    client = ResilientClient(max_retries=1, base_backoff=0.01, rate_limit_delay=0.0, session=session)
    with pytest.raises(HarvestHTTPError) as exc:
        client.get_html("http://example.com/not-found")
    assert exc.value.status_code == 404

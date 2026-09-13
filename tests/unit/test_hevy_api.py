from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest
import requests

from app.services.hevy_api import HevyAPI  # Adjust import as needed


@pytest.fixture
def hevy_api_instance():
    return HevyAPI(api_key="fake-key", is_encrypted=False)


def make_workout(start_time):
    return {"start_time": start_time, "id": "workout-id", "title": "Test Workout"}


def mock_response(workouts, page_count=1):
    return {"workouts": workouts, "page_count": page_count}


@patch("app.services.hevy_api.requests.request")
def test_get_workouts_filters_by_date(mock_request, hevy_api_instance):
    # Arrange
    start_date = datetime(2025, 5, 23, tzinfo=timezone.utc)
    end_date = datetime(2025, 6, 22, tzinfo=timezone.utc)
    # One workout inside, one outside the range
    inside = make_workout("2025-06-01T10:00:00+00:00")
    outside = make_workout("2025-05-01T10:00:00+00:00")
    mock_request.return_value = MagicMock(
        status_code=200, json=lambda: mock_response([inside, outside], page_count=1)
    )

    # Act
    results = hevy_api_instance.get_workouts(start_date, end_date)

    # Assert
    assert len(results) == 1
    assert results[0]["start_time"] == inside["start_time"]
    # Guard: a wrong patch target would silently hit the real API instead.
    assert mock_request.called


@patch("app.services.hevy_api.requests.request")
def test_get_workouts_pagination(mock_request, hevy_api_instance):
    # Arrange
    start_date = datetime(2025, 5, 23, tzinfo=timezone.utc)
    end_date = datetime(2025, 6, 22, tzinfo=timezone.utc)
    # Page 1 and 2, both with one workout in range
    page1 = make_workout("2025-06-01T10:00:00+00:00")
    page2 = make_workout("2025-06-10T10:00:00+00:00")
    # Set up side effects for pagination
    mock_request.side_effect = [
        MagicMock(status_code=200, json=lambda: mock_response([page1], page_count=2)),
        MagicMock(status_code=200, json=lambda: mock_response([page2], page_count=2)),
    ]

    # Act
    results = hevy_api_instance.get_workouts(start_date, end_date)

    # Assert
    assert len(results) == 2
    assert results[0]["start_time"] == page1["start_time"]
    assert results[1]["start_time"] == page2["start_time"]
    # Guard: a wrong patch target would silently hit the real API instead.
    assert mock_request.called


@patch("app.services.hevy_api.requests.request")
def test_get_workouts_handles_http_error(mock_request, hevy_api_instance):
    # Arrange: a realistic 401 response. Real raise_for_status() raises,
    # which is what drives hevy_api's retry-then-propagate path.
    mock_response = MagicMock()
    mock_response.status_code = 401
    mock_response.text = "InvalidApiKey"
    mock_response.headers = {}
    mock_response.request.url = "http://fake.url"
    mock_response.request.headers = {}
    http_error = requests.exceptions.HTTPError("401 Client Error: Unauthorized")
    http_error.response = mock_response
    mock_response.raise_for_status.side_effect = http_error
    mock_request.return_value = mock_response

    # Keep the test fast without changing the code path: retries still run,
    # they just don't sleep. This exercises the real retry logic at
    # _make_request_with_retry:99-109 without the 7s of backoff delays.
    hevy_api_instance.retry_delay = 0

    # Act & Assert
    with pytest.raises(requests.exceptions.HTTPError) as excinfo:
        hevy_api_instance.get_workouts()

    assert "401 Client Error" in str(excinfo.value)
    # The wrapper retries before giving up, so more than one attempt happens.
    assert mock_request.call_count == hevy_api_instance.max_retries + 1
    # Guard: a wrong patch target would silently hit the real API instead.
    assert mock_request.called

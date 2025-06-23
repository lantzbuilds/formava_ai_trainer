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


@patch("app.services.hevy_api.requests.get")
def test_get_workouts_filters_by_date(mock_get, hevy_api_instance):
    # Arrange
    start_date = datetime(2025, 5, 23, tzinfo=timezone.utc)
    end_date = datetime(2025, 6, 22, tzinfo=timezone.utc)
    # One workout inside, one outside the range
    inside = make_workout("2025-06-01T10:00:00+00:00")
    outside = make_workout("2025-05-01T10:00:00+00:00")
    mock_get.return_value = MagicMock(
        status_code=200, json=lambda: mock_response([inside, outside], page_count=1)
    )

    # Act
    results = hevy_api_instance.get_workouts(start_date, end_date)

    # Assert
    assert len(results) == 1
    assert results[0]["start_time"] == inside["start_time"]


@patch("app.services.hevy_api.requests.get")
def test_get_workouts_pagination(mock_get, hevy_api_instance):
    # Arrange
    start_date = datetime(2025, 5, 23, tzinfo=timezone.utc)
    end_date = datetime(2025, 6, 22, tzinfo=timezone.utc)
    # Page 1 and 2, both with one workout in range
    page1 = make_workout("2025-06-01T10:00:00+00:00")
    page2 = make_workout("2025-06-10T10:00:00+00:00")
    # Set up side effects for pagination
    mock_get.side_effect = [
        MagicMock(status_code=200, json=lambda: mock_response([page1], page_count=2)),
        MagicMock(status_code=200, json=lambda: mock_response([page2], page_count=2)),
    ]

    # Act
    results = hevy_api_instance.get_workouts(start_date, end_date)

    # Assert
    assert len(results) == 2
    assert results[0]["start_time"] == page1["start_time"]
    assert results[1]["start_time"] == page2["start_time"]


@patch("app.services.hevy_api.requests.get")
def test_get_workouts_handles_http_error(mock_get, hevy_api_instance):
    # Arrange
    mock_response = MagicMock()
    mock_response.status_code = 401
    mock_response.text = "Unauthorized"
    mock_response.headers = {}
    mock_response.request.url = "http://fake.url"
    mock_response.request.headers = {}

    # Create the HTTPError and attach the mock_response
    http_error = requests.exceptions.HTTPError("401 Unauthorized: Invalid API key")
    http_error.response = mock_response

    # Set the side_effect to the *instance*, not the class or a lambda
    mock_response.raise_for_status.side_effect = http_error
    mock_get.return_value = mock_response

    # Act & Assert
    with pytest.raises(requests.exceptions.HTTPError) as excinfo:
        hevy_api_instance.get_workouts()
    assert "401 Unauthorized" in str(excinfo.value)

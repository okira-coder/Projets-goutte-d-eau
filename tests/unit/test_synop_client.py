from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

from src.ingestion.synop_client import SynopClient, parse_csv_row

SAMPLE_CSV = (
    "numer_sta;date;t;u;pres;ff;dd;rr3;rr24;n;ww\n"
    "07643;20240101120000;285.65;80;101500;3.2;180;0.5;1.2;75;10\n"
    "07630;20240101120000;284.15;75;101200;4.1;200;0.0;0.5;50;5\n"
)


def test_parse_csv_row_handles_kelvin_and_pascals():
    row = {
        "numer_sta": "07643",
        "date": "20240101120000",
        "t": "285.65",
        "u": "80",
        "pres": "101500",
        "ff": "3.2",
        "dd": "180",
        "rr3": "0.5",
        "rr24": "1.2",
        "n": "75",
        "ww": "10",
    }
    obs = parse_csv_row(row)
    assert obs["synop_code"] == "07643"
    assert obs["observed_at"] == datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    assert obs["temperature_c"] == 12.5  # K → °C
    assert obs["humidity_pct"] == 80
    assert obs["pressure_hpa"] == 1015.0  # Pa → hPa
    assert obs["precipitation_3h_mm"] == 0.5


def test_parse_csv_row_handles_missing_values():
    row = {
        "numer_sta": "07643",
        "date": "20240101120000",
        "t": "mq",
        "u": "",
        "pres": "mq",
        "ff": "3.2",
        "dd": "180",
        "rr3": "0.5",
        "rr24": "1.2",
        "n": "",
        "ww": "mq",
    }
    obs = parse_csv_row(row)
    assert obs["temperature_c"] is None
    assert obs["humidity_pct"] is None
    assert obs["pressure_hpa"] is None
    assert obs["cloud_cover_pct"] is None
    assert obs["weather_code"] is None


def test_client_fetch_returns_filtered_stations():
    client = SynopClient(allowed_synop_codes=["07643"])
    mock_response = MagicMock(text=SAMPLE_CSV, status_code=200)
    mock_response.raise_for_status = MagicMock()
    with patch("src.ingestion.synop_client.httpx.get", return_value=mock_response):
        result = client.fetch_hour(datetime(2024, 1, 1, 12, tzinfo=timezone.utc))
    assert len(result) == 1
    assert result[0]["synop_code"] == "07643"


def test_client_fetch_returns_empty_on_http_error():
    client = SynopClient(allowed_synop_codes=["07643"])
    with patch(
        "src.ingestion.synop_client.httpx.get",
        side_effect=Exception("network down"),
    ):
        result = client.fetch_hour(datetime(2024, 1, 1, 12, tzinfo=timezone.utc))
    assert result == []

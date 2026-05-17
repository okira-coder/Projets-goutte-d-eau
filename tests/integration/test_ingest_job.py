from datetime import datetime, timezone

from src.ingestion.ingest_job import months_in_range


def test_months_in_range_single_month():
    start = datetime(2024, 6, 1, tzinfo=timezone.utc)
    end = datetime(2024, 6, 30, tzinfo=timezone.utc)
    months = list(months_in_range(start, end))
    assert months == [(2024, 6)]


def test_months_in_range_multi_year():
    start = datetime(2023, 11, 15, tzinfo=timezone.utc)
    end = datetime(2024, 2, 5, tzinfo=timezone.utc)
    months = list(months_in_range(start, end))
    assert months == [(2023, 11), (2023, 12), (2024, 1), (2024, 2)]


def test_months_in_range_full_year():
    start = datetime(2024, 1, 1, tzinfo=timezone.utc)
    end = datetime(2024, 12, 31, tzinfo=timezone.utc)
    months = list(months_in_range(start, end))
    assert len(months) == 12
    assert months[0] == (2024, 1)
    assert months[-1] == (2024, 12)

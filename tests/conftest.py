from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import main
from src.storage import MovieStorage


@pytest.fixture
def client(tmp_path, monkeypatch):
    test_storage = MovieStorage(str(tmp_path / "movies.db"))
    monkeypatch.setattr(main, "storage", test_storage)

    with TestClient(main.app) as test_client:
        yield test_client


@pytest.fixture
def sample_csv_bytes():
    return (Path("fixtures") / "sample_movies.csv").read_bytes()


@pytest.fixture
def processing_body():
    return {
        "validation": {
            "required_columns": [
                "title",
                "release_year",
                "rating",
                "genre"
            ],
            "numeric_columns": [
                "release_year",
                "rating"
            ]
        },
        "processing": {
            "remove_duplicates": True,
            "missing": {
                "enabled": True,
                "axis": "rows"
            },
            "outliers": {
                "enabled": False,
                "columns": [],
                "method": "iqr",
                "threshold": 1.5
            }
        }
    }
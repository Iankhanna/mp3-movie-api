import pandas as pd

from src.storage import MovieStorage

MOVIE_CSV = (
    b"title,release_year,rating,genre\n"
    b"Movie A,2020,8.0,Drama\n"
    b"Movie B,2021,8.5,Comedy\n"
    b"Movie C,2022,9.0,Action\n"
)


def upload(client, content=MOVIE_CSV, filename="movies.csv"):
    return client.post(
        "/upload",
        files={"file": (filename, content, "text/csv")}
    )


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "version": "1.0.0"
    }
    assert "x-request-id" in response.headers


def test_upload(client):
    response = upload(client)
    assert response.status_code == 200
    assert response.json() == {
        "filename": "movies.csv",
        "rows": 3,
        "columns": 4,
        "column_names": [
            "title",
            "release_year",
            "rating",
            "genre"
        ]
    }


def test_sample_upload(client, sample_csv_bytes):
    response = upload(
        client,
        sample_csv_bytes,
        "sample_movies.csv"
    )
    assert response.status_code == 200
    assert response.json()["rows"] == 20
    assert response.json()["columns"] == 4


def test_get_movies(client):
    upload(client)
    response = client.get("/movies")
    assert response.status_code == 200
    data = response.json()
    assert data["total_rows"] == 3
    assert len(data["data"]) == 3
    assert data["data"][0]["title"] == "Movie A"


def test_movie_limit(client):
    upload(client)
    response = client.get("/movies?limit=2")
    assert response.status_code == 200
    assert response.json()["total_rows"] == 3
    assert len(response.json()["data"]) == 2


def test_invalid_limit(client):
    response = client.get("/movies?limit=-1")
    assert response.status_code == 422


def test_search_movies(client):
    upload(client)
    response = client.get(
        "/movies/search",
        params={"min_rating": 8.5, "limit": 2}
    )
    assert response.status_code == 200
    data = response.json()
    assert [row["title"] for row in data] == [
        "Movie C",
        "Movie B"
    ]
    assert all(set(row) == {"id", "title"} for row in data)


def test_search_selected_columns(client):
    upload(client)
    response = client.get(
        "/movies/search",
        params=[
            ("columns", "title"),
            ("columns", "rating"),
            ("min_rating", "8.5"),
            ("limit", "2")
        ]
    )
    assert response.status_code == 200
    data = response.json()
    assert data[0]["title"] == "Movie C"
    assert data[0]["rating"] == 9.0
    assert data[1]["title"] == "Movie B"
    assert data[1]["rating"] == 8.5


def test_invalid_search_column(client):
    upload(client)
    response = client.get(
        "/movies/search",
        params={"columns": "invalid"}
    )
    assert response.status_code == 400


def test_search_no_matches(client):
    upload(client)
    response = client.get(
        "/movies/search",
        params={"min_rating": 9.9}
    )
    assert response.status_code == 200
    assert response.json() == []


def test_upload_replaces_movies(client):
    upload(client)
    upload(client)
    response = client.get("/movies")
    assert response.json()["total_rows"] == 3


def test_invalid_extension(client):
    response = upload(
        client,
        b"hello world",
        "notes.txt"
    )
    assert response.status_code == 400


def test_invalid_columns(client):
    response = upload(
        client,
        b"title,rating\nMovie A,8.0\n"
    )
    assert response.status_code == 400


def test_empty_csv(client):
    response = upload(
        client,
        b"title,release_year,rating,genre\n"
    )
    assert response.status_code == 400


def test_empty_database(client):
    response = client.get("/movies")
    assert response.status_code == 200
    assert response.json() == {
        "data": [],
        "total_rows": 0
    }


def test_process_empty_database(client, processing_body):
    response = client.post(
        "/movies/process",
        json=processing_body
    )
    assert response.status_code == 400


def test_process_movies(client, processing_body):
    csv_content = (
        b"title,release_year,rating,genre\n"
        b"Movie A,2020,8.0,Drama\n"
        b"Movie B,2021,8.5,Comedy\n"
        b"Movie B,2021,8.5,Comedy\n"
        b"Movie C,2022,9.0,Action\n"
    )
    assert upload(client, csv_content).status_code == 200

    response = client.post(
        "/movies/process",
        json=processing_body
    )
    assert response.status_code == 200

    report = response.json()
    assert report["validation_rows_removed"] == 0
    assert report["cleaning_report"]["rows_before"] == 4
    assert report["cleaning_report"]["rows_after"] == 3

    retrieved = client.get("/movies")
    assert retrieved.json()["total_rows"] == 3


def test_persistence(tmp_path):
    db_path = str(tmp_path / "persistent.db")

    first = MovieStorage(db_path)
    df = pd.DataFrame({
        "title": ["Movie A"],
        "release_year": [2020],
        "rating": [8.0],
        "genre": ["Drama"]
    })
    first.save(df)

    second = MovieStorage(db_path)
    assert second.count_movies() == 1
    assert second.get().iloc[0]["title"] == "Movie A"


def test_null_values(tmp_path):
    storage = MovieStorage(str(tmp_path / "nulls.db"))
    df = pd.DataFrame({
        "title": ["Movie A"],
        "release_year": [2020],
        "rating": [None],
        "genre": ["Drama"]
    })
    storage.save(df)
    assert pd.isna(storage.get().iloc[0]["rating"])

def test_movies_persist(client, test_storage, uploaded_movies):
    second_storage = MovieStorage(test_storage.db_path)

    movies = second_storage.get()

    assert len(movies) == 20
    assert list(movies.columns) == [
        "title",
        "release_year",
        "rating",
        "genre"
    ]

    expected_titles = [
        "Movie A",
        "Movie B",
        "Movie B",
        "Movie C",
        "Movie D",
        "Movie D",
        "Movie E",
        "Movie F",
        "Movie G",
        "Movie H",
        "Movie I",
        "Movie J",
        "Movie K",
        "Movie L",
        "Movie M",
        "Movie N",
        "Movie O",
        "Movie P",
        "Movie Q",
        "Movie R"
    ]

    assert movies["title"].tolist() == expected_titles

    stored_records = second_storage.select_columns(
        ["title", "release_year", "rating", "genre"],
        100
    )

    response = client.get("/movies?limit=100")

    assert response.status_code == 200
    assert response.json()["total_rows"] == 20

    expected_ids = list(range(1, 21))

    assert [row["id"] for row in stored_records] == expected_ids
    assert [row["id"] for row in response.json()["data"]] == expected_ids

def test_cache_and_processing(client, uploaded_movies, processing_body):
    import main

    response_100 = client.get("/movies?limit=100")
    assert response_100.status_code == 200
    assert response_100.json()["total_rows"] == 20
    assert main.cache.get(100) == response_100.json()

    response_1 = client.get("/movies?limit=1")
    assert response_1.status_code == 200
    assert len(response_1.json()["data"]) == 1
    assert main.cache.get(1) == response_1.json()

    repeated_response = client.get("/movies?limit=100")
    assert repeated_response.status_code == 200
    assert repeated_response.json() == response_100.json()

    process_response = client.post(
        "/movies/process",
        json=processing_body
    )

    assert process_response.status_code == 200

    report = process_response.json()
    assert report["validation_rows_removed"] == 0
    assert report["cleaning_report"]["rows_before"] == 20
    assert report["cleaning_report"]["rows_after"] == 16
    assert report["cleaning_report"]["rows_removed"] == 4

    assert main.cache.get(100) is None
    assert main.cache.get(1) is None

    updated_response = client.get("/movies?limit=100")

    assert updated_response.status_code == 200

    updated_data = updated_response.json()

    assert updated_data["total_rows"] == 16
    assert len(updated_data["data"]) == 16
    assert [row["title"] for row in updated_data["data"]] == [
        f"Movie {letter}" for letter in "ABCDEFGHIJKLMNOP"
    ]
    assert [row["id"] for row in updated_data["data"]] == list(range(1, 17))

    assert main.cache.get(100) == updated_data

def test_cache_hit_skips_database(client, uploaded_movies, monkeypatch):
    first_response = client.get("/movies?limit=100")

    assert first_response.status_code == 200
    assert first_response.json()["total_rows"] == 20

    import main

    def fail_if_called(*args, **kwargs):
        raise AssertionError("Database should not be queried on cache hit")

    monkeypatch.setattr(main.storage, "select_columns", fail_if_called)
    monkeypatch.setattr(main.storage, "count_movies", fail_if_called)

    second_response = client.get("/movies?limit=100")

    assert second_response.status_code == 200
    assert second_response.json() == first_response.json()

def test_cache_hit_skips_database(client, uploaded_movies, monkeypatch):
    import main

    first_response = client.get("/movies?limit=100")

    assert first_response.status_code == 200
    assert first_response.json()["total_rows"] == 20

    def fail_if_called(*args, **kwargs):
        raise AssertionError("Database should not be queried on cache hit")

    monkeypatch.setattr(main.storage, "select_columns", fail_if_called)
    monkeypatch.setattr(main.storage, "count_movies", fail_if_called)

    second_response = client.get("/movies?limit=100")

    assert second_response.status_code == 200
    assert second_response.json() == first_response.json()
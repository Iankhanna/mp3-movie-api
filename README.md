# Movie Processing API

I built a REST API built with FastAPI for uploading, storing, retrieving, searching, and processing movie datasets. The application uses SQLite for persistent storage and fakeredis for caching.

## Features

- Upload CSV files containing movie data.
- Store and retrieve movies using SQLite.
- Search movies by rating and selected columns.
- Process datasets by removing duplicates, handling missing values, and detecting outliers.
- Cache movie retrieval responses for 90 seconds using fakeredis.
- Automatically invalidate the cache when movie data changes.
- Test API functionality using pytest.

## Installation

Clone the repository and navigate to the project directory:

```bash
git clone https://github.com/Iankhanna/mp3-movie-api.git
cd mp3-movie-api
```

Create and activate a virtual environment:

```bash
python3 -m venv venv
source venv/bin/activate
```

Install dependencies:

```bash
python -m pip install -r requirements.txt
```

## Running the API

Start the FastAPI server:

```bash
python -m uvicorn main:app --reload
```

Open http://127.0.0.1:8000/docs to access the interactive API documentation.

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Check API status |
| POST | `/upload` | Upload a movie CSV dataset |
| GET | `/movies` | Retrieve movies with an optional limit |
| GET | `/movies/search` | Search movies by rating and columns |
| POST | `/movies/process` | Validate and clean stored movie data |

Uploaded CSV files must contain the following columns:

`title`, `release_year`, `rating`, `genre`

## Database and Caching

Movie records are stored in SQLite, allowing data to persist across server restarts.

The `/movies` endpoint uses fakeredis to cache responses for 90 seconds. Cache entries are stored separately for different query limits.

The cache is automatically invalidated whenever movies are uploaded or processed, ensuring updated data is returned.

## Testing

Run the automated tests using:

```bash
python -m pytest tests -v
```

The test suite covers API endpoints, input validation, database persistence, data processing, and caching.

All 22 automated tests passed during local testing.


## Example Processing Request

After uploading `fixtures/sample_movies.csv`, send POST `/movies/process` with:

```json
{
  "validation": {
    "required_columns": ["title", "release_year", "rating", "genre"],
    "numeric_columns": ["release_year", "rating"]
  },
  "processing": {
    "remove_duplicates": true,
    "missing": {
      "enabled": true,
      "axis": "rows"
    },
    "outliers": {
      "enabled": true,
      "columns": ["rating"],
      "method": "iqr",
      "threshold": 1.5
    }
  }
}
```

Expected response:

```json
{
  "validation_rows_removed": 0,
  "cleaning_report": {
    "rows_before": 20,
    "rows_after": 16,
    "rows_removed": 4,
    "columns_before": 4,
    "columns_after": 4,
    "columns_removed": 0
  }
}
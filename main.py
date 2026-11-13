
import io
import json
import logging

from pathlib import Path

import pandas as pd
from fastapi import FastAPI, File, HTTPException, Query, UploadFile

from src import (
    HealthResponse,
    MovieStorage,
    MovieCache,
    MovieUploadInfo,
    MovieDataResponse,
    MovieProcessingReport,
    ProcessConfig,
    setup_logging,
    log_requests,
)
from src.storage import MOVIE_COLUMNS

from data_pipeline import (
    process_data,
    validate_dataframe,
    create_cleaning_report,
)


setup_logging(verbose=True)
logger = logging.getLogger(__name__)

app = FastAPI(title="Movie Processing API", version="1.0.0")

app.middleware("http")(log_requests)

storage = MovieStorage()
cache = MovieCache()


@app.get("/health", response_model=HealthResponse)
def health_check():
    return {
        "status": "ok",
        "version": "1.0.0"
    }


@app.post("/upload", response_model=MovieUploadInfo)
async def upload_movies(file: UploadFile = File(...)):
    extension = Path(file.filename or "").suffix.lower()

    if extension != ".csv":
        logger.warning(f"Unsupported file format: {extension}")
        raise HTTPException(
            status_code=400,
            detail="Only CSV files are supported"
        )

    try:
        contents = await file.read()
        df = pd.read_csv(io.BytesIO(contents))

    except (
        pd.errors.EmptyDataError,
        pd.errors.ParserError,
        UnicodeDecodeError
    ):
        logger.warning("Could not read uploaded CSV file")
        raise HTTPException(
            status_code=400,
            detail="Could not read CSV file"
        )

    if len(df.columns) != len(MOVIE_COLUMNS) or set(df.columns) != set(MOVIE_COLUMNS):
        raise HTTPException(
            status_code=400,
            detail=f"CSV must contain exactly these columns: {MOVIE_COLUMNS}"
        )

    if df.empty:
        raise HTTPException(
            status_code=400,
            detail="CSV must contain at least one movie"
        )

    df = df[MOVIE_COLUMNS]

    storage.save(df)
    cache.invalidate()

    logger.info(
        f"Uploaded movies: filename={file.filename}, rows={len(df)}"
    )

    return {
        "filename": file.filename,
        "rows": len(df),
        "columns": len(df.columns),
        "column_names": list(df.columns)
    }


@app.get("/movies", response_model=MovieDataResponse)
def get_movies(limit: int = Query(default=100, ge=1)):
    cached_response = cache.get(limit)

    if cached_response is not None:
        logger.info(f"Cache hit for movies: limit={limit}")
        return cached_response

    total_rows = storage.count_movies()

    if total_rows == 0:
        response = {
            "data": [],
            "total_rows": 0
        }
        cache.set(limit, response)
        logger.info("Retrieved movies: rows=0")
        return response

    records = storage.select_columns(MOVIE_COLUMNS, limit)

    response = {
        "data": records,
        "total_rows": total_rows
    }

    cache.set(limit, response)
    logger.info(f"Retrieved movies: rows={len(records)}")
    return response


@app.get("/movies/search", response_model=list[dict])
def query_movies(
    columns: list[str] = Query(default=["title"]),
    min_rating: float = Query(default=0, ge=0, le=10),
    limit: int = Query(default=100, ge=1)
):
    try:
        records = storage.query_movies(
            columns,
            min_rating,
            limit
        )

    except ValueError as e:
        logger.warning(f"Movie query failed: {e}")
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )

    logger.info(
        f"Queried movies: columns={columns}, "
        f"min_rating={min_rating}, returned_rows={len(records)}"
    )

    return records


@app.post("/movies/process", response_model=MovieProcessingReport)
def process_movies(config: ProcessConfig):
    df = storage.get()

    if df.empty:
        logger.warning("No movies available for processing")
        raise HTTPException(
            status_code=400,
            detail="No movies available for processing"
        )

    validation = config.validation

    missing_numeric = [
        col for col in validation.numeric_columns
        if col not in df.columns
    ]

    if missing_numeric:
        raise HTTPException(
            status_code=400,
            detail=f"Numeric columns not found: {missing_numeric}"
        )

    original_rows = len(df)

    try:
        validated_df = validate_dataframe(
            df.copy(),
            validation.required_columns,
            validation.numeric_columns
        )

    except ValueError as e:
        logger.warning(f"Movie validation failed: {e}")
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )

    validation_rows_removed = original_rows - len(validated_df)

    try:
        cleaned_df = process_data(
            validated_df.copy(),
            config.model_dump()
        )

    except ValueError as e:
        logger.warning(f"Movie processing failed: {e}")
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )

    cleaning_report = create_cleaning_report(
        validated_df,
        cleaned_df
    )

    storage.save(cleaned_df)
    cache.invalidate()

    logger.info(
        f"Processed movies: "
        f"validation_removed={validation_rows_removed}, "
        f"rows_before={len(validated_df)}, "
        f"rows_after={len(cleaned_df)}"
    )

    return {
        "validation_rows_removed": validation_rows_removed,
        "cleaning_report": cleaning_report
    }

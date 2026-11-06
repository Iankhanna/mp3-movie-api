
import logging
import sqlite3

import pandas as pd

from .database import get_connection, initialize_database

logger = logging.getLogger(__name__)
MOVIE_COLUMNS = ["title", "release_year", "rating", "genre"]


class MovieStorage:
    def __init__(self, db_path="data/movies.db"):
        self.db_path = db_path
        initialize_database(self.db_path)

    def save(self, df):
        connection = get_connection(self.db_path)
        try:
            records = [
                tuple(None if pd.isna(value) else value for value in row)
                for row in df[MOVIE_COLUMNS].itertuples(index=False, name=None)
            ]
            
            connection.execute("DELETE FROM movies")
            connection.executemany(
                """
                INSERT INTO movies (title, release_year, rating, genre)
                VALUES (?, ?, ?, ?)
                """,
                records
            )
            connection.commit()
            logger.debug(f"Stored movies in SQLite: rows={len(records)}")
        except sqlite3.Error:
            connection.rollback()
            raise
        finally:
            connection.close()

    def get(self):
        connection = get_connection(self.db_path)
        try:
            cursor = connection.execute(
                """
                SELECT title, release_year, rating, genre
                FROM movies
                ORDER BY id
                """
            )
            rows = cursor.fetchall()
            return pd.DataFrame(
                [dict(row) for row in rows],
                columns=MOVIE_COLUMNS
            )
        finally:
            connection.close()

    def select_columns(self, columns, limit=5):
        if not columns:
            logger.error("Select at least one column")
            raise ValueError("Select at least one column")

        for column in columns:
            if column not in MOVIE_COLUMNS:
                logger.error(f"Unsupported column: {column}")
                raise ValueError(f"Unsupported column: {column}")

        selected_columns = ", ".join(["id"] + columns)
        connection = get_connection(self.db_path)
        try:
            cursor = connection.execute(
                f"SELECT {selected_columns} FROM movies ORDER BY id LIMIT ?",
                (limit,)
            )
            rows = [dict(row) for row in cursor.fetchall()]
            logger.debug(f"Selected columns: {columns}, rows={len(rows)}")
            return rows
        finally:
            connection.close()

    def count_movies(self):
        connection = get_connection(self.db_path)
        try:
            cursor = connection.execute(
                "SELECT COUNT(*) FROM movies"
            )
            return cursor.fetchone()[0]
        finally:
            connection.close()

    def query_movies(self, columns, min_rating, limit):
        if not columns:
            logger.error("Select at least one column")
            raise ValueError("Select at least one column")

        for column in columns:
            if column not in MOVIE_COLUMNS:
                logger.error(f"Unsupported column: {column}")
                raise ValueError(f"Unsupported column: {column}")

        selected_columns = ", ".join(["id"] + columns)
        connection = get_connection(self.db_path)
        try:
            cursor = connection.execute(
                f"""
                SELECT {selected_columns}
                FROM movies
                WHERE rating >= ?
                ORDER BY rating DESC, id ASC
                LIMIT ?
                """,
                (min_rating, limit)
            )
            rows = [dict(row) for row in cursor.fetchall()]
            logger.debug(
                f"Queried movies: columns={columns}, rows={len(rows)}"
            )
            return rows
        finally:
            connection.close()

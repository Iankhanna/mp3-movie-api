import logging
import pandas as pd
#Checks required columns and invalid numeric values.
logger = logging.getLogger(__name__)


def validate_dataframe(df, required_columns, numeric_columns):
    """Validate the DataFrame and return valid data."""
    rows_before = len(df)
    for col in required_columns:
        if col not in df.columns:
            logger.error(f"Required column missing: {col}")
            raise ValueError(f"Required column missing: {col}")
    for col in numeric_columns:
        invalid_rows = []
        for i, value in df[col].items():
            if pd.notna(value):
                try:
                    float(value)
                except ValueError:
                    invalid_rows.append(i)
        if invalid_rows:
            logger.warning(
                f"Removed {len(invalid_rows)} rows with invalid numeric values in {col}"
            )
            df = df.drop(index=invalid_rows)
        df[col] = pd.to_numeric(df[col])
    logger.debug(f"Validation: {rows_before} -> {len(df)} rows")
    return df
import logging
import pandas as pd
#Removes duplicates, missing values, and outliers.
logger = logging.getLogger(__name__)

def remove_duplicates(df):
    """Remove duplicate rows."""
    before = len(df)
    df = df.drop_duplicates()
    logger.debug(f"Removed {before - len(df)} duplicate rows")
    return df

def handle_missing(df, axis="rows"):
    """Drop rows or columns containing missing values."""
    if axis == "rows":
        before = len(df)
        df = df.dropna()
        logger.debug(f"Dropped {before - len(df)} rows with missing values")
    elif axis == "columns":
        before = df.shape[1]
        df = df.dropna(axis=1)
        logger.debug(f"Dropped {before - df.shape[1]} columns with missing values")
    else:
        logger.error(f"Unsupported axis: {axis}")
        raise ValueError(f"Unsupported axis: {axis}")
    return df

def remove_outliers(df, columns, method, threshold):
    """Remove outliers from the specified numeric columns."""
    supported_methods = ["iqr", "zscore"]
    if method not in supported_methods:
        logger.error(f"Unsupported method: {method}")
        raise ValueError(f"Unsupported method: {method}")
    for column in columns:
        if column not in df.columns:
            logger.warning(f"Column does not exist: {column}")
            continue
        if not pd.api.types.is_numeric_dtype(df[column]):
            logger.warning(f"Column is not numeric: {column}")
            continue
        before = len(df)
        if method == "iqr":
            q1 = df[column].quantile(0.25)
            q3 = df[column].quantile(0.75)
            iqr = q3 - q1
            lower = q1 - threshold * iqr
            upper = q3 + threshold * iqr
            df = df[(df[column] >= lower) & (df[column] <= upper)]
        elif method == "zscore":
            mean = df[column].mean()
            std = df[column].std()
            z_scores = (df[column] - mean)/std
            df = df[z_scores.abs() <= threshold]
        logger.debug(f"{column}: method={method}, threshold={threshold}, "f"removed={before - len(df)}")
    return df

def process_data(df, config):
    """Apply the processing steps enabled in the configuration."""
    processing = config["processing"]
    if processing["remove_duplicates"]:
        df = remove_duplicates(df)
    if processing["missing"]["enabled"]:
        df = handle_missing(df,processing["missing"]["axis"])
    if processing["outliers"]["enabled"]:
        df = remove_outliers(df,processing["outliers"]["columns"],processing["outliers"]["method"],processing["outliers"]["threshold"])
    return df

def create_cleaning_report(df_before, df_after):
    """Return a dictionary summarizing the cleaning results."""
    report = {"rows_before": df_before.shape[0],"rows_after": df_after.shape[0],"rows_removed": df_before.shape[0] - df_after.shape[0],
              "columns_before": df_before.shape[1],"columns_after": df_after.shape[1],"columns_removed": df_before.shape[1] - df_after.shape[1]}
    return report
"""Bronze transform: keep the latest change per primary key."""
from pyspark.sql import DataFrame, Window
from pyspark.sql import functions as F


def latest_per_key(df: DataFrame, pk: str) -> DataFrame:
    """Return one row per primary key: the one with the highest change_version.

    Rows from the full load have no change_version, so they count as version 0.
    A winning row whose change_operation is 'D' is kept and flagged _is_deleted.
    """
    if "change_version" not in df.columns:
        df = df.withColumn("change_version", F.lit(None).cast("long"))
    if "change_operation" not in df.columns:
        df = df.withColumn("change_operation", F.lit(None).cast("string"))

    df = df.withColumn("change_version", F.coalesce(F.col("change_version"), F.lit(0)).cast("long"))

    order_cols = [F.col("change_version").desc()]
    if "_source_file" in df.columns:
        order_cols.append(F.col("_source_file").desc())
    newest_first = Window.partitionBy(pk).orderBy(*order_cols)
    latest = (
        df.withColumn("_rn", F.row_number().over(newest_first))
        .filter(F.col("_rn") == 1)
        .drop("_rn")
    )
    return (
        latest.withColumn("_is_deleted", F.coalesce(F.col("change_operation") == "D", F.lit(False)))
        .withColumnRenamed("change_version", "_change_version")
        .drop("change_operation")
    )


import os
import sys

import pytest
from pyspark.sql import SparkSession
from pyspark.sql.types import LongType, StringType, StructField, StructType

from bronze_transform import latest_per_key

os.environ.setdefault("PYSPARK_PYTHON", sys.executable)
os.environ.setdefault("SPARK_LOCAL_IP", "127.0.0.1")


@pytest.fixture(scope="module")
def spark():
    session = (
        SparkSession.builder.master("local[1]")
        .config("spark.ui.enabled", "false")
        .config("spark.driver.bindAddress", "127.0.0.1")
        .config("spark.driver.host", "127.0.0.1")
        .config("spark.sql.shuffle.partitions", "1")
        .getOrCreate()
    )
    yield session
    session.stop()


FULL = StructType([StructField("CustomerID", LongType()), StructField("City", StringType())])
INCR = StructType([
    StructField("CustomerID", LongType()),
    StructField("City", StringType()),
    StructField("change_operation", StringType()),
    StructField("change_version", LongType()),
])


def run(spark):
    full = spark.createDataFrame([(7, "A"), (8, "A"), (9, "A")], FULL)
    incr = spark.createDataFrame(
        [(7, "B", "U", 73), (7, "C", "U", 80), (9, None, "D", 75)], INCR
    )
    both = full.unionByName(incr, allowMissingColumns=True)
    return {r["CustomerID"]: r for r in latest_per_key(both, "CustomerID").collect()}


def test_one_row_per_key(spark):
    assert len(run(spark)) == 3


def test_highest_version_wins(spark):
    row = run(spark)[7]
    assert row["City"] == "C" and row["_change_version"] == 80


def test_untouched_row_comes_from_full_load(spark):
    row = run(spark)[8]
    assert row["City"] == "A" and row["_change_version"] == 0 and row["_is_deleted"] is False


def test_delete_is_flagged_not_dropped(spark):
    row = run(spark)[9]
    assert row["_is_deleted"] is True


import sys
from awsglue.utils import getResolvedOptions
from pyspark import SparkConf
from pyspark.context import SparkContext
from pyspark.sql import functions as F
from awsglue.context import GlueContext

from bronze_transform import latest_per_key

args = getResolvedOptions(
    sys.argv, ["raw_bucket", "bronze_bucket", "table", "pk", "database"]
)
CATALOG = "glue_catalog"
target = f"{CATALOG}.{args['database']}.{args['table']}"

conf = (
    SparkConf()
    .set("spark.sql.extensions", "org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions")
    .set(f"spark.sql.catalog.{CATALOG}", "org.apache.iceberg.spark.SparkCatalog")
    .set(f"spark.sql.catalog.{CATALOG}.catalog-impl", "org.apache.iceberg.aws.glue.GlueCatalog")
    .set(f"spark.sql.catalog.{CATALOG}.io-impl", "org.apache.iceberg.aws.s3.S3FileIO")
    .set(f"spark.sql.catalog.{CATALOG}.warehouse", f"s3://{args['bronze_bucket']}/warehouse/")
)
sc = SparkContext(conf=conf)
spark = GlueContext(sc).spark_session

# 1. Read every parquet file raw holds for this table (full load + all incremental runs)
raw_path = f"s3://{args['raw_bucket']}/{args['table']}/"
raw = (
    spark.read.option("recursiveFileLookup", "true")
    .option("pathGlobFilter", "*.parquet")
    .option("mergeSchema", "true")
    .parquet(raw_path)
    .withColumn("_source_file", F.input_file_name())
)

# 2. Keep the latest change per key (the rule we unit-tested)
latest = latest_per_key(raw, args["pk"]).withColumn("_loaded_at", F.current_timestamp())

# 3. Create the table the first time, MERGE every time after
if not spark.catalog.tableExists(target):
    latest.writeTo(target).using("iceberg").create()
else:
    latest.createOrReplaceTempView("updates")
    spark.sql(f"""
        MERGE INTO {target} t
        USING updates u
        ON t.{args['pk']} = u.{args['pk']}
        WHEN MATCHED AND (u._change_version > t._change_version OR (u._change_version = t._change_version AND u._source_file > t._source_file)) THEN UPDATE SET *
        WHEN NOT MATCHED THEN INSERT *
    """)

print(f"bronze rows now: {spark.table(target).count()}")


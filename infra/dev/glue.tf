data "aws_caller_identity" "glue" {}

locals {
  glue_layers     = ["raw", "bronze", "silver", "gold", "ops"]
  glue_raw_bucket = "dev-pipeline-raw-${data.aws_caller_identity.glue.account_id}"
}

# One Glue database per lake layer. A database is only a labelled shelf.
resource "aws_glue_catalog_database" "layer" {
  for_each    = toset(local.glue_layers)
  name        = "dev_pipeline_${each.key}"
  description = "Dev pipeline ${each.key} layer"
}

# The first table: the pipeline run log. Files already exist in S3.
resource "aws_glue_catalog_table" "run_log" {
  database_name = aws_glue_catalog_database.layer["ops"].name
  name          = "run_log"
  table_type    = "EXTERNAL_TABLE"
  description   = "One row per table per pipeline run, exported as Parquet"

  parameters = {
    classification                      = "parquet"
    "projection.enabled"                = "true"
    "projection.run_date.type"          = "date"
    "projection.run_date.format"        = "yyyy-MM-dd"
    "projection.run_date.range"         = "2026-11-01,NOW"
    "projection.run_date.interval"      = "1"
    "projection.run_date.interval.unit" = "DAYS"
    "storage.location.template"         = "s3://${local.glue_raw_bucket}/ops/run_log/run_date=$${run_date}/"
  }

  partition_keys {
    name = "run_date"
    type = "string"
  }

  storage_descriptor {
    location      = "s3://${local.glue_raw_bucket}/ops/run_log/"
    input_format  = "org.apache.hadoop.hive.ql.io.parquet.MapredParquetInputFormat"
    output_format = "org.apache.hadoop.hive.ql.io.parquet.MapredParquetOutputFormat"

    ser_de_info {
      serialization_library = "org.apache.hadoop.hive.ql.io.parquet.serde.ParquetHiveSerDe"
    }

    columns {
      name = "log_id"
      type = "bigint"
    }
    columns {
      name = "run_id"
      type = "string"
    }
    columns {
      name = "table_name"
      type = "string"
    }
    columns {
      name = "layer"
      type = "string"
    }
    columns {
      name = "load_type"
      type = "string"
    }
    columns {
      name = "status"
      type = "string"
    }
    columns {
      name = "rows_in"
      type = "bigint"
    }
    columns {
      name = "rows_out"
      type = "bigint"
    }
    columns {
      name = "rows_rejected"
      type = "bigint"
    }
    columns {
      name = "started_at"
      type = "timestamp"
    }
    columns {
      name = "finished_at"
      type = "timestamp"
    }
    columns {
      name = "message"
      type = "string"
    }
  }
}

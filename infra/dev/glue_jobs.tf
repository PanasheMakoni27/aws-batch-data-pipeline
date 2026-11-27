# DAY-11: Glue job that builds the bronze customers table (Iceberg)

locals {
  bronze_code_prefix = "_code"
  bronze_job_files = {
    "glue_bronze_job.py"  = "${path.module}/../../src/glue_bronze_job.py"
    "bronze_transform.py" = "${path.module}/../../src/bronze_transform.py"
  }
}

# 1. Upload the scripts (re-uploaded only when the file content changes)
resource "aws_s3_object" "bronze_code" {
  for_each               = local.bronze_job_files
  bucket                 = aws_s3_bucket.layer["bronze"].id
  key                    = "${local.bronze_code_prefix}/${each.key}"
  source                 = each.value
  source_hash            = filemd5(each.value)
  server_side_encryption = "aws:kms"
  kms_key_id             = aws_kms_key.data.arn
}

# 2. Extra permissions the bronze role needs on top of glue_perms
data "aws_iam_policy_document" "glue_bronze_extra" {
  statement {
    sid       = "ReadOwnBronzeFiles"
    actions   = ["s3:GetObject"]
    resources = ["${aws_s3_bucket.layer["bronze"].arn}/*"]
  }
  statement {
    sid = "BronzeCatalog"
    actions = [
      "glue:GetDatabase", "glue:GetDatabases",
      "glue:GetTable", "glue:GetTables",
      "glue:CreateTable", "glue:UpdateTable", "glue:DeleteTable",
      "glue:GetPartitions", "glue:GetPartition",
    ]
    resources = [
      "arn:aws:glue:us-east-1:${local.account_id}:catalog",
      "arn:aws:glue:us-east-1:${local.account_id}:database/${aws_glue_catalog_database.layer["bronze"].name}",
      "arn:aws:glue:us-east-1:${local.account_id}:table/${aws_glue_catalog_database.layer["bronze"].name}/*",
    ]
  }
}

resource "aws_iam_role_policy" "glue_bronze_extra" {
  name   = "glue-bronze-extra"
  role   = aws_iam_role.glue["bronze"].id
  policy = data.aws_iam_policy_document.glue_bronze_extra.json
}

# 3. The job itself
resource "aws_glue_job" "bronze" {
  for_each          = local.bronze_tables
  name              = "dev-pipeline-bronze-${each.key}"
  role_arn          = aws_iam_role.glue["bronze"].arn
  glue_version      = "5.0"
  worker_type       = "G.1X"
  number_of_workers = 2
  timeout           = 10
  max_retries       = 0

  command {
    name            = "glueetl"
    python_version  = "3"
    script_location = "s3://${aws_s3_bucket.layer["bronze"].id}/${local.bronze_code_prefix}/glue_bronze_job.py"
  }

  default_arguments = {
    "--datalake-formats"      = "iceberg"
    "--enable-spark-ui"       = "true"
    "--spark-event-logs-path" = "s3://${aws_s3_bucket.layer["bronze"].id}/_spark-logs/"
    "--extra-py-files"        = "s3://${aws_s3_bucket.layer["bronze"].id}/${local.bronze_code_prefix}/bronze_transform.py"
    "--raw_bucket"            = aws_s3_bucket.layer["raw"].id
    "--bronze_bucket"         = aws_s3_bucket.layer["bronze"].id
    "--table"                 = each.key
    "--pk"                    = each.value
    "--database"              = aws_glue_catalog_database.layer["bronze"].name
  }

  depends_on = [aws_s3_object.bronze_code, aws_iam_role_policy.glue_bronze_extra]
}

# Let the human user run and watch this job (and nothing else in Glue)
locals {
  me = element(split("/", data.aws_caller_identity.current.arn), 1)
}

data "aws_iam_policy_document" "run_bronze_job" {
  statement {
    sid = "RunAndWatchBronzeJob"
    actions = [
      "glue:StartJobRun", "glue:GetJob", "glue:GetJobRun",
      "glue:GetJobRuns", "glue:BatchStopJobRun",
    ]
    resources = [for j in aws_glue_job.bronze : j.arn]
  }
  statement {
    sid       = "ReadGlueLogs"
    actions   = ["logs:DescribeLogStreams", "logs:GetLogEvents", "logs:FilterLogEvents", "logs:DescribeLogGroups"]
    resources = ["arn:aws:logs:us-east-1:${local.account_id}:log-group:/aws-glue/*"]
  }
}

resource "aws_iam_user_policy" "run_bronze_job" {
  name   = "run-bronze-job"
  user   = local.me
  policy = data.aws_iam_policy_document.run_bronze_job.json
}

locals {
  bronze_tables = {
    customers         = "CustomerID"
    accounts          = "AccountID"
    transactions      = "TransactionID"
    branches          = "BranchID"
    account_types     = "AccountTypeID"
    transaction_types = "TransactionTypeID"
  }
}

moved {
  from = aws_glue_job.bronze_customers
  to   = aws_glue_job.bronze["customers"]
}

variable "enable_airflow" {
  type    = bool
  default = false
}

locals {
  airflow_on   = var.enable_airflow ? 1 : 0
  airflow_name = "${local.name}-airflow"
}

# ---------- temporary outbound internet (IGW + NAT) ----------
resource "aws_internet_gateway" "airflow" {
  count  = local.airflow_on
  vpc_id = aws_vpc.main.id
  tags   = { Name = "${local.airflow_name}-igw" }
}

resource "aws_subnet" "airflow_public" {
  count             = local.airflow_on
  vpc_id            = aws_vpc.main.id
  cidr_block        = "10.10.100.0/24"
  availability_zone = data.aws_availability_zones.available.names[0]
  tags              = { Name = "${local.airflow_name}-public" }
}

resource "aws_route_table" "airflow_public" {
  count  = local.airflow_on
  vpc_id = aws_vpc.main.id
  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.airflow[0].id
  }
  tags = { Name = "${local.airflow_name}-public-rt" }
}

resource "aws_route_table_association" "airflow_public" {
  count          = local.airflow_on
  subnet_id      = aws_subnet.airflow_public[0].id
  route_table_id = aws_route_table.airflow_public[0].id
}

resource "aws_eip" "airflow_nat" {
  count  = local.airflow_on
  domain = "vpc"
  tags   = { Name = "${local.airflow_name}-nat-eip" }
}

resource "aws_nat_gateway" "airflow" {
  count         = local.airflow_on
  allocation_id = aws_eip.airflow_nat[0].id
  subnet_id     = aws_subnet.airflow_public[0].id
  tags          = { Name = "${local.airflow_name}-nat" }
  depends_on    = [aws_internet_gateway.airflow]
}

resource "aws_route" "private_to_nat" {
  count                  = local.airflow_on
  route_table_id         = aws_route_table.private.id
  destination_cidr_block = "0.0.0.0/0"
  nat_gateway_id         = aws_nat_gateway.airflow[0].id
}

# ---------- DAG bucket ----------
resource "aws_s3_bucket" "airflow" {
  count         = local.airflow_on
  bucket        = "${local.airflow_name}-${data.aws_caller_identity.current.account_id}"
  force_destroy = true
}

resource "aws_s3_bucket_versioning" "airflow" {
  count  = local.airflow_on
  bucket = aws_s3_bucket.airflow[0].id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_public_access_block" "airflow" {
  count                   = local.airflow_on
  bucket                  = aws_s3_bucket.airflow[0].id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_object" "airflow_dag" {
  count      = local.airflow_on
  bucket     = aws_s3_bucket.airflow[0].id
  key        = "dags/bronze_pipeline.py"
  source     = "${path.module}/../../dags/bronze_pipeline.py"
  etag       = filemd5("${path.module}/../../dags/bronze_pipeline.py")
  depends_on = [aws_s3_bucket_versioning.airflow]
}

# ---------- execution role ----------
resource "aws_iam_role" "airflow" {
  count = local.airflow_on
  name  = "${local.airflow_name}-exec"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Action    = "sts:AssumeRole"
      Principal = { Service = ["airflow.amazonaws.com", "airflow-env.amazonaws.com"] }
    }]
  })
}

resource "aws_iam_role_policy" "airflow" {
  count = local.airflow_on
  name  = "airflow-permissions"
  role  = aws_iam_role.airflow[0].id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = "airflow:PublishMetrics"
        Resource = "arn:aws:airflow:us-east-1:${data.aws_caller_identity.current.account_id}:environment/${local.airflow_name}"
      },
      {
        Effect   = "Allow"
        Action   = ["s3:GetObject*", "s3:GetBucket*", "s3:List*"]
        Resource = [aws_s3_bucket.airflow[0].arn, "${aws_s3_bucket.airflow[0].arn}/*"]
      },
      {
        Effect   = "Allow"
        Action   = "s3:GetAccountPublicAccessBlock"
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogStream", "logs:CreateLogGroup", "logs:PutLogEvents",
          "logs:GetLogEvents", "logs:GetLogRecord", "logs:GetLogGroupFields",
          "logs:GetQueryResults"
        ]
        Resource = "arn:aws:logs:us-east-1:${data.aws_caller_identity.current.account_id}:log-group:airflow-${local.airflow_name}-*"
      },
      {
        Effect   = "Allow"
        Action   = ["logs:DescribeLogGroups", "cloudwatch:PutMetricData"]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "sqs:ChangeMessageVisibility", "sqs:DeleteMessage", "sqs:GetQueueAttributes",
          "sqs:GetQueueUrl", "sqs:ReceiveMessage", "sqs:SendMessage"
        ]
        Resource = "arn:aws:sqs:us-east-1:*:airflow-celery-*"
      },
      {
        Effect      = "Allow"
        Action      = ["kms:Decrypt", "kms:DescribeKey", "kms:GenerateDataKey*", "kms:Encrypt"]
        NotResource = "arn:aws:kms:*:${data.aws_caller_identity.current.account_id}:key/*"
        Condition = {
          StringLike = { "kms:ViaService" = ["sqs.us-east-1.amazonaws.com"] }
        }
      },
      {
        Sid    = "RunBronzeGlueJobs"
        Effect = "Allow"
        Action = [
          "glue:StartJobRun", "glue:GetJobRun", "glue:GetJobRuns",
          "glue:GetJob", "glue:BatchStopJobRun"
        ]
        Resource = "arn:aws:glue:us-east-1:${data.aws_caller_identity.current.account_id}:job/dev-pipeline-bronze-*"
      },
      {
        Sid      = "ReadGlueJobLogs"
        Effect   = "Allow"
        Action   = ["logs:GetLogEvents", "logs:FilterLogEvents", "logs:DescribeLogStreams"]
        Resource = "arn:aws:logs:us-east-1:${data.aws_caller_identity.current.account_id}:log-group:/aws-glue/jobs/*"
      }
    ]
  })
}

# ---------- the Airflow environment ----------
resource "aws_mwaa_environment" "airflow" {
  count                 = local.airflow_on
  name                  = local.airflow_name
  airflow_version       = "2.10.3"
  environment_class     = "mw1.micro"
  min_workers           = 1
  max_workers           = 1
  webserver_access_mode = "PUBLIC_ONLY"

  source_bucket_arn  = aws_s3_bucket.airflow[0].arn
  dag_s3_path        = "dags/"
  execution_role_arn = aws_iam_role.airflow[0].arn

  network_configuration {
    security_group_ids = [aws_security_group.private.id]
    subnet_ids         = [for s in aws_subnet.private : s.id]
  }

  airflow_configuration_options = {
    "core.dags_are_paused_at_creation" = "False"
  }

  logging_configuration {
    task_logs {
      enabled   = true
      log_level = "INFO"
    }
  }

  depends_on = [
    aws_route.private_to_nat,
    aws_s3_object.airflow_dag,
    aws_iam_role_policy.airflow,
  ]
}

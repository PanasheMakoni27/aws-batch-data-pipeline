data "aws_iam_policy_document" "uploader_trust" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "AWS"
      identifiers = ["arn:aws:iam::${local.account_id}:user/panashe-admin"]
    }
  }
}

data "aws_iam_policy_document" "uploader_perms" {
  statement {
    sid       = "WriteToRaw"
    actions   = ["s3:PutObject", "s3:AbortMultipartUpload"]
    resources = ["${aws_s3_bucket.layer["raw"].arn}/*"]
  }
  statement {
    sid       = "UseDataKey"
    actions   = ["kms:GenerateDataKey", "kms:Decrypt"]
    resources = [aws_kms_key.data.arn]
  }
}

resource "aws_iam_role" "uploader" {
  name               = "dev-pipeline-uploader"
  assume_role_policy = data.aws_iam_policy_document.uploader_trust.json
}

resource "aws_iam_role_policy" "uploader" {
  name   = "uploader-permissions"
  role   = aws_iam_role.uploader.id
  policy = data.aws_iam_policy_document.uploader_perms.json
}

locals {
  glue_jobs = {
    bronze = { read = "raw", write = "bronze" }
    silver = { read = "bronze", write = "silver" }
    gold   = { read = "silver", write = "gold" }
  }
}

data "aws_iam_policy_document" "glue_trust" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["glue.amazonaws.com"]
    }
  }
}

data "aws_iam_policy_document" "glue_perms" {
  for_each = local.glue_jobs
  statement {
    sid     = "ListLayers"
    actions = ["s3:ListBucket"]
    resources = [
      aws_s3_bucket.layer[each.value.read].arn,
      aws_s3_bucket.layer[each.value.write].arn,
    ]
  }
  statement {
    sid       = "ReadInput"
    actions   = ["s3:GetObject"]
    resources = ["${aws_s3_bucket.layer[each.value.read].arn}/*"]
  }
  statement {
    sid       = "WriteOutput"
    actions   = ["s3:PutObject", "s3:DeleteObject", "s3:AbortMultipartUpload"]
    resources = ["${aws_s3_bucket.layer[each.value.write].arn}/*"]
  }
  statement {
    sid       = "UseDataKey"
    actions   = ["kms:Decrypt", "kms:GenerateDataKey"]
    resources = [aws_kms_key.data.arn]
  }
  statement {
    sid       = "WriteLogs"
    actions   = ["logs:CreateLogGroup", "logs:CreateLogStream", "logs:PutLogEvents"]
    resources = ["arn:aws:logs:us-east-1:${local.account_id}:log-group:/aws-glue/*"]
  }
}

resource "aws_iam_role" "glue" {
  for_each           = local.glue_jobs
  name               = "dev-pipeline-glue-${each.key}"
  assume_role_policy = data.aws_iam_policy_document.glue_trust.json
}

resource "aws_iam_role_policy" "glue" {
  for_each = local.glue_jobs
  name     = "glue-${each.key}-permissions"
  role     = aws_iam_role.glue[each.key].id
  policy   = data.aws_iam_policy_document.glue_perms[each.key].json
}

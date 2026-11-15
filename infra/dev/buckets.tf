locals {
  account_id = data.aws_caller_identity.current.account_id
  layers     = toset(["raw", "bronze", "silver", "gold", "logs"])
}

resource "aws_s3_bucket" "layer" {
  for_each      = local.layers
  bucket        = "dev-pipeline-${each.key}-${local.account_id}"
  force_destroy = true
}

resource "aws_s3_bucket_public_access_block" "layer" {
  for_each                = aws_s3_bucket.layer
  bucket                  = each.value.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_server_side_encryption_configuration" "layer" {
  for_each = aws_s3_bucket.layer
  bucket   = each.value.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm     = "aws:kms"
      kms_master_key_id = aws_kms_key.data.arn
    }
    bucket_key_enabled = true
  }
}

resource "aws_s3_bucket_versioning" "layer" {
  for_each = aws_s3_bucket.layer
  bucket   = each.value.id
  versioning_configuration {
    status = "Enabled"
  }
}

data "aws_iam_policy_document" "layer" {
  for_each = aws_s3_bucket.layer
  statement {
    sid       = "DenyInsecureTransport"
    effect    = "Deny"
    actions   = ["s3:*"]
    resources = [each.value.arn, "${each.value.arn}/*"]
    principals {
      type        = "*"
      identifiers = ["*"]
    }
    condition {
      test     = "Bool"
      variable = "aws:SecureTransport"
      values   = ["false"]
    }
  }
  statement {
    sid       = "DenyNonKmsUploads"
    effect    = "Deny"
    actions   = ["s3:PutObject"]
    resources = ["${each.value.arn}/*"]
    principals {
      type        = "*"
      identifiers = ["*"]
    }
    condition {
      test     = "StringNotEqualsIfExists"
      variable = "s3:x-amz-server-side-encryption"
      values   = ["aws:kms"]
    }
  }
}

resource "aws_s3_bucket_policy" "layer" {
  for_each   = aws_s3_bucket.layer
  bucket     = each.value.id
  policy     = data.aws_iam_policy_document.layer[each.key].json
  depends_on = [aws_s3_bucket_public_access_block.layer]
}

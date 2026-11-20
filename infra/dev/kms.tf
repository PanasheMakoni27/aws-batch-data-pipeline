resource "aws_kms_key" "data" {
  description             = "dev pipeline data key for S3 buckets"
  enable_key_rotation     = true
  deletion_window_in_days = 7
}

resource "aws_kms_alias" "data" {
  name          = "alias/dev-pipeline-data"
  target_key_id = aws_kms_key.data.key_id
}

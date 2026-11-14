data "aws_caller_identity" "current" {}

resource "aws_s3_bucket" "test" {
  bucket = "dev-pipeline-test-${data.aws_caller_identity.current.account_id}"
}

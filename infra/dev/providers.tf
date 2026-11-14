provider "aws" {
  region  = "us-east-1"
  profile = "dev-tf"

  default_tags {
    tags = {
      project = "aws-pipeline"
      env     = "dev"
      owner   = "panashe"
    }
  }
}

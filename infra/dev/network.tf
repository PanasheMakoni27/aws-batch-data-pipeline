locals {
  name     = "dev-pipeline"
  vpc_cidr = "10.10.0.0/16"

  private_subnets = {
    a = { cidr = "10.10.1.0/24", az_index = 0 }
    b = { cidr = "10.10.2.0/24", az_index = 1 }
  }
}

data "aws_availability_zones" "available" {
  state = "available"
}

resource "aws_vpc" "main" {
  cidr_block           = local.vpc_cidr
  enable_dns_support   = true
  enable_dns_hostnames = true

  tags = { Name = "${local.name}-vpc" }
}

resource "aws_subnet" "private" {
  for_each          = local.private_subnets
  vpc_id            = aws_vpc.main.id
  cidr_block        = each.value.cidr
  availability_zone = data.aws_availability_zones.available.names[each.value.az_index]

  tags = { Name = "${local.name}-private-${each.key}" }
}

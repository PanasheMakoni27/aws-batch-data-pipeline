resource "aws_security_group" "private" {
  name        = "${local.name}-private-sg"
  description = "Shared by pipeline components in the private subnets"
  vpc_id      = aws_vpc.main.id

  tags = { Name = "${local.name}-private-sg" }
}

resource "aws_vpc_security_group_ingress_rule" "self" {
  security_group_id            = aws_security_group.private.id
  referenced_security_group_id = aws_security_group.private.id
  ip_protocol                  = "-1"
  description                  = "Components in this group can talk to each other"
}

resource "aws_vpc_security_group_egress_rule" "all" {
  security_group_id = aws_security_group.private.id
  cidr_ipv4         = "0.0.0.0/0"
  ip_protocol       = "-1"
  description       = "Outbound allowed, but no internet route exists"
}

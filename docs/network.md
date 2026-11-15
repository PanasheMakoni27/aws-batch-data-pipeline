# Network plan (dev)

| Item | Value |
|---|---|
| Region | us-east-1 |
| VPC CIDR | 10.10.0.0/16 |
| Private subnet A | 10.10.1.0/24 (us-east-1a) |
| Private subnet B | 10.10.2.0/24 (us-east-1b) |
| Prod VPC CIDR (planned) | 10.20.0.0/16 |

## Notes
- No internet gateway and no NAT gateway, so nothing is reachable from the internet.
- The S3 gateway endpoint gives the private subnets a private path to S3 at no cost.
- Redshift Serverless needs 2 subnets in 2 AZs without Enhanced VPC Routing, and 3 free IPs per subnet.
- Ranges differ between dev and prod so they never overlap.

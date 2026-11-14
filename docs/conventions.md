# Conventions: AWS Batch Data Pipeline

## Region and account
- Single region: us-east-1 (N. Virginia).
- One AWS account, split into two logical environments: `dev` and `prod`.
- AWS Organizations is deliberately not used. Creating an organization moves the account to pay-as-you-go and ends the free credits that fund this project. Trade-off: weaker isolation and a shared blast radius, compared with separate dev and prod accounts. In a real company these would be separate accounts under Organizations.

## Environments
- `dev` is where everything is built and tested first.
- `prod` is deployed only through the CI pipeline (DAY-27 onward), not by hand.
- Rule: nothing in one environment may use a resource that belongs to the other. Each environment has its own buckets, roles, Glue jobs, Redshift workgroup and DAG.

## Naming
Pattern: `{env}-pipeline-{purpose}`

| Resource | Example |
|---|---|
| S3 bucket | `dev-pipeline-raw-<account-id>` (account ID makes the name globally unique) |
| IAM role | `dev-pipeline-glue-bronze-role` |
| Glue job | `dev-pipeline-raw-to-bronze` |
| Glue database | `dev_pipeline_bronze` (underscores, because Athena does not allow hyphens) |
| KMS key alias | `alias/dev-pipeline-data` |
| Redshift workgroup | `dev-pipeline-wg` |

## Tags (on every resource that supports tags)
| Key | Value |
|---|---|
| project | aws-pipeline |
| env | dev or prod |
| owner | panashe |

Tags are set once in Terraform provider default tags, not per resource.

## IAM roles planned (one per component, per environment)
Created on DAY-06, not before.

| Role | Purpose |
|---|---|
| `{env}-pipeline-uploader-role` | Laptop uploads to the raw bucket only |
| `{env}-pipeline-glue-bronze-role` | Reads raw, writes bronze |
| `{env}-pipeline-glue-silver-role` | Reads bronze, writes silver and rejects |
| `{env}-pipeline-glue-gold-role` | Reads silver, writes gold |
| `{env}-pipeline-redshift-copy-role` | Reads gold, decrypts with KMS, attached to Redshift |
| `{env}-pipeline-mwaa-execution-role` | Runs the DAG: starts Glue jobs, calls Redshift Data API, publishes to SNS |

## Rules
- No access keys. Humans use the IAM admin user with MFA; the CLI uses console-credential login; CI uses OIDC.
- No secrets in Git. Secrets live in Secrets Manager.
- Everything is created with Terraform from DAY-03 onward. Console clicks are for learning only and are recorded.
- Expensive services (Redshift, MWAA, NAT gateway) are destroyed at the end of each session.

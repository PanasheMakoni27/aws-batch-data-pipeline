# Decision log

Each row: what I chose, what I considered, and why. Equivalents on GCP and Azure/Fabric are included so the design is easy to translate.

| Area | Chosen | Alternatives considered | Why | GCP / Azure equivalent |
|---|---|---|---|---|
| File format | Parquet | CSV, JSON | Columnar and compressed (125.7 MB vs 702.8 MB for Transactions), typed, faster to query | Parquet on GCS / ADLS |
| Storage | S3, with raw, bronze, silver, gold buckets | One bucket with folders | Separate buckets allow separate permissions, lifecycle rules and encryption | GCS buckets / ADLS containers |
| Encryption | SSE-KMS with a customer-managed key | SSE-S3, DSSE-KMS | Key-level access control, audit trail, and a kill switch | CMEK / Key Vault |
| Incremental loads | SQL Server Change Tracking | Timestamp column, SQL Server CDC, log-based CDC (DMS) | Reliable, low overhead, and detects deletes. Bookmark moves only after success | Datastream / Fabric mirroring |
| Run safety | Manifest uploaded last, watermark saved last | Saving state first | A failed run retries from the last good point, and nothing is skipped | Same pattern |
| Catalog | Glue Data Catalog with schemas declared in Terraform | Crawlers | Controlled, reviewed schema changes. Crawlers only for discovery or drift alerts | Dataplex / Purview |
| Table format (bronze onward) | Apache Iceberg | Plain Parquet, Delta, Hudi | Best native AWS support, MERGE, time travel, safe deletes | Delta in Fabric, BigQuery managed tables |
| Bronze update method | MERGE of the latest change per key | Full rebuild each run | Idempotent, and scales. Rebuild was fine only for tiny data | Dataform incremental / MERGE |
| Processing engine | AWS Glue (PySpark) | EMR, Lambda, Athena SQL | Serverless Spark, pay per second, least-privilege role per job | Dataproc Serverless / Fabric Spark |
| Access control | IAM roles, bucket policies, KMS, Lake Formation | IAM only | Defence in depth, with column-level control later | IAM + policy tags / RBAC + Purview |
| Recovery | Versioning, replication of raw, Object Lock, AWS Backup | Backing up every layer | Raw and Terraform state are the sources of truth. Other layers rebuild | Backup and DR / Azure Backup |
| Business metadata | Amazon DataZone (glossary, metadata forms, portal) | Glue tags only | A business layer for discovery and access requests | Dataplex / Purview |
| Infrastructure | Terraform, one folder per environment | Console clicks, CloudFormation | Repeatable, reviewed in git | Terraform works on all clouds |

## Revisit later
- Hudi for streaming or update-heavy workloads.
- Redshift for a warehouse layer.
- Tokenising personal data before it lands in raw.

# Control layer and source tables

Source: BankingDB (SQL Server, synthetic data). Extract source schema: Core, plus Reference lookups.

## Source tables in scope (counts as of 2026-11-19)

| Table | Rows | Primary key | Load type | Watermark |
|---|---|---|---|---|
| Core.Transactions | 5,838,810 | TransactionID | incremental | Change Tracking version |
| Core.Accounts | 25,000 | AccountID | incremental | Change Tracking version |
| Core.Customers | 10,000 | CustomerID | incremental | Change Tracking version |
| Core.Branches | 200 | BranchID | full | none |
| Reference.AccountTypes | 6 | AccountTypeID | full | none |
| Reference.TransactionTypes | 8 | TransactionTypeID | full | none |

Inactive (0 rows): Loans, LoanPayments, Payments, Cards, Merchants.

## Change Tracking
- Enabled on the Core tables. Retention set to 14 days (was 2).
- Watermark = last extracted version, stored in Metadata.PipelineWatermark.
- If the saved version is below CHANGE_TRACKING_MIN_VALID_VERSION, the extract falls back to a full reload.
- The watermark is saved only after the upload to S3 succeeds, so re-runs are idempotent.

## Settings: config/tables.yaml
One entry per table: source schema and table, primary key, load type, watermark type, watermark column, partition column (Transactions: year/month of TransactionDate), active flag.

## State: Metadata.PipelineWatermark
table_name, watermark_type, last_version, last_timestamp, updated_at.

## History: Metadata.PipelineRunLog
| Column | Meaning |
|---|---|
| log_id | Unique row id |
| run_id | Groups all tables in one pipeline run |
| table_name | Matches name in tables.yaml |
| layer | extract, bronze, silver or gold |
| load_type | full or incremental |
| status | RUNNING, SUCCESS or FAILED |
| rows_in / rows_out / rows_rejected | Counts for reconciliation |
| started_at / finished_at | Timing |
| message | Error or note |
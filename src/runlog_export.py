"""Export one run's rows from Metadata.PipelineRunLog to S3 as Parquet."""
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

from db import get_connection

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"

RUN_LOG_SCHEMA = pa.schema([
    ("log_id", pa.int64()),
    ("run_id", pa.string()),
    ("table_name", pa.string()),
    ("layer", pa.string()),
    ("load_type", pa.string()),
    ("status", pa.string()),
    ("rows_in", pa.int64()),
    ("rows_out", pa.int64()),
    ("rows_rejected", pa.int64()),
    ("started_at", pa.timestamp("us")),
    ("finished_at", pa.timestamp("us")),
    ("message", pa.string()),
])


def rows_to_table(rows):
    """rows: list of dicts keyed by column name. Missing keys become NULL."""
    return pa.Table.from_pylist(rows, schema=RUN_LOG_SCHEMA)


def fetch_run_rows(conn, run_id):
    cur = conn.cursor()
    cur.execute(
        "SELECT log_id, CAST(run_id AS varchar(36)) AS run_id, table_name, layer, "
        "load_type, status, rows_in, rows_out, rows_rejected, started_at, "
        "finished_at, message "
        "FROM Metadata.PipelineRunLog WHERE run_id = ? ORDER BY log_id",
        str(run_id),
    )
    columns = [c[0] for c in cur.description]
    return [dict(zip(columns, row)) for row in cur.fetchall()]


def export_run_log(session, bucket, run_id, run_date):
    with get_connection() as conn:
        rows = fetch_run_rows(conn, run_id)
    table = rows_to_table(rows)

    out_dir = OUTPUT_DIR / "ops" / "run_log" / f"run_date={run_date}"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / f"run_id={run_id}.parquet"
    pq.write_table(table, out_file)

    key = f"ops/run_log/run_date={run_date}/run_id={run_id}.parquet"
    session.client("s3").upload_file(
        str(out_file), bucket, key, ExtraArgs={"ChecksumAlgorithm": "SHA256"}
    )
    return key

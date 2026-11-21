"""Incremental extract for Change Tracking tables.

Cycle per table:
  1. read the saved bookmark and snapshot the current version (BEFORE extracting)
  2. decide: incremental, or full reload if the bookmark is missing/expired
  3. extract changed rows (LEFT JOIN so deletes survive) to Parquet
  4. upload data, then the manifest last
  5. move the bookmark, only after everything succeeded
"""
import sys
import uuid
from datetime import date

import pyarrow as pa
import pyarrow.parquet as pq

from config import active_tables, load_tables
from db import get_connection
from extract import BATCH_SIZE, OUTPUT_DIR, build_schema, extract_table, verify
from runlog_export import export_run_log
from upload import get_session, raw_bucket, upload_table
from watermark import (
    decide_mode,
    get_current_version,
    get_min_valid_version,
    get_saved_version,
    save_version,
)


def log_start(conn, run_id, table_name, load_type):
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO Metadata.PipelineRunLog "
        "(run_id, table_name, layer, load_type, status, started_at) "
        "OUTPUT INSERTED.log_id "
        "VALUES (?, ?, 'extract', ?, 'RUNNING', SYSDATETIME())",
        str(run_id), table_name, load_type,
    )
    log_id = cur.fetchone()[0]
    conn.commit()
    return log_id


def log_finish(conn, log_id, status, rows, message=None):
    cur = conn.cursor()
    cur.execute(
        "UPDATE Metadata.PipelineRunLog "
        "SET status = ?, rows_in = ?, rows_out = ?, finished_at = SYSDATETIME(), message = ? "
        "WHERE log_id = ?",
        status, rows, rows, message, log_id,
    )
    conn.commit()


def extract_changes(conn, cfg, load_date, run_id, since_version, to_version):
    """Write rows changed in (since_version, to_version] to Parquet."""
    schema_name, table_name, pk = cfg["source_schema"], cfg["source_table"], cfg["primary_key"]
    out_dir = OUTPUT_DIR / cfg["name"] / f"load_date={load_date}" / f"run_id={run_id}"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / "part-0000.parquet"

    cur = conn.cursor()
    base = build_schema(cur, schema_name, table_name)
    schema = pa.schema(
        list(base)
        + [pa.field("change_operation", pa.string()), pa.field("change_version", pa.int64())]
    )
    # The key comes from the change list (ct): for a deleted row there is nothing in t.
    select_cols = ", ".join(
        f"ct.[{f.name}] AS [{f.name}]" if f.name == pk else f"t.[{f.name}] AS [{f.name}]"
        for f in base
    )
    cur.execute(
        f"SELECT {select_cols}, "
        f"ct.SYS_CHANGE_OPERATION AS change_operation, ct.SYS_CHANGE_VERSION AS change_version "
        f"FROM CHANGETABLE(CHANGES [{schema_name}].[{table_name}], {int(since_version)}) AS ct "
        f"LEFT JOIN [{schema_name}].[{table_name}] AS t ON t.[{pk}] = ct.[{pk}] "
        f"WHERE ct.SYS_CHANGE_VERSION <= {int(to_version)}"
    )
    rows_written = 0
    with pq.ParquetWriter(out_file, schema) as writer:
        while True:
            batch = cur.fetchmany(BATCH_SIZE)
            if not batch:
                break
            columns = list(zip(*batch))
            arrays = [pa.array(col, type=f.type) for col, f in zip(columns, schema)]
            writer.write_table(pa.Table.from_arrays(arrays, schema=schema))
            rows_written += len(batch)

    if pq.read_table(out_file).num_rows != rows_written:
        raise RuntimeError("Parquet row count does not match rows written")
    return out_file, rows_written


def run_table(cfg, run_id, load_date, session, bucket):
    name = cfg["name"]
    with get_connection() as conn:
        saved = get_saved_version(conn, name)
        current = get_current_version(conn)  # snapshot BEFORE extracting
        min_valid = get_min_valid_version(conn, cfg["source_schema"], cfg["source_table"])
        mode = decide_mode(saved, min_valid)
        log_id = log_start(conn, run_id, name, mode)
        try:
            if mode == "full":
                out_file, n = extract_table(cfg, load_date)
                verify(cfg, out_file, n)
            else:
                out_file, n = extract_changes(conn, cfg, load_date, run_id, saved, current)

            if mode == "full" or n > 0:
                upload_table(
                    session, bucket, cfg, out_file, n, run_id, load_date,
                    load_type=mode,
                    extra={"from_version": saved, "to_version": current},
                )
            # Last step: the bookmark moves only now.
            save_version(conn, name, current)
            log_finish(conn, log_id, "SUCCESS", n)
            return f"{name}: {mode} ({saved} -> {current}): {n} rows"
        except Exception as exc:
            log_finish(conn, log_id, "FAILED", 0, str(exc)[:1000])
            raise


def main():
    only = sys.argv[1] if len(sys.argv) > 1 else None
    tables = [
        t for t in active_tables(load_tables())
        if t["watermark_type"] == "change_tracking" and (only is None or t["name"] == only)
    ]
    run_id = uuid.uuid4()
    load_date = date.today().isoformat()
    session = get_session()
    bucket = raw_bucket(session)
    print(f"run_id: {run_id}")
    failed = False
    for cfg in tables:
        try:
            print(run_table(cfg, run_id, load_date, session, bucket))
        except Exception as exc:
            failed = True
            print(f"{cfg['name']}: FAILED - {exc}")
    try:
        key = export_run_log(session, bucket, run_id, load_date)
        print(f"run log exported: {key}")
    except Exception as exc:
        print(f"run log export FAILED (pipeline result unaffected): {exc}")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()

"""Run the extract for every active table and log each table in Metadata.PipelineRunLog."""
import uuid
from datetime import date

from config import active_tables, load_tables
from db import get_connection
from extract import extract_table, verify


def log_start(conn, run_id, cfg):
    cur = conn.cursor()
    cur.execute(
        """INSERT INTO Metadata.PipelineRunLog
               (run_id, table_name, layer, load_type, status, started_at)
           OUTPUT INSERTED.log_id
           VALUES (?, ?, 'extract', 'full', 'RUNNING', SYSDATETIME())""",
        str(run_id), cfg["name"],
    )
    log_id = cur.fetchone()[0]
    conn.commit()
    return log_id


def log_finish(conn, log_id, status, rows, message=None):
    conn.cursor().execute(
        """UPDATE Metadata.PipelineRunLog
              SET status = ?, rows_in = ?, rows_out = ?, rows_rejected = 0,
                  finished_at = SYSDATETIME(), message = ?
            WHERE log_id = ?""",
        status, rows, rows, message, log_id,
    )
    conn.commit()


def main():
    run_id = uuid.uuid4()
    load_date = date.today().isoformat()
    results = []
    with get_connection() as log_conn:
        for cfg in active_tables(load_tables()):
            log_id = log_start(log_conn, run_id, cfg)
            try:
                out_file, n = extract_table(cfg, load_date)
                verify(cfg, out_file, n)
                log_finish(log_conn, log_id, "SUCCESS", n)
                results.append((cfg["name"], "SUCCESS", n))
            except Exception as exc:
                log_finish(log_conn, log_id, "FAILED", None, str(exc)[:1000])
                results.append((cfg["name"], "FAILED", str(exc)[:80]))
    print(f"run_id={run_id}")
    for r in results:
        print(r)
    if any(r[1] == "FAILED" for r in results):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
"""Extract one table from SQL Server to Parquet, partitioned by load_date."""
import sys
from datetime import date
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

from config import active_tables, load_tables
from db import get_connection
from type_map import arrow_type

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"
BATCH_SIZE = 100_000


def build_schema(cur, schema_name, table_name):
    cur.execute(
        """SELECT c.name, ty.name, c.precision, c.scale
           FROM sys.columns c
           JOIN sys.types ty ON ty.user_type_id = c.user_type_id
           WHERE c.object_id = OBJECT_ID(?)
           ORDER BY c.column_id""",
        f"{schema_name}.{table_name}",
    )
    return pa.schema([(n, arrow_type(t, p, s)) for n, t, p, s in cur.fetchall()])


def extract_table(cfg, load_date):
    schema_name, table_name = cfg["source_schema"], cfg["source_table"]
    out_dir = OUTPUT_DIR / cfg["name"] / f"load_date={load_date}"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / "part-0000.parquet"
    rows_written = 0
    with get_connection() as conn:
        cur = conn.cursor()
        schema = build_schema(cur, schema_name, table_name)
        cur.execute(f"SELECT * FROM [{schema_name}].[{table_name}]")
        with pq.ParquetWriter(out_file, schema) as writer:
            while True:
                batch = cur.fetchmany(BATCH_SIZE)
                if not batch:
                    break
                columns = list(zip(*batch))
                arrays = [pa.array(col, type=f.type) for col, f in zip(columns, schema)]
                writer.write_table(pa.Table.from_arrays(arrays, schema=schema))
                rows_written += len(batch)
    return out_file, rows_written


def verify(cfg, out_file, rows_written):
    table = pq.read_table(out_file)
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(f"SELECT COUNT(*) FROM [{cfg['source_schema']}].[{cfg['source_table']}]")
        source_count = cur.fetchone()[0]
    if not (table.num_rows == rows_written == source_count):
        raise RuntimeError(
            f"Row count mismatch: parquet={table.num_rows}, written={rows_written}, source={source_count}"
        )
    return f"OK: {table.num_rows} rows, {len(table.schema)} columns"


if __name__ == "__main__":
    name = sys.argv[1]
    cfg = next(t for t in active_tables(load_tables()) if t["name"] == name)
    out_file, n = extract_table(cfg, date.today().isoformat())
    print(f"{name}: wrote {n} rows to {out_file}")
    print(verify(cfg, out_file, n))
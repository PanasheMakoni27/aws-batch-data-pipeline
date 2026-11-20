"""Map SQL Server column types to Arrow (Parquet) types."""
import pyarrow as pa


def arrow_type(sql_type, precision=0, scale=0):
    t = sql_type.lower()
    if t == "bigint":
        return pa.int64()
    if t == "int":
        return pa.int32()
    if t == "smallint":
        return pa.int16()
    if t == "tinyint":
        return pa.uint8()
    if t == "bit":
        return pa.bool_()
    if t in ("decimal", "numeric"):
        return pa.decimal128(precision, scale)
    if t == "float":
        return pa.float64()
    if t == "real":
        return pa.float32()
    if t in ("char", "varchar", "nchar", "nvarchar"):
        return pa.string()
    if t == "date":
        return pa.date32()
    if t in ("datetime", "datetime2", "smalldatetime"):
        return pa.timestamp("us")
    raise ValueError(f"Unmapped SQL type: {sql_type}")
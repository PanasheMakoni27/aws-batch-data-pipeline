"""Read and move the watermark (the bookmark) for Change Tracking tables."""


def get_current_version(conn):
    cur = conn.cursor()
    cur.execute("SELECT CHANGE_TRACKING_CURRENT_VERSION()")
    return cur.fetchone()[0]


def get_saved_version(conn, table_name):
    cur = conn.cursor()
    cur.execute(
        "SELECT last_version FROM Metadata.PipelineWatermark WHERE table_name = ?",
        table_name,
    )
    row = cur.fetchone()
    return row[0] if row else None


def get_min_valid_version(conn, schema_name, table_name):
    cur = conn.cursor()
    cur.execute(
        "SELECT CHANGE_TRACKING_MIN_VALID_VERSION(OBJECT_ID(?))",
        f"{schema_name}.{table_name}",
    )
    return cur.fetchone()[0]


def decide_mode(saved_version, min_valid_version):
    """Return 'full' or 'incremental'.

    No bookmark yet, or a bookmark older than what SQL Server still
    remembers, means we cannot trust the changes: reload everything.
    """
    if saved_version is None:
        return "full"
    if min_valid_version is None or saved_version < min_valid_version:
        return "full"
    return "incremental"


def save_version(conn, table_name, version):
    """Move the bookmark. Call this ONLY after the upload succeeded."""
    cur = conn.cursor()
    cur.execute(
        "UPDATE Metadata.PipelineWatermark "
        "SET last_version = ?, updated_at = SYSDATETIME() "
        "WHERE table_name = ?",
        version,
        table_name,
    )
    conn.commit()

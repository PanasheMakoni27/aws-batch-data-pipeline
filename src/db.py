"""Database connection helper for BankingDB."""
import pyodbc

SERVER = "DB-3711\\MSSQLSERVER2"
DATABASE = "BankingDB"


def pick_driver():
    drivers = sorted(d for d in pyodbc.drivers()
                     if d.startswith("ODBC Driver") and "SQL Server" in d)
    if not drivers:
        raise RuntimeError("No modern SQL Server ODBC driver installed.")
    return drivers[-1]


def get_connection():
    conn_str = (
        f"DRIVER={{{pick_driver()}}};SERVER={SERVER};DATABASE={DATABASE};"
        "Trusted_Connection=yes;TrustServerCertificate=yes;"
    )
    return pyodbc.connect(conn_str)


if __name__ == "__main__":
    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT TOP 2 BranchID, CreatedDate FROM Core.Branches")
        for row in cur.fetchall():
            print(row, type(row.CreatedDate).__name__)
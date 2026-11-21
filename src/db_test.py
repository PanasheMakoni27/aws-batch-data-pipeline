"""Connection test: read a few rows from Core.Branches."""
import pyodbc

SERVER = "DB-3711\\MSSQLSERVER2"
DATABASE = "BankingDB"

drivers = sorted(d for d in pyodbc.drivers() if "SQL Server" in d)
print("Drivers found:", drivers)
if not drivers:
    raise SystemExit("No SQL Server ODBC driver installed.")

conn_str = (
    f"DRIVER={{{drivers[-1]}}};SERVER={SERVER};DATABASE={DATABASE};"
    "Trusted_Connection=yes;TrustServerCertificate=yes;"
)
with pyodbc.connect(conn_str) as conn:
    cur = conn.cursor()
    cur.execute("SELECT TOP 5 * FROM Core.Branches")
    print([c[0] for c in cur.description])
    for row in cur.fetchall():
        print(row)
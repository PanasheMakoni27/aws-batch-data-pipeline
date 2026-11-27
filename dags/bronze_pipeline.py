"""Daily bronze pipeline: run the six Glue bronze jobs in parallel."""
from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.empty import EmptyOperator
from airflow.providers.amazon.aws.operators.glue import GlueJobOperator

TABLES = [
    "customers",
    "accounts",
    "transactions",
    "branches",
    "account_types",
    "transaction_types",
]

default_args = {
    "owner": "panashe",
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}

with DAG(
    dag_id="bronze_pipeline",
    description="Raw to bronze (Iceberg) for every active table",
    start_date=datetime(2026, 12, 1),
    schedule="0 3 * * *",
    catchup=False,
    default_args=default_args,
    tags=["bronze", "glue"],
) as dag:
    start = EmptyOperator(task_id="start")
    bronze_done = EmptyOperator(task_id="bronze_done")

    for table in TABLES:
        run_job = GlueJobOperator(
            task_id=f"bronze_{table}",
            job_name=f"dev-pipeline-bronze-{table}",
            region_name="us-east-1",
            wait_for_completion=True,
        )
        start >> run_job >> bronze_done

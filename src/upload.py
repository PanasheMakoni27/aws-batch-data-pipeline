"""Upload extracted Parquet files to the raw bucket, then write the manifest last."""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import boto3

PROFILE = "dev-uploader"


def get_session():
    return boto3.Session(profile_name=PROFILE)


def raw_bucket(session):
    account_id = session.client("sts").get_caller_identity()["Account"]
    return f"dev-pipeline-raw-{account_id}"


def sha256_of(path, chunk=8 * 1024 * 1024):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while block := f.read(chunk):
            h.update(block)
    return h.hexdigest()


def upload_table(session, bucket, cfg, out_file, rows, run_id, load_date):
    s3 = session.client("s3")
    out_file = Path(out_file)
    prefix = f'{cfg["name"]}/load_date={load_date}'
    key = f"{prefix}/{out_file.name}"

    # Data file first. S3 verifies the SHA-256 during transfer.
    # No encryption header is sent: the bucket default (our KMS key) applies.
    s3.upload_file(str(out_file), bucket, key, ExtraArgs={"ChecksumAlgorithm": "SHA256"})

    # Manifest last: its presence means "everything for this load arrived".
    manifest = {
        "run_id": str(run_id),
        "table": cfg["name"],
        "load_type": "full",
        "load_date": load_date,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "files": [
            {
                "key": key,
                "rows": rows,
                "bytes": out_file.stat().st_size,
                "sha256": sha256_of(out_file),
            }
        ],
        "total_rows": rows,
    }
    s3.put_object(
        Bucket=bucket,
        Key=f"{prefix}/_manifest.json",
        Body=json.dumps(manifest, indent=2).encode("utf-8"),
        ContentType="application/json",
    )
    return key
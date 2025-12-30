"""Google Cloud Storage utilities."""

from google.cloud import storage
from google.cloud.exceptions import Conflict, NotFound


def ensure_staging_bucket(project_id: str, agent_name: str) -> str:
    """Ensure a staging bucket exists, creating one if needed."""
    storage_client = storage.Client(project=project_id)

    candidates = [
        f"{project_id}-staging",
        f"{project_id}-{agent_name}-staging",
    ] + [f"{project_id}-{agent_name}-staging-{i}" for i in range(2, 50)]

    for bucket_name in candidates:
        try:
            bucket = storage_client.bucket(bucket_name)
            try:
                bucket.reload()
                print(f"Found existing bucket: {bucket_name}")
                return bucket_name
            except NotFound:
                print(f"Creating bucket: {bucket_name}")
                bucket.storage_class = "STANDARD"
                storage_client.create_bucket(bucket, location="us")
                return bucket_name
        except Conflict:
            continue
        except Exception:
            continue

    raise RuntimeError(f"Failed to create staging bucket after {len(candidates)} attempts")

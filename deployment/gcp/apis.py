"""Google Cloud API management utilities."""

import subprocess
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

REQUIRED_APIS = [
    "iam.googleapis.com",
    "cloudresourcemanager.googleapis.com",
    "aiplatform.googleapis.com",
    "storage.googleapis.com",
]


def run_commands_parallel(
    commands: list[tuple[str, str]], max_workers: int = 5
) -> list[tuple[str, bool, str]]:
    """Execute shell commands in parallel."""
    results = []

    def execute(desc_cmd: tuple[str, str]) -> tuple[str, bool, str]:
        description, cmd = desc_cmd
        try:
            result = subprocess.run(
                cmd, shell=True, capture_output=True, text=True, timeout=300, check=True
            )
            return (description, True, result.stdout.strip())
        except subprocess.CalledProcessError as e:
            return (description, False, e.stderr.strip() if e.stderr else str(e))
        except Exception as e:
            return (description, False, str(e))

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(execute, cmd): cmd[0] for cmd in commands}
        for future in as_completed(futures):
            try:
                results.append(future.result())
            except Exception as e:
                results.append((futures[future], False, str(e)))

    return results


def enable_required_apis(project_id: str) -> None:
    """Enable required Google Cloud APIs for Agent Engine deployment."""
    print("Enabling required Google Cloud APIs...")

    commands = [
        (api, f"gcloud services enable {api} --project={project_id} --quiet")
        for api in REQUIRED_APIS
    ]

    results = run_commands_parallel(commands, max_workers=6)

    failed = []
    for api, success, error in results:
        if success or "enabled" in error.lower():
            print(f"  [ok] {api}")
        else:
            print(f"  [error] {api}: {error}")
            failed.append(api)

    if failed:
        raise RuntimeError(f"Failed to enable APIs: {', '.join(failed)}")

    print("Waiting for API propagation...")
    time.sleep(5)

"""Google Cloud IAM utilities for service account management."""

import base64
import time
from pathlib import Path

from google.cloud.exceptions import Conflict, NotFound
from google.cloud.iam_admin_v1 import (
    CreateServiceAccountKeyRequest,
    CreateServiceAccountRequest,
    IAMClient,
    ServiceAccount,
    ServiceAccountPrivateKeyType,
)
from google.cloud.resourcemanager_v3 import ProjectsClient
from google.iam.v1 import policy_pb2

REQUIRED_ROLES = [
    "roles/aiplatform.user",
    "roles/iam.serviceAccountTokenCreator",
]


def _sanitize_sa_name(agent_name: str) -> str:
    """Generate a valid service account name from agent name."""
    name = agent_name.lower().replace("_", "-").replace(" ", "-")
    name = "".join(c for c in name if c.isalnum() or c == "-")
    while "--" in name:
        name = name.replace("--", "-")
    name = name.strip("-")

    # Remove common suffixes
    for suffix in ["agent", "analysis", "service", "processor", "engine", "app"]:
        if name.endswith(f"-{suffix}"):
            name = name[: -len(suffix) - 1]
            break

    return f"{name[:25]}-sa" if len(name) > 25 else f"{name}-sa"


def _ensure_roles(project_id: str, sa_email: str) -> None:
    """Ensure service account has required IAM roles."""
    try:
        client = ProjectsClient()
        policy = client.get_iam_policy(request={"resource": f"projects/{project_id}"})
        member = f"serviceAccount:{sa_email}"

        for role in REQUIRED_ROLES:
            has_role = any(
                binding.role == role and member in binding.members
                for binding in policy.bindings
            )
            if not has_role:
                print(f"  Adding role: {role}")
                binding = next((b for b in policy.bindings if b.role == role), None)
                if binding:
                    binding.members.append(member)
                else:
                    policy.bindings.append(
                        policy_pb2.Binding(role=role, members=[member])
                    )

        client.set_iam_policy(
            request={"resource": f"projects/{project_id}", "policy": policy}
        )
    except Exception as e:
        print(f"  Warning: Could not manage IAM roles: {e}")


def _create_key(iam_client: IAMClient, sa_email: str, project_id: str) -> str | None:
    """Create and return base64-encoded service account key."""
    for attempt in range(3):
        try:
            if attempt > 0:
                time.sleep(2**attempt)

            request = CreateServiceAccountKeyRequest(
                name=f"projects/{project_id}/serviceAccounts/{sa_email}",
                private_key_type=ServiceAccountPrivateKeyType.TYPE_GOOGLE_CREDENTIALS_FILE,
            )
            key = iam_client.create_service_account_key(request=request)
            return base64.b64encode(key.private_key_data).decode("utf-8")
        except Exception as e:
            error_str = str(e)
            # Check if key creation is disabled by organization policy
            if "disableServiceAccountKeyCreation" in error_str or "Key creation is not allowed" in error_str:
                if attempt == 2:
                    print(f"  Note: Service account key creation is disabled by organization policy.")
                    print(f"  This is not required for agent deployment - continuing without key.")
                return None
            if attempt == 2:
                print(f"  Warning: Could not create key: {e}")
                print(f"  This is not required for agent deployment - continuing without key.")
    return None


def ensure_service_account(project_id: str, agent_name: str) -> str:
    """Ensure a service account exists with required roles."""
    iam_client = IAMClient()
    base_name = _sanitize_sa_name(agent_name)

    candidates = [base_name] + [
        f"{base_name[:-3]}-sa-{i}"
        for i in range(2, 50)
        if len(f"{base_name[:-3]}-sa-{i}") <= 30
    ]

    for sa_name in candidates:
        sa_email = f"{sa_name}@{project_id}.iam.gserviceaccount.com"

        try:
            try:
                iam_client.get_service_account(
                    name=f"projects/{project_id}/serviceAccounts/{sa_email}"
                )
                print(f"Found existing service account: {sa_email}")
            except NotFound:
                print(f"Creating service account: {sa_name}")
                iam_client.create_service_account(
                    request=CreateServiceAccountRequest(
                        name=f"projects/{project_id}",
                        account_id=sa_name,
                        service_account=ServiceAccount(
                            display_name=f"ADK Agent ({agent_name})",
                            description=f"Service account for: {agent_name}",
                        ),
                    )
                )
                time.sleep(5)

            _ensure_roles(project_id, sa_email)

            # Create key for external access
            time.sleep(4)
            key = _create_key(iam_client, sa_email, project_id)
            if key:
                _save_key_to_web_env(key)

            return sa_email

        except Conflict:
            continue
        except Exception as e:
            print(f"  Error with {sa_name}: {e}")
            continue

    raise RuntimeError("Failed to create service account after multiple attempts")


def _save_key_to_web_env(key: str) -> None:
    """Save service account key to web app's environment file."""
    project_root = Path(__file__).parent.parent.parent
    env_file = project_root.parent / "web" / ".env.prod"

    if not env_file.parent.exists():
        return

    var_name = "GOOGLE_SERVICE_ACCOUNT_KEY_BASE64"
    lines = env_file.read_text().splitlines() if env_file.exists() else []

    updated = False
    for i, line in enumerate(lines):
        if line.startswith(f"{var_name}="):
            lines[i] = f"{var_name}={key}"
            updated = True
            break

    if not updated:
        lines.append(f"{var_name}={key}")

    env_file.write_text("\n".join(lines) + "\n")
    print(f"  Updated {env_file}")

"""Deploy agent to Vertex AI Agent Engine."""

import argparse
import datetime
import json
import os
import sys
import time
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import vertexai
from vertexai import agent_engines
from vertexai.agent_engines import AdkApp

from healthcare_agent.agent import root_agent
from deployment.config import load_config, update_env_file

_PROJECT_ROOT = Path(__file__).parent.parent


def _force_delete_agent(agent, location: str) -> None:
    """Delete an agent with force=True using low-level API."""
    from google.cloud import aiplatform_v1

    client = aiplatform_v1.ReasoningEngineServiceClient(
        client_options={"api_endpoint": f"{location}-aiplatform.googleapis.com"}
    )
    request = aiplatform_v1.DeleteReasoningEngineRequest(
        name=agent.resource_name,
        force=True
    )
    operation = client.delete_reasoning_engine(request=request)
    operation.result()


def _print_deployment_error(error: Exception, deployment_config) -> None:
    """Print helpful error information for deployment failures."""
    import re
    error_str = str(error)
    print(f"\n❌ Deployment failed: {error}")
    
    # Extract reasoning engine ID if available
    engine_match = re.search(r'reasoningEngines/(\d+)', error_str)
    if engine_match:
        engine_id = engine_match.group(1)
        log_url = (
            f"https://console.cloud.google.com/logs/query?"
            f"project={deployment_config.project}&"
            f"query=resource.type%3D%22vertex_ai_reasoning_engine%22%20"
            f"resource.labels.reasoning_engine_id%3D%22{engine_id}%22%20"
            f"severity%3E%3DERROR"
        )
        print(f"\n🔍 View detailed error logs:")
        print(f"   {log_url}")
    
    print(f"\n💡 Common causes:")
    print(f"   • Missing or incompatible dependencies in requirements.txt")
    print(f"   • Agent code has import errors or syntax issues")
    print(f"   • Service account lacks required permissions")
    print(f"   • Invalid environment variables")
    print(f"\n💡 Troubleshooting steps:")
    print(f"   1. Check the logs at the URL above for specific errors")
    print(f"   2. Verify all dependencies in requirements.txt are compatible")
    print(f"   3. Test agent code locally: python3 -c 'from healthcare_agent.agent import root_agent'")
    print(f"   4. Ensure service account has roles/aiplatform.user permission")


def deploy(force_recreate: bool = False) -> agent_engines.AgentEngine:
    """Deploy agent to Vertex AI Agent Engine."""
    from deployment.gcp.apis import enable_required_apis
    from deployment.gcp.storage import ensure_staging_bucket
    from deployment.gcp.iam import ensure_service_account

    print(f"\n{'=' * 50}")
    print("Deploying to Vertex AI Agent Engine")
    print(f"{'=' * 50}\n")

    # Load configuration
    deployment_config = load_config()
    print(f"Agent: {deployment_config.agent_name}")
    print(f"Project: {deployment_config.project}")
    print(f"Location: {deployment_config.location}\n")

    # Enable required APIs
    enable_required_apis(deployment_config.project)

    # Handle staging bucket (auto-create if not provided)
    staging_bucket = deployment_config.staging_bucket
    if not staging_bucket:
        staging_bucket = ensure_staging_bucket(
            deployment_config.project, deployment_config.agent_name
        )
        update_env_file("GOOGLE_CLOUD_STAGING_BUCKET", staging_bucket)

    # Setup service account
    print("\nSetting up service account...")
    service_account = ensure_service_account(
        deployment_config.project, deployment_config.agent_name
    )

    # Initialize Vertex AI
    vertexai.init(
        project=deployment_config.project,
        location=deployment_config.location,
        staging_bucket=f"gs://{staging_bucket}",
    )

    # Read requirements
    requirements_path = _PROJECT_ROOT / deployment_config.requirements_file
    requirements = [
        line.strip()
        for line in requirements_path.read_text().splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]

    # Validate agent can be imported and initialized
    print("\nValidating agent code...")
    try:
        # Test that agent can be imported and initialized
        from healthcare_agent.agent import root_agent as test_agent
        if test_agent is None:
            raise ValueError("root_agent is None")
        print("  ✓ Agent code validated")
    except Exception as e:
        print(f"  ❌ Agent validation failed: {e}")
        print(f"  Please fix agent code before deploying")
        raise

    # Create agent app
    agent_engine = AdkApp(
        agent=root_agent,
    )

    # Prepare deployment config
    deploy_kwargs = {
        "agent_engine": agent_engine,
        "display_name": deployment_config.agent_name,
        "description": "Healthcare Intake Agent",
        "extra_packages": ["healthcare_agent"],
        "env_vars": {
            "NUM_WORKERS": os.getenv("NUM_WORKERS", "1"),
            "GCP_PROJECT_ID": deployment_config.project,
            "GCP_LOCATION": deployment_config.location,
            "AGENT_NAME": deployment_config.agent_name,
        },
        "requirements": requirements,
    }

    # Check for existing agent
    existing = list(
        agent_engines.list(filter=f'display_name="{deployment_config.agent_name}"')
    )

    # Force recreate if requested
    if force_recreate and existing:
        print("\nForce recreating agent...")
        try:
            _force_delete_agent(existing[0], deployment_config.location)
            time.sleep(5)
            existing = []
        except Exception as e:
            print(f"  Warning: Could not delete: {e}")

    # Deploy or update
    remote_agent = None
    if existing:
        print(f"\nUpdating existing agent...")
        try:
            deploy_kwargs["agent_engine"] = agent_engine.clone()
            remote_agent = existing[0].update(**deploy_kwargs)
        except Exception as e:
            error_str = str(e)
            if "400" in error_str or "failed to start" in error_str.lower():
                print("  Update failed, attempting to recreate...")
                try:
                    _force_delete_agent(existing[0], deployment_config.location)
                    time.sleep(5)
                    deploy_kwargs["agent_engine"] = agent_engine
                    remote_agent = agent_engines.create(**deploy_kwargs)
                except Exception as recreate_error:
                    _print_deployment_error(recreate_error, deployment_config)
                    raise
            else:
                _print_deployment_error(e, deployment_config)
                raise
    else:
        print(f"\nCreating new agent...")
        try:
            remote_agent = agent_engines.create(**deploy_kwargs)
        except Exception as e:
            _print_deployment_error(e, deployment_config)
            raise

    # Save metadata
    logs_dir = _PROJECT_ROOT / "logs"
    logs_dir.mkdir(exist_ok=True)
    metadata = {
        "resource_name": remote_agent.resource_name,
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "agent_name": deployment_config.agent_name,
        "project": deployment_config.project,
        "location": deployment_config.location,
        "service_account": service_account,
    }

    (logs_dir / "deployment_metadata.json").write_text(json.dumps(metadata, indent=2))

    print(f"\n{'=' * 50}")
    print("Deployment successful!")
    print(f"Agent ID: {remote_agent.resource_name}")
    print(f"{'=' * 50}\n")

    return remote_agent


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Deploy agent to Vertex AI")
    parser.add_argument(
        "--force-recreate",
        action="store_true",
        help="Force delete and recreate agent",
    )
    args = parser.parse_args()

    deploy(force_recreate=args.force_recreate)


if __name__ == "__main__":
    main()

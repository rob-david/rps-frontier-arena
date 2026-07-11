from __future__ import annotations

import argparse
import fnmatch
import os
import re
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from textwrap import dedent
from typing import Iterable

from dotenv import load_dotenv
from huggingface_hub import HfApi, SpaceStage
from huggingface_hub.utils import HfHubHTTPError, RepositoryNotFoundError

ROOT_DIR = Path(__file__).resolve().parents[1]

PROVIDER_SECRET_KEYS = [
    "OPENAI_API_KEY",
    "ANTHROPIC_API_KEY",
    "GROK_API_KEY",
    "GEMINI_API_KEY",
]

REQUIRED_UPLOAD_PATTERNS = [
    "Dockerfile",
    "backend/**",
    "frontend/**",
    "config/models.json",
    "docs/index.html",
    "pyproject.toml",
    "uv.lock",
    ".dockerignore",
]

EXPLICIT_REQUIRED_FILES = [
    "Dockerfile",
    "config/models.json",
    "docs/index.html",
    "README.md",
    "pyproject.toml",
    "uv.lock",
    ".dockerignore",
]

TERMINAL_FAILURE_STAGES = {
    "BUILD_ERROR",
    "RUNTIME_ERROR",
    "CONFIG_ERROR",
    "NO_APP_FILE",
}

SPACE_README_FRONTMATTER = dedent(
    """\
    ---
    title: RPS Frontier Arena
    sdk: docker
    app_port: 7860
    ---

    """
)


@dataclass(frozen=True)
class DeployConfig:
    hf_token: str
    hf_space: str
    provider_secrets: dict[str, str]


def _resolve_space_id(api: HfApi, raw_space_id: str) -> str:
    if "/" in raw_space_id:
        return raw_space_id

    username = api.whoami()["name"]
    return f"{username}/{raw_space_id}"


def _normalize_pattern(pattern: str) -> str:
    normalized = pattern.strip().replace("\\", "/")
    if normalized.startswith("./"):
        normalized = normalized[2:]
    if normalized.startswith("/"):
        normalized = normalized[1:]
    return normalized


def _load_ignore_file(path: Path) -> list[str]:
    if not path.exists():
        return []

    patterns: list[str] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("!"):
            # Keep behavior simple: explicit include rules are handled by REQUIRED_UPLOAD_PATTERNS.
            continue
        patterns.append(_normalize_pattern(line))
    return patterns


def _matches(pattern: str, rel_path: str) -> bool:
    candidate = pattern
    if candidate.endswith("/"):
        candidate = f"{candidate}**"
    return fnmatch.fnmatch(rel_path, candidate)


def _collect_ignore_patterns() -> list[str]:
    patterns = _load_ignore_file(ROOT_DIR / ".gitignore") + _load_ignore_file(ROOT_DIR / ".dockerignore")

    # Required files must always be uploadable even if a broad ignore (e.g. docs/) exists.
    filtered: list[str] = []
    for pattern in patterns:
        if any(_matches(pattern, required) for required in EXPLICIT_REQUIRED_FILES):
            continue
        filtered.append(pattern)

    extras = [
        ".env",
        ".env.*",
        ".git/**",
        "frontend/out/**",
        "frontend/node_modules/**",
        "frontend/.next/**",
    ]

    deduped: list[str] = []
    for pattern in [*filtered, *extras]:
        if pattern not in deduped:
            deduped.append(pattern)
    return deduped


def load_config() -> DeployConfig:
    load_dotenv(ROOT_DIR / ".env")

    hf_token = os.getenv("HF_TOKEN", "").strip()
    hf_space = os.getenv("HF_SPACE", "").strip()

    missing: list[str] = []
    if not hf_token:
        missing.append("HF_TOKEN")
    if not hf_space:
        missing.append("HF_SPACE")

    provider_secrets: dict[str, str] = {}
    for key in PROVIDER_SECRET_KEYS:
        value = os.getenv(key, "").strip()
        if not value:
            missing.append(key)
        else:
            provider_secrets[key] = value

    if missing:
        raise RuntimeError(f"Missing required environment variables: {', '.join(missing)}")

    return DeployConfig(hf_token=hf_token, hf_space=hf_space, provider_secrets=provider_secrets)


def _space_exists(api: HfApi, space_id: str, token: str) -> bool:
    try:
        api.repo_info(repo_id=space_id, repo_type="space", token=token)
        return True
    except RepositoryNotFoundError:
        return False
    except HfHubHTTPError as exc:
        status_code = exc.response.status_code if exc.response is not None else None
        if status_code == 404:
            return False
        raise


def _set_space_secrets(api: HfApi, config: DeployConfig) -> None:
    print("Setting provider secrets on Space...")
    for key in PROVIDER_SECRET_KEYS:
        api.add_space_secret(repo_id=config.hf_space, key=key, value=config.provider_secrets[key], token=config.hf_token)
    print("Provider secrets updated.")


def _ensure_space_readme_metadata(readme_text: str) -> str:
    # Hugging Face Spaces need README metadata with sdk/app_port.
    frontmatter_match = re.match(r"\A---\n(.*?)\n---\n", readme_text, flags=re.DOTALL)

    if frontmatter_match is None:
        return f"{SPACE_README_FRONTMATTER}{readme_text}"

    frontmatter_body = frontmatter_match.group(1)
    if "sdk: docker" in frontmatter_body and "app_port: 7860" in frontmatter_body:
        return readme_text

    remainder = readme_text[frontmatter_match.end() :]
    return f"{SPACE_README_FRONTMATTER}{remainder}"


def _upload_project(api: HfApi, config: DeployConfig, commit_message: str) -> None:
    ignore_patterns = _collect_ignore_patterns()
    print("Uploading project files to Space repo...")
    api.upload_folder(
        repo_id=config.hf_space,
        repo_type="space",
        folder_path=ROOT_DIR,
        allow_patterns=REQUIRED_UPLOAD_PATTERNS,
        ignore_patterns=ignore_patterns,
        path_in_repo=".",
        commit_message=commit_message,
        token=config.hf_token,
    )

    readme_content = (ROOT_DIR / "README.md").read_text(encoding="utf-8")
    readme_content = _ensure_space_readme_metadata(readme_content)
    api.upload_file(
        repo_id=config.hf_space,
        repo_type="space",
        path_in_repo="README.md",
        path_or_fileobj=readme_content.encode("utf-8"),
        commit_message=f"{commit_message} (Space README metadata)",
        token=config.hf_token,
    )

    print("Upload complete.")


def _stage_name(stage: object) -> str:
    if hasattr(stage, "value"):
        return str(stage.value)
    return str(stage)


def _poll_until_running(api: HfApi, config: DeployConfig, poll_interval: float, timeout_seconds: float) -> str:
    print("Polling Space runtime status...")
    deadline = time.time() + timeout_seconds
    stage_name = "UNKNOWN"

    while time.time() < deadline:
        runtime = api.get_space_runtime(repo_id=config.hf_space, token=config.hf_token)
        stage_name = _stage_name(runtime.stage).upper()
        print(f"Current Space stage: {stage_name}")

        if stage_name == "RUNNING":
            return stage_name

        if stage_name in TERMINAL_FAILURE_STAGES:
            error_message = ""
            if hasattr(runtime, "raw") and isinstance(runtime.raw, dict):
                maybe_error = runtime.raw.get("errorMessage")
                if maybe_error:
                    error_message = f" ({maybe_error})"
            raise RuntimeError(f"Space entered failure stage: {stage_name}{error_message}")

        time.sleep(poll_interval)

    raise TimeoutError(f"Timed out waiting for Space to reach RUNNING (last stage: {stage_name})")


def deploy_space(
    api: HfApi,
    config: DeployConfig,
    *,
    poll_interval: float = 10.0,
    timeout_seconds: float = 1200.0,
    dry_run: bool = False,
) -> str:
    config = DeployConfig(
        hf_token=config.hf_token,
        hf_space=_resolve_space_id(api, config.hf_space),
        provider_secrets=config.provider_secrets,
    )

    print(f"Resolved Space repo: {config.hf_space}")

    exists = _space_exists(api, config.hf_space, config.hf_token)

    if exists:
        print("Space exists, redeploying...")
    else:
        print("Space not found, creating with Docker SDK...")
        if not dry_run:
            api.create_repo(
                repo_id=config.hf_space,
                repo_type="space",
                space_sdk="docker",
                token=config.hf_token,
                exist_ok=True,
            )
            print("Space created.")

    if dry_run:
        print("Dry run enabled, skipping secret update/upload/poll.")
        return "DRY_RUN"

    _set_space_secrets(api, config)
    _upload_project(api, config, commit_message="Deploy from local workspace")
    final_stage = _poll_until_running(api, config, poll_interval=poll_interval, timeout_seconds=timeout_seconds)
    print("Space is Running.")
    return final_stage


def parse_args(argv: Iterable[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Deploy this project to a Hugging Face Docker Space.")
    parser.add_argument("--dry-run", action="store_true", help="Resolve config and code path without making API changes.")
    parser.add_argument("--poll-interval", type=float, default=10.0, help="Seconds between runtime status checks.")
    parser.add_argument("--timeout-seconds", type=float, default=1200.0, help="Maximum total wait for RUNNING stage.")
    return parser.parse_args(argv)


def main(argv: Iterable[str] | None = None) -> int:
    args = parse_args(argv)

    try:
        config = load_config()
        print(f"Target Space: {config.hf_space}")
        api = HfApi(token=config.hf_token)
        resolved_space = _resolve_space_id(api, config.hf_space)
        deploy_space(
            api,
            config,
            poll_interval=args.poll_interval,
            timeout_seconds=args.timeout_seconds,
            dry_run=args.dry_run,
        )
        print(f"Space URL: https://huggingface.co/spaces/{resolved_space}")
        return 0
    except Exception as exc:  # noqa: BLE001
        print(f"Deployment failed: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())

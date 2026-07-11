from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace

import httpx
from huggingface_hub import SpaceStage
from huggingface_hub.utils import RepositoryNotFoundError

import deploy_hf


@dataclass
class FakeApi:
    exists: bool
    stages: list[SpaceStage]

    def __post_init__(self) -> None:
        self.created: list[dict] = []
        self.secret_keys: list[str] = []
        self.upload_calls: list[dict] = []
        self.upload_file_calls: list[dict] = []

    def repo_info(self, *, repo_id: str, repo_type: str, token: str):
        if self.exists:
            return {"id": repo_id, "type": repo_type}

        response = httpx.Response(
            404,
            request=httpx.Request("GET", f"https://huggingface.co/api/spaces/{repo_id}"),
        )
        raise RepositoryNotFoundError("not found", response=response)

    def create_repo(self, **kwargs):
        self.created.append(kwargs)

    def add_space_secret(self, *, repo_id: str, key: str, value: str, token: str):
        # Record key names only. Never store/print secret values.
        self.secret_keys.append(key)

    def upload_folder(self, **kwargs):
        self.upload_calls.append(kwargs)

    def upload_file(self, **kwargs):
        self.upload_file_calls.append(kwargs)

    def get_space_runtime(self, *, repo_id: str, token: str):
        if self.stages:
            stage = self.stages.pop(0)
        else:
            stage = SpaceStage.RUNNING
        return SimpleNamespace(stage=stage)


def _fake_config() -> deploy_hf.DeployConfig:
    return deploy_hf.DeployConfig(
        hf_token="fake-token",
        hf_space="example/test-space",
        provider_secrets={
            "OPENAI_API_KEY": "x",
            "ANTHROPIC_API_KEY": "x",
            "GROK_API_KEY": "x",
            "GEMINI_API_KEY": "x",
        },
    )


def test_space_missing_creates_then_deploys() -> None:
    api = FakeApi(exists=False, stages=[SpaceStage.BUILDING, SpaceStage.RUNNING])
    config = _fake_config()

    stage = deploy_hf.deploy_space(api, config, poll_interval=0.0, timeout_seconds=5)

    assert stage == "RUNNING"
    assert len(api.created) == 1
    assert len(api.upload_calls) == 1
    assert len(api.upload_file_calls) == 1
    assert sorted(api.secret_keys) == sorted(deploy_hf.PROVIDER_SECRET_KEYS)

    upload = api.upload_calls[0]
    assert upload["repo_type"] == "space"
    assert upload["allow_patterns"] == deploy_hf.REQUIRED_UPLOAD_PATTERNS
    assert "frontend/out/**" in upload["ignore_patterns"]

    readme_upload = api.upload_file_calls[0]
    assert readme_upload["path_in_repo"] == "README.md"


def test_space_exists_redeploys_without_create() -> None:
    api = FakeApi(exists=True, stages=[SpaceStage.RUNNING])
    config = _fake_config()

    stage = deploy_hf.deploy_space(api, config, poll_interval=0.0, timeout_seconds=5)

    assert stage == "RUNNING"
    assert len(api.created) == 0
    assert len(api.upload_calls) == 1
    assert len(api.upload_file_calls) == 1
    assert sorted(api.secret_keys) == sorted(deploy_hf.PROVIDER_SECRET_KEYS)


def run() -> None:
    test_space_missing_creates_then_deploys()
    print("[OK] mock path: space missing -> created + deployed")

    test_space_exists_redeploys_without_create()
    print("[OK] mock path: space exists -> redeployed without create")


if __name__ == "__main__":
    run()

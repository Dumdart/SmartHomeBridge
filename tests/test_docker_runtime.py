from pathlib import Path


def test_dockerfile_runs_bridge_without_gui():
    dockerfile = Path("Dockerfile").read_text()

    assert 'pip install --no-cache-dir "."' in dockerfile
    assert ".[inference]" not in dockerfile
    assert ".[gui]" not in dockerfile
    assert 'CMD ["smart-home-bridge"]' in dockerfile


def test_inference_dockerfile_installs_inference_dependencies_for_default_detector():
    dockerfile = Path("Dockerfile.inference").read_text()
    env_example = Path(".env.example").read_text()

    assert "CHICKEN_THREAT_ENABLED=true" in env_example
    assert "CHICKEN_THREAT_INFERENCE_URL" in env_example
    assert "libgl1" in dockerfile
    assert "libglib2.0-0" in dockerfile
    assert "libxcb1" in dockerfile
    assert "YOLO_CONFIG_DIR=/tmp/Ultralytics" in dockerfile
    assert ".[inference]" in dockerfile
    assert 'CMD ["smart-home-inference"]' in dockerfile
    assert "chicken_threat_detector.pt" in Path("pyproject.toml").read_text()


def test_compose_splits_bridge_and_inference_profiles():
    compose = Path("docker-compose.yml").read_text()

    assert 'command: ["smart-home-bridge"]' in compose
    assert "Dockerfile.inference" in compose
    assert 'command: ["smart-home-inference"]' in compose
    assert 'profiles: ["inference"]' in compose
    assert "CHICKEN_THREAT_INFERENCE_URL" in compose
    assert "smart-home-bridge-gui" not in compose


def test_docs_include_inference_only_compose_command():
    readme = Path("README.MD").read_text()
    technical = Path("TECHNICAL.MD").read_text()
    command = "docker compose --profile inference up -d smart-home-inference"

    assert command in readme
    assert command in technical

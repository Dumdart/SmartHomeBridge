from pathlib import Path


def test_dockerfile_runs_bridge_without_gui():
    dockerfile = Path("Dockerfile").read_text()

    assert 'pip install --no-cache-dir ".[inference]"' in dockerfile
    assert ".[gui]" not in dockerfile
    assert 'CMD ["smart-home-bridge"]' in dockerfile


def test_dockerfile_installs_inference_dependencies_for_default_detector():
    dockerfile = Path("Dockerfile").read_text()
    env_example = Path(".env.example").read_text()

    assert "CHICKEN_THREAT_ENABLED=true" in env_example
    assert ".[inference]" in dockerfile


def test_compose_runs_bridge_without_gui():
    compose = Path("docker-compose.yml").read_text()

    assert 'command: ["smart-home-bridge"]' in compose
    assert "smart-home-bridge-gui" not in compose

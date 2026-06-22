from pathlib import Path


def test_dockerfile_runs_bridge_without_gui():
    dockerfile = Path("Dockerfile").read_text()

    assert "pip install --no-cache-dir ." in dockerfile
    assert ".[gui]" not in dockerfile
    assert 'CMD ["loxone-bridge"]' in dockerfile


def test_compose_runs_bridge_without_gui():
    compose = Path("docker-compose.yml").read_text()

    assert 'command: ["loxone-bridge"]' in compose
    assert "loxone-bridge-gui" not in compose

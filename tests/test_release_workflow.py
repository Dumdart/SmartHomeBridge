from pathlib import Path


def test_release_workflow_publishes_only_loxberry_archives():
    workflow = Path(".github/workflows/cd.yml").read_text()

    assert "path: dist/Loxberry/*.zip" in workflow
    assert "dist/*.zip" in workflow
    assert "docker image save" not in workflow
    assert "dist/*.tar.gz" not in workflow

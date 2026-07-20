from importlib.util import find_spec
from pathlib import Path


def test_runtime_dependencies_are_pinned():
    requirements = Path("requirements.txt").read_text().splitlines()
    package_lines = [
        line for line in requirements
        if line and not line.startswith(("#", "--"))
    ]

    assert package_lines
    assert all("==" in line or " @ " in line for line in package_lines)


def test_cpu_install_contract_uses_official_pytorch_index():
    requirements = Path("requirements-cpu.txt").read_text()

    assert "https://download.pytorch.org/whl/cpu" in requirements
    assert "torch==2.7.0" in requirements
    assert "-r requirements.txt" in requirements


def test_required_spacy_model_is_installed():
    assert find_spec("en_core_web_sm") is not None

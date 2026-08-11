"""Shared fixtures for notify_mqtt tests."""
from __future__ import annotations

import os

import pytest

pytest_plugins = "pytest_homeassistant_custom_component"

# pytest-homeassistant-custom-component ships its own `custom_components`
# package (with an __init__.py) inside its testing_config dir. Because it has
# an __init__.py, Python's import system resolves `custom_components` to that
# *regular* package and stops looking, rather than merging it as a namespace
# package with the repo's `custom_components` dir. Extend its __path__ so our
# repo's integration is discoverable by Home Assistant's loader in tests.
import custom_components  # noqa: E402

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_REPO_CUSTOM_COMPONENTS = os.path.join(_REPO_ROOT, "custom_components")
if _REPO_CUSTOM_COMPONENTS not in custom_components.__path__:
    custom_components.__path__.append(_REPO_CUSTOM_COMPONENTS)


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations: None) -> None:
    """Make our custom integration discoverable in every test."""

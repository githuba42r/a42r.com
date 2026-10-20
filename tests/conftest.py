from __future__ import annotations

import pytest

from helpers import SITE_SRC


@pytest.fixture(scope="session")
def built(tmp_path_factory):
    """The real site, built once per test session; returns the output dir."""
    from a42r_site.build import build

    out = tmp_path_factory.mktemp("website")
    build(SITE_SRC, out)
    return out

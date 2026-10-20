"""The deploy files: CI workflow, manual script, nginx vhost, cache-busting."""
from __future__ import annotations

import hashlib
import re
from pathlib import Path

import yaml

from helpers import ROOT, SITE_SRC, read

WORKFLOW = ROOT / ".github/workflows/deploy-website.yml"
VHOST = ROOT / "deploy/nginx-www.a42r.com.conf"
SCRIPT = ROOT / "scripts/deploy-website.sh"


def test_workflow_targets_www():
    text = WORKFLOW.read_text()
    wf = yaml.safe_load(text)
    assert wf["name"] == "Deploy website"
    assert "/opt/apps/a42r/website" in text and "https://www.a42r.com/" in text
    assert "pevplugshare" not in text
    assert "--delete" in text and "pytest" in text and "a42r_site.build" in text
    assert "--exclude=.a42r-build" in text
    assert "requirements-dev.txt" in text and "favicon-32.png" in text and "android/" in text
    triggers = wf.get("on") or wf[True]
    assert triggers["push"]["branches"] == ["main"]
    assert "workflow_dispatch" in triggers


def test_script_is_safe_and_excludes_marker():
    text = SCRIPT.read_text()
    assert "set -euo pipefail" in text and "--dry-run" in text
    assert "--exclude=.a42r-build" in text and "--delete" in text
    assert "oracle-cloud:/opt/apps/a42r/website/" in text


def test_vhost_is_www_only():
    conf = VHOST.read_text()
    names = re.findall(r"server_name\s+([^;]+);", conf)
    assert names and all(n.strip() == "www.a42r.com" for n in names)
    assert "/opt/apps/a42r/website" in conf and "error_page 404 /404.html" in conf
    assert "/etc/letsencrypt/live/www.a42r.com/" in conf
    assert "return 301 https://" in conf and "application/manifest+json" in conf


def test_css_cache_busted(built):
    css = (SITE_SRC / "static/styles.css").read_bytes()
    version = hashlib.sha256(css).hexdigest()[:10]
    assert f'href="/styles.css?v={version}"' in read(built, "index.html")

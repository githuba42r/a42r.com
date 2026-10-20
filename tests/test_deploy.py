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
    assert "https://www.a42r.com/" in text
    assert "pevplugshare" not in text
    assert "--delete" in text and "pytest" in text and "a42r_site.build" in text
    assert "--exclude=.a42r-build" in text
    assert "requirements-dev.txt" in text and "favicon-32.png" in text and "android/" in text
    triggers = wf.get("on") or wf[True]
    assert triggers["push"]["branches"] == ["main"]
    assert "requirements-dev.txt" in triggers["push"]["paths"]
    purge = next(st["run"] for st in wf["jobs"]["deploy"]["steps"] if st["name"] == "Purge Cloudflare cache")
    assert "! -name .a42r-build" in purge
    assert "-name index.html" in purge and "index\\.html$##" in purge
    assert "workflow_dispatch" in triggers
    assert wf["concurrency"]["cancel-in-progress"] is False


def _sync_step(wf) -> str:
    return next(st["run"] for st in wf["jobs"]["deploy"]["steps"] if st["name"] == "Sync website/ to server")


def test_workflow_rsync_fits_rrsync_restricted_key():
    text = WORKFLOW.read_text()
    wf = yaml.safe_load(text)
    run = _sync_step(wf)
    # The remote spec is the last argument of the rsync command: host only,
    # no path, because rrsync on the server pins the web root.
    cmd = " ".join(l.rstrip("\\").strip() for l in run.splitlines() if not l.strip().startswith("#"))
    remote = cmd.split()[-1].strip('"')
    assert remote == "$USER@$HOST:", remote
    assert "/" not in remote.split(":", 1)[1]
    assert "DEPLOY_PATH" not in text and "WEBSITE_DEPLOY_PATH" not in text
    assert "env" not in wf  # no workflow-level deploy path
    for line in text.splitlines():
        if "/opt/apps/a42r/website" in line:
            assert line.lstrip().startswith("#"), line
    assert 'command="/usr/bin/rrsync /opt/apps/a42r/website",restrict ssh-ed25519' in text


def test_workflow_smoke_tests_favicon_ico():
    run = next(st["run"] for st in yaml.safe_load(WORKFLOW.read_text())["jobs"]["deploy"]["steps"]
               if st["name"] == "Smoke-test live site")
    assert " favicon.ico " in run


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


def test_vhost_nginx_118_compatible():
    conf = VHOST.read_text()
    assert not re.search(r"^\s*http2\s+on\s*;", conf, re.M)
    for line in conf.splitlines():
        if "http2" in line:
            assert line.strip().startswith("listen "), line
    assert "listen 443 ssl http2;" in conf and "listen [::]:443 ssl http2;" in conf


def test_readme_documents_triggers_and_image_step():
    text = (ROOT / "README.md").read_text()
    deploy = text[text.index("## Deploy"):]
    assert "requirements-dev.txt" in deploy
    add = text[text.index("## Add or launch a project"):text.index("## Images")]
    assert "IMAGE_SOURCES" in add and "scripts/import_images.py <base>" in add

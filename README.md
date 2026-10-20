# a42r.com

The a42r portfolio site at <https://www.a42r.com/>: a static, no-JavaScript
index of the projects a42r builds, uses and gives away. Pages are generated
from `site/projects.yaml` by `a42r_site/` into `website/` (not committed).

## Add or launch a project

1. Edit `site/projects.yaml`: add an entry, or change its `status` from `soon`
   to `live` and set its URL when it launches.
2. Run the tests, which also validate the YAML (bad slugs, statuses and
   low-contrast accents fail the build):

       .venv/bin/pytest -q

3. Build and preview:

       .venv/bin/python -m a42r_site.build
       python -m http.server -d website

   Then open <http://localhost:8000/>.

Set up the venv once with `python3 -m venv .venv && .venv/bin/pip install -r requirements-dev.txt`.

## Images and brand assets

- Project images: `.venv/bin/python scripts/import_images.py` re-imports every
  source listed in `IMAGE_SOURCES` (`a42r_site/images.py`), normalises it into
  `site/static/img/` and rewrites `sizes.json`. Add a new image by adding its
  source there.
- Favicons and other brand assets: `scripts/make_brand_assets.py` regenerates them (`.venv/bin/python scripts/make_brand_assets.py`).

## Deploy

- **CI:** a push to `main` that touches `site/**`, `a42r_site/**`,
  `requirements.txt` or the workflow runs `.github/workflows/deploy-website.yml`:
  tests, build, rsync to the server (`--delete`), Cloudflare cache purge and a
  smoke test. It can also be started by hand (`workflow_dispatch`).
- **Manual:** `scripts/deploy-website.sh` builds and rsyncs to
  `oracle-cloud:/opt/apps/a42r/website/`. Use `--dry-run` first to see what
  would change.
- **Server:** `deploy/nginx-www.a42r.com.conf` is the nginx vhost for
  `www.a42r.com` only (the apex is not served).

The build's `.a42r-build` marker file is never uploaded.

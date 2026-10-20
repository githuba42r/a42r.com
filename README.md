# a42r.com

The a42r portfolio site at <https://www.a42r.com/>: a static, no-JavaScript
index of the projects a42r builds, uses and gives away. Pages are generated
from `site/projects.yaml` by `a42r_site/` into `website/` (not committed).

## Add or launch a project

1. Edit `site/projects.yaml`: add an entry, or change its `status` from `soon`
   to `live` and set its URL when it launches.
2. If the project has an image (its `image:` field), add the source to
   `IMAGE_SOURCES` in `a42r_site/images.py` under the same base name, then
   import just that one (this merges it into `sizes.json`):

       .venv/bin/python scripts/import_images.py <base>

   A project without an image gets a monogram tile instead.
3. Run the tests, which also validate the YAML (bad slugs, statuses and
   low-contrast accents fail the build):

       .venv/bin/pytest -q

4. Build and preview:

       .venv/bin/python -m a42r_site.build
       python -m http.server -d website

   Then open <http://localhost:8000/>.

Set up the venv once with `python3 -m venv .venv && .venv/bin/pip install -r requirements-dev.txt`.

## Images and brand assets

- Project images: `.venv/bin/python scripts/import_images.py <base> ...`
  imports the named `IMAGE_SOURCES` entries (`a42r_site/images.py`) into
  `site/static/img/` and merges their sizes into `sizes.json`; with no names it
  re-imports every source and rewrites `sizes.json`. Local sources are read
  from the sibling repos under `A42R_PROJECTS_ROOT` (default
  `~/src/AndroidStudioProjects`).
- Favicons and other brand assets: `.venv/bin/python scripts/make_brand_assets.py`
  regenerates them all (icons, `favicon.ico`, `og-image.png`); pass file names,
  e.g. `favicon.ico`, to write only those.
- Every local image and icon URL in the pages carries `?v=<content hash>`, so
  they can be cached for 30 days and still update on the next deploy.

## Deploy

- **CI:** a push to `main` that touches `site/**`, `a42r_site/**`,
  `requirements.txt`, `requirements-dev.txt` or the workflow runs
  `.github/workflows/deploy-website.yml`: tests, build, rsync to the server
  (`--delete`), Cloudflare cache purge and a smoke test. It can also be started
  by hand (`workflow_dispatch`). The deploy key is restricted on the server
  with `command="/usr/bin/rrsync /opt/apps/a42r/website",restrict`, so the
  workflow syncs to `"$USER@$HOST:"` with no remote path.
- **Manual:** `scripts/deploy-website.sh` builds and rsyncs to
  `oracle-cloud:/opt/apps/a42r/website/`. Use `--dry-run` first to see what
  would change.
- **Server:** `deploy/nginx-www.a42r.com.conf` is the nginx vhost for
  `www.a42r.com` only (the apex is not served).

The build's `.a42r-build` marker file is never uploaded.

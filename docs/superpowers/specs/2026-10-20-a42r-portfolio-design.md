# www.a42r.com — project portfolio site: design

Date: 2026-10-20 · Status: draft for approval

## Intent

`a42r` is the brand under which Phil publishes small apps and tools. Each
project that is far enough along has its own site on an `a42r.com` subdomain,
but nothing ties them together. `www.a42r.com` is the parent: a light,
brand-led portfolio that profiles every project, groups them by **platform** and
by **purpose**, and sends visitors on to each project's own site. It should be
easy to keep current as work-in-progress projects launch and new ones (more
browser extensions are planned) are added. It gets full SEO treatment.

## Goals

- One home page with a short brand summary and every project shown as a
  "showcase band".
- Sub-pages per platform and per purpose. A project appears on every page it
  belongs to.
- Each band links to the project's own site (or GitHub where agreed); unfinished
  projects show a **Coming soon** badge.
- Adding or launching a project = edit one data file and rebuild.
- Full SEO: crawlable static HTML, unique metadata, structured data, sitemap,
  social cards, fast and accessible.
- Hosted on the Oracle Cloud VM alongside the other project sites, deployed the
  same way.

## Non-goals

- Per-project detail pages on a42r.com (the project sites already do that and
  would compete with them in search). *(Builder's call recorded; see below.)*
- Blog, contact form, accounts, analytics, comments, CMS.
- Moving the apex `a42r.com` — it stays on the home lab (see Constraints).
- Building websites for the Coming-soon projects.

## Anti-goals (would make this a failure even if it "works")

- Presenting a42r as Phil personally — it is a **brand**. No personal name in
  page copy (author metadata can say "a42r").
- Duplicating project-site content so a42r.com outranks the project sites.
- Dark theme — the chosen design is the **light** version.
- Anything that needs a database, server-side runtime or third-party tracking.

## Information architecture

| URL | Content |
|---|---|
| `/` | Header **"Projects"**, subtitle **"Things I build, use, and give away."**, short brand summary, then all projects as bands (live first, then Coming soon). |
| `/android/` | Android apps |
| `/browser-extensions/` | Browser extensions |
| `/web-apps/` | Web apps |
| `/desktop-self-hosted/` | Desktop & self-hosted tools |
| `/development-tools/` | Development tools |
| `/euc-riding-tools/` | EUC riding tools |
| `/other-tools/` | Other tools |
| `/privacy/` | Short statement: static site, no cookies, no tracking |
| `/404.html` | Not-found page in the same style |

Navigation has two groups, **Platforms** and **Purposes**. Each listing page has
an intro paragraph (unique text, for SEO) and the bands of its projects. Each
band shows small tag links to the platform/purpose pages it belongs to.

## Projects (agreed 2026-10-20)

| Project | Status | Link target | Platforms | Purposes |
|---|---|---|---|---|
| PEV PlugShare | Live | https://pevplugshare.a42r.com | Android | EUC riding |
| Destination ETA | Live | https://destination.a42r.com | Android | EUC riding |
| EUC World for OsmAnd | Live | https://osmand-euc.a42r.com | Android | EUC riding |
| Scooter Parking Crimes | Live | https://spc.a42r.com | Android, Web app | EUC riding, Other |
| MDRender | Live | https://mdrender.a42r.com | Android, Desktop & self-hosted | Development, Other |
| ImageTools | Live | https://image-tools.a42r.com | Web app, Browser extension, Android | Development |
| EUC Charging Monitor | Live | https://github.com/githuba42r/euc_charging | Desktop & self-hosted (Home Assistant) | EUC riding |
| MotoEye Remote | Coming soon | GitHub releases: githuba42r/MotoEyeRemote (public) — *builder's call: follows the public-repo rule; status stays Coming soon as agreed* | Android | EUC riding |
| EUC World Dashboard Overlay | Coming soon | GitHub: githuba42r/eucworld-dashboard-overlay | Desktop & self-hosted | EUC riding |
| GPX Route Exploration | Coming soon | GitHub: githuba42r/gpx-route-exploration | Web app | EUC riding |
| SmartForm Filler | Coming soon | none | Browser extension | Development |
| Sudoku Trainer | Coming soon | none (repo is private) | Web app, Android | Other |
| LinuxTorrentDownloader | Coming soon | none | Desktop & self-hosted | Other |

Project descriptions, taglines, colours and asset paths for each are in the KB:
`/home/philg/AI-Agent-Config/knowledgebase/personal-projects/projects-overview.md`.
Write each band's copy (2 short sentences) from that, in plain language, not
copied verbatim from the project sites.

Rules: *Live* = has a public site (or, for EUC Charging Monitor, a public
GitHub install page). *Coming soon* = badge; show a "View on GitHub" link only
when the repo is public; otherwise no outbound link. Live projects get a
"Visit site →" button. Use `rel="noopener"`; links are normal (followed).

## Visual design (agreed from mockups)

Layout **C, showcase bands**, **light** theme (mockup:
`.superpowers/brainstorm/*/content/showcase-light.html`):

- Warm paper background `#f7f4ee`, text `#1c2430`/`#141a22`, muted `#5b6573`,
  borders `#e4ddd0`; brand accent amber, darkened for light bg (`#a8701c`).
- Serif headings (Iowan Old Style / Palatino / Georgia stack), system sans body —
  the same type family as the existing project sites. No web fonts.
- One full-width band per project, tinted with that project's colour (deep
  variants for light bg), image alternating left/right, button in the accent.
  Starting accents: PEV `#1e824c`, MDRender `#c4314b`, Destination `#1976d2`,
  SPC `#dc2626`, ImageTools `#6366f1`; pick suitable ones for the rest. Check
  text/button contrast meets WCAG AA.
- Band image: the project's existing OG image / feature graphic / icon (paths in
  KB). Copy and optimise into this repo (WebP/AVIF + fallback, explicit
  width/height, lazy below the fold). Coming-soon projects without art get a
  tasteful placeholder (initials/monogram in the accent colour).
- Mobile: bands stack, image above text, 16px gutters, no horizontal scroll.

## SEO requirements

- Every page: unique `<title>` and meta description, `<link rel=canonical>` to
  `https://www.a42r.com/...` (trailing-slash URLs), `lang="en-AU"`, one `<h1>`.
- Open Graph + Twitter card tags; a 1200×630 a42r OG image (to be designed for
  the brand, light style).
- JSON-LD: `Organization` (name a42r, url, logo, `sameAs` GitHub
  `githuba42r`) and `WebSite` on home; `CollectionPage` + `ItemList` of
  `SoftwareApplication` (name, description, url, operatingSystem /
  applicationCategory) on listing pages; `BreadcrumbList` on sub-pages.
- `sitemap.xml` (all pages, lastmod), `robots.txt` pointing at it, favicon set
  (SVG + 32px PNG + apple-touch), `site.webmanifest`, `theme-color`.
- Semantic HTML, descriptive alt text, visible focus styles, no layout shift.
  Target Lighthouse ≥ 95 in Performance, Accessibility, Best Practices, SEO.
- Generated HTML must contain all content (no client-side rendering).
- Each project site should eventually link back to www.a42r.com (footer
  "An a42r project") — **out of scope for this build**; note it as follow-up.

## How it's built (builder's calls, recorded)

- **Data-driven static generator.** `projects.yaml` (or JSON) holds the project
  list and the platform/purpose definitions; a small build script renders HTML
  templates to `website/`. Keep dependencies minimal (Python 3 stdlib + Jinja2
  is fine). The *output* is plain static files, like the other sites.
- **Repo:** its own git repo at
  `/home/philg/src/AndroidStudioProjects/a42r.com` (currently an empty folder
  inside the AndroidStudioProjects repo — `git init` it, add `.superpowers/` to
  `.gitignore`), remote `github.com/githuba42r/a42r.com`. Creating the GitHub
  repo and pushing need the operator's go-ahead at that point.

## Hosting and deploy

Follow the established pattern (KB: `personal-projects/oracle-cloud-server.md`
and the server's `/opt/apps/README.md`):

1. Server: `/opt/apps/a42r/website`; nginx vhost
   `/etc/nginx/sites-available/www.a42r.com` (`server_name www.a42r.com`,
   static root, `try_files $uri $uri/ =404`, `error_page 404 /404.html`, long
   cache for hashed assets, short for HTML), symlinked into `sites-enabled`.
2. TLS: `sudo certbot --nginx -d www.a42r.com`.
3. DNS: `www` is already pointed at the VM (operator). On 2026-10-20 Cloudflare
   returned error 1016 for `www`; verify after the vhost is live and report if it
   persists (likely a CNAME rather than an A record to `161.33.93.37`).
4. CI: `.github/workflows/deploy-website.yml` copied from PEVPlugShare —
   build, then rsync `website/` to the server, purge Cloudflare cache, smoke-test
   `/`, `/robots.txt`, `/sitemap.xml`, `/favicon.ico`, one sub-page. Deploy key
   restricted with `command="rrsync /opt/apps/a42r/website",restrict`.
5. Manual fallback script `scripts/deploy-website.sh`.

Server changes (nginx, certbot, deploy user/key) are run by the agent via
`ssh oracle-cloud` once the plan is approved; adding GitHub secrets needs the
operator.

## Constraints

- **Apex `a42r.com` must not be touched.** It points at the home lab; home lab
  services are CNAMEs to it. Moving it later requires repointing those CNAMEs to
  a dedicated host record first (documented in the KB). No apex→www redirect in
  this build.
- Oracle VM is 1 GB RAM, shared with other sites — static only.
- Do not modify other projects' repos or sites in this build.

## Left to the builder

Exact copy for intros and bands (brand voice: plain, practical, a little dry);
template structure; image processing tooling; OG image design within the light
style; accent colours for projects without one; order of bands within a status
group; footer content (GitHub link, privacy, © a42r).

## Follow-ups (not this build)

- Back-links from each project site to www.a42r.com.
- Google Search Console / Bing Webmaster verification and sitemap submission
  (needs operator's account; a DNS TXT or HTML file can be added on request).
- Apex `a42r.com` migration and redirect to `www`.

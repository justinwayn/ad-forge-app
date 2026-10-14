# Ad Forge — UGC Ad Package Generator

Justin's own rebuild of Ad Forge (the AI UGC video ad generator originally
built on Emergent, 2026-10-08). Rebuilt by the Agent Army on 2026-10-14 so
the product is owned outright — no Emergent account, no credits, no expiry.

**What it does:** a seller describes a product → Ad Forge produces a complete
UGC ad package: **3 hook options** (Problem-Solution, Trend/Meme, Authentic
Testimonial), a **timed shooting script** per hook (voiceover lines, visuals,
on-screen text), a **scene-by-scene shot list**, a **caption sequence**, and a
**hashtag pack** — formatted for a ~30s 9:16 TikTok/Reels/Shorts ad. When a
video API is configured, the package is also submitted for rendering.

## Run locally

```bash
cd app
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --host 127.0.0.1 --port 8000
# open http://127.0.0.1:8000
```

No environment variables are required — with none set, the app runs in
**stub mode**: pricing buttons fall back to email capture, and video
rendering returns a storyboard package instead of an MP4 job.

## Deploy to Render

1. Push this `app/` directory to a GitHub repo.
2. In Render: **New → Blueprint** and select the repo (uses `render.yaml`),
   or **New → Web Service** with build `pip install -r requirements.txt`
   and start `uvicorn main:app --host 0.0.0.0 --port $PORT`.
3. Set env vars in the Render dashboard (all optional — see `.env.example`).
   For a persistent database across deploys, attach a Render disk and set
   `DB_PATH` to a path on it (e.g. `/data/adforge.db`).

## Configuration (env vars only — nothing is hardcoded)

| Variable | What it does |
|---|---|
| `AD_FORGE_PAYMENT_LINK_STARTER` | Stripe Payment Link URL for Starter ($19/mo). Unset → email capture fallback. |
| `AD_FORGE_PAYMENT_LINK_PRO` | Same, Pro ($49/mo). |
| `AD_FORGE_PAYMENT_LINK_AGENCY` | Same, Agency ($99/mo). |
| `VIDEO_API_URL` / `VIDEO_API_KEY` | Video provider endpoint + Bearer key. Unset → storyboard (stub) mode. |
| `BASE_URL` | Public URL of the deployment (used in docs/links). |
| `DB_PATH` | SQLite file path (default: `adforge.db` next to the code). |
| `FREE_PACKAGE_LIMIT` | Free ad packages per email before the upgrade gate (default 3). |
| `CONTACT_EMAIL` | Owner contact address. |

## Taking payments live (Justin's steps)

1. Stripe Dashboard → **Payment Links** → create three recurring links:
   Starter $19/mo, Pro $49/mo, Agency $99/mo. Set each link's
   "after payment" redirect to `https://<your-domain>/success`.
2. Paste each link URL into the matching env var above and redeploy (or set
   them in the Render dashboard — no code change needed).
3. Done: pricing buttons switch from email capture to live Stripe checkout
   automatically, and every click is counted (`checkout_click` events).

## Plugging in a real video API

Any HTTP service that accepts `POST {"package": {...}}` with an
`Authorization: Bearer <key>` header and returns `{"job_id": "..."}` or
`{"video_url": "..."}` works. Set `VIDEO_API_URL` + `VIDEO_API_KEY`.
Provider failures never break the create flow — the package is saved and
the user sees an honest status message.

## Analytics

Lightweight first-party event log (SQLite `events` table) — the Army web
app pattern. Events: `page_view`, `package_created`, `checkout_click`,
`lead_captured`, `forge_gate_hit`. Read them at **GET /api/stats**.
No third-party tracker, no cookies, no cost.

## Layout

```
main.py            routes (landing, pricing, studio, package, gallery, api)
config.py          env-only configuration + tier definitions
forge.py           ad-package generator (hooks, scripts, captions, shots)
video_provider.py  video API adapter with stub mode
db.py              SQLite: leads, packages, events
templates/         Jinja2 pages    static/  one CSS file, no external assets
render.yaml        Render blueprint   .env.example  config template
```

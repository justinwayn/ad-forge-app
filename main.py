"""Ad Forge — Justin's own AI UGC ad package generator.

Rebuilt by the Agent Army (2026-10-14) to replace the Emergent-hosted
original. Same product idea, owned outright: paste/describe a product,
get a complete UGC ad package — 3 hook options, timed shooting scripts,
captions, hashtags, shot list — and (when a video API is configured)
a rendered video job.

Routes:
  GET  /                landing page
  GET  /pricing         4 tiers; Stripe Payment Link buttons when configured,
                        email capture fallback when not (ChurnClinic pattern)
  POST /pricing/notify  save a notify-me email for a tier
  GET  /checkout/{tier} logs the click, 302s to that tier's Stripe link
  GET  /studio          create form
  POST /studio          generate + save an ad package, redirect to it
  GET  /package/{id}    a saved ad package (scripts, captions, shot list)
  GET  /gallery         public sample packages (same engine, demo products)
  GET  /success         post-checkout landing page
  GET  /api/stats       analytics event counts (JSON)
  GET  /health          liveness probe
"""
from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

import config
import db
import forge
import video_provider

app = FastAPI(title="Ad Forge")
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

db.init_db()


def _tiers_ctx():
    return {
        "tiers": config.TIERS,
        "configured": {t["slug"]: config.payment_configured(t["slug"])
                       for t in config.TIERS},
    }


# ---------- pages ----------

@app.get("/", response_class=HTMLResponse)
def landing(request: Request):
    db.log_event("page_view", "page=landing")
    return templates.TemplateResponse(request, "landing.html",
                                        {"request": request})


@app.get("/pricing", response_class=HTMLResponse)
def pricing(request: Request):
    db.log_event("page_view", "page=pricing")
    return templates.TemplateResponse(request, "pricing.html",
                                      {"request": request, **_tiers_ctx()})


@app.post("/pricing/notify", response_class=HTMLResponse)
def pricing_notify(request: Request, email: str = Form(""),
                   tier: str = Form("")):
    ok = db.save_lead(email, tier=tier, source="pricing")
    return templates.TemplateResponse(request, "pricing.html", {
        "request": request, **_tiers_ctx(),
        "notify_ok": ok, "notify_email": email if ok else "",
        "notify_tier": tier,
    })


@app.get("/checkout/{tier}")
def checkout(tier: str):
    if not config.payment_configured(tier):
        return RedirectResponse("/pricing", status_code=302)
    db.log_event("checkout_click", f"tier={tier}")
    return RedirectResponse(config.payment_link(tier), status_code=302)


@app.get("/studio", response_class=HTMLResponse)
def studio(request: Request):
    db.log_event("page_view", "page=studio")
    return templates.TemplateResponse(request, "studio.html", {
        "request": request, "free_limit": config.FREE_PACKAGE_LIMIT,
    })


@app.post("/studio")
def studio_submit(request: Request,
                  product_name: str = Form(...),
                  description: str = Form(...),
                  audience: str = Form(""),
                  offer: str = Form(""),
                  product_url: str = Form(""),
                  email: str = Form("")):
    email = email.strip().lower()
    # Free-tier gate: packages are counted per email. (Documented limit:
    # email-based, so it's a soft gate until real accounts + Stripe
    # webhooks land — see BUILD_REPORT.md.)
    if email and db.count_packages_for_email(email) >= config.FREE_PACKAGE_LIMIT:
        db.log_event("forge_gate_hit", f"email={email}")
        return templates.TemplateResponse(request, "studio.html", {
            "request": request, "free_limit": config.FREE_PACKAGE_LIMIT,
            "gate_email": email,
        })
    package = forge.generate(product_name, description, audience, offer,
                             product_url)
    video = video_provider.submit(package)
    pkg_id = db.new_package_id()
    db.save_package(pkg_id, email, package["product_name"], package,
                    video["status"], video["ref"])
    db.log_event("package_created",
                 f"video_status={video['status']} product={package['product_name'][:40]}")
    return RedirectResponse(f"/package/{pkg_id}", status_code=302)


@app.get("/package/{pkg_id}", response_class=HTMLResponse)
def package_page(request: Request, pkg_id: str):
    pkg = db.get_package(pkg_id)
    if not pkg:
        return HTMLResponse("That ad package doesn't exist.", status_code=404)
    db.log_event("page_view", "page=package")
    video_detail = ""
    if pkg["video_status"] == "stub":
        video_detail = ("Storyboard mode — no video API configured. "
                        "Shoot it from the shot list below, or plug a "
                        "video API in to render automatically.")
    return templates.TemplateResponse(request, "package.html", {
        "request": request, "pkg": pkg, "p": pkg["payload"],
        "video_detail": video_detail,
    })


@app.get("/gallery", response_class=HTMLResponse)
def gallery(request: Request):
    db.log_event("page_view", "page=gallery")
    return templates.TemplateResponse(request, "gallery.html", {
        "request": request, "samples": forge.samples(),
    })


@app.get("/success", response_class=HTMLResponse)
def success(request: Request):
    db.log_event("page_view", "page=success")
    return templates.TemplateResponse(request, "success.html",
                                        {"request": request})


# ---------- api / ops ----------

@app.get("/api/stats")
def api_stats():
    return JSONResponse(db.stats())


@app.get("/health")
def health():
    return {"status": "ok", "video_mode": "api" if config.video_configured()
            else "stub"}

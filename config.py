"""Configuration — everything secret or deploy-specific comes from
environment variables. Nothing is hardcoded.

Missing values = stub mode, so the app runs at $0 with zero credentials:
  - No Stripe Payment Links set  -> pricing page falls back to email capture.
  - No video API configured      -> video generation runs in STUB mode and
                                    returns a storyboard package instead of
                                    an MP4 render job.
"""
import os


def _env(name: str, default: str = "") -> str:
    return os.environ.get(name, default)


# --- Stripe Payment Links (public URLs, not secrets) ---
# Justin creates one Payment Link per paid tier in the Stripe Dashboard
# (Payment Links) and pastes the URL into the matching env var.
# Until a tier's link is set, that tier's button falls back to email capture.
PAYMENT_LINKS = {
    "starter": _env("AD_FORGE_PAYMENT_LINK_STARTER", ""),
    "pro": _env("AD_FORGE_PAYMENT_LINK_PRO", ""),
    "agency": _env("AD_FORGE_PAYMENT_LINK_AGENCY", ""),
}


def payment_link(tier: str) -> str:
    return PAYMENT_LINKS.get(tier, "")


def payment_configured(tier: str) -> bool:
    return PAYMENT_LINKS.get(tier, "").startswith("https://buy.stripe.com/")


# --- Video generation provider (adapter) ---
# Point these at any HTTP video API that accepts a JSON POST of the ad
# package and returns a job id / video URL. Unset = stub mode.
VIDEO_API_URL = _env("VIDEO_API_URL", "")
VIDEO_API_KEY = _env("VIDEO_API_KEY", "")


def video_configured() -> bool:
    return bool(VIDEO_API_URL and VIDEO_API_KEY)


# --- App ---
BASE_URL = _env("BASE_URL", "http://localhost:8000").rstrip("/")
DB_PATH = _env("DB_PATH", os.path.join(os.path.dirname(__file__), "adforge.db"))
CONTACT_EMAIL = _env("CONTACT_EMAIL", "justinwaynedillon5@gmail.com")

# Free tier: ad packages per email before the upgrade gate shows.
FREE_PACKAGE_LIMIT = int(_env("FREE_PACKAGE_LIMIT", "3"))

TIERS = [
    {
        "slug": "free",
        "name": "Free",
        "price": 0,
        "period": "",
        "blurb": "Test the forge. No card.",
        "features": [
            "3 ad packages, total",
            "All 3 hook styles (Problem-Solution, Trend, Testimonial)",
            "Full shooting script + shot list",
            "Captions & hashtag pack",
            "Storyboard preview",
        ],
    },
    {
        "slug": "starter",
        "name": "Starter",
        "price": 19,
        "period": "/mo",
        "blurb": "For sellers testing products every week.",
        "features": [
            "15 ad packages / month",
            "Everything in Free",
            "Offer & discount angles built into scripts",
            "Package history — re-open any past forge",
        ],
    },
    {
        "slug": "pro",
        "name": "Pro",
        "price": 49,
        "period": "/mo",
        "blurb": "For stores running ads daily.",
        "features": [
            "60 ad packages / month",
            "Everything in Starter",
            "Priority script angles for launches",
            "Multiple audience angles per product",
        ],
    },
    {
        "slug": "agency",
        "name": "Agency",
        "price": 99,
        "period": "/mo",
        "blurb": "For freelancers & teams making ads for clients.",
        "features": [
            "200 ad packages / month",
            "Everything in Pro",
            "Client-ready package exports",
            "Batch product runs",
        ],
    },
]

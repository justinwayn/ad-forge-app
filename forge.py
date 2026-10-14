"""The forge: turn a product description into a complete UGC ad package.

This is a deterministic template engine, not an LLM call. It fills
battle-tested UGC script structures (the same three hook shapes the
original Ad Forge shipped: Problem-Solution, Trend, Authentic
Testimonial) with the seller's product facts. Output is everything a
creator — or a video API — needs to shoot/render the ad:

  - hooks:      3 hook options (one per style), each the first-3-seconds line
  - scripts:    a full timed voiceover/shooting script per hook style
  - captions:   on-screen text sequence for the primary script
  - hashtags:   caption/hashtag pack for TikTok / Reels / Shorts
  - shot_list:  scene-by-scene shooting directions (time, visual, camera)

Honest scope note: scripts are structured templates tuned per product
inputs — fast and consistent, not free-form AI writing.
"""
import hashlib
import re

HOOK_STYLES = [
    {
        "slug": "problem-solution",
        "name": "Problem-Solution",
        "tag": "Highest ROAS",
        "why": "Names the pain in the first 3 seconds, then makes the product the obvious fix.",
    },
    {
        "slug": "trend",
        "name": "Trend / Meme",
        "tag": "Viral spike",
        "why": "Rides a familiar POV format so the ad feels native to the feed, not like an ad.",
    },
    {
        "slug": "testimonial",
        "name": "Authentic Testimonial",
        "tag": "Most trusted",
        "why": "Sounds like a real buyer talking to a friend. Low polish on purpose — that's what converts.",
    },
]


def _pick(options, seed_text):
    h = int(hashlib.sha256(seed_text.encode()).hexdigest(), 16)
    return options[h % len(options)]


def _clean(text, fallback):
    text = (text or "").strip()
    return text if text else fallback


def _benefit_phrases(description, limit=3):
    parts = re.split(r"[.;\n]", description or "")
    out = []
    for p in parts:
        p = p.strip(" -•\t")
        if len(p) >= 8:
            out.append(p[0].upper() + p[1:])
        if len(out) >= limit:
            break
    return out


def _hashtags(product_name, audience, description):
    words = set()
    for text in (product_name, audience, description):
        for w in re.findall(r"[a-zA-Z]{4,}", (text or "").lower()):
            words.add(w)
    stop = {"with", "that", "this", "from", "your", "their", "people", "anyone",
            "product", "really", "every", "about", "which", "these", "those"}
    tags = [f"#{w}" for w in sorted(words - stop)[:6]]
    tags += ["#tiktokmademebuyit", "#smallbusiness", "#ugcad", "#founditonamazon"]
    seen, out = set(), []
    for t in tags:
        if t not in seen:
            seen.add(t)
            out.append(t)
    return out[:10]


def generate(product_name, description, audience, offer, product_url=""):
    """Return the full ad package dict."""
    name = _clean(product_name, "This product")
    desc = _clean(description, "It solves an everyday problem, fast.")
    who = _clean(audience, "anyone who needs this")
    deal = _clean(offer, "Link in bio to get yours")
    benefits = _benefit_phrases(desc) or [desc]
    b1 = benefits[0]
    b2 = benefits[1] if len(benefits) > 1 else benefits[0]
    pain = _pick([
        f"still dealing with the problem {name} fixes",
        f"wasting time on this every single day",
        f"paying too much for something that barely works",
    ], name + desc)

    hooks = [
        {
            "style": HOOK_STYLES[0]["name"],
            "tag": HOOK_STYLES[0]["tag"],
            "line": _pick([
                f"Stop scrolling if you're {pain}.",
                f"If you're {pain}, you need to see this.",
                f"Nobody talks about this, but {who} — watch.",
            ], name + "ps"),
            "why": HOOK_STYLES[0]["why"],
        },
        {
            "style": HOOK_STYLES[1]["name"],
            "tag": HOOK_STYLES[1]["tag"],
            "line": _pick([
                f"POV: you finally tried {name} and it actually works",
                f"POV: {who} discover {name} for the first time",
                f"Tell me you need {name} without telling me",
            ], name + "trend"),
            "why": HOOK_STYLES[1]["why"],
        },
        {
            "style": HOOK_STYLES[2]["name"],
            "tag": HOOK_STYLES[2]["tag"],
            "line": _pick([
                f"Honest review: I didn't expect {name} to work this well",
                f"I bought {name} so you don't have to wonder — here's the truth",
                f"Three weeks with {name}. Here's what actually happened",
            ], name + "test"),
            "why": HOOK_STYLES[2]["why"],
        },
    ]

    def script_for(hook):
        return [
            {"time": "0–3s", "label": "HOOK",
             "voiceover": hook["line"],
             "visual": "Face to camera, product already in hand. No intro, no logo — straight into the line.",
             "onscreen": hook["line"]},
            {"time": "3–10s", "label": "PROBLEM",
             "voiceover": f"Here's the thing — {b1[0].lower() + b1[1:] if b1 else desc}",
             "visual": "Show the problem up close, then the product entering frame.",
             "onscreen": b1},
            {"time": "10–20s", "label": "DEMO",
             "voiceover": f"Watch this. {b2} That's it. That's the whole pitch.",
             "visual": "Use the product for real, one continuous take. Hands in frame, no cuts during the key moment.",
             "onscreen": b2},
            {"time": "20–27s", "label": "OFFER",
             "voiceover": f"And right now: {deal}.",
             "visual": "Hold the product next to your face. Point down at the link area.",
             "onscreen": deal},
            {"time": "27–30s", "label": "CTA",
             "voiceover": "Link's right there. Go get yours before you forget — I almost did.",
             "visual": "Smile, tap toward the link, end on the product. Cut hard, no fade.",
             "onscreen": "Link in bio — get yours"},
        ]

    scripts = {h["style"]: script_for(h) for h in hooks}
    primary = scripts[hooks[0]["style"]]
    captions = [s["onscreen"] for s in primary]
    shot_list = [
        {"scene": i + 1, "time": s["time"], "label": s["label"],
         "visual": s["visual"],
         "camera": "Vertical 9:16, arm's length, natural light facing you. "
                   + ("Lock focus on the product." if s["label"] == "DEMO"
                      else "Eye contact with the lens.")}
        for i, s in enumerate(primary)
    ]

    return {
        "product_name": name,
        "description": desc,
        "audience": who,
        "offer": deal,
        "product_url": product_url.strip(),
        "format": "9:16 vertical · ~30 seconds · TikTok / Reels / Shorts",
        "hooks": hooks,
        "scripts": scripts,
        "captions": captions,
        "hashtags": _hashtags(name, who, desc),
        "shot_list": shot_list,
    }


# Built-in gallery samples, generated by the same engine (no hand-written fakes).
def samples():
    demos = [
        ("Red Demon Tee", "A black tee with a red demon graphic that gets comments "
         "every time you wear it. Soft print, no cracking, holds up in the wash.",
         "streetwear fans", "20% off this week at Dillonsprints"),
        ("Portable Blender", "Crushes ice and frozen fruit in 20 seconds. USB "
         "rechargeable, fits in a gym bag, rinses clean under the tap.",
         "gym-goers and busy parents", "Free shipping today"),
        ("Tiny Key Tracker", "A coin-size tracker that rings from your phone. "
         "Finds keys, bags, and remotes in seconds instead of morning panic.",
         "anyone who loses their keys", "50% off today"),
    ]
    return [generate(n, d, a, o) for n, d, a, o in demos]

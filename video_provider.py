"""Video generation provider adapter.

The ad package (script, shot list, captions) is the deliverable Ad Forge
controls. Turning it into a rendered MP4 is delegated to a provider
behind this adapter so the app never depends on one vendor:

  CONFIGURED MODE — VIDEO_API_URL + VIDEO_API_KEY are set:
    POSTs the ad package as JSON to VIDEO_API_URL with a Bearer key.
    Expects back {"job_id": "..."} or {"video_url": "..."}.
    Any HTTP video API (self-hosted renderer, Runway/Pika-style
    services, an internal Army renderer) can sit behind this contract.

  STUB MODE — no keys set (the default, $0):
    Returns status "stub" with a storyboard reference. The user gets
    the complete shoot-ready package (scripts, shot list, captions)
    and renders it with any phone/camera or a future provider.
    The app runs end-to-end in stub mode and never crashes for a
    missing key.
"""
import json
import urllib.request

import config


def submit(package: dict) -> dict:
    """Submit an ad package for video rendering.

    Returns {"status": "stub"|"queued"|"ready"|"error",
             "ref": storyboard id / job id / video url,
             "detail": human-readable explanation}
    """
    if not config.video_configured():
        return {
            "status": "stub",
            "ref": "storyboard",
            "detail": (
                "Video rendering is in storyboard mode: no video API is "
                "configured yet, so you get the complete shoot-ready "
                "package instead of a rendered MP4. Film it from the "
                "shot list, or plug a video API into VIDEO_API_URL / "
                "VIDEO_API_KEY to render automatically."
            ),
        }

    try:
        req = urllib.request.Request(
            config.VIDEO_API_URL,
            data=json.dumps({"package": package}).encode(),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {config.VIDEO_API_KEY}",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=20) as resp:
            body = json.loads(resp.read().decode() or "{}")
        if body.get("video_url"):
            return {"status": "ready", "ref": body["video_url"],
                    "detail": "Video rendered by the configured provider."}
        return {"status": "queued", "ref": body.get("job_id", "unknown"),
                "detail": "Render job accepted by the configured provider."}
    except Exception as exc:  # provider down/misconfigured — never crash the flow
        return {"status": "error", "ref": "",
                "detail": f"Video provider call failed ({exc}). The ad "
                          "package itself is complete and saved."}

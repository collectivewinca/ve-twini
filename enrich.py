"""URL expansion and media extraction for ve-twini"""
import subprocess


def expand_tco_urls(urls: list[str]) -> list[dict]:
    """Resolve t.co shortened URLs to real URLs"""
    results = []
    for url in urls:
        result = subprocess.run(
            ["curl", "-sIL", "-o", "/dev/null", "-w", "%{url_effective}", url],
            capture_output=True, text=True
        )
        if result.returncode == 0:
            effective_url = result.stdout.strip()
            results.append({
                "original": url,
                "expanded": effective_url
            })
        else:
            results.append({"original": url, "expanded": url})
    return results


def extract_media_urls(tweet: dict) -> list[dict]:
    """Extract media URLs from a bird tweet object"""
    media = tweet.get("media", [])
    return [
        {
            "url": m.get("url") or m.get("videoUrl") or m.get("previewUrl", ""),
            "type": m.get("type", "unknown"),
            "width": m.get("width"),
            "height": m.get("height"),
        }
        for m in media
        if m.get("url") or m.get("videoUrl") or m.get("previewUrl")
    ]
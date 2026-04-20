import pytest
from enrich import expand_tco_urls, extract_media_urls

def test_expand_tco_urls():
    """Resolves t.co shortened URLs to real URLs"""
    urls = ["https://t.co/xgecemAaiq"]
    expanded = expand_tco_urls(urls)
    assert "x.com/HeritageMatterz" in expanded[0]["expanded"]
    assert "video" in expanded[0]["expanded"] or "pbs.twimg.com" in expanded[0]["expanded"]

def test_extract_media_from_tweet():
    """Extracts media URLs from bird JSON tweet objects"""
    tweet = {
        "id": "123",
        "text": "check this out https://t.co/abc",
        "media": [
            {"url": "https://pbs.twimg.com/media/img.jpg", "type": "photo"}
        ]
    }
    result = extract_media_urls(tweet)
    assert result[0]["url"] == "https://pbs.twimg.com/media/img.jpg"
    assert result[0]["type"] == "photo"
from urllib.parse import urlparse

def is_valid_space_url(url: str) -> bool:
    url = (url or "").strip()
    if not url:
        return False
    p = urlparse(url)
    if p.scheme not in ("http", "https"):
        return False
    if not p.netloc:
        return False
    host = p.netloc.lower()
    return any(host.endswith(h) for h in ("x.com", "twitter.com", "mobile.twitter.com"))

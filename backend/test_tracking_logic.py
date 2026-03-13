import re
from urllib.parse import quote

def _inject_tracking(html_content: str, tracking_token: str, base_url: str) -> str:
    # ── Step 1: Rewrite links ─────────────────────────────────────────────────
    def rewrite_link(match: re.Match) -> str:
        original_url = match.group(1)
        encoded_url  = quote(original_url, safe="")
        track_url    = (
            f"{base_url}/api/track/click"
            f"?token={tracking_token}&url={encoded_url}"
        )
        return f'href="{track_url}"'

    html_content = re.sub(r'href="(https?://[^"]+)"', rewrite_link, html_content)

    # ── Step 1.5: Convert bare URLs to clickable tracked links ───────────────
    def rewrite_bare_link(match: re.Match) -> str:
        tag_match = match.group(1)
        url_match = match.group(2)
        
        if tag_match:
            return tag_match # Return <a> tag as-is
            
        # Avoid double-rewriting if it's already a tracking URL
        if base_url in url_match:
            return url_match
        
        encoded_url  = quote(url_match, safe="")
        track_url    = (
            f"{base_url}/api/track/click"
            f"?token={tracking_token}&url={encoded_url}"
        )
        return f'<a href="{track_url}">{url_match}</a>'
        
    # Pattern: match <a>...</a> OR a standalone URL
    pattern = r'(<a\s+[^>]*>.*?</a>)|(?<!["\'])(https?://[^\s<>"\']+)'
    html_content = re.sub(pattern, rewrite_bare_link, html_content, flags=re.IGNORECASE | re.DOTALL)

    return html_content

# Test Cases
test_html = """
<p>Visit <a href="http://google.com">http://google.com</a></p>
<p>Plain link: https://example.com</p>
"""

token = "test-token"
base = "http://localhost:8000"

output = _inject_tracking(test_html, token, base)
print("--- OUTPUT ---")
print(output)
print("--- END ---")

# A nested link would look like <a ...><a ...>...</a></a>
# We can check if there's an <a> tag starting inside another <a> tag's content.
if re.search(r'<a[^>]*>[^<]*<a[^>]*>', output, re.DOTALL):
    print("NESTED LINK DETECTED!")
else:
    print("No nested links found.")

# Verify that plain links are still tracked
if 'Plain link: <a href="http://localhost:8000/api/track/click?token=test-token&url=https%3A%2F%2Fexample.com">https://example.com</a>' in output:
    print("Plain link tracked correctly.")
else:
    print("Plain link NOT tracked correctly or formatted wrong.")

# Verify that existing links are tracked but not nested
if 'Visit <a href="http://localhost:8000/api/track/click?token=test-token&url=http%3A%2F%2Fgoogle.com">http://google.com</a>' in output:
    print("Existing link tracked correctly (not nested).")
else:
    print("Existing link NOT tracked correctly.")

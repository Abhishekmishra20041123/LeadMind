import re

def clean_ai_content(content: str) -> str:
    """
    Remove redundant AI-generated elements like footers, unsubscribe links, 
    and extra buttons that are already part of the global template.
    """
    if not content:
        return ""
        
    # FOOTER CLEANING: Only look at the last 1000 characters to avoid middle-content wipe
    if len(content) > 1000:
        main_body = content[:-1000]
        potential_footer = content[-1000:]
    else:
        main_body = ""
        potential_footer = content

    # Patterns focused on footer markers
    footer_patterns = [
        r'<hr[^>]*>.*?(?:unsubscribe|privacy policy|©|copyright).*',
        r'<footer[^>]*>.*?</footer>',
        r'<div[^>]*padding-top[^>]*>.*?(?:unsubscribe|privacy policy).*?</div>',
        # Simple text lines often found at the bottom
        r'<p[^>]*>.*?unsubscribe.*?\|.*?privacy policy.*?</p>',
    ]
    
    cleaned_footer = potential_footer
    for pattern in footer_patterns:
        cleaned_footer = re.sub(pattern, '', cleaned_footer, flags=re.DOTALL | re.IGNORECASE)
        
    # BUTTON CLEANING: Only remove if it contains typical CTA text and has large styling
    button_pattern = r'<a[^>]*style=[^>]*?(?:background|padding:1\dpx)[^>]*>.*?(?:Visit|Order|Book|Call|Shop|Store).*?</a>'
    
    # Run button cleaning on the whole thing but be VERY specific about what's a CTA button
    cleaned = main_body + cleaned_footer
    cleaned = re.sub(button_pattern, '', cleaned, flags=re.IGNORECASE | re.DOTALL)
    
    return cleaned.strip()

# Test with various inputs
test_cases = [
    "Hi there, enjoy your coffee.<hr><p>© 2025 Coffee Co | Unsubscribe</p>",
    "Hey! <a href='#' style='background:red;padding:15px'>Visit our store</a> and buy more.",
    "Normal text with copyright © symbol in middle should stay."
]

for tc in test_cases:
    print(f"Input: {tc}")
    print(f"Output: {clean_ai_content(tc)}")
    print("-" * 20)

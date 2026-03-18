import re

# Actual HTML from DB dump
email_preview = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Tiffany & Co. - Personalized Selection for You</title>
</head>
<body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; color: #333;">
    
    <p>Dear Alex,</p>
    
    <p>I wanted to reach out because I noticed you were exploring our stunning collection.</p>
    
    <h3>Platinum Diamond Engagement Rings</h3>
    <div style="border:1px solid #e0e0e0; border-radius:8px; padding:20px; margin:20px 0; background-color:#f9f9f9; text-align:center;">
        <h4 style="margin:0 0 10px 0; color:#333;">Platinum Diamond Engagement Rings</h4>
        <p style="color:#666; margin-bottom:15px;">Iconic Tiffany setting, exceptional brilliance</p>
        <a href="https://example.com" style="...">View Selection</a>
    </div>
    
    <p>I'd be delighted to discuss any of these pieces with you. Would you have a moment to chat?</p>
    
    <p>Warm regards,<br>
    <strong>Your Dedicated Sales Advisor</strong><br>
    Tiffany & Co.</p>
</body>
</html>
"""

product_cards_html = "<!-- VERIFIED PRODUCT CARDS HERE -->"

# 1. Sanitize
email_preview = re.sub(r'<iframe.*?>.*?</iframe>', '', email_preview, flags=re.DOTALL)
# Strip hallucinated card-like structures with "View Selection"
email_preview = re.sub(r'<div[^>]*?>.*?View Selection.*?</div>', '', email_preview, flags=re.DOTALL | re.IGNORECASE)

# 2. Replace placeholders or fallback to append
if "[PRODUCT_CATALOG]" in email_preview or "[INSERT_PRODUCTS_HERE]" in email_preview:
    email_preview = email_preview.replace("[PRODUCT_CATALOG]", product_cards_html)
    email_preview = email_preview.replace("[INSERT_PRODUCTS_HERE]", product_cards_html)
else:
    # Force insertion before the closing sign-off if possible, otherwise append
    sign_offs = ["Best,", "Regards,", "Sincerely,", "Thanks,", "Best Regards,", "Warm regards,", "Yours,"]
    inserted = False
    for sign_off in sign_offs:
        if sign_off.lower() in email_preview.lower():
            start_idx = email_preview.lower().find(sign_off.lower())
            actual_sign_off = email_preview[start_idx:start_idx+len(sign_off)]
            email_preview = email_preview.replace(actual_sign_off, f"\n\n{product_cards_html}\n\n{actual_sign_off}")
            inserted = True
            break
    if not inserted:
        email_preview += f"\n\n{product_cards_html}"

print("=== PROCESSED HTML ===")
print(email_preview)

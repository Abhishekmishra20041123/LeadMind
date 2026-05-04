import re

def render_block_html(block: dict, gs: dict) -> str:
    bg = block.get("bgColor") or gs.get("contentBgColor", "#ffffff")
    def wrap(inner: str, bgcol: str) -> str:
        return f'<tr><td style="background:{bgcol};padding:0 24px;">{inner}</td></tr>'

    btype = block.get("type")
    
    if btype == "logo":
        align = block.get("align", "center")
        src = block.get("src", "")
        width = block.get("width", 150)
        alt = block.get("alt", "Logo")
        inner = f'<table width="100%" cellpadding="0" cellspacing="0" border="0"><tr><td align="{align}" style="padding:16px 0;">'
        if src:
            inner += f'<img src="{src}" width="{width}" alt="{alt}" style="display:block;border:0;max-width:100%;" />'
        else:
            inner += f'<div style="width:{width}px;height:60px;background:#e0e0e0;line-height:60px;text-align:center;color:#999;font-size:13px;font-family:Arial,sans-serif;display:inline-block;">Logo Placeholder</div>'
        inner += '</td></tr></table>'
        return wrap(inner, bg)
        
    elif btype == "banner":
        src = block.get("src", "")
        max_h = block.get("maxHeight", 220)
        link = block.get("link", "#")
        alt = block.get("alt", "Banner")
        if src:
            inner = f'<a href="{link}" style="display:block;line-height:0;"><img src="{src}" style="display:block;width:100%;max-height:{max_h}px;object-fit:cover;border:0;" alt="{alt}" /></a>'
        else:
            inner = f'<table width="100%" cellpadding="0" cellspacing="0" border="0"><tr><td align="center" valign="middle" height="{max_h}" style="background:linear-gradient(135deg,#667eea,#764ba2);color:#ffffff;font-size:20px;font-family:Arial,sans-serif;opacity:0.7;">Banner Image</td></tr></table>'
        return wrap(inner, bg)
        
    elif btype == "heading":
        fs = block.get("fontSize", 26)
        col = block.get("color", "#1a1a1a")
        align = block.get("align", "left")
        wgt = "700" if block.get("bold", True) else "400"
        stl = "italic" if block.get("italic", False) else "normal"
        ff = gs.get("fontFamily", "Arial, sans-serif")
        text = block.get("text", "Your Headline Here")
        inner = f'<h2 style="margin:20px 0 10px;font-size:{fs}px;color:{col};text-align:{align};font-weight:{wgt};font-style:{stl};font-family:{ff};">{text}</h2>'
        return wrap(inner, bg)
        
    elif btype == "text":
        fs = block.get("fontSize", 15)
        col = block.get("color", "#333333")
        align = block.get("align", "left")
        lh = block.get("lineHeight", 1.7)
        ff = gs.get("fontFamily", "Arial, sans-serif")
        text = block.get("text", "").replace("\\n", "<br/>")
        inner = f'<p style="margin:0 0 16px;font-size:{fs}px;color:{col};text-align:{align};line-height:{lh};font-family:{ff};">{text}</p>'
        return wrap(inner, bg)
        
    elif btype == "ai_body":
        fs = block.get("fontSize", 15)
        col = block.get("color", "#333333")
        align = block.get("align", "left")
        lh = block.get("lineHeight", 1.7)
        ff = gs.get("fontFamily", "Arial, sans-serif")
        inner = f'<div id="ai-email-body-editable" style="font-size:{fs}px;color:{col};text-align:{align};line-height:{lh};font-family:{ff};">{{{{personalized_message}}}}</div>'
        return wrap(inner, bg)
        
    elif btype == "greeting":
        fs = block.get("fontSize", 18)
        col = block.get("color", "#1a1a1a")
        wgt = "700" if block.get("bold", True) else "400"
        ff = gs.get("fontFamily", "Arial, sans-serif")
        pref = block.get("prefix", "Hi")
        name = block.get("name", "{{customer_name}}")
        suff = block.get("suffix", ",")
        inner = f'<p style="margin:20px 0 10px;font-size:{fs}px;color:{col};font-weight:{wgt};font-family:{ff};">{pref} {name}{suff}</p>'
        return wrap(inner, bg)
        
    elif btype == "desc":
        fs = block.get("fontSize", 15)
        col = block.get("color", "#333333")
        align = block.get("align", "left")
        lh = block.get("lineHeight", 1.7)
        ff = gs.get("fontFamily", "Arial, sans-serif")
        text = block.get("text", "").replace("\\n", "<br/>")
        inner = f'<p style="margin:0 0 16px;font-size:{fs}px;color:{col};text-align:{align};line-height:{lh};font-family:{ff};background:{bg};padding:16px;border-left:4px solid #0a0a0a;">{text}</p>'
        return wrap(inner, bg)
        
    elif btype == "cta":
        url = block.get("url", "https://")
        btc = block.get("bgColor", "#0a0a0a")
        tc = block.get("textColor", "#ffffff")
        fs = block.get("fontSize", 15)
        ff = gs.get("fontFamily", "Arial, sans-serif")
        rad = block.get("borderRadius", 4)
        lbl = block.get("label", "Book a Call")
        cta = f'<a href="{url}" style="display:inline-block;padding:14px 32px;background:{btc};color:{tc};font-size:{fs}px;font-family:{ff};font-weight:700;text-decoration:none;border-radius:{rad}px;">{lbl}</a>'
        align = block.get("align", "center")
        return wrap(f'<table width="100%" cellpadding="0" cellspacing="0"><tr><td align="{align}" style="padding:20px 0;">{cta}</td></tr></table>', "#ffffff")
        
    elif btype == "divider":
        my = block.get("marginY", 16)
        th = block.get("thickness", 1)
        st = block.get("style", "solid")
        col = block.get("color", "#e0e0e0")
        return f'<tr><td style="padding:{my}px 24px;"><hr style="border:none;border-top:{th}px {st} {col};margin:0;" /></td></tr>'
        
    elif btype == "footer":
        align = block.get("align", "center")
        fs = block.get("fontSize", 12)
        col = block.get("color", "#888888")
        ff = gs.get("fontFamily", "Arial, sans-serif")
        
        company = block.get("companyText") or block.get("text") or "© 2026 BRIGHT ZENITH PRIVATE LIMITED"
        socials = block.get("socials", {})
        icons = []
        icon_size = 24
        icon_color = col.replace('#', '') if col.startswith('#') else col
        
        mapping = {
            "x": "twitterx--v2",
            "discord": "discord-logo",
            "youtube": "youtube-play",
            "linkedin": "linkedin",
            "facebook": "facebook-new",
            "instagram": "instagram-new"
        }
        
        for plat, slug in mapping.items():
            url = socials.get(plat)
            if url:
                icons.append(
                    f'<a href="{url}" style="display:inline-block;margin:0 12px;">'
                    f'<img src="https://img.icons8.com/ios-filled/50/{icon_color}/{slug}.png" '
                    f'alt="{plat.upper()}" width="{icon_size}" height="{icon_size}" style="border:0;display:block;" />'
                    f'</a>'
                )
        
        icons_html = f'<div style="margin-bottom:16px;text-align:center;">{"".join(icons)}</div>' if icons else ""
        
        links_html = []
        website = block.get("websiteUrl")
        unsub = block.get("unsubscribeUrl", "https://")
        if website:
            links_html.append(f'<a href="{website}" style="color:{col};text-decoration:none;">Visit website</a>')
        if unsub:
            links_html.append(f'<a href="{unsub}" style="color:{col};text-decoration:none;">Unsubscribe</a>')
        
        bottom_links = f'<div style="margin-top:16px;opacity:0.8;">{" &nbsp;|&nbsp; ".join(links_html)}</div>' if links_html else ""
        
        inner = (
            f'<div style="padding:24px 0;text-align:{align};font-size:{fs}px;color:{col};font-family:{ff};line-height:1.6;">'
            f'{icons_html}'
            f'<div>{company.replace("\\n", "<br/>")}</div>'
            f'{bottom_links}'
            f'</div>'
        )
        return wrap(inner, bg)
        
    return ""

def render_blocks_to_html(blocks: list, gs: dict) -> str:
    rows = "\n".join(render_block_html(b, gs) for b in blocks)
    obg = gs.get("outerBgColor", "#e8e8e8")
    cbg = gs.get("contentBgColor", "#ffffff")
    ff = gs.get("fontFamily", "Arial, sans-serif")
    mw = gs.get("maxWidth", 600)
    
    return f"""<!DOCTYPE html>
<html><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>
    #ai-email-body-editable h3 {{
        margin: 24px 0 12px 0 !important;
        font-size: 18px !important;
        line-height: 1.3 !important;
        color: #1a1a1a !important;
        font-weight: 700 !important;
    }}
    #ai-email-body-editable ul {{
        margin: 0 0 16px 0 !important;
        padding: 0 0 0 20px !important;
    }}
    #ai-email-body-editable li {{
        margin-bottom: 8px !important;
        line-height: 1.6 !important;
    }}
    #ai-email-body-editable p {{
        margin: 0 0 16px 0 !important;
        line-height: 1.7 !important;
    }}
    #ai-email-body-editable strong {{
        color: #000000 !important;
    }}
</style>
</head>
<body style="margin:0;padding:0;background:{obg};font-family:{ff};">
<table width="100%" cellpadding="0" cellspacing="0" style="background:{obg};">
<tr><td align="center" style="padding:24px 12px;">
<table width="{mw}" cellpadding="0" cellspacing="0" style="background:{cbg};border-radius:4px;overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,0.08);">
{rows}
</table>
</td></tr></table>
</body></html>"""

def clean_ai_content(content: str) -> str:
    """
    Remove redundant AI-generated elements like footers and buttons 
    only if they clearly match a footer pattern at the end of the text.
    """
    if not content:
        return ""
        
    # Pattern 1: Horizontal rule followed specifically by a copyright/unsubscribe block
    # We restrict this to a non-greedy block to avoid matching the whole rest of the email
    footer_block_pattern = r'<hr[^>]*>\s*<(?:p|div|footer)[^>]*>.*?(?:unsubscribe|privacy policy|©|copyright).*?<\/(?:p|div|footer)>'
    
    # Pattern 2: Standalone footer tags
    standalone_footer = r'<footer[^>]*>.*?</footer>'
    
    # Pattern 3: Common AI generated button with specific CTA text
    cta_button = r'<a[^>]*style=[^>]*?(?:background|padding)[^>]*>.*?(?:Order|Shop|Visit|Book|Chat|Call).*?</a>'

    cleaned = content
    # Remove footer blocks
    cleaned = re.sub(footer_block_pattern, '', cleaned, flags=re.DOTALL | re.IGNORECASE)
    cleaned = re.sub(standalone_footer, '', cleaned, flags=re.DOTALL | re.IGNORECASE)
    # Remove CTA buttons
    cleaned = re.sub(cta_button, '', cleaned, flags=re.IGNORECASE)
    
    return cleaned.strip()

def render_template(html: str, lead: dict, company: dict) -> str:
    """Replace {{placeholder}} tokens in a template HTML with actual lead/company data.
    Also supports single {placeholder} for common fields to be robust.
    """
    raw_preview = lead.get("intel", {}).get("email", {}).get("preview", "")
    # Clean the content to remove redundant footers/buttons
    cleaned_preview = clean_ai_content(raw_preview)
    
    replacements = {
        "customer_name": lead.get("profile", {}).get("name", ""),
        "customer_company": lead.get("profile", {}).get("company", ""),
        "customer_title": lead.get("profile", {}).get("title", ""),
        "personalized_message": cleaned_preview,
        "operator_name": company.get("contact_person_name", company.get("company_name", "")),
        "operator_company": company.get("company_name", ""),
        "operator_email": company.get("email", ""),
    }
    
    for key, value in replacements.items():
        v_str = str(value) if value else ""
        # Replace double braces
        html = html.replace(f"{{{{{key}}}}}", v_str)
        # Replace single braces
        html = html.replace(f"{{{key}}}", v_str)
        
    return html

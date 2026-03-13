import sys
import os

# Add the backend directory to sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from api.templates import render_block_html

def test_footer_icons():
    print("Testing footer social icons rendering...")
    
    gs = {"fontFamily": "Arial, sans-serif"}
    footer_block = {
        "type": "footer",
        "align": "center",
        "fontSize": 12,
        "color": "#888888",
        "bgColor": "#ffffff",
        "companyText": "Shelby Company Limited",
        "websiteUrl": "https://shelby.com",
        "unsubscribeUrl": "https://shelby.com/unsubscribe",
        "socials": {
            "x": "https://x.com/shelby",
            "discord": "https://discord.gg/shelby",
            "youtube": "https://youtube.com/shelby"
        }
    }
    
    html = render_block_html(footer_block, gs)
    
    # Assertions
    icons = [
        "twitterx--v2",
        "discord-logo",
        "youtube-play"
    ]
    
    all_passed = True
    for icon in icons:
        if icon in html:
            print(f"✅ Icon slug '{icon}' detected")
        else:
            print(f"❌ Icon slug '{icon}' MISSING")
            all_passed = False
            
    if "888888" in html:
        print("✅ Icon color hex detected")
    else:
        print("❌ Icon color hex MISSING")
        all_passed = False
        
    if "Shelby Company Limited" in html:
        print("✅ Company text detected")
    else:
        print("❌ Company text MISSING")
        all_passed = False

    if "Visit website" in html and "Unsubscribe" in html:
        print("✅ Footer links detected")
    else:
        print("❌ Footer links MISSING")
        all_passed = False
            
    if all_passed:
        print("\nSUCCESS: Footer social icons are rendering correctly.")
    else:
        print("\nFAILURE: Some elements are missing.")
        sys.exit(1)

if __name__ == "__main__":
    test_footer_icons()

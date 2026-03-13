import sys
import os

# Add the backend directory to sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from api.templates import render_blocks_to_html

def test_aesthetics():
    print("Testing email aesthetics enhancement...")
    
    blocks = [
        {"type": "ai_body"}
    ]
    gs = {
        "outerBgColor": "#f4f4f4",
        "contentBgColor": "#ffffff",
        "fontFamily": "Inter, Arial, sans-serif",
        "maxWidth": 650
    }
    
    html = render_blocks_to_html(blocks, gs)
    
    # Assertions
    checks = {
        "h3 style": "#ai-email-body-editable h3",
        "ul style": "#ai-email-body-editable ul",
        "li style": "#ai-email-body-editable li",
        "p style": "#ai-email-body-editable p",
        "strong style": "#ai-email-body-editable strong",
        "viewport": 'meta name="viewport"',
        "personalized message": "{{personalized_message}}"
    }
    
    all_passed = True
    for name, snippet in checks.items():
        if snippet in html:
            print(f"✅ {name} detected")
        else:
            print(f"❌ {name} MISSING")
            all_passed = False
            
    if all_passed:
        print("\nSUCCESS: All aesthetic enhancements are present in the template renderer.")
    else:
        print("\nFAILURE: Some elements are missing.")
        sys.exit(1)

if __name__ == "__main__":
    test_aesthetics()

import asyncio
from db import leads_collection

async def main():
    lead_doc = await leads_collection.find_one({"lead_id": "L209"})
    if lead_doc:
         html = lead_doc.get("intel", {}).get("email", {}).get("sent_html", "")
         print("Length of sent HTML:", len(html))
         
         # See if the text "Tony Starkg" or "Jordan" is in the HTML
         if "Jordan" in html:
              print("YES! 'Jordan' is in the HTML.")
         else:
              print("NO! 'Jordan' is missing from the HTML.")
              
         if "Tony Starkg" in html:
              print("YES! 'Tony Starkg' is in the HTML.")
         else:
              print("NO! 'Tony Starkg' is missing from the HTML.")
              
         # Let's print the actual AI body container to see what's in it
         import re
         # Find the div that contains the personalized message
         parts = html.split('<div id="ai-email-body-editable"')
         if len(parts) > 1:
              body_and_rest = parts[1]
              end_idx = body_and_rest.find('</div>')
              if end_idx != -1:
                   print("--- AI BODY EXTRACT ---")
                   print('<div id="ai-email-body-editable"' + body_and_rest[:end_idx+6])
              else:
                   print("Could not find end of AI body div")
         else:
              # Fallback to check if the old style div is there
              parts2 = html.split('<div style="font-size:15px;color:#333333;text-align:left;line-height:1.7;font-family:Arial, sans-serif;">')
              if len(parts2) > 1:
                   body_and_rest2 = parts2[1]
                   end_idx2 = body_and_rest2.find('</div>')
                   print("--- OLD AI BODY EXTRACT ---")
                   print("CONTENT:", body_and_rest2[:end_idx2])
              else:
                   print("Could not find AI body div at all in the HTML")

asyncio.run(main())

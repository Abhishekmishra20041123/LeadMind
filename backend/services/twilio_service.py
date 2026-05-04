import os
import re
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from bson import ObjectId
from db import (
    leads_collection, agent_activity_collection, channel_settings_collection,
    companies_collection
)

DEFAULT_FALLBACK_PHONE = "+917777039470"

class TwilioService:
    @staticmethod
    def _extract_channel_media(lead: dict):
        # ── Step 0: Check for standardized 'scraped_media' populated by EmailNode ──
        intel = lead.get("intel", {})
        scraped = intel.get("scraped_media", [])
        if scraped and isinstance(scraped, list):
            # Return the list of all images and the primary page link
            primary_link = scraped[0].get("url", "")
            all_images = [item.get("image") for item in scraped if item.get("image")]
            return primary_link, all_images

        email_preview = intel.get("email", {}).get("preview", "")
        page_link = ""
        # Default fallback (Diamond rings)
        img_urls = ["https://images.unsplash.com/photo-1617038220319-276d3cfab638?q=80&w=800"]
        
        if email_preview:
            img_match = re.search(r'<img[^>]+src="([^"]+)"', email_preview)
            if img_match:
                img_urls = [img_match.group(1)]
                
            link_match = re.search(r'<a[^>]+href="([^"]+)"', email_preview)
            if link_match:
                page_link = link_match.group(1)
                
        if not page_link:
            raw_data = lead.get("raw_data", {})
            sdk = lead.get("sdk_activity", {})
            visited_urls = sdk.get("urls", sdk.get("page_link", []))
            if not visited_urls:
                visited_urls = raw_data.get("page_link", [])
            if not visited_urls:
                visited_urls = lead.get("page_link", [])
            
            if isinstance(visited_urls, str):
                visited_urls = [u.strip() for u in visited_urls.replace("|", ",").split(",") if u.strip()]
                
            for u in visited_urls:
                if str(u).startswith("http"):
                    page_link = str(u)
                    break
                    
        # If using the default fallback, try to refine it based on industry
        if "photo-1617038220319-276d3cfab638" in img_urls[0]:
            industry = str(lead.get("profile", {}).get("industry", lead.get("raw_data", {}).get("industry", ""))).lower()
            company = str(lead.get("profile", {}).get("company", "")).lower()
            
            fallbacks = {
                "headphones": "https://images.unsplash.com/photo-1505740420928-5e560c06d30e?q=80&w=800",
                "earbuds": "https://images.unsplash.com/photo-1590658268037-6bf12165a8df?q=80&w=800",
                "speaker": "https://images.unsplash.com/photo-1608156639585-340049e79780?q=80&w=800",
                "boat": "https://images.unsplash.com/photo-1505740420928-5e560c06d30e?q=80&w=800",
                "electronics": "https://images.unsplash.com/photo-1505740420928-5e560c06d30e?q=80&w=800",
                "jewelry": "https://images.unsplash.com/photo-1515562141207-7a88fb7ce33e?q=80&w=800",
                "bakery": "https://images.unsplash.com/photo-1509440159596-0249088772ff?q=80&w=800"
            }
            
            for key, url in fallbacks.items():
                if key in industry or key in company or (page_link and key in page_link.lower()):
                    img_urls = [url]
                    break

        return page_link, img_urls

    @staticmethod
    async def send_channel_message(company_id: str, lead_id: str, channel: str, draft_override: str = None):
        """
        Core logic to send a message via Twilio (SMS, WhatsApp, or Voice).
        Reused by both manual triggers and bulk approve flows.
        """
        if channel not in ("sms", "whatsapp", "voice"):
            raise ValueError("Invalid channel")

        try:
            comp_oid = ObjectId(company_id)
        except:
            comp_oid = company_id

        lead = await leads_collection.find_one({
            "lead_id": lead_id, 
            "$or": [{"company_id": company_id}, {"company_id": comp_oid}]
        })
        
        if not lead:
            raise ValueError("Lead not found")

        phone = lead.get("profile", {}).get("phone", "")
        if not phone:
            phone = DEFAULT_FALLBACK_PHONE

        draft = draft_override or lead.get("intel", {}).get("channels", {}).get(channel, {}).get("draft", "")
        if not draft:
            raise ValueError("No draft found. Please generate first.")

        # Fetch media and links
        page_link, img_urls = TwilioService._extract_channel_media(lead)
        
        # ── TEMPLATE ASSEMBLY ───────────────────────────────────────────────────
        chan_settings = await channel_settings_collection.find_one({
            "$or": [{"company_id": company_id}, {"company_id": str(company_id)}]
        })
        
        blocks = chan_settings.get(f"{channel}_template_blocks", []) if chan_settings else []
        
        final_body = ""
        template_img = None
        
        if not blocks:
            final_body = draft
        else:
            def repl(t):
                if not t: return ""
                name = lead.get("profile", {}).get("name", "there").split(" ")[0]
                comp = lead.get("profile", {}).get("company", lead.get("raw_data", {}).get("company", "your company"))
                t = t.replace("{{customer_name}}", name)
                t = t.replace("{{customer_company}}", comp)
                t = t.replace("{{sender_name}}", "Our Team")
                t = t.replace("{{page_link}}", page_link or "")
                return t

            for blk in blocks:
                btype = blk.get("type")
                btext = blk.get("text", "")
                
                if btype == "greeting":
                    final_body += repl(btext) + "\n\n"
                elif btype == "ai_msg":
                    final_body += draft + "\n\n"
                elif btype == "text":
                    final_body += repl(btext) + "\n\n"
                elif btype == "cta_link":
                    label = repl(blk.get("label", ""))
                    url = repl(blk.get("url", ""))
                    final_body += f"{label} {url}\n\n" if label else f"{url}\n\n"
                elif btype == "signature":
                    final_body += repl(btext)
                elif btype == "image_url":
                    if blk.get("url"):
                        template_img = blk.get("url")
            
        final_imgs = [template_img] if template_img else img_urls
            
        if page_link and page_link not in final_body:
            final_body += f"\n\nView here: {page_link}"
        
        final_body = final_body.strip()

        # Fetch credentials
        company = await companies_collection.find_one({"_id": ObjectId(company_id)})
        cfg = (company or {}).get("settings", {})
        
        has_creds = bool(cfg and cfg.get("twilio_account_sid") and cfg.get("twilio_auth_token"))
        sid = f"SIMULATED_{channel.upper()}_{lead_id}"

        if has_creds:
            try:
                from twilio.rest import Client
                client = Client(cfg["twilio_account_sid"], cfg["twilio_auth_token"])
                
                msg_kwargs = {"body": final_body}
                if final_imgs:
                    msg_kwargs["media_url"] = final_imgs

                if channel == "sms":
                    from_num = cfg.get("twilio_phone_number")
                    if not from_num: raise Exception("Twilio Phone Number missing")
                    msg_kwargs["from_"] = from_num
                    
                    clean_phone = phone.replace(" ", "").replace("-", "")
                    if len(clean_phone) == 10 and clean_phone.isdigit(): clean_phone = f"+91{clean_phone}"
                    elif not clean_phone.startswith("+"): clean_phone = f"+{clean_phone}"
                        
                    msg_kwargs["to"] = clean_phone
                    msg = client.messages.create(**msg_kwargs)
                    sid = msg.sid

                elif channel == "whatsapp":
                    wa_from = cfg.get("twilio_whatsapp_number") or cfg.get("twilio_phone_number")
                    if not wa_from: raise Exception("Twilio WhatsApp Number missing")
                    if not wa_from.startswith("whatsapp:"): wa_from = f"whatsapp:{wa_from}"
                    
                    # Sandbox Override: Force WhatsApp messages to the verified default receiver
                    sandbox_phone = DEFAULT_FALLBACK_PHONE
                    clean_phone = sandbox_phone.replace(" ", "").replace("-", "")
                    if len(clean_phone) == 10 and clean_phone.isdigit(): clean_phone = f"+91{clean_phone}"
                    elif not clean_phone.startswith("+"): clean_phone = f"+{clean_phone}"
                    
                    to_wa = f"whatsapp:{clean_phone}" if not clean_phone.startswith("whatsapp:") else clean_phone
                    msg_kwargs["from_"] = wa_from
                    msg_kwargs["to"] = to_wa
                    
                    print(f"\n==================================================")
                    print(f"[TWILIO DEBUG] SENDING WHATSAPP:")
                    print(f"  FROM: {msg_kwargs.get('from_')}")
                    print(f"  TO:   {msg_kwargs.get('to')}")
                    print(f"  BODY: {str(msg_kwargs.get('body'))[:60]}...")
                    print(f"  MEDIA: {msg_kwargs.get('media_url')}")
                    print(f"==================================================\n")
                    
                    msg = client.messages.create(**msg_kwargs)
                    
                    print(f"\n==================================================")
                    print(f"[TWILIO DEBUG] WHATSAPP RESPONSE:")
                    print(f"  SID:    {msg.sid}")
                    print(f"  STATUS: {msg.status}")
                    print(f"  ERROR:  {msg.error_message}")
                    print(f"  CODE:   {msg.error_code}")
                    print(f"==================================================\n")
                    
                    sid = msg.sid

                elif channel == "voice":
                    from twilio.twiml.voice_response import VoiceResponse, Gather
                    vr = VoiceResponse()
                    
                    base_url = os.getenv("BACKEND_BASE_URL", "").rstrip("/")
                    if base_url:
                        gather = Gather(input="speech", action=f"{base_url}/api/channels/voice-reply?lead_id={lead_id}", speechTimeout="auto", language="en-IN", enhanced="true")
                        gather.say(draft, voice="Polly.Aditi", language="en-IN")
                        vr.append(gather)
                    else:
                        vr.say(draft, voice="Polly.Aditi", language="en-IN")
                    
                    clean_phone = phone.replace(" ", "").replace("-", "")
                    if len(clean_phone) == 10 and clean_phone.isdigit(): clean_phone = f"+91{clean_phone}"
                    elif not clean_phone.startswith("+"): clean_phone = f"+{clean_phone}"
                        
                    call = client.calls.create(twiml=str(vr), from_=cfg["twilio_phone_number"], to=clean_phone)
                    sid = call.sid
            except ImportError:
                print("[TwilioService] twilio-python not installed. Simulating.")
            except Exception as e:
                print(f"[TwilioService] Twilio delivery failed: {e}")
                raise e

        now = datetime.now(timezone.utc)
        await leads_collection.update_one(
            {"lead_id": lead_id, "$or": [{"company_id": company_id}, {"company_id": comp_oid}]},
            {"$set": {f"intel.channels.{channel}.sent": True,
                      f"intel.channels.{channel}.sent_at": now,
                      f"intel.channels.{channel}.sid": sid,
                      f"intel.channels.{channel}.draft": draft}}
        )
        await agent_activity_collection.insert_one({
            "company_id": company_id, "lead_id": lead_id,
            "agent": f"{channel.upper()}_AGENT",
            "action": f"{channel.upper()} sent to {phone} | SID: {sid}",
            "status": "SUCCESS", "timestamp": now,
        })
        
        return {"success": True, "sid": sid, "channel": channel, "sent_at": now.isoformat()}

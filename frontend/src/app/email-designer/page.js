"use client";
import DashboardLayout from "../../components/DashboardLayout";
import { useState, useRef, useCallback, useEffect } from "react";

const API = "http://localhost:8000/api";

// ─────────────────────────────────────────────────────────────────────────────
// Helpers
// ─────────────────────────────────────────────────────────────────────────────
const uid = () => Math.random().toString(36).slice(2, 9);

const FONTS = ["Arial, sans-serif", "Georgia, serif", "Courier New, monospace", "Trebuchet MS, sans-serif", "Inter, sans-serif"];
const FONT_LABELS = ["Arial", "Georgia", "Courier New", "Trebuchet MS", "Inter"];

const PLACEHOLDERS = [
    { label: "Customer Name", token: "{{customer_name}}" },
    { label: "Customer Company", token: "{{customer_company}}" },
    { label: "Customer Title", token: "{{customer_title}}" },
    { label: "AI Message", token: "{{personalized_message}}" },
    { label: "Your Name", token: "{{operator_name}}" },
    { label: "Your Company", token: "{{operator_company}}" },
];

const SAMPLE_VALUES = {
    "{{customer_name}}": "Alex Johnson",
    "{{customer_company}}": "TechVision Corp",
    "{{customer_title}}": "VP of Engineering",
    "{{personalized_message}}": "We noticed TechVision Corp recently expanded its engineering team and has been investing heavily in cloud infrastructure — this aligns perfectly with what we offer.",
    "{{operator_name}}": "Sarah Mitchell",
    "{{operator_company}}": "YourCompany Inc.",
    "{{operator_email}}": "sarah@yourcompany.com",
};

function fillPreview(text) {
    let out = text || "";
    Object.entries(SAMPLE_VALUES).forEach(([t, v]) => { out = out.replaceAll(t, v); });
    return out;
}

// ─────────────────────────────────────────────────────────────────────────────
// Default block factories
// ─────────────────────────────────────────────────────────────────────────────
const makeBlock = (type) => {
    const base = { id: uid(), type };
    const defaults = {
        logo: { src: "", imageMode: "url", width: 150, align: "center", alt: "Logo", bgColor: "#ffffff" },
        banner: { src: "", imageMode: "url", fullWidth: true, maxHeight: 220, alt: "Banner", link: "", bgColor: "#ffffff" },
        heading: { text: "Your Headline Here", fontSize: 26, color: "#1a1a1a", bgColor: "#ffffff", align: "left", bold: true, italic: false },
        text: { text: "Write your message here. Use the placeholder buttons to add personalized fields.", fontSize: 15, color: "#333333", bgColor: "#ffffff", align: "left", lineHeight: 1.7 },
        greeting: { prefix: "Hi", suffix: ",", name: "{{customer_name}}", fontSize: 18, color: "#1a1a1a", bgColor: "#ffffff", bold: true },
        desc: { text: "Describe your product or service here.", fontSize: 15, color: "#333333", bgColor: "#f9f9f9", align: "left", lineHeight: 1.7 },
        cta: { label: "Book a Call", url: "https://", bgColor: "#0a0a0a", textColor: "#ffffff", borderRadius: 4, align: "center", fontSize: 15 },
        divider: { color: "#e0e0e0", thickness: 1, style: "solid", marginY: 16 },
        footer: { text: "© 2026 BRIGHT ZENITH PRIVATE LIMITED", websiteUrl: "https://brightzenith.com", unsubscribeUrl: "https://yourcompany.com/unsubscribe", socials: { x: "https://x.com", discord: "https://discord.com", youtube: "https://youtube.com", linkedin: "", facebook: "", instagram: "" }, fontSize: 12, color: "#888888", bgColor: "#ffffff", align: "center" },
        ai_body: { fontSize: 15, color: "#333333", bgColor: "#ffffff", align: "left", lineHeight: 1.7 },
    };
    return { ...base, ...(defaults[type] || {}) };
};

const BLOCK_PALETTE = [
    { type: "logo", icon: "image", label: "Logo" },
    { type: "banner", icon: "panorama", label: "Banner Image" },
    { type: "heading", icon: "title", label: "Heading" },
    { type: "text", icon: "subject", label: "Text Block" },
    { type: "ai_body", icon: "auto_awesome", label: "AI Email Body" },
    // { type: "greeting", icon: "waving_hand", label: "Greeting" },
    // { type: "desc", icon: "description", label: "Product Desc" },
    { type: "cta", icon: "smart_button", label: "CTA Button" },
    { type: "divider", icon: "horizontal_rule", label: "Divider" },
    { type: "footer", icon: "article", label: "Footer" },
];

// ─────────────────────────────────────────────────────────────────────────────
// HTML generator for preview / send
// ─────────────────────────────────────────────────────────────────────────────
function renderBlockHTML(block, gs, isPreview = false) {
    const fill = isPreview ? (t) => fillPreview(t) : (t) => t;
    const wrap = (inner, bg = block.bgColor || gs.contentBgColor) =>
        `<tr><td style="background:${bg};padding:0 24px;">${inner}</td></tr>`;

    switch (block.type) {
        case "logo":
            return wrap(
                `<table width="100%" cellpadding="0" cellspacing="0"><tr><td align="${block.align}" style="padding:16px 0;">` +
                (block.src ? `<img src="${block.src}" width="${block.width}" alt="${block.alt}" style="display:block;border:0;max-width:100%;" />` : `<div style="width:${block.width}px;height:60px;background:#e0e0e0;display:inline-flex;align-items:center;justify-content:center;color:#999;font-size:13px;font-family:Arial,sans-serif;">Logo Placeholder</div>`) +
                `</td></tr></table>`, block.bgColor
            );
        case "banner":
            return wrap(
                block.src
                    ? `<a href="${block.link || "#"}" style="display:block;line-height:0;"><img src="${block.src}" style="display:block;width:100%;max-height:${block.maxHeight}px;object-fit:cover;border:0;" alt="${block.alt}" /></a>`
                    : `<div style="width:100%;height:${block.maxHeight}px;background:linear-gradient(135deg,#667eea,#764ba2);display:flex;align-items:center;justify-content:center;"><span style="color:white;font-size:20px;font-family:Arial,sans-serif;opacity:0.7;">Banner Image</span></div>`,
                block.bgColor
            );
        case "heading":
            return wrap(`<h2 style="margin:20px 0 10px;font-size:${block.fontSize}px;color:${block.color};text-align:${block.align};font-weight:${block.bold ? "700" : "400"};font-style:${block.italic ? "italic" : "normal"};font-family:${gs.fontFamily};">${fill(block.text)}</h2>`, block.bgColor);
        case "text":
            return wrap(`<p style="margin:0 0 16px;font-size:${block.fontSize}px;color:${block.color};text-align:${block.align};line-height:${block.lineHeight};font-family:${gs.fontFamily};">${fill(block.text).replace(/\n/g, "<br/>")}</p>`, block.bgColor);
        case "ai_body":
            return wrap(
                isPreview
                    ? `<div style="padding:16px 0;font-size:${block.fontSize}px;color:${block.color};text-align:${block.align};line-height:${block.lineHeight};font-family:${gs.fontFamily};"><p style="margin:0 0 16px;font-style:italic;color:#999;">✨ [ AI Generated Email Content ]</p><p style="margin:0 0 16px;">Hi ${SAMPLE_VALUES["{{customer_name}"] || "Alex"},</p><p style="margin:0 0 16px;">${SAMPLE_VALUES["{{personalized_message}}"]}</p><p style="margin:0;">Best,<br/>${SAMPLE_VALUES["{{operator_name}"] || "Sarah"}</p></div>`
                    : `<div style="font-size:${block.fontSize}px;color:${block.color};text-align:${block.align};line-height:${block.lineHeight};font-family:${gs.fontFamily};">{{personalized_message}}</div>`,
                block.bgColor
            );
        case "greeting":
            return wrap(`<p style="margin:20px 0 10px;font-size:${block.fontSize}px;color:${block.color};font-weight:${block.bold ? "700" : "400"};font-family:${gs.fontFamily};">${block.prefix} ${fill(block.name)}${block.suffix}</p>`, block.bgColor);
        case "desc":
            return wrap(`<p style="margin:0 0 16px;font-size:${block.fontSize}px;color:${block.color};text-align:${block.align};line-height:${block.lineHeight};font-family:${gs.fontFamily};background:${block.bgColor};padding:16px;border-left:4px solid #0a0a0a;">${fill(block.text).replace(/\n/g, "<br/>")}</p>`, block.bgColor);
        case "cta": {
            const cta = `<a href="${block.url}" style="display:inline-block;padding:14px 32px;background:${block.bgColor};color:${block.textColor};font-size:${block.fontSize}px;font-family:${gs.fontFamily};font-weight:700;text-decoration:none;border-radius:${block.borderRadius}px;">${block.label}</a>`;
            return wrap(`<table width="100%" cellpadding="0" cellspacing="0"><tr><td align="${block.align}" style="padding:20px 0;">${cta}</td></tr></table>`, "#ffffff");
        }
        case "divider":
            return `<tr><td style="padding:${block.marginY}px 24px;"><hr style="border:none;border-top:${block.thickness}px ${block.style} ${block.color};margin:0;" /></td></tr>`;
        case "footer": {
            const company = block.companyText ?? block.text ?? "© 2026 BRIGHT ZENITH PRIVATE LIMITED";
            const socials = block.socials || {};
            const icons = [];
            const iconSize = 24;
            const iconColor = block.color ? block.color.replace('#', '') : "888888";
            
            if (socials.x) icons.push(`<a href="${socials.x}" style="display:inline-block;margin:0 12px;"><img src="https://img.icons8.com/ios-filled/50/${iconColor}/twitterx--v2.png" alt="X" width="${iconSize}" height="${iconSize}" style="border:0;display:block;" /></a>`);
            if (socials.discord) icons.push(`<a href="${socials.discord}" style="display:inline-block;margin:0 12px;"><img src="https://img.icons8.com/ios-filled/50/${iconColor}/discord-logo.png" alt="Discord" width="${iconSize}" height="${iconSize}" style="border:0;display:block;" /></a>`);
            if (socials.youtube) icons.push(`<a href="${socials.youtube}" style="display:inline-block;margin:0 12px;"><img src="https://img.icons8.com/ios-filled/50/${iconColor}/youtube-play.png" alt="YouTube" width="${iconSize}" height="${iconSize}" style="border:0;display:block;" /></a>`);
            if (socials.linkedin) icons.push(`<a href="${socials.linkedin}" style="display:inline-block;margin:0 12px;"><img src="https://img.icons8.com/ios-filled/50/${iconColor}/linkedin.png" alt="LinkedIn" width="${iconSize}" height="${iconSize}" style="border:0;display:block;" /></a>`);
            if (socials.facebook) icons.push(`<a href="${socials.facebook}" style="display:inline-block;margin:0 12px;"><img src="https://img.icons8.com/ios-filled/50/${iconColor}/facebook-new.png" alt="Facebook" width="${iconSize}" height="${iconSize}" style="border:0;display:block;" /></a>`);
            if (socials.instagram) icons.push(`<a href="${socials.instagram}" style="display:inline-block;margin:0 12px;"><img src="https://img.icons8.com/ios-filled/50/${iconColor}/instagram-new.png" alt="Instagram" width="${iconSize}" height="${iconSize}" style="border:0;display:block;" /></a>`);

            const iconsHtml = icons.length > 0 ? `<div style="margin-bottom:16px;text-align:center;">${icons.join("")}</div>` : "";
            const linksHtml = [];
            if (block.websiteUrl) linksHtml.push(`<a href="${block.websiteUrl}" style="color:${block.color};text-decoration:none;">Visit website</a>`);
            if (block.unsubscribeUrl) linksHtml.push(`<a href="${block.unsubscribeUrl}" style="color:${block.color};text-decoration:none;">Unsubscribe</a>`);
            const bottomLinks = linksHtml.length > 0 ? `<div style="margin-top:16px;opacity:0.8;">${linksHtml.join(' &nbsp;|&nbsp; ')}</div>` : "";

            return wrap(
                `<div style="padding:24px 0;text-align:${block.align};font-size:${block.fontSize}px;color:${block.color};font-family:${gs.fontFamily};line-height:1.6;">${iconsHtml}<div>${fill(company).replace(/\n/g, "<br/>")}</div>${bottomLinks}</div>`,
                block.bgColor
            );
        }
        default: return "";
    }
}

function renderEmailHTML(blocks, gs, isPreview = false) {
    const rows = blocks.map(b => renderBlockHTML(b, gs, isPreview)).join("\n");
    return `<!DOCTYPE html>
<html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;background:${gs.outerBgColor};font-family:${gs.fontFamily};">
<table width="100%" cellpadding="0" cellspacing="0" style="background:${gs.outerBgColor};">
<tr><td align="center" style="padding:24px 12px;">
<table width="${gs.maxWidth}" cellpadding="0" cellspacing="0" style="background:${gs.contentBgColor};border-radius:4px;overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,0.08);">
${rows}
</table>
</td></tr></table>
</body></html>`;
}

// ─────────────────────────────────────────────────────────────────────────────
// Sub-components
// ─────────────────────────────────────────────────────────────────────────────

function ColorPicker({ label, value, onChange }) {
    return (
        <div className="flex items-center justify-between mb-3">
            <span className="font-mono text-xs text-ink/60 uppercase">{label}</span>
            <div className="flex items-center gap-2">
                <div className="w-7 h-7 border border-ink rounded-sm overflow-hidden cursor-pointer relative">
                    <input type="color" value={value} onChange={e => onChange(e.target.value)}
                        className="absolute inset-0 w-full h-full opacity-0 cursor-pointer" />
                    <div className="w-full h-full" style={{ background: value }} />
                </div>
                <input type="text" value={value} onChange={e => onChange(e.target.value)}
                    className="font-mono text-xs border border-ink px-2 py-1 w-20 bg-paper" />
            </div>
        </div>
    );
}

function SliderProp({ label, value, min, max, unit = "", onChange }) {
    return (
        <div className="mb-3">
            <div className="flex justify-between items-center mb-1">
                <span className="font-mono text-xs text-ink/60 uppercase">{label}</span>
                <span className="font-mono text-xs font-bold">{value}{unit}</span>
            </div>
            <input type="range" min={min} max={max} value={value}
                onChange={e => onChange(Number(e.target.value))}
                className="w-full accent-ink h-1.5" />
        </div>
    );
}

function ImageInput({ label, src, mode, onSrcChange, onModeChange }) {
    const fileRef = useRef();
    const [isUploading, setIsUploading] = useState(false);

    const handleFile = async (e) => {
        const file = e.target.files[0];
        if (!file) return;

        setIsUploading(true);
        const formData = new FormData();
        formData.append("file", file);

        try {
            const token = localStorage.getItem("access_token");
            const res = await fetch(`${API}/templates/upload`, {
                method: "POST",
                headers: {
                    "Authorization": `Bearer ${token}`
                },
                body: formData
            });
            if (!res.ok) throw new Error("Upload failed");
            const data = await res.json();
            onSrcChange(data.url);
        } catch (err) {
            console.error(err);
            alert("Image upload failed. Please try again or use a URL.");
        } finally {
            setIsUploading(false);
        }
    };
    return (
        <div className="mb-4">
            <div className="font-mono text-xs text-ink/60 uppercase mb-2">{label}</div>
            <div className="flex gap-2 mb-2">
                <button onClick={() => onModeChange("url")} className={`flex-1 font-mono text-xs py-1 border border-ink ${mode === "url" ? "bg-ink text-paper" : "bg-paper hover:bg-mute"}`}>URL</button>
                <button onClick={() => onModeChange("upload")} className={`flex-1 font-mono text-xs py-1 border border-ink ${mode === "upload" ? "bg-ink text-paper" : "bg-paper hover:bg-mute"}`}>Upload</button>
            </div>
            {mode === "url" ? (
                <input type="text" value={src} onChange={e => onSrcChange(e.target.value)}
                    placeholder="https://example.com/image.png"
                    className="w-full font-mono text-xs border border-ink px-2 py-1.5 bg-paper" />
            ) : (
                <div>
                    <button 
                        onClick={() => fileRef.current?.click()}
                        disabled={isUploading}
                        className={`w-full font-mono text-xs border border-dashed border-ink py-2 text-ink/60 ${isUploading ? "opacity-50 cursor-not-allowed" : "hover:bg-mute"}`}>
                        {isUploading ? "Uploading to Cloudinary..." : "Click to upload image"}
                    </button>
                    <input ref={fileRef} type="file" accept="image/*" className="hidden" onChange={handleFile} />
                    {src && src.startsWith("http") && <p className="font-mono text-[10px] text-data-green mt-1">✓ Image uploaded to Cloudinary</p>}
                    {src && src.startsWith("data:") && <p className="font-mono text-[10px] text-red-500 mt-1">⚠ Legacy base64 image (re-upload to fix clipping)</p>}
                </div>
            )}
        </div>
    );
}

// ─────────────────────────────────────────────────────────────────────────────
// Properties panel content per block type
// ─────────────────────────────────────────────────────────────────────────────
function BlockProperties({ block, onUpdate, onInsertPlaceholder }) {
    const u = (key, val) => onUpdate(block.id, { ...block, [key]: val });

    const alignBtns = (key = "align") => (
        <div className="flex gap-1 mb-3">
            {["left", "center", "right"].map(a => (
                <button key={a} onClick={() => u(key, a)}
                    className={`flex-1 py-1 border border-ink font-mono text-xs uppercase ${block[key] === a ? "bg-ink text-paper" : "bg-paper hover:bg-mute"}`}>
                    <span className="material-symbols-outlined text-[14px]">format_align_{a}</span>
                </button>
            ))}
        </div>
    );

    const placeholderBar = (targetKey = "text") => (
        <div className="mb-3">
            <div className="font-mono text-xs text-ink/60 uppercase mb-1">Insert Placeholder</div>
            <div className="flex flex-wrap gap-1">
                {PLACEHOLDERS.map(p => (
                    <button key={p.token} onClick={() => onInsertPlaceholder(block.id, targetKey, p.token)}
                        className="px-2 py-0.5 font-mono text-[10px] bg-mute border border-ink hover:bg-ink hover:text-paper truncate max-w-[120px]">
                        {p.label}
                    </button>
                ))}
            </div>
        </div>
    );

    switch (block.type) {
        case "logo": return (
            <div>
                <ImageInput label="Logo Image" src={block.src} mode={block.imageMode} onSrcChange={v => u("src", v)} onModeChange={v => u("imageMode", v)} />
                <SliderProp label="Width" value={block.width} min={50} max={300} unit="px" onChange={v => u("width", v)} />
                <ColorPicker label="Row Background" value={block.bgColor} onChange={v => u("bgColor", v)} />
                {alignBtns()}
                <div className="mb-3">
                    <div className="font-mono text-xs text-ink/60 uppercase mb-1">Alt Text</div>
                    <input type="text" value={block.alt} onChange={e => u("alt", e.target.value)} className="w-full font-mono text-xs border border-ink px-2 py-1.5 bg-paper" />
                </div>
            </div>
        );

        case "banner": return (
            <div>
                <ImageInput label="Banner Image" src={block.src} mode={block.imageMode} onSrcChange={v => u("src", v)} onModeChange={v => u("imageMode", v)} />
                <SliderProp label="Max Height" value={block.maxHeight} min={80} max={500} unit="px" onChange={v => u("maxHeight", v)} />
                <ColorPicker label="Row Background" value={block.bgColor} onChange={v => u("bgColor", v)} />
                <div className="mb-3">
                    <div className="font-mono text-xs text-ink/60 uppercase mb-1">Click Destination URL</div>
                    <input type="text" value={block.link} onChange={e => u("link", e.target.value)} placeholder="https://" className="w-full font-mono text-xs border border-ink px-2 py-1.5 bg-paper" />
                </div>
                <div className="mb-3">
                    <div className="font-mono text-xs text-ink/60 uppercase mb-1">Alt Text</div>
                    <input type="text" value={block.alt} onChange={e => u("alt", e.target.value)} className="w-full font-mono text-xs border border-ink px-2 py-1.5 bg-paper" />
                </div>
            </div>
        );

        case "heading": return (
            <div>
                <div className="mb-3">
                    <div className="font-mono text-xs text-ink/60 uppercase mb-1">Heading Text</div>
                    <textarea value={block.text} onChange={e => u("text", e.target.value)} rows={3} className="w-full font-mono text-xs border border-ink px-2 py-1.5 bg-paper resize-none" />
                </div>
                {placeholderBar("text")}
                <SliderProp label="Font Size" value={block.fontSize} min={14} max={72} unit="px" onChange={v => u("fontSize", v)} />
                <ColorPicker label="Text Color" value={block.color} onChange={v => u("color", v)} />
                <ColorPicker label="Background" value={block.bgColor} onChange={v => u("bgColor", v)} />
                {alignBtns()}
                <div className="flex gap-2 mb-3">
                    <button onClick={() => u("bold", !block.bold)} className={`flex-1 py-1 border border-ink font-bold text-sm ${block.bold ? "bg-ink text-paper" : "bg-paper hover:bg-mute"}`}>B</button>
                    <button onClick={() => u("italic", !block.italic)} className={`flex-1 py-1 border border-ink italic text-sm ${block.italic ? "bg-ink text-paper" : "bg-paper hover:bg-mute"}`}>I</button>
                </div>
            </div>
        );

        case "text":
        case "desc": return (
            <div>
                <div className="mb-3">
                    <div className="font-mono text-xs text-ink/60 uppercase mb-1">Text Content</div>
                    <textarea value={block.text} onChange={e => u("text", e.target.value)} rows={5} className="w-full font-mono text-xs border border-ink px-2 py-1.5 bg-paper resize-none" />
                </div>
                {placeholderBar("text")}
                <SliderProp label="Font Size" value={block.fontSize} min={10} max={30} unit="px" onChange={v => u("fontSize", v)} />
                <SliderProp label="Line Height" value={block.lineHeight} min={1} max={3} unit="x" onChange={v => u("lineHeight", parseFloat(v.toFixed(1)))} />
                <ColorPicker label="Text Color" value={block.color} onChange={v => u("color", v)} />
                <ColorPicker label="Background" value={block.bgColor} onChange={v => u("bgColor", v)} />
                {alignBtns()}
            </div>
        );

        case "ai_body": return (
            <div>
                <div className="mb-4 p-3 bg-primary/10 border border-primary text-primary font-mono text-[10px] leading-tight">
                    This block acts as a placeholder. The full email content generated by the AI (including greeting, body, and sign-off) will be injected here when sending.
                </div>
                <SliderProp label="Font Size" value={block.fontSize} min={10} max={30} unit="px" onChange={v => u("fontSize", v)} />
                <SliderProp label="Line Height" value={block.lineHeight} min={1} max={3} unit="x" onChange={v => u("lineHeight", parseFloat(v.toFixed(1)))} />
                <ColorPicker label="Text Color" value={block.color} onChange={v => u("color", v)} />
                <ColorPicker label="Background" value={block.bgColor} onChange={v => u("bgColor", v)} />
                {alignBtns()}
            </div>
        );

        case "greeting": return (
            <div>
                <div className="mb-3">
                    <div className="font-mono text-xs text-ink/60 uppercase mb-1">Prefix (e.g. &quot;Hi&quot;)</div>
                    <input type="text" value={block.prefix} onChange={e => u("prefix", e.target.value)} className="w-full font-mono text-xs border border-ink px-2 py-1.5 bg-paper" />
                </div>
                <div className="mb-3">
                    <div className="font-mono text-xs text-ink/60 uppercase mb-1">Name Field</div>
                    <select value={block.name} onChange={e => u("name", e.target.value)} className="w-full font-mono text-xs border border-ink px-2 py-1.5 bg-paper">
                        {PLACEHOLDERS.slice(0, 3).map(p => <option key={p.token} value={p.token}>{p.label}</option>)}
                    </select>
                </div>
                <div className="mb-3">
                    <div className="font-mono text-xs text-ink/60 uppercase mb-1">Suffix (e.g. &quot;,&quot;)</div>
                    <input type="text" value={block.suffix} onChange={e => u("suffix", e.target.value)} className="w-full font-mono text-xs border border-ink px-2 py-1.5 bg-paper" />
                </div>
                <SliderProp label="Font Size" value={block.fontSize} min={14} max={36} unit="px" onChange={v => u("fontSize", v)} />
                <ColorPicker label="Text Color" value={block.color} onChange={v => u("color", v)} />
                <ColorPicker label="Background" value={block.bgColor} onChange={v => u("bgColor", v)} />
                <div className="mb-3">
                    <label className="flex items-center gap-2 cursor-pointer">
                        <input type="checkbox" checked={block.bold} onChange={e => u("bold", e.target.checked)} className="accent-ink" />
                        <span className="font-mono text-xs uppercase">Bold</span>
                    </label>
                </div>
            </div>
        );

        case "cta": return (
            <div>
                <div className="mb-3">
                    <div className="font-mono text-xs text-ink/60 uppercase mb-1">Button Label</div>
                    <input type="text" value={block.label} onChange={e => u("label", e.target.value)} className="w-full font-mono text-xs border border-ink px-2 py-1.5 bg-paper" />
                </div>
                <div className="mb-3">
                    <div className="font-mono text-xs text-ink/60 uppercase mb-1">Destination URL</div>
                    <input type="text" value={block.url} onChange={e => u("url", e.target.value)} placeholder="https://" className="w-full font-mono text-xs border border-ink px-2 py-1.5 bg-paper" />
                </div>
                <ColorPicker label="Button Color" value={block.bgColor} onChange={v => u("bgColor", v)} />
                <ColorPicker label="Text Color" value={block.textColor} onChange={v => u("textColor", v)} />
                <SliderProp label="Border Radius" value={block.borderRadius} min={0} max={30} unit="px" onChange={v => u("borderRadius", v)} />
                <SliderProp label="Font Size" value={block.fontSize} min={12} max={24} unit="px" onChange={v => u("fontSize", v)} />
                {alignBtns()}
            </div>
        );

        case "divider": return (
            <div>
                <ColorPicker label="Line Color" value={block.color} onChange={v => u("color", v)} />
                <SliderProp label="Thickness" value={block.thickness} min={1} max={8} unit="px" onChange={v => u("thickness", v)} />
                <SliderProp label="Vertical Spacing" value={block.marginY} min={4} max={48} unit="px" onChange={v => u("marginY", v)} />
                <div className="mb-3">
                    <div className="font-mono text-xs text-ink/60 uppercase mb-2">Line Style</div>
                    <div className="flex gap-2">
                        {["solid", "dashed", "dotted"].map(s => (
                            <button key={s} onClick={() => u("style", s)}
                                className={`flex-1 py-1 border border-ink font-mono text-xs uppercase ${block.style === s ? "bg-ink text-paper" : "bg-paper hover:bg-mute"}`}>{s}</button>
                        ))}
                    </div>
                </div>
            </div>
        );

        case "footer": return (
            <div>
                <div className="mb-3">
                    <div className="font-mono text-xs text-ink/60 uppercase mb-1">Company / Copyright Text</div>
                    <textarea value={block.companyText !== undefined ? block.companyText : (block.text || "")} onChange={e => u("companyText", e.target.value)} rows={2} className="w-full font-mono text-xs border border-ink px-2 py-1.5 bg-paper resize-none" />
                </div>
                {placeholderBar("companyText")}
                
                <div className="mb-3">
                    <div className="font-mono text-xs text-ink/60 uppercase mb-1">Website URL (leave blank to hide)</div>
                    <input type="text" value={block.websiteUrl || ""} onChange={e => u("websiteUrl", e.target.value)} placeholder="https://" className="w-full font-mono text-xs border border-ink px-2 py-1.5 bg-paper" />
                </div>
                
                <div className="mb-3">
                    <div className="font-mono text-xs text-ink/60 uppercase mb-1">Unsubscribe URL</div>
                    <input type="text" value={block.unsubscribeUrl || ""} onChange={e => u("unsubscribeUrl", e.target.value)} placeholder="https://" className="w-full font-mono text-xs border border-ink px-2 py-1.5 bg-paper" />
                </div>

                <div className="mb-4 p-3 bg-mute border border-ink/20">
                    <div className="font-mono text-xs text-ink/80 uppercase font-bold mb-3">Social Links</div>
                    <div className="text-[10px] text-ink/50 mb-3 leading-tight">Leave blank to hide. Using URLs will automatically show the platform&apos;s icon.</div>
                    {["x", "discord", "youtube", "linkedin", "facebook", "instagram"].map(plat => (
                        <div key={plat} className="flex items-center gap-2 mb-2">
                            <span className="font-mono text-[10px] w-16 uppercase">{plat}</span>
                            <input type="text" value={(block.socials && block.socials[plat]) || ""} onChange={e => {
                                const newSocials = { ...(block.socials || {}) };
                                newSocials[plat] = e.target.value;
                                u("socials", newSocials);
                            }} placeholder="https://" className="flex-1 font-mono text-xs border border-ink px-2 py-1 bg-paper" />
                        </div>
                    ))}
                </div>

                <SliderProp label="Font Size" value={block.fontSize} min={10} max={18} unit="px" onChange={v => u("fontSize", v)} />
                <ColorPicker label="Text & Icon Color" value={block.color} onChange={v => u("color", v)} />
                <ColorPicker label="Background" value={block.bgColor} onChange={v => u("bgColor", v)} />
                {alignBtns()}
            </div>
        );

        default: return <div className="font-mono text-xs text-ink/40 p-4">Select a block to edit its properties.</div>;
    }
}

// ─────────────────────────────────────────────────────────────────────────────
// Block renderer for canvas (visual preview of each block)
// ─────────────────────────────────────────────────────────────────────────────
function CanvasBlock({ block, gs }) {
    switch (block.type) {
        case "logo":
            return (
                <div style={{ background: block.bgColor, padding: "12px 24px", textAlign: block.align }}>
                    {block.src
                        ? <img src={block.src} alt={block.alt} style={{ width: block.width, maxWidth: "100%", display: "inline-block" }} />
                        : <div style={{ width: block.width, height: 50, background: "#e8e8e8", display: "inline-flex", alignItems: "center", justifyContent: "center", color: "#999", fontSize: 12, fontFamily: "monospace" }}>Logo Placeholder</div>
                    }
                </div>
            );
        case "banner":
            return (
                <div style={{ background: block.bgColor }}>
                    {block.src
                        ? <img src={block.src} alt={block.alt} style={{ display: "block", width: "100%", maxHeight: block.maxHeight, objectFit: "cover" }} />
                        : <div style={{ height: block.maxHeight, background: "linear-gradient(135deg,#667eea,#764ba2)", display: "flex", alignItems: "center", justifyContent: "center" }}><span style={{ color: "white", fontSize: 18, fontFamily: "sans-serif", opacity: 0.7 }}>Banner Image</span></div>
                    }
                </div>
            );
        case "heading":
            return (
                <div style={{ background: block.bgColor, padding: "12px 24px" }}>
                    <h2 style={{ margin: 0, fontSize: block.fontSize, color: block.color, textAlign: block.align, fontWeight: block.bold ? 700 : 400, fontStyle: block.italic ? "italic" : "normal", fontFamily: gs.fontFamily }}>
                        {block.text || "Heading"}
                    </h2>
                </div>
            );
        case "text":
        case "desc":
            return (
                <div style={{ background: block.bgColor, padding: block.type === "desc" ? "12px 24px" : "8px 24px" }}>
                    {block.type === "desc"
                        ? <div style={{ fontSize: block.fontSize, color: block.color, textAlign: block.align, lineHeight: block.lineHeight, fontFamily: gs.fontFamily, borderLeft: "4px solid #0a0a0a", paddingLeft: 12 }}>{block.text}</div>
                        : <p style={{ margin: 0, fontSize: block.fontSize, color: block.color, textAlign: block.align, lineHeight: block.lineHeight, fontFamily: gs.fontFamily }}>{block.text}</p>
                    }
                </div>
            );
        case "ai_body":
            return (
                <div style={{ background: block.bgColor, padding: "16px 24px" }}>
                    <div style={{ padding: "24px", border: "2px dashed #999", borderRadius: 4, background: "rgba(0,0,0,0.02)", textAlign: block.align }}>
                        <span className="material-symbols-outlined text-primary mb-2" style={{ fontSize: 28 }}>auto_awesome</span>
                        <div style={{ fontSize: block.fontSize, color: block.color, lineHeight: block.lineHeight, fontFamily: gs.fontFamily }}>
                            <p style={{ margin: 0, fontWeight: "bold", opacity: 0.8 }}>AI Generated Content Placeholder</p>
                            <p style={{ margin: "8px 0 0", fontSize: "0.9em", opacity: 0.6 }}>The personalized email strategy (greeting, body, and sign-off) will seamlessly merge here at send time.</p>
                        </div>
                    </div>
                </div>
            );
        case "greeting":
            return (
                <div style={{ background: block.bgColor, padding: "12px 24px" }}>
                    <p style={{ margin: 0, fontSize: block.fontSize, color: block.color, fontWeight: block.bold ? 700 : 400, fontFamily: gs.fontFamily }}>
                        {block.prefix} <span style={{ background: "#fef08a", padding: "0 4px", borderRadius: 2 }}>{block.name}</span>{block.suffix}
                    </p>
                </div>
            );
        case "cta":
            return (
                <div style={{ background: "#fff", padding: "16px 24px", textAlign: block.align }}>
                    <span style={{ display: "inline-block", padding: "12px 28px", background: block.bgColor, color: block.textColor, fontSize: block.fontSize, fontFamily: gs.fontFamily, fontWeight: 700, borderRadius: block.borderRadius }}>
                        {block.label}
                    </span>
                </div>
            );
        case "divider":
            return (
                <div style={{ padding: `${block.marginY}px 24px` }}>
                    <hr style={{ border: "none", borderTop: `${block.thickness}px ${block.style} ${block.color}`, margin: 0 }} />
                </div>
            );
        case "footer": {
            const company = block.companyText ?? block.text ?? "© 2026 BRIGHT ZENITH PRIVATE LIMITED";
            const socials = block.socials || {};
            const icons = [];
            const iconSize = 24;
            const iconColor = block.color ? block.color.replace('#', '') : "888888";
            
            if (socials.x) icons.push(<img key="x" src={`https://img.icons8.com/ios-filled/50/${iconColor}/twitterx--v2.png`} alt="X" style={{ width: iconSize, height: iconSize, margin: "0 12px" }} />);
            if (socials.discord) icons.push(<img key="discord" src={`https://img.icons8.com/ios-filled/50/${iconColor}/discord-logo.png`} alt="Discord" style={{ width: iconSize, height: iconSize, margin: "0 12px" }} />);
            if (socials.youtube) icons.push(<img key="youtube" src={`https://img.icons8.com/ios-filled/50/${iconColor}/youtube-play.png`} alt="YouTube" style={{ width: iconSize, height: iconSize, margin: "0 12px" }} />);
            if (socials.linkedin) icons.push(<img key="linkedin" src={`https://img.icons8.com/ios-filled/50/${iconColor}/linkedin.png`} alt="LinkedIn" style={{ width: iconSize, height: iconSize, margin: "0 12px" }} />);
            if (socials.facebook) icons.push(<img key="facebook" src={`https://img.icons8.com/ios-filled/50/${iconColor}/facebook-new.png`} alt="Facebook" style={{ width: iconSize, height: iconSize, margin: "0 12px" }} />);
            if (socials.instagram) icons.push(<img key="instagram" src={`https://img.icons8.com/ios-filled/50/${iconColor}/instagram-new.png`} alt="Instagram" style={{ width: iconSize, height: iconSize, margin: "0 12px" }} />);

            const linksHtml = [];
            if (block.websiteUrl) linksHtml.push(<span key="web">Visit website</span>);
            if (block.unsubscribeUrl) linksHtml.push(<span key="unsub">Unsubscribe</span>);

            return (
                <div style={{ background: block.bgColor, padding: "24px 24px", textAlign: block.align, fontSize: block.fontSize, color: block.color, fontFamily: gs.fontFamily, lineHeight: 1.6 }}>
                    {icons.length > 0 && <div style={{ marginBottom: 16, display: "flex", justifyContent: "center" }}>{icons}</div>}
                    <div style={{ whiteSpace: "pre-line" }}>{company}</div>
                    {linksHtml.length > 0 && <div style={{ marginTop: 16, opacity: 0.8 }}>
                        {linksHtml.map((item, i) => <span key={i}>{i > 0 ? "  |  " : ""}{item}</span>)}
                    </div>}
                </div>
            );
        }
        default: return null;
    }
}

// ─────────────────────────────────────────────────────────────────────────────
// Main page
// ─────────────────────────────────────────────────────────────────────────────
const DEFAULT_GLOBAL_STYLES = {
    outerBgColor: "#e8e8e8",
    contentBgColor: "#ffffff",
    fontFamily: "Arial, sans-serif",
    baseFontSize: 15,
    maxWidth: 600,
    spacing: "normal",
};

export default function EmailDesigner() {
    const [blocks, setBlocks] = useState([]);
    const [selectedId, setSelectedId] = useState(null);
    const [gs, setGs] = useState(DEFAULT_GLOBAL_STYLES);
    const [propTab, setPropTab] = useState("block"); // "block" | "global"
    const [showPreview, setShowPreview] = useState(false);
    const [previewMode, setPreviewMode] = useState("desktop"); // "desktop" | "mobile"
    const [showSaveModal, setShowSaveModal] = useState(false);
    const [templateName, setTemplateName] = useState("");
    const [currentTplId, setCurrentTplId] = useState(null);
    const [templates, setTemplates] = useState([]);
    const [toast, setToast] = useState(null);
    const [showLoadDropdown, setShowLoadDropdown] = useState(false);
    const dragSrcIdx = useRef(null);

    const token = typeof window !== "undefined" ? localStorage.getItem("access_token") : null;
    const headers = token ? { Authorization: `Bearer ${token}`, "Content-Type": "application/json" } : { "Content-Type": "application/json" };

    const showToast = (msg, type = "success") => {
        setToast({ msg, type });
        setTimeout(() => setToast(null), 3000);
    };

    const loadTemplateList = useCallback(async () => {
        try {
            const res = await fetch(`${API}/templates/`, { headers });
            const data = await res.json();
            setTemplates(data.templates || []);
        } catch { /* ignore */ }
    }, []);

    useEffect(() => { setTimeout(() => loadTemplateList(), 0); }, [loadTemplateList]);

    // ── Block mutations ────────────────────────────────────────────────────────
    const addBlock = (type) => {
        const b = makeBlock(type);
        setBlocks(prev => [...prev, b]);
        setSelectedId(b.id);
    };

    const updateBlock = (id, updated) => setBlocks(prev => prev.map(b => b.id === id ? updated : b));
    const deleteBlock = (id) => { setBlocks(prev => prev.filter(b => b.id !== id)); setSelectedId(null); };
    const duplicateBlock = (id) => {
        const b = blocks.find(x => x.id === id);
        if (!b) return;
        const copy = { ...b, id: uid() };
        const idx = blocks.findIndex(x => x.id === id);
        setBlocks(prev => [...prev.slice(0, idx + 1), copy, ...prev.slice(idx + 1)]);
        setSelectedId(copy.id);
    };
    const moveBlock = (id, dir) => {
        const idx = blocks.findIndex(b => b.id === id);
        if (dir === -1 && idx === 0) return;
        if (dir === 1 && idx === blocks.length - 1) return;
        const arr = [...blocks];
        [arr[idx], arr[idx + dir]] = [arr[idx + dir], arr[idx]];
        setBlocks(arr);
    };

    const insertPlaceholder = (id, key, token) => {
        const b = blocks.find(x => x.id === id);
        if (!b) return;
        updateBlock(id, { ...b, [key]: (b[key] || "") + token });
    };

    // ── Drag to reorder ────────────────────────────────────────────────────────
    const onDragStart = (e, idx) => { dragSrcIdx.current = idx; e.dataTransfer.effectAllowed = "move"; };
    const onDragOver = (e) => { e.preventDefault(); e.dataTransfer.dropEffect = "move"; };
    const onDrop = (e, idx) => {
        e.preventDefault();
        const src = dragSrcIdx.current;
        if (src === null || src === idx) return;
        const arr = [...blocks];
        const [removed] = arr.splice(src, 1);
        arr.splice(idx, 0, removed);
        setBlocks(arr);
        dragSrcIdx.current = null;
    };

    // ── Save / Load ────────────────────────────────────────────────────────────
    const saveTemplate = async () => {
        if (!templateName.trim()) return;
        const body = { name: templateName.trim(), blocks, global_styles: gs };
        try {
            if (currentTplId) {
                await fetch(`${API}/templates/${currentTplId}`, { method: "PUT", headers, body: JSON.stringify(body) });
                showToast("Template updated ✓");
            } else {
                const res = await fetch(`${API}/templates/`, { method: "POST", headers, body: JSON.stringify(body) });
                const data = await res.json();
                setCurrentTplId(data.template_id);
                showToast("Template saved ✓");
            }
            setShowSaveModal(false);
            loadTemplateList();
        } catch { showToast("Save failed", "error"); }
    };

    const loadTemplate = async (tplId) => {
        try {
            const res = await fetch(`${API}/templates/${tplId}`, { headers });
            const data = await res.json();
            setBlocks(data.blocks || []);
            setGs(data.global_styles || DEFAULT_GLOBAL_STYLES);
            setTemplateName(data.name || "");
            setCurrentTplId(tplId);
            setSelectedId(null);
            setShowLoadDropdown(false);
            showToast(`Loaded: ${data.name}`);
        } catch { showToast("Load failed", "error"); }
    };

    const deleteTemplate = async (tplId, e) => {
        e.stopPropagation();
        if (!confirm("Delete this template?")) return;
        await fetch(`${API}/templates/${tplId}`, { method: "DELETE", headers });
        loadTemplateList();
        if (currentTplId === tplId) { setCurrentTplId(null); setTemplateName(""); setBlocks([]); setGs(DEFAULT_GLOBAL_STYLES); }
        showToast("Template deleted");
    };

    const selectedBlock = blocks.find(b => b.id === selectedId);
    const emailHTML = renderEmailHTML(blocks, gs, false);
    const previewHTML = renderEmailHTML(blocks, gs, true);

    return (
        <DashboardLayout>
            {/* ── Toast ── */}
            {toast && (
                <div className={`fixed bottom-6 right-6 z-[70] px-5 py-3 border border-ink font-mono text-sm shadow-lg transition-all ${toast.type === "error" ? "bg-red-50 text-red-700" : "bg-paper text-ink"}`}>
                    {toast.msg}
                </div>
            )}

            {/* ── Save Modal ── */}
            {showSaveModal && (
                <div className="fixed inset-0 bg-ink/40 z-[60] flex items-center justify-center" onClick={() => setShowSaveModal(false)}>
                    <div className="bg-paper border border-ink p-8 w-full max-w-md shadow-2xl" onClick={e => e.stopPropagation()}>
                        <h3 className="font-display text-2xl font-bold uppercase mb-6">Save Template</h3>
                        <div className="font-mono text-xs text-ink/60 uppercase mb-2">Template Name</div>
                        <input type="text" value={templateName} onChange={e => setTemplateName(e.target.value)}
                            onKeyDown={e => e.key === "Enter" && saveTemplate()}
                            placeholder="e.g. Q2 Outreach Template"
                            className="w-full font-mono text-sm border border-ink px-4 py-3 bg-paper mb-6 focus:outline-none" />
                        <div className="flex gap-3">
                            <button onClick={saveTemplate} className="flex-1 bg-ink text-paper font-mono text-sm py-3 font-bold hover:bg-primary transition-colors">
                                {currentTplId ? "Update Template" : "Save Template"}
                            </button>
                            <button onClick={() => setShowSaveModal(false)} className="px-6 border border-ink font-mono text-sm hover:bg-mute">Cancel</button>
                        </div>
                    </div>
                </div>
            )}

            {/* ── Preview Modal ── */}
            {showPreview && (
                <div className="fixed inset-0 bg-ink/60 z-[60] flex flex-col" onClick={() => setShowPreview(false)}>
                    <div className="bg-paper border-b border-ink px-6 py-3 flex items-center gap-4 shrink-0" onClick={e => e.stopPropagation()}>
                        <h3 className="font-display text-xl font-bold uppercase mr-4">Email Preview</h3>
                        <button onClick={() => setPreviewMode("desktop")} className={`font-mono text-xs px-4 py-2 border border-ink flex items-center gap-2 ${previewMode === "desktop" ? "bg-ink text-paper" : "hover:bg-mute"}`}>
                            <span className="material-symbols-outlined text-[16px]">desktop_windows</span> Desktop
                        </button>
                        <button onClick={() => setPreviewMode("mobile")} className={`font-mono text-xs px-4 py-2 border border-ink flex items-center gap-2 ${previewMode === "mobile" ? "bg-ink text-paper" : "hover:bg-mute"}`}>
                            <span className="material-symbols-outlined text-[16px]">smartphone</span> Mobile
                        </button>
                        <div className="ml-auto flex items-center gap-2 px-4 py-2 bg-mute border border-ink">
                            <span className="material-symbols-outlined text-[16px] text-ink/50">info</span>
                            <span className="font-mono text-xs text-ink/60">Tracking pixel auto-injected on send. Showing sample placeholder values.</span>
                        </div>
                        <button onClick={() => setShowPreview(false)} className="ml-4 font-mono text-xs px-4 py-2 border border-ink hover:bg-mute">✕ Close</button>
                    </div>
                    <div className="flex-1 overflow-auto flex items-start justify-center p-8 bg-ink/10" onClick={e => e.stopPropagation()}>
                        <div style={{ width: previewMode === "mobile" ? 375 : 700 }} className="shadow-2xl transition-all duration-300">
                            <iframe
                                srcDoc={previewHTML}
                                style={{ width: "100%", height: "700px", border: "none", borderRadius: 4, background: "#fff" }}
                                title="Email Preview"
                                sandbox="allow-same-origin"
                            />
                        </div>
                    </div>
                </div>
            )}

            {/* ── Page Header ── */}
            <div className="bg-paper border-b border-ink px-8 py-5 flex flex-col sm:flex-row justify-between sm:items-center gap-3 shrink-0">
                <div>
                    <h2 className="font-display text-3xl font-bold uppercase tracking-tighter leading-none mb-0.5">Email Designer</h2>
                    <p className="font-mono text-xs text-ink/50">
                        {currentTplId ? `Editing: ${templateName}` : "Design a reusable email template"}
                    </p>
                </div>
                <div className="flex gap-2 flex-wrap">
                    {/* Load Template */}
                    <div className="relative">
                        <button onClick={() => setShowLoadDropdown(!showLoadDropdown)}
                            className="h-9 px-4 border border-ink bg-paper hover:bg-mute font-mono text-xs uppercase flex items-center gap-2 transition-colors">
                            <span className="material-symbols-outlined text-[15px]">folder_open</span>
                            Load Template
                            <span className="material-symbols-outlined text-[13px]">expand_more</span>
                        </button>
                        {showLoadDropdown && (
                            <div className="absolute top-full left-0 mt-1 bg-paper border border-ink z-30 shadow-xl min-w-[240px] max-h-64 overflow-y-auto">
                                <button onClick={() => { setBlocks([]); setGs(DEFAULT_GLOBAL_STYLES); setCurrentTplId(null); setTemplateName(""); setShowLoadDropdown(false); }}
                                    className="w-full text-left px-4 py-2.5 font-mono text-xs hover:bg-mute border-b border-ink/30 flex items-center gap-2">
                                    <span className="material-symbols-outlined text-[14px]">add</span> Start Fresh (blank)
                                </button>
                                {templates.length === 0
                                    ? <div className="px-4 py-3 font-mono text-xs text-ink/40">No saved templates yet</div>
                                    : templates.map(t => (
                                        <div key={t._id} className="flex items-center group hover:bg-mute border-b border-ink/10">
                                            <button onClick={() => loadTemplate(t._id)} className="flex-1 text-left px-4 py-2.5 font-mono text-xs">
                                                {t.name}
                                            </button>
                                            <button onClick={(e) => deleteTemplate(t._id, e)} className="px-3 py-2.5 text-ink/30 hover:text-red-500 hidden group-hover:block">
                                                <span className="material-symbols-outlined text-[14px]">delete</span>
                                            </button>
                                        </div>
                                    ))
                                }
                            </div>
                        )}
                    </div>

                    <button onClick={() => setShowPreview(true)}
                        className="h-9 px-4 border border-ink bg-paper hover:bg-mute font-mono text-xs uppercase flex items-center gap-2 transition-colors">
                        <span className="material-symbols-outlined text-[15px]">visibility</span>
                        Preview
                    </button>

                    <button onClick={() => { setShowSaveModal(true); setShowLoadDropdown(false); }}
                        className="h-9 px-5 bg-ink text-paper font-mono text-xs uppercase font-bold hover:bg-primary transition-colors flex items-center gap-2">
                        <span className="material-symbols-outlined text-[15px]">save</span>
                        {currentTplId ? "Update" : "Save Template"}
                    </button>
                </div>
            </div>

            {/* ── 3-Column Canvas Layout ── */}
            <div className="flex flex-1 overflow-hidden min-h-0">

                {/* ── LEFT: Block Palette ── */}
                <div className="w-[180px] shrink-0 border-r border-ink bg-paper overflow-y-auto flex flex-col">
                    <div className="px-4 pt-4 pb-2">
                        <div className="font-mono text-[10px] text-ink/40 uppercase tracking-widest">Add Blocks</div>
                    </div>
                    {BLOCK_PALETTE.map(item => (
                        <button key={item.type} onClick={() => addBlock(item.type)}
                            className="flex items-center gap-3 px-4 py-3 border-b border-ink/20 hover:bg-mute text-left transition-colors group">
                            <span className="material-symbols-outlined text-[18px] text-ink/50 group-hover:text-ink">{item.icon}</span>
                            <span className="font-mono text-xs">{item.label}</span>
                        </button>
                    ))}
                </div>

                {/* ── CENTER: Design Canvas ── */}
                <div className="flex-1 overflow-y-auto bg-ink/5 p-6" onClick={() => setSelectedId(null)}>
                    {blocks.length === 0 && (
                        <div className="flex flex-col items-center justify-center h-full text-center opacity-40 select-none py-20">
                            <span className="material-symbols-outlined text-[64px] mb-4">draw</span>
                            <p className="font-display text-2xl font-bold uppercase">Canvas Empty</p>
                            <p className="font-mono text-sm mt-2">Click blocks on the left to add them</p>
                        </div>
                    )}

                    {/* Email Outer Wrapper Preview */}
                    <div className="mx-auto" style={{ maxWidth: gs.maxWidth, background: gs.outerBgColor, padding: "16px", borderRadius: 4 }}>
                        <div style={{ background: gs.contentBgColor, borderRadius: 4, overflow: "hidden", boxShadow: "0 2px 12px rgba(0,0,0,0.1)" }}>
                            {blocks.map((block, idx) => (
                                <div key={block.id}
                                    draggable
                                    onDragStart={e => onDragStart(e, idx)}
                                    onDragOver={onDragOver}
                                    onDrop={e => onDrop(e, idx)}
                                    onClick={e => { e.stopPropagation(); setSelectedId(block.id); setPropTab("block"); }}
                                    className={`relative group cursor-pointer transition-all ${selectedId === block.id ? "ring-2 ring-primary ring-offset-0 z-10" : "hover:ring-1 hover:ring-ink/40"}`}
                                >
                                    {/* Block Controls */}
                                    <div className={`absolute top-1 right-1 flex items-center gap-0.5 z-20 transition-opacity ${selectedId === block.id ? "opacity-100" : "opacity-0 group-hover:opacity-100"}`}>
                                        <span className="cursor-grab p-1 bg-paper border border-ink text-ink/50 hover:text-ink material-symbols-outlined text-[14px]">drag_indicator</span>
                                        <button onClick={e => { e.stopPropagation(); moveBlock(block.id, -1); }} className="p-1 bg-paper border border-ink text-ink/50 hover:text-ink">
                                            <span className="material-symbols-outlined text-[14px]">arrow_upward</span>
                                        </button>
                                        <button onClick={e => { e.stopPropagation(); moveBlock(block.id, 1); }} className="p-1 bg-paper border border-ink text-ink/50 hover:text-ink">
                                            <span className="material-symbols-outlined text-[14px]">arrow_downward</span>
                                        </button>
                                        <button onClick={e => { e.stopPropagation(); duplicateBlock(block.id); }} className="p-1 bg-paper border border-ink text-ink/50 hover:text-ink">
                                            <span className="material-symbols-outlined text-[14px]">content_copy</span>
                                        </button>
                                        <button onClick={e => { e.stopPropagation(); deleteBlock(block.id); }} className="p-1 bg-paper border border-ink text-ink/50 hover:text-red-500">
                                            <span className="material-symbols-outlined text-[14px]">delete</span>
                                        </button>
                                    </div>

                                    {/* Block type badge */}
                                    <div className={`absolute top-1 left-1 z-20 px-1.5 py-0.5 font-mono text-[9px] uppercase border transition-opacity ${selectedId === block.id ? "bg-primary text-white border-primary opacity-100" : "opacity-0 group-hover:opacity-100 bg-paper border-ink text-ink/60"}`}>
                                        {block.type}
                                    </div>

                                    <CanvasBlock block={block} gs={gs} />
                                </div>
                            ))}
                        </div>
                    </div>
                </div>

                {/* ── RIGHT: Properties Panel ── */}
                <div className="w-[260px] shrink-0 border-l border-ink bg-paper overflow-y-auto flex flex-col">
                    {/* Tab switcher */}
                    <div className="flex border-b border-ink shrink-0">
                        <button onClick={() => setPropTab("block")}
                            className={`flex-1 py-3 font-mono text-xs uppercase transition-colors ${propTab === "block" ? "bg-ink text-paper font-bold" : "hover:bg-mute"}`}>
                            Block
                        </button>
                        <button onClick={() => setPropTab("global")}
                            className={`flex-1 py-3 font-mono text-xs uppercase transition-colors ${propTab === "global" ? "bg-ink text-paper font-bold" : "hover:bg-mute"}`}>
                            Canvas
                        </button>
                    </div>

                    <div className="p-4 flex-1 overflow-y-auto">
                        {propTab === "global" ? (
                            /* ── Global Styles ── */
                            <div>
                                <div className="font-mono text-xs text-ink/40 uppercase mb-4">Canvas Settings</div>
                                <ColorPicker label="Outer Background" value={gs.outerBgColor} onChange={v => setGs(p => ({ ...p, outerBgColor: v }))} />
                                <ColorPicker label="Content Background" value={gs.contentBgColor} onChange={v => setGs(p => ({ ...p, contentBgColor: v }))} />
                                <div className="mb-3">
                                    <div className="font-mono text-xs text-ink/60 uppercase mb-2">Max Email Width</div>
                                    <div className="flex gap-1">
                                        {[480, 600, 700].map(w => (
                                            <button key={w} onClick={() => setGs(p => ({ ...p, maxWidth: w }))}
                                                className={`flex-1 py-1.5 border border-ink font-mono text-xs ${gs.maxWidth === w ? "bg-ink text-paper" : "bg-paper hover:bg-mute"}`}>{w}</button>
                                        ))}
                                    </div>
                                </div>
                                <div className="mb-3">
                                    <div className="font-mono text-xs text-ink/60 uppercase mb-2">Font Family</div>
                                    <select value={gs.fontFamily} onChange={e => setGs(p => ({ ...p, fontFamily: e.target.value }))}
                                        className="w-full font-mono text-xs border border-ink px-2 py-1.5 bg-paper">
                                        {FONTS.map((f, i) => <option key={f} value={f}>{FONT_LABELS[i]}</option>)}
                                    </select>
                                </div>
                                <SliderProp label="Base Font Size" value={gs.baseFontSize} min={12} max={20} unit="px" onChange={v => setGs(p => ({ ...p, baseFontSize: v }))} />
                                <div className="mb-3">
                                    <div className="font-mono text-xs text-ink/60 uppercase mb-2">Spacing</div>
                                    <div className="flex gap-1">
                                        {["compact", "normal", "relaxed"].map(s => (
                                            <button key={s} onClick={() => setGs(p => ({ ...p, spacing: s }))}
                                                className={`flex-1 py-1.5 border border-ink font-mono text-xs capitalize ${gs.spacing === s ? "bg-ink text-paper" : "bg-paper hover:bg-mute"}`}>{s}</button>
                                        ))}
                                    </div>
                                </div>
                            </div>
                        ) : (
                            /* ── Block Properties ── */
                            selectedBlock
                                ? <BlockProperties block={selectedBlock} onUpdate={updateBlock} onInsertPlaceholder={insertPlaceholder} />
                                : (
                                    <div className="flex flex-col items-center justify-center text-center h-full opacity-40 py-8">
                                        <span className="material-symbols-outlined text-[40px] mb-3">touch_app</span>
                                        <p className="font-mono text-xs">Click a block on the canvas to edit its properties</p>
                                    </div>
                                )
                        )}
                    </div>

                    {/* Export HTML button */}
                    {blocks.length > 0 && (
                        <div className="p-4 border-t border-ink shrink-0">
                            <button
                                onClick={() => { navigator.clipboard.writeText(emailHTML); showToast("HTML copied to clipboard ✓"); }}
                                className="w-full py-2 border border-ink font-mono text-xs uppercase hover:bg-mute flex items-center justify-center gap-2">
                                <span className="material-symbols-outlined text-[14px]">content_copy</span>
                                Copy HTML
                            </button>
                        </div>
                    )}
                </div>
            </div>
        </DashboardLayout>
    );
}

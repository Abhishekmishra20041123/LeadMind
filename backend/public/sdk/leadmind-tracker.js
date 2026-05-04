/**
 * LeadMind Tracker SDK v2.0
 * Full behavioral tracking: page views, scroll depth, time on page,
 * click events, UTM params, device info, page type detection,
 * cart/checkout/purchase events, and auto-identify from forms.
 *
 * Usage — plain HTML / Vite / React CRA:
 *   <script src="https://your-api.com/public/sdk/leadmind-tracker.js"
 *           data-api-key="lm_live_YOUR_KEY"
 *           data-api-host="https://your-api.com"></script>
 *
 * Usage — Next.js App Router (app/layout.tsx):
 *   <Script id="leadmind-tracker"
 *           src=".../leadmind-tracker.js"
 *           strategy="afterInteractive"
 *           data-api-key="lm_live_YOUR_KEY"
 *           data-api-host="https://your-api.com" />
 */
(function () {
  "use strict";

  // ── Config ─────────────────────────────────────────────────────────────────
  var script     = document.currentScript || document.querySelector('script[data-api-key]');
  var API_KEY    = script ? script.getAttribute("data-api-key")  : "";
  var API_HOST   = script ? (script.getAttribute("data-api-host") || "http://localhost:8000") : "http://localhost:8000";
  var INGEST_URL   = API_HOST + "/api/ingest/event";
  var IDENTIFY_URL = API_HOST + "/api/ingest/identify";

  if (!API_KEY) {
    console.warn("[LeadMind] No data-api-key found on script tag. Tracking disabled.");
    return;
  }

  // ── Visitor & Session IDs ──────────────────────────────────────────────────
  function uuid() {
    return "lmv_" + Math.random().toString(36).slice(2) + Date.now().toString(36);
  }
  function getVisitorId() {
    var key = "_lm_vid";
    var id  = localStorage.getItem(key);
    if (!id) { id = uuid(); localStorage.setItem(key, id); }
    return id;
  }
  function getSessionId() {
    var key = "_lm_sid";
    var id  = sessionStorage.getItem(key);
    if (!id) { id = uuid().replace("lmv_", "lms_"); sessionStorage.setItem(key, id); }
    return id;
  }
  var visitorId = getVisitorId();
  var sessionId = getSessionId();

  // ── Device & Browser Detection ─────────────────────────────────────────────
  function getDeviceInfo() {
    var ua  = navigator.userAgent || "";
    var plat = navigator.platform  || "";
    var device = /Mobi|Android|iPhone|iPod/i.test(ua)       ? "Mobile"
               : /iPad|Tablet/i.test(ua)                     ? "Tablet"
               : "Desktop";
    var browser = /Edge\/|Edg\//i.test(ua)  ? "Edge"
                : /OPR\/|Opera/i.test(ua)   ? "Opera"
                : /Firefox/i.test(ua)        ? "Firefox"
                : /Safari/i.test(ua) && !/Chrome/i.test(ua) ? "Safari"
                : /Chrome/i.test(ua)         ? "Chrome"
                : "Other";
    var os = /Win/i.test(plat)      ? "Windows"
           : /Mac/i.test(plat)      ? "macOS"
           : /Linux/i.test(plat)    ? "Linux"
           : /Android/i.test(ua)    ? "Android"
           : /iPhone|iPad/i.test(ua)? "iOS"
           : "Other";
    var conn = (navigator.connection || {}).effectiveType || null;
    return {
      device_type:       device,
      browser:           browser,
      os:                os,
      screen_resolution: screen.width + "x" + screen.height,
      connection_type:   conn
    };
  }

  // ── UTM Parameters ─────────────────────────────────────────────────────────
  function getUTMs() {
    var p = new URLSearchParams(window.location.search);
    var utms = {};
    ["utm_source","utm_medium","utm_campaign","utm_term","utm_content"].forEach(function(k){
      var v = p.get(k);
      if (v) {
        utms[k] = v;
        sessionStorage.setItem("_lm_" + k, v); // persist across pages
      } else {
        var stored = sessionStorage.getItem("_lm_" + k);
        if (stored) utms[k] = stored;
      }
    });
    return utms;
  }

  // ── Page Type Detection ────────────────────────────────────────────────────
  var PAGE_PATTERNS = {
    product:      ["/products/","/product/","/item/","/p/","/shop/"],
    category:     ["/collections/","/category/","/cat/","/c/","/browse/"],
    cart:         ["/cart","/basket"],
    checkout:     ["/checkout","/order"],
    confirmation: ["/thank-you","/order-confirmation","/success","/confirmed"],
    pricing:      ["/pricing","/plans","/subscribe"]
  };
  function detectPageType(url) {
    var path = url.toLowerCase();
    for (var type in PAGE_PATTERNS) {
      var pats = PAGE_PATTERNS[type];
      for (var i = 0; i < pats.length; i++) {
        if (path.indexOf(pats[i]) !== -1) return type;
      }
    }
    return path === "/" || path === "" ? "homepage" : "other";
  }
  function extractProductCategory(url) {
    // Simple heuristic: grab segment after /products/ or /collections/
    var m = url.match(/(?:products|collections|category|cat)\/([^/?#]+)/i);
    return m ? decodeURIComponent(m[1]).replace(/-/g," ") : null;
  }

  // ── Hour-of-day (for active_time_window) ──────────────────────────────────
  function getHourWindow() {
    var h = new Date().getHours();
    return h + ":00-" + (h + 1) + ":00";
  }

  // ── Build full metadata object ─────────────────────────────────────────────
  var pageType     = detectPageType(window.location.href);
  var pageCategory = extractProductCategory(window.location.href);
  var deviceInfo   = getDeviceInfo();
  var utmParams    = getUTMs();
  var sessionStart = Date.now();
  var landing_page = window.location.href;
  var referrer     = document.referrer;

  function buildBase(extra) {
    return Object.assign({
      api_key:    API_KEY,
      visitor_id: visitorId,
      session_id: sessionId,
      event_type: "page_view",
      url:        window.location.href,
      title:      document.title,
      referrer:   referrer,
      landing_page: landing_page,
      // Device
      device_type:       deviceInfo.device_type,
      browser:           deviceInfo.browser,
      os:                deviceInfo.os,
      screen_resolution: deviceInfo.screen_resolution,
      connection_type:   deviceInfo.connection_type,
      // Page type
      page_type:         pageType,
      is_product_page:   pageType === "product",
      is_category_page:  pageType === "category",
      is_pricing_page:   pageType === "pricing",
      is_cart_page:      pageType === "cart",
      is_checkout_page:  pageType === "checkout",
      is_confirmation_page: pageType === "confirmation",
      product_category:  pageCategory,
      // Timing
      active_time_window: getHourWindow(),
      metadata: {}
    }, utmParams, extra || {});
  }

  // ── Send helper ────────────────────────────────────────────────────────────
  function send(url, payload) {
    try {
      if (navigator.sendBeacon) {
        navigator.sendBeacon(url, JSON.stringify(payload));
      } else {
        var xhr = new XMLHttpRequest();
        xhr.open("POST", url, true);
        xhr.setRequestHeader("Content-Type", "application/json");
        xhr.send(JSON.stringify(payload));
      }
    } catch (e) {}
  }
  function track(eventType, extra) {
    var p = buildBase(extra);
    p.event_type = eventType;
    send(INGEST_URL, p);
  }

  // ── 1. Page View (Track on load + SPA navigation) ──────────────────────────
  var lastTrackedUrl = "";
  function trackPageView() {
    var currentUrl = window.location.href;
    if (currentUrl === lastTrackedUrl) return;
    lastTrackedUrl = currentUrl;
    track("page_view");
  }

  // Initial track
  trackPageView();

  // ── 2. Time on page + Heartbeat (Robust Tracking) ─────────────────────────
  var sessionStart = Date.now();
  var lastHeartbeat = Date.now();

  function sendTimeSpent(isExit) {
    var now = Date.now();
    var duration = Math.round((now - lastHeartbeat) / 1000);
    if (duration < 1 && !isExit) return;

    track("time_spent", {
      exit_page_type: pageType,
      metadata: {
        duration_s:        duration,
        session_duration_s: Math.round((now - sessionStart) / 1000),
        is_exit:           !!isExit
      }
    });
    lastHeartbeat = now;
  }

  // Heartbeat every 30 seconds
  setInterval(function() { sendTimeSpent(false); }, 30000);

  // Track on visibility change (more reliable than beforeunload)
  document.addEventListener("visibilitychange", function() {
    if (document.visibilityState === "hidden") {
      sendTimeSpent(false);
    }
  });

  // Fallback for older browsers
  window.addEventListener("beforeunload", function () {
    sendTimeSpent(true);
  });

  // ── 3. Scroll Depth (Improved logic) ──────────────────────────────────────
  var maxScroll = 0;
  var scrollTimer;
  var SCROLL_MILESTONES = [25, 50, 75, 90, 100];
  var firedMilestones   = {};

  function checkScroll() {
    var h = document.documentElement, 
        b = document.body,
        st = 'scrollTop',
        sh = 'scrollHeight';
    var percent = ((h[st]||b[st]) / ((h[sh]||b[sh]) - h.clientHeight)) * 100;
    var depth = Math.round(percent);
    
    if (depth > maxScroll) maxScroll = depth;
    
    SCROLL_MILESTONES.forEach(function (m) {
      if (depth >= m && !firedMilestones[m]) {
        firedMilestones[m] = true;
        track("scroll", { metadata: { scroll_depth: m, max_scroll: maxScroll } });
      }
    });
  }

  window.addEventListener("scroll", function () {
    clearTimeout(scrollTimer);
    scrollTimer = setTimeout(checkScroll, 500);
  });
  // Also check on load for short pages
  setTimeout(checkScroll, 1000);

  // ── 4. Click Tracking ──────────────────────────────────────────────────────
  var clickCount = 0;
  document.addEventListener("click", function (e) {
    clickCount++;
    var el = e.target.closest("a, button, [data-lm-track]");
    if (!el) return;
    var text = (el.innerText || el.value || "").slice(0, 80).trim();
    track("click", {
      metadata: {
        element:     el.tagName.toLowerCase(),
        text:        text,
        href:        el.href  || null,
        id:          el.id    || null,
        data_label:  el.getAttribute("data-lm-track") || null,
        click_count: clickCount
      }
    });
  });

  // ── 5. SPA Route Change Detection (History API) ───────────────────────────
  function detectSpecialPage(url) {
    var t = detectPageType(url);
    if (t === "cart")         track("cart_view",         { url: url, metadata: { cart_added: true } });
    if (t === "checkout")     track("checkout_started",  { url: url, metadata: { checkout_started: true } });
    if (t === "confirmation") track("purchase_complete", { url: url, metadata: { purchase_made: true } });
  }

  var _pushState    = history.pushState;
  var _replaceState = history.replaceState;
  
  function onRouteChange(url) {
    setTimeout(function () { 
      trackPageView(); // Now tracks page view on route change
      detectSpecialPage(url); 
    }, 200);
  }

  history.pushState = function () {
    _pushState.apply(history, arguments);
    onRouteChange(window.location.href);
  };
  history.replaceState = function () {
    _replaceState.apply(history, arguments);
    onRouteChange(window.location.href);
  };
  window.addEventListener("popstate", function () {
    onRouteChange(window.location.href);
  });
  
  detectSpecialPage(window.location.href);

  // ── 6. Form Auto-Identify ──────────────────────────────────────────────────
  document.addEventListener("submit", function (e) {
    var form  = e.target;
    var email = (form.querySelector("input[type=email]") || form.querySelector("input[name=email]"));
    if (!email || !email.value) return;
    var fname = form.querySelector("input[name=fname],input[name=first_name],input[name=firstName]");
    var lname = form.querySelector("input[name=lname],input[name=last_name],input[name=lastName]");
    var name  = form.querySelector("input[name=name]");
    var uname = form.querySelector("input[name=username],input[name=userName]");
    var nameVal = (fname ? fname.value + " " : "") + (lname ? lname.value : "") || (name ? name.value : "");
    var company = form.querySelector("input[name=company],input[name=organization]");
    send(IDENTIFY_URL, {
      api_key:    API_KEY,
      visitor_id: visitorId,
      session_id: sessionId,
      email:      email.value.trim(),
      name:       nameVal.trim() || undefined,
      username:   uname ? uname.value.trim() : undefined,
      first_name: fname ? fname.value.trim() : undefined,
      last_name:  lname ? lname.value.trim() : undefined,
      company:    company ? company.value.trim() : undefined,
    });
  });

  // ── 7. Public API ──────────────────────────────────────────────────────────
  window.LeadMind = {
    identify: function (traits) {
      if (!traits || !traits.email) return;
      send(IDENTIFY_URL, Object.assign({
        api_key:    API_KEY,
        visitor_id: visitorId,
        session_id: sessionId,
      }, traits));
    },
    track: function (eventType, metadata) {
      track(eventType, { metadata: metadata || {} });
    },
    getVisitorId: function () { return visitorId; },
    getSessionId: function () { return sessionId; }
  };

})();

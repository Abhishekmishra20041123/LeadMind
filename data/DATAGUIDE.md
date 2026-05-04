# 📖 Sales Multi-Agent AI: Data Guide

This guide explains how to prepare your data so the agents can use "Behavior-First" reasoning to research and personal outreach.

## 🚀 The "Behavior-First" Approach
Unlike traditional systems that rely on 6 months of historical data, this system is optimized for **immediate action**. It uses the customer's *current* session to frame every interaction.

---

## 📄 Main Leads File (`Leads_Data.csv`)
This is where the agents look first. Even for a new customer, you should provide these details:

| Column | Purpose | Why it matters |
| :--- | :--- | :--- |
| `lead_id` | Unique Identifier | Links all agent actions to one person. |
| `page_link` | **CRITICAL** | The exact product page they are on. The Email Agent uses this to mention specific jewelry (e.g., "Diamond Solitaire"). |
| `visits` | Depth check | 1 visit = New user. 5+ visits = Serious buyer. |
| `time_on_site` | Intensity check | High time on a specific luxury page triggers higher urgency. |
| `engage_date` | **Timing Anchor** | The timestamp of their last visit. We use this to follow up at the same time they were browsing. |

---

## 📄 Email Logs File (`Email_Logs.csv`)
*Optional for new customers, required for long-term optimization.*

| Column | Purpose | Why it matters |
| :--- | :--- | :--- |
| `opened` / `replied` | Engagement | If they replied to a previous email at 6 PM, we learn that's their "Free Time." |
| `sentiment` | Mood tracking | Helps the Email Agent choose a tone (Formal vs. Friendly). |

---

## 🛠️ How to handle a Brand New Customer?
1. **Add them to your CSV**: Add a new row for the user.
2. **Fill the Basics**: Provide their `lead_id`, `name`, and most importantly, the `page_link` they just visited.
3. **Leave History Blank**: You don't need `Email_Logs` for new people. The agents will automatically fall back to **Global Best Practices** and use the `page_link` info to write a perfect "Cold Intro."

---

## ✅ Best Practices
- **Real Links**: Always use real website URLs in `page_link`. The AI analyzes the URL structure to understand the product category.
- **Timestamp Accuracy**: Ensure `engage_date` is accurate. If a user visits at lunch, we want the agent to know that lunch is a good time to reach them.

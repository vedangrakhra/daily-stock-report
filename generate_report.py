import os
import json
import requests
from datetime import datetime

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_KEY"]
ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]
NTFY_TOPIC = "vedang-stocks-2026"


# ── Seen history (Supabase) ───────────────────────────────────────────────

def get_seen_companies():
    """Return a set of all company names already covered."""
    resp = requests.get(
        SUPABASE_URL + "/rest/v1/seen_companies?select=company",
        headers={"apikey": SUPABASE_KEY, "Authorization": "Bearer " + SUPABASE_KEY},
        timeout=15
    )
    resp.raise_for_status()
    return set(row["company"] for row in resp.json())


def save_seen_companies(companies):
    """Record today's companies as seen."""
    today = datetime.utcnow().strftime("%Y-%m-%d")
    rows = [{"company": c, "first_seen": today} for c in companies]
    resp = requests.post(
        SUPABASE_URL + "/rest/v1/seen_companies",
        headers={
            "apikey": SUPABASE_KEY,
            "Authorization": "Bearer " + SUPABASE_KEY,
            "Content-Type": "application/json",
            "Prefer": "return=minimal"
        },
        json=rows,
        timeout=15
    )
    resp.raise_for_status()


# ── Company selection via Claude ──────────────────────────────────────────

SELECTION_PROMPT = """You are building a daily stock research schedule for a corporate development professional who wants to systematically learn about public companies across global markets.

Your job: pick exactly 6 companies for today's report — 2 from North America, 2 from Asia, 2 from Emerging Markets.

Rules:
- Do NOT pick any company from the SEEN LIST below
- Pick from well-known public companies in major indices: S&P 500, TSX 60 for North America; Nikkei 225, Hang Seng, Nifty 50, ASX 200, KOSPI for Asia; MSCI EM constituents for Emerging Markets
- Choose whatever sectors feel most interesting or relevant today — no strict sector requirements
- Aim for variety: don't pick two companies from the exact same sub-industry
- Prefer companies with genuine learning value — clear business models, interesting competitive dynamics, relevant to understanding global markets
- Include the stock ticker in brackets after the company name

SEEN LIST (do not repeat these):
{seen_list}

Today's date: {date_str}
Companies seen so far: {seen_count}

Respond with ONLY a JSON object in exactly this format, no other text:
{{
  "north_america": {{
    "companies": ["Company Name (TICKER)", "Company Name (TICKER)"],
    "sector": "sector name",
    "rationale": "one sentence on why these two today"
  }},
  "asia": {{
    "companies": ["Company Name (TICKER)", "Company Name (TICKER)"],
    "sector": "sector name",
    "rationale": "one sentence on why these two today"
  }},
  "emerging_markets": {{
    "companies": ["Company Name (TICKER)", "Company Name (TICKER)"],
    "sector": "sector name",
    "rationale": "one sentence on why these two today"
  }}
}}"""


def pick_companies(seen_companies, date_str):
    """Ask Claude to pick today's 6 companies, avoiding seen ones."""
    seen_count = len(seen_companies)

    if seen_count == 0:
        seen_list = "None yet — this is the first report."
    elif seen_count <= 60:
        seen_list = ", ".join(sorted(seen_companies))
    else:
        # Once the list gets long, pass the most recent 60 to save tokens
        recent = sorted(seen_companies)[-60:]
        seen_list = f"[{seen_count} companies total — recent 60]: " + ", ".join(recent)

    prompt = SELECTION_PROMPT.format(
        seen_list=seen_list,
        date_str=date_str,
        seen_count=seen_count
    )

    resp = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "x-api-key": ANTHROPIC_API_KEY,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        },
        json={
            "model": "claude-sonnet-4-6",
            "max_tokens": 600,
            "messages": [{"role": "user", "content": prompt}]
        },
        timeout=60
    )
    resp.raise_for_status()

    raw = resp.json()["content"][0]["text"].strip()
    raw = raw.replace("```json", "").replace("```", "").strip()
    selection = json.loads(raw)

    market_map = {
        "north_america": "North America",
        "asia": "Asia",
        "emerging_markets": "Emerging Markets"
    }
    schedule = []
    for key, market_name in market_map.items():
        block = selection[key]
        schedule.append({
            "market": market_name,
            "sector": block["sector"],
            "companies": block["companies"],
            "rationale": block.get("rationale", "")
        })

    return schedule


# ── Report prompts ────────────────────────────────────────────────────────

def build_company_prompt(company, market, sector, date_str):
    prompt = f"""You are a senior equity research analyst writing a daily morning briefing. The reader is a corporate development professional learning global public markets — they want to quickly understand a company and decide if it's worth exploring further.

Today's date: {date_str}
Company: {company} | {market} | {sector}

Write a concise but sharp briefing using EXACTLY this HTML structure. Replace every [PLACEHOLDER]. Be specific — name real products, real competitors, real numbers. No generic filler.

---
<div style="font-family:'Helvetica Neue',Helvetica,Arial,sans-serif;padding:22px;background:#ffffff;">

  <div style="margin-bottom:4px;">
    <span style="font-size:10px;letter-spacing:2px;text-transform:uppercase;color:#4a90d9;font-weight:600;">{market} · {sector}</span>
  </div>
  <h2 style="font-size:20px;font-weight:700;color:#0f1e3c;margin:0 0 16px 0;">[COMPANY NAME]</h2>

  <div style="margin-bottom:18px;">
    <div style="font-size:10px;letter-spacing:2px;text-transform:uppercase;color:#1e3a5f;font-weight:700;border-bottom:2px solid #e2e8f0;padding-bottom:6px;margin-bottom:10px;">What They Do & How They Make Money</div>
    <p style="font-size:14px;color:#374151;line-height:1.75;margin:0;">[2-3 sentences. What is the core product or service, who uses it, and what are the main revenue streams. Name specific products and approximate revenue mix if known.]</p>
  </div>

  <div style="margin-bottom:18px;">
    <div style="font-size:10px;letter-spacing:2px;text-transform:uppercase;color:#1e3a5f;font-weight:700;border-bottom:2px solid #e2e8f0;padding-bottom:6px;margin-bottom:10px;">Competitive Position & Moat</div>
    <p style="font-size:14px;color:#374151;line-height:1.75;margin:0;">[2-3 sentences. What specifically protects this business — name the actual mechanism. Name their 2 main competitors and how this company differs from each.]</p>
  </div>

  <div style="margin-bottom:18px;">
    <div style="font-size:10px;letter-spacing:2px;text-transform:uppercase;color:#1e3a5f;font-weight:700;border-bottom:2px solid #e2e8f0;padding-bottom:6px;margin-bottom:10px;">Valuation Sense</div>
    <p style="font-size:14px;color:#374151;line-height:1.75;margin:0;">[2 sentences. Approximate P/E or EV/EBITDA versus sector peers — cheap, fair, or expensive and why. If high-growth, note what growth rate the market is pricing in.]</p>
  </div>

  <div style="margin-bottom:6px;">
    <div style="font-size:10px;letter-spacing:2px;text-transform:uppercase;color:#1e3a5f;font-weight:700;border-bottom:2px solid #e2e8f0;padding-bottom:6px;margin-bottom:10px;">1–2 Catalysts to Watch</div>
    <p style="font-size:14px;color:#374151;line-height:1.75;margin:0;">[1-2 specific named catalysts in the next 12 months. Not vague "continued growth".]</p>
  </div>

</div>
---

Output ONLY the HTML. No explanation, no markdown, no code fences."""
    return prompt


def build_summary_prompt(schedule, date_str):
    lines = []
    for s in schedule:
        rationale = f" ({s['rationale']})" if s.get("rationale") else ""
        lines.append(f"- {s['companies'][0]} and {s['companies'][1]} | {s['market']} / {s['sector']}{rationale}")

    prompt = f"""You are writing the opening "Daily Market Theme" for a stock research newsletter dated {date_str}.

Today's 6 companies:
{chr(10).join(lines)}

Write 4-5 sentences that:
1. Name the dominant macro theme connecting these companies today
2. Identify one specific tension the market is navigating across these names
3. End with one concrete thing worth watching this week

Be specific. Write like a strategist, not a journalist.

Format as a single HTML paragraph: font-size 14px, color #374151, line-height 1.8, font Helvetica Neue. No outer wrapper tags."""
    return prompt


# ── API call ──────────────────────────────────────────────────────────────

def call_api(prompt, max_tokens=3500):
    resp = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "x-api-key": ANTHROPIC_API_KEY,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        },
        json={
            "model": "claude-sonnet-4-6",
            "max_tokens": max_tokens,
            "messages": [{"role": "user", "content": prompt}]
        },
        timeout=120
    )
    if resp.status_code != 200:
        print("API Error " + str(resp.status_code) + ": " + resp.text)
    resp.raise_for_status()
    return resp.json()["content"][0]["text"]


# ── Supabase save ─────────────────────────────────────────────────────────

def save_to_supabase(date_label, schedule, company_html, summary_html):
    full_html = "<div style='font-family:Helvetica Neue,Helvetica,Arial,sans-serif;max-width:680px;margin:0 auto;'>"
    full_html += "<div style='background:#0f1e3c;padding:24px;border-radius:8px;margin-bottom:20px;'>"
    full_html += "<h1 style='color:#fff;font-size:20px;margin:0;'>Daily Stock Research</h1>"
    full_html += "<p style='color:#7fa8d4;margin:6px 0 0;font-size:13px;'>" + date_label + "</p>"
    full_html += "</div>"
    for key, html in company_html.items():
        full_html += "<div style='border:1px solid #e2e8f0;border-radius:8px;margin-bottom:16px;overflow:hidden;'>" + html + "</div>"
    full_html += "<div style='background:#f8fafc;border:1px solid #e2e8f0;border-radius:8px;padding:20px;margin-top:8px;'>"
    full_html += "<p style='font-size:10px;letter-spacing:2px;text-transform:uppercase;color:#4a90d9;font-weight:700;margin:0 0 10px 0;'>Daily Market Theme</p>"
    full_html += summary_html
    full_html += "</div></div>"

    resp = requests.post(
        SUPABASE_URL + "/rest/v1/reports",
        headers={
            "apikey": SUPABASE_KEY,
            "Authorization": "Bearer " + SUPABASE_KEY,
            "Content-Type": "application/json",
            "Prefer": "return=representation"
        },
        json={
            "date_label": date_label,
            "html": full_html,
            "schedule": schedule,
            "company_html": company_html,
            "comments": []
        },
        timeout=30
    )
    if resp.status_code not in [200, 201]:
        print("Supabase Error " + str(resp.status_code) + ": " + resp.text)
    resp.raise_for_status()
    return resp.json()[0]["id"]


# ── Notification ──────────────────────────────────────────────────────────

def send_ntfy(date_label, schedule):
    companies = ", ".join(c for s in schedule for c in s["companies"])
    requests.post(
        "https://ntfy.sh/" + NTFY_TOPIC,
        headers={
            "Title": "Stock Report Ready - " + date_label,
            "Priority": "default",
            "Tags": "chart_increasing"
        },
        data="Today's 6 companies: " + companies + ". Open your report app to read.",
        timeout=15
    )


# ── Main ──────────────────────────────────────────────────────────────────

def main():
    date_str = datetime.utcnow().strftime("%A, %B %-d, %Y")
    print("Generating report for " + date_str + "...")

    # Step 1 — get seen history
    print("  Loading seen history...")
    seen = get_seen_companies()
    print(f"  {len(seen)} companies seen so far.")

    # Step 2 — ask Claude to pick today's 6
    print("  Picking today's companies...")
    schedule = pick_companies(seen, date_str)
    for s in schedule:
        print(f"  {s['market']}: {s['companies'][0]} & {s['companies'][1]} ({s['sector']})")
        if s.get("rationale"):
            print(f"    → {s['rationale']}")

    # Step 3 — save to seen history immediately (before generating,
    # so a crash mid-run doesn't cause the same companies to re-appear tomorrow)
    all_companies = [c for s in schedule for c in s["companies"]]
    save_seen_companies(all_companies)
    print("  Saved to seen history.")

    # Step 4 — generate individual company reports
    company_html = {}
    for seg in schedule:
        for company in seg["companies"]:
            print(f"  Generating report: {company}")
            prompt = build_company_prompt(company, seg["market"], seg["sector"], date_str)
            html = call_api(prompt, max_tokens=3500)
            company_html[company] = html

    # Step 5 — market theme
    print("  Generating market theme...")
    summary_html = call_api(build_summary_prompt(schedule, date_str), max_tokens=600)

    # Step 6 — save full report to Supabase
    report_id = save_to_supabase(date_str, schedule, company_html, summary_html)
    print("Saved to Supabase, id: " + str(report_id))

    # Step 7 — push notification
    send_ntfy(date_str, schedule)
    print("Notification sent. Done.")


if __name__ == "__main__":
    main()

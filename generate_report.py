import os
import requests
from datetime import datetime

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_KEY"]
ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]
NTFY_TOPIC = "vedang-stocks-2026"

SECTORS = {
    "North America": {
        "Technology": [["Nvidia (NVDA)","Snowflake (SNOW)"],["Salesforce (CRM)","Cloudflare (NET)"],["Apple (AAPL)","MongoDB (MDB)"]],
        "Financials": [["Visa (V)","Moody's (MCO)"],["KKR (KKR)","Intercontinental Exchange (ICE)"],["Brookfield AM (BAM)","TD Bank (TD.TO)"]],
        "Industrials": [["Canadian National Railway (CNR.TO)","Waste Connections (WCN)"],["Caterpillar (CAT)","Aecom (ACM)"],["Constellation Software (CSU.TO)","WSP Global (WSP.TO)"]],
        "Consumer": [["Costco (COST)","Restaurant Brands (QSR)"],["Amazon (AMZN)","Lululemon (LULU)"],["Couche-Tard (ATD.TO)","Dollarama (DOL.TO)"]],
        "Healthcare": [["UnitedHealth (UNH)","Intuitive Surgical (ISRG)"],["Danaher (DHR)","Abbott Labs (ABT)"]],
        "Energy & Materials": [["Canadian Natural Resources (CNQ.TO)","Agnico Eagle (AEM.TO)"],["Teck Resources (TECK.TO)","Pembina Pipeline (PPL.TO)"]],
    },
    "Asia": {
        "Technology": [["TSMC (TSM)","Samsung (005930.KS)"],["Tencent (0700.HK)","Infosys (INFY)"],["Keyence (6861.T)","HCL Tech (HCLTECH.NS)"]],
        "Financials": [["HDFC Bank (HDB)","DBS Group (D05.SI)"],["Bajaj Finance (BAJFINANCE.NS)","ICICI Bank (IBN)"]],
        "Industrials": [["Toyota (TM)","Siemens India (SIEMENS.NS)"],["Komatsu (6301.T)","Larsen & Toubro (LT.NS)"]],
        "Consumer": [["Meituan (3690.HK)","Zomato (ZOMATO.NS)"],["Fast Retailing (9983.T)","Titan Company (TITAN.NS)"]],
        "Conglomerates": [["Reliance Industries (RELIANCE.NS)","SoftBank (9984.T)"],["Sony Group (SONY)","Tata Consultancy (TCS.NS)"]],
    },
    "Emerging Markets": {
        "Technology": [["MercadoLibre (MELI)","Sea Limited (SE)"],["Totvs (TOTS3.SA)","Grab Holdings (GRAB)"]],
        "Financials": [["XP Inc (XP)","Bank Central Asia (BBCA.JK)"],["Nu Holdings (NU)","Itau Unibanco (ITUB)"]],
        "Industrials": [["Embraer (ERJ)","WEG S.A. (WEGE3.SA)"],["Localiza (RENT3.SA)","Rumo Logistica (RAIL3.SA)"]],
        "Resources": [["Vale S.A. (VALE)","Petrobras (PBR)"],["Gerdau (GGB)","Suzano (SUZ)"]],
        "Consumer": [["Grupo Bimbo (BIMBOA.MX)","Magazine Luiza (MGLU3.SA)"],["Nu Holdings (NU)","Natura (NTCO)"]],
    }
}

MARKETS = ["North America", "Asia", "Emerging Markets"]

def get_schedule():
    idx = int(datetime.utcnow().timestamp() // 86400)
    schedule = []
    for i, market in enumerate(MARKETS):
        sectors = list(SECTORS[market].keys())
        sector = sectors[(idx + i * 3) % len(sectors)]
        pairs = SECTORS[market][sector]
        pair = pairs[idx % len(pairs)]
        schedule.append({"market": market, "sector": sector, "companies": pair})
    return schedule

def build_prompt(schedule, date_str):
    company_list = "\n".join(
        f"{s['market']} / {s['sector']}: {s['companies'][0]} and {s['companies'][1]}"
        for s in schedule
    )
    return f"""You are a senior equity research analyst writing a structured daily stock briefing for a corporate development professional learning about global public markets.

Today's date: {date_str}

Write a deep-dive research briefing for EXACTLY these 6 companies grouped by market:
{company_list}

For EACH company use this exact structure:

[Company Name] ([Ticker]) - [Market] | [Sector]
What They Do: 2-3 sentences plain English.
How They Make Money: Revenue model, key segments, unit economics.
Customer Type: B2B/B2C/B2G/mixed, retention dynamics.
Industry Overview: Market size, growth rate, tailwinds and headwinds.
Competitive Advantages: Specific moats - network effects, switching costs, scale, IP, brand, regulatory.
Catalysts (Next 12-24 Months): 2-3 specific near/medium-term catalysts.
Key Risks: 2-3 genuine company-specific risks.
Valuation Snapshot: Approximate EV/EBITDA or P/E vs sector median. One sentence on cheap/fair/expensive and why.

After all 6 companies add a Daily Market Theme: 4-5 sentences connecting the macro/sector thread across today's picks.

Format as clean professional HTML with inline styles. Background #ffffff. Header bar #0f1e3c white text. Each company in a card: white bg, border 1px solid #e2e8f0, border-radius 8px, padding 24px, margin-bottom 20px. Section labels bold #1e3a5f. Body text #374151 14px line-height 1.7. Font Helvetica Neue. Market group headers with colored pill: NA=#1d4ed8, Asia=#0891b2, EM=#059669. Max-width 680px centered. Footer with date."""

def def generate_report(prompt):     resp = requests.post(         "https://api.anthropic.com/v1/messages",         headers={             "x-api-key": ANTHROPIC_API_KEY,             "anthropic-version": "2023-06-01",             "content-type": "application/json"         },         json={             "model": "claude-opus-4-5-20251101",             "max_tokens": 8000,             "messages": [{"role": "user", "content": prompt}]         },         timeout=120     )     if resp.status_code != 200:         print(f"API Error {resp.status_code}: {resp.text}")     resp.raise_for_status()     return resp.json()["content"][0]["text"](prompt):
    resp = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "x-api-key": ANTHROPIC_API_KEY,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        },
        json={
            "model": "claude-opus-4-5-20251101",
            "max_tokens": 8000,
            "messages": [{"role": "user", "content": prompt}]
        },
        timeout=120
    )
    resp.raise_for_status()
    return resp.json()["content"][0]["text"]

def save_to_supabase(date_label, html, schedule):
    resp = requests.post(
        f"{SUPABASE_URL}/rest/v1/reports",
        headers={
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}",
            "Content-Type": "application/json",
            "Prefer": "return=representation"
        },
        json={
            "date_label": date_label,
            "html": html,
            "schedule": schedule,
            "comments": []
        },
        timeout=30
    )
    resp.raise_for_status()
    return resp.json()[0]["id"]

def send_ntfy(date_label, schedule):
    companies = ", ".join(c for s in schedule for c in s["companies"])
    requests.post(
        f"https://ntfy.sh/{NTFY_TOPIC}",
        headers={
            "Title": f"Stock Report Ready - {date_label}",
            "Priority": "default",
            "Tags": "chart_increasing"
        },
        data=f"Today's 6 companies: {companies}. Open your report app to read.",
        timeout=15
    )

def main():
    schedule = get_schedule()
    date_str = datetime.utcnow().strftime("%A, %B %-d, %Y")
    print(f"Generating report for {date_str}...")
    prompt = build_prompt(schedule, date_str)
    html = def generate_report(prompt):     resp = requests.post(         "https://api.anthropic.com/v1/messages",         headers={             "x-api-key": ANTHROPIC_API_KEY,             "anthropic-version": "2023-06-01",             "content-type": "application/json"         },         json={             "model": "claude-opus-4-5-20251101",             "max_tokens": 8000,             "messages": [{"role": "user", "content": prompt}]         },         timeout=120     )     if resp.status_code != 200:         print(f"API Error {resp.status_code}: {resp.text}")     resp.raise_for_status()     return resp.json()["content"][0]["text"](prompt)
    print("Report generated.")
    report_id = save_to_supabase(date_str, html, schedule)
    print(f"Saved to Supabase, id: {report_id}")
    send_ntfy(date_str, schedule)
    print("Notification sent. Done.")

if __name__ == "__main__":
    main()

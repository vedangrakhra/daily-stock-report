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
        "Financials": [["Visa (V)","Moodys (MCO)"],["KKR (KKR)","Intercontinental Exchange (ICE)"],["Brookfield AM (BAM)","TD Bank (TD.TO)"]],
        "Industrials": [["Canadian National Railway (CNR.TO)","Waste Connections (WCN)"],["Caterpillar (CAT)","Aecom (ACM)"],["Constellation Software (CSU.TO)","WSP Global (WSP.TO)"]],
        "Consumer": [["Costco (COST)","Restaurant Brands (QSR)"],["Amazon (AMZN)","Lululemon (LULU)"],["Couche-Tard (ATD.TO)","Dollarama (DOL.TO)"]],
        "Healthcare": [["UnitedHealth (UNH)","Intuitive Surgical (ISRG)"],["Danaher (DHR)","Abbott Labs (ABT)"]],
        "Energy": [["Canadian Natural Resources (CNQ.TO)","Agnico Eagle (AEM.TO)"],["Teck Resources (TECK.TO)","Pembina Pipeline (PPL.TO)"]],
    },
    "Asia": {
        "Technology": [["TSMC (TSM)","Samsung (005930.KS)"],["Tencent (0700.HK)","Infosys (INFY)"],["Keyence (6861.T)","HCL Tech (HCLTECH.NS)"]],
        "Financials": [["HDFC Bank (HDB)","DBS Group (D05.SI)"],["Bajaj Finance (BAJFINANCE.NS)","ICICI Bank (IBN)"]],
        "Industrials": [["Toyota (TM)","Siemens India (SIEMENS.NS)"],["Komatsu (6301.T)","Larsen and Toubro (LT.NS)"]],
        "Consumer": [["Meituan (3690.HK)","Zomato (ZOMATO.NS)"],["Fast Retailing (9983.T)","Titan Company (TITAN.NS)"]],
        "Conglomerates": [["Reliance Industries (RELIANCE.NS)","SoftBank (9984.T)"],["Sony Group (SONY)","Tata Consultancy (TCS.NS)"]],
    },
    "Emerging Markets": {
        "Technology": [["MercadoLibre (MELI)","Sea Limited (SE)"],["Totvs (TOTS3.SA)","Grab Holdings (GRAB)"]],
        "Financials": [["XP Inc (XP)","Bank Central Asia (BBCA.JK)"],["Nu Holdings (NU)","Itau Unibanco (ITUB)"]],
        "Industrials": [["Embraer (ERJ)","WEG SA (WEGE3.SA)"],["Localiza (RENT3.SA)","Rumo Logistica (RAIL3.SA)"]],
        "Resources": [["Vale SA (VALE)","Petrobras (PBR)"],["Gerdau (GGB)","Suzano (SUZ)"]],
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
    lines = []
    for s in schedule:
        lines.append(s["market"] + " / " + s["sector"] + ": " + s["companies"][0] + " and " + s["companies"][1])
    company_list = "\n".join(lines)

    prompt = "You are a senior equity research analyst writing a structured daily stock briefing for a corporate development professional learning about global public markets.\n\n"
    prompt += "Today's date: " + date_str + "\n\n"
    prompt += "Write a deep-dive research briefing for EXACTLY these 6 companies grouped by market:\n"
    prompt += company_list + "\n\n"
    prompt += "For EACH company use this exact structure:\n\n"
    prompt += "[Company Name] ([Ticker]) - [Market] | [Sector]\n"
    prompt += "What They Do: 2-3 sentences plain English.\n"
    prompt += "How They Make Money: Revenue model, key segments, unit economics.\n"
    prompt += "Customer Type: B2B/B2C/B2G/mixed, retention dynamics.\n"
    prompt += "Industry Overview: Market size, growth rate, tailwinds and headwinds.\n"
    prompt += "Competitive Advantages: Specific moats - network effects, switching costs, scale, IP, brand, regulatory.\n"
    prompt += "Catalysts (Next 12-24 Months): 2-3 specific near/medium-term catalysts.\n"
    prompt += "Key Risks: 2-3 genuine company-specific risks.\n"
    prompt += "Valuation Snapshot: Approximate EV/EBITDA or P/E vs sector median. One sentence on cheap/fair/expensive and why.\n\n"
    prompt += "After all 6 companies add a Daily Market Theme: 4-5 sentences connecting the macro/sector thread across today's picks.\n\n"
    prompt += "Format as clean professional HTML with inline styles. Background #ffffff. Header bar #0f1e3c white text. "
    prompt += "Each company in a card: white bg, border 1px solid #e2e8f0, border-radius 8px, padding 24px, margin-bottom 20px. "
    prompt += "Section labels bold #1e3a5f. Body text #374151 14px line-height 1.7. Font Helvetica Neue. "
    prompt += "Market group headers with colored pill: NA=#1d4ed8, Asia=#0891b2, EM=#059669. Max-width 680px centered. Footer with date."
    return prompt


def generate_report(prompt):
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
    if resp.status_code != 200:
        print("API Error " + str(resp.status_code) + ": " + resp.text)
    resp.raise_for_status()
    return resp.json()["content"][0]["text"]


def save_to_supabase(date_label, html, schedule):
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
        "https://ntfy.sh/" + NTFY_TOPIC,
        headers={
            "Title": "Stock Report Ready - " + date_label,
            "Priority": "default",
            "Tags": "chart_increasing"
        },
        data="Today's 6 companies: " + companies + ". Open your report app to read.",
        timeout=15
    )


def main():
    schedule = get_schedule()
    date_str = datetime.utcnow().strftime("%A, %B %-d, %Y")
    print("Generating report for " + date_str + "...")
    prompt = build_prompt(schedule, date_str)
    html = generate_report(prompt)
    print("Report generated.")
    report_id = save_to_supabase(date_str, html, schedule)
    print("Saved to Supabase, id: " + str(report_id))
    send_ntfy(date_str, schedule)
    print("Notification sent. Done.")


if __name__ == "__main__":
    main()

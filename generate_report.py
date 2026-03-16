
import os
import json
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


def build_company_prompt(company, market, sector, date_str):
    prompt = "You are a senior equity research analyst writing a structured stock briefing for a corporate development professional learning about global public markets.\n\n"
    prompt += "Today's date: " + date_str + "\n\n"
    prompt += "Write a deep-dive research briefing for this ONE company: " + company + " (" + market + " | " + sector + ")\n\n"
    prompt += "Use this exact structure:\n\n"
    prompt += "What They Do: 2-3 sentences plain English.\n"
    prompt += "How They Make Money: Revenue model, key segments, unit economics.\n"
    prompt += "Customer Type: B2B/B2C/B2G/mixed, retention dynamics.\n"
    prompt += "Industry Overview: Market size, growth rate, tailwinds and headwinds.\n"
    prompt += "Competitive Advantages: Specific moats - network effects, switching costs, scale, IP, brand, regulatory.\n"
    prompt += "Catalysts (Next 12-24 Months): 2-3 specific near/medium-term catalysts.\n"
    prompt += "Key Risks: 2-3 genuine company-specific risks.\n"
    prompt += "Valuation Snapshot: Approximate EV/EBITDA or P/E vs sector median. One sentence on cheap/fair/expensive and why.\n\n"
    prompt += "Format as a self-contained HTML section with inline styles only. "
    prompt += "White background #ffffff. Company name as h2 in #0f1e3c. "
    prompt += "Section labels bold #1e3a5f. Body text #374151 14px line-height 1.7. "
    prompt += "Font Helvetica Neue. Padding 24px. No outer card border - just the content. "
    prompt += "Do not include html, head, or body tags. Just the content div."
    return prompt


def call_api(prompt):
    resp = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "x-api-key": ANTHROPIC_API_KEY,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        },
        json={
            "model": "claude-opus-4-5-20251101",
            "max_tokens": 2000,
            "messages": [{"role": "user", "content": prompt}]
        },
        timeout=120
    )
    if resp.status_code != 200:
        print("API Error " + str(resp.status_code) + ": " + resp.text)
    resp.raise_for_status()
    return resp.json()["content"][0]["text"]


def build_summary_prompt(schedule, date_str):
    lines = []
    for s in schedule:
        lines.append(s["market"] + " / " + s["sector"] + ": " + s["companies"][0] + " and " + s["companies"][1])
    prompt = "Write a Daily Market Theme: 4-5 sentences connecting the macro and sector thread across these 6 companies:\n"
    prompt += "\n".join(lines)
    prompt += "\n\nFormat as a simple HTML paragraph with inline styles. Text color #374151, font-size 14px, line-height 1.7, font Helvetica Neue. No outer tags."
    return prompt


def save_to_supabase(date_label, schedule, company_html, summary_html):
    full_html = "<div style='font-family:Helvetica Neue,Helvetica,Arial,sans-serif;max-width:680px;margin:0 auto;'>"
    full_html += "<div style='background:#0f1e3c;padding:24px;border-radius:8px;margin-bottom:20px;'>"
    full_html += "<h1 style='color:#fff;font-size:20px;margin:0;'>Daily Stock Research</h1>"
    full_html += "<p style='color:#7fa8d4;margin:6px 0 0;font-size:13px;'>" + date_label + "</p>"
    full_html += "</div>"
    for key, html in company_html.items():
        full_html += "<div style='border:1px solid #e2e8f0;border-radius:8px;margin-bottom:16px;overflow:hidden;'>" + html + "</div>"
    full_html += "<div style='background:#f8fafc;border-radius:8px;padding:20px;margin-top:8px;'>"
    full_html += "<p style='font-weight:bold;color:#1e3a5f;margin-bottom:8px;'>Daily Market Theme</p>"
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
    
def report_exists_today():
    today = datetime.utcnow().strftime("%Y-%m-%d")
    resp = requests.get(
        SUPABASE_URL + "/rest/v1/reports?select=id&created_at=gte." + today + "T00:00:00",
        headers={"apikey": SUPABASE_KEY, "Authorization": "Bearer " + SUPABASE_KEY}
    )
    data = resp.json()
    return len(data) > 0

def main():
    if report_exists_today():
        print("Report already exists for today, skipping.")
        return
    schedule = get_schedule()
    date_str = datetime.utcnow().strftime("%A, %B %-d, %Y")
    print("Generating report for " + date_str + "...")

    company_html = {}
    for seg in schedule:
        for company in seg["companies"]:
            print("Generating: " + company)
            prompt = build_company_prompt(company, seg["market"], seg["sector"], date_str)
            html = call_api(prompt)
            company_html[company] = html

    print("Generating market theme...")
    summary_html = call_api(build_summary_prompt(schedule, date_str))

    report_id = save_to_supabase(date_str, schedule, company_html, summary_html)
    print("Saved to Supabase, id: " + str(report_id))

    send_ntfy(date_str, schedule)
    print("Notification sent. Done.")


if __name__ == "__main__":
    main()

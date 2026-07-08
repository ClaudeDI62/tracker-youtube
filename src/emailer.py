"""Send daily summary email via Gmail SMTP."""

import os
import smtplib
from datetime import date, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from src.db import get_client

DASHBOARD_URL = "https://tracker-youtube-txtaayzqutvy4dkhy2tfse.streamlit.app"


def _get_smtp_config():
    return {
        "sender": os.environ.get("GMAIL_ADDRESS", "").strip(),
        "password": os.environ.get("GMAIL_APP_PASSWORD", "").replace("\xa0", "").strip(),
        "recipient": os.environ.get("EMAIL_RECIPIENT", "").strip(),
    }


def _action_emoji(action):
    return {"buy": "\U0001f7e2", "sell": "\U0001f534", "hold": "\U0001f7e1"}.get(action, "")


def _hit_badge(hit):
    if hit is True:
        return '<span style="background:#059669;color:#fff;padding:2px 8px;border-radius:4px;font-size:13px;">HIT</span>'
    elif hit is False:
        return '<span style="background:#DC2626;color:#fff;padding:2px 8px;border-radius:4px;font-size:13px;">MISS</span>'
    return '<span style="background:#D97706;color:#fff;padding:2px 8px;border-radius:4px;font-size:13px;">HOLD</span>'


def build_daily_html() -> str:
    client = get_client()
    today = date.today()
    yesterday = today - timedelta(days=1)

    recos = (
        client.table("recommendations")
        .select("asset_name, ticker, action, reco_date, videos!inner(channels!inner(name))")
        .gte("reco_date", yesterday.isoformat())
        .order("reco_date", desc=True)
        .execute()
    )

    evals = (
        client.table("evaluations")
        .select("horizon_days, hit, excess_return_pct, recommendation_id, "
                "recommendations!inner(asset_name, ticker, action, videos!inner(channels!inner(name)))")
        .gte("evaluated_at", yesterday.isoformat())
        .execute()
    )

    ratings = (
        client.table("ratings")
        .select("*, channels(name)")
        .eq("horizon_days", 7)
        .order("score", desc=True)
        .execute()
    )

    jobs = (
        client.table("job_runs")
        .select("*")
        .order("started_at", desc=True)
        .limit(1)
        .execute()
    )

    # --- Build HTML ---
    recos_html = ""
    if recos.data:
        rows = ""
        for r in recos.data:
            ch = r.get("videos", {}).get("channels", {}).get("name", "?")
            action = r["action"].upper()
            rows += f"""<tr>
                <td style="padding:8px 12px;border-bottom:1px solid #eee;">{_action_emoji(r['action'])} {action}</td>
                <td style="padding:8px 12px;border-bottom:1px solid #eee;"><strong>{r['asset_name']}</strong></td>
                <td style="padding:8px 12px;border-bottom:1px solid #eee;">{r['ticker'] or '—'}</td>
                <td style="padding:8px 12px;border-bottom:1px solid #eee;">{ch}</td>
            </tr>"""
        recos_html = f"""<table style="width:100%;border-collapse:collapse;margin:8px 0;">
            <tr style="background:#2563EB;color:#fff;">
                <th style="padding:8px 12px;text-align:left;">Azione</th>
                <th style="padding:8px 12px;text-align:left;">Asset</th>
                <th style="padding:8px 12px;text-align:left;">Ticker</th>
                <th style="padding:8px 12px;text-align:left;">Canale</th>
            </tr>{rows}</table>"""
    else:
        recos_html = '<p style="color:#888;margin:8px 0;">Nessuna nuova raccomandazione oggi.</p>'

    evals_html = ""
    if evals.data:
        rows = ""
        for e in evals.data:
            rec = e.get("recommendations", {})
            ch = rec.get("videos", {}).get("channels", {}).get("name", "?")
            excess = float(e["excess_return_pct"] or 0)
            sign = "+" if excess >= 0 else ""
            rows += f"""<tr>
                <td style="padding:8px 12px;border-bottom:1px solid #eee;">{_action_emoji(rec.get('action',''))} {rec.get('action','?').upper()}</td>
                <td style="padding:8px 12px;border-bottom:1px solid #eee;"><strong>{rec.get('asset_name','?')}</strong></td>
                <td style="padding:8px 12px;border-bottom:1px solid #eee;">{rec.get('ticker','?')}</td>
                <td style="padding:8px 12px;border-bottom:1px solid #eee;">{e['horizon_days']}g</td>
                <td style="padding:8px 12px;border-bottom:1px solid #eee;">{_hit_badge(e['hit'])}</td>
                <td style="padding:8px 12px;border-bottom:1px solid #eee;">{sign}{excess:.1f}%</td>
                <td style="padding:8px 12px;border-bottom:1px solid #eee;">{ch}</td>
            </tr>"""
        evals_html = f"""<table style="width:100%;border-collapse:collapse;margin:8px 0;">
            <tr style="background:#2563EB;color:#fff;">
                <th style="padding:8px 12px;text-align:left;">Azione</th>
                <th style="padding:8px 12px;text-align:left;">Asset</th>
                <th style="padding:8px 12px;text-align:left;">Ticker</th>
                <th style="padding:8px 12px;text-align:left;">Orizzonte</th>
                <th style="padding:8px 12px;text-align:left;">Esito</th>
                <th style="padding:8px 12px;text-align:left;">Excess</th>
                <th style="padding:8px 12px;text-align:left;">Canale</th>
            </tr>{rows}</table>"""
    else:
        evals_html = '<p style="color:#888;margin:8px 0;">Nessun esito maturato oggi.</p>'

    medals = ["\U0001f947", "\U0001f948", "\U0001f949"]
    rankings_html = ""
    if ratings.data:
        rows = ""
        for i, r in enumerate(ratings.data):
            ch = r.get("channels", {}).get("name", "?")
            hit_rate = float(r["hit_rate"] or 0) * 100
            wilson = float(r["score"] or 0)
            avg_ex = float(r["avg_excess_return"] or 0)
            sign = "+" if avg_ex >= 0 else ""
            medal = medals[i] if i < 3 else f"#{i+1}"
            rows += f"""<tr>
                <td style="padding:8px 12px;border-bottom:1px solid #eee;text-align:center;">{medal}</td>
                <td style="padding:8px 12px;border-bottom:1px solid #eee;"><strong>{ch}</strong></td>
                <td style="padding:8px 12px;border-bottom:1px solid #eee;text-align:center;">{r['n_recos']}</td>
                <td style="padding:8px 12px;border-bottom:1px solid #eee;text-align:center;">{hit_rate:.0f}%</td>
                <td style="padding:8px 12px;border-bottom:1px solid #eee;text-align:center;">{wilson:.3f}</td>
                <td style="padding:8px 12px;border-bottom:1px solid #eee;text-align:center;">{sign}{avg_ex:.1f}%</td>
            </tr>"""
        rankings_html = f"""<table style="width:100%;border-collapse:collapse;margin:8px 0;">
            <tr style="background:#2563EB;color:#fff;">
                <th style="padding:8px 12px;text-align:center;">Pos.</th>
                <th style="padding:8px 12px;text-align:left;">Canale</th>
                <th style="padding:8px 12px;text-align:center;">Reco</th>
                <th style="padding:8px 12px;text-align:center;">Hit Rate</th>
                <th style="padding:8px 12px;text-align:center;">Wilson</th>
                <th style="padding:8px 12px;text-align:center;">Excess</th>
            </tr>{rows}</table>"""
    else:
        rankings_html = '<p style="color:#888;margin:8px 0;">Nessun rating disponibile.</p>'

    job_html = ""
    if jobs.data:
        job = jobs.data[0]
        status = job["status"]
        color = "#059669" if status == "success" else "#D97706"
        job_html = f'<span style="background:{color};color:#fff;padding:2px 8px;border-radius:4px;font-size:13px;">{status.upper()}</span> — {job["started_at"][:16].replace("T"," ")}'
        if job.get("notes"):
            job_html += f'<br><span style="color:#888;font-size:13px;">Note: {job["notes"]}</span>'

    html = f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="font-family:'Segoe UI',Arial,sans-serif;background:#f5f5f5;margin:0;padding:20px;">
<div style="max-width:640px;margin:0 auto;background:#fff;border-radius:12px;overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,0.08);">

    <div style="background:#1A1F36;color:#fff;padding:24px 28px;">
        <h1 style="margin:0;font-size:22px;font-weight:700;">\U0001f4ca YouTube Tracker</h1>
        <p style="margin:6px 0 0;opacity:0.8;font-size:14px;">Riepilogo giornaliero — {today.strftime('%d/%m/%Y')}</p>
    </div>

    <div style="padding:24px 28px;">

        <h2 style="font-size:16px;color:#1A1F36;margin:0 0 8px;border-bottom:2px solid #2563EB;padding-bottom:6px;">
            Nuove Raccomandazioni
        </h2>
        {recos_html}

        <h2 style="font-size:16px;color:#1A1F36;margin:24px 0 8px;border-bottom:2px solid #2563EB;padding-bottom:6px;">
            Esiti Maturati
        </h2>
        {evals_html}

        <h2 style="font-size:16px;color:#1A1F36;margin:24px 0 8px;border-bottom:2px solid #2563EB;padding-bottom:6px;">
            Classifica Canali (7 giorni)
        </h2>
        {rankings_html}

        <h2 style="font-size:16px;color:#1A1F36;margin:24px 0 8px;border-bottom:2px solid #2563EB;padding-bottom:6px;">
            Stato Sistema
        </h2>
        <p style="margin:8px 0;">{job_html}</p>

    </div>

    <div style="background:#f5f7fa;padding:16px 28px;text-align:center;border-top:1px solid #eee;">
        <a href="{DASHBOARD_URL}" style="display:inline-block;background:#2563EB;color:#fff;text-decoration:none;padding:10px 24px;border-radius:6px;font-weight:600;font-size:14px;">
            Apri Dashboard
        </a>
        <p style="margin:10px 0 0;color:#888;font-size:12px;">YouTube Recommendation Tracker — Report automatico</p>
    </div>

</div>
</body>
</html>"""
    return html


def send_daily_email() -> bool:
    config = _get_smtp_config()

    if not config["sender"] or not config["password"] or not config["recipient"]:
        print("[EMAIL] Configurazione email incompleta, skip invio.")
        return False

    html_body = build_daily_html()

    msg = MIMEMultipart("alternative")
    msg["From"] = config["sender"]
    msg["To"] = config["recipient"]
    msg["Subject"] = f"\U0001f4ca YT Tracker — {date.today().strftime('%d/%m/%Y')}"
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(config["sender"], config["password"])
            server.send_message(msg)
        print("[EMAIL] Email inviata con successo.")
        return True
    except Exception as e:
        print(f"[EMAIL] Errore invio: {type(e).__name__}: {e}")
        return False

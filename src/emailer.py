"""Send daily summary email via Gmail SMTP."""

import os
import smtplib
from datetime import date, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from src.db import get_client


def _get_smtp_config():
    return {
        "sender": os.environ.get("GMAIL_ADDRESS", "").strip(),
        "password": os.environ.get("GMAIL_APP_PASSWORD", "").replace("\xa0", "").strip(),
        "recipient": os.environ.get("EMAIL_RECIPIENT", "").strip(),
    }


def build_daily_summary() -> str:
    """Build the daily summary email body."""
    client = get_client()
    today = date.today()
    yesterday = today - timedelta(days=1)

    # New recommendations (last 24h)
    recos = (
        client.table("recommendations")
        .select("asset_name, ticker, action, reco_date, videos!inner(channels!inner(name))")
        .gte("reco_date", yesterday.isoformat())
        .order("reco_date", desc=True)
        .execute()
    )

    # Recent evaluations (last 24h)
    evals = (
        client.table("evaluations")
        .select("horizon_days, hit, excess_return_pct, recommendation_id, "
                "recommendations!inner(asset_name, ticker, action, videos!inner(channels!inner(name)))")
        .gte("evaluated_at", yesterday.isoformat())
        .execute()
    )

    # Current ratings
    ratings = (
        client.table("ratings")
        .select("*, channels(name)")
        .eq("horizon_days", 7)
        .order("score", desc=True)
        .execute()
    )

    # Last job run
    jobs = (
        client.table("job_runs")
        .select("*")
        .order("started_at", desc=True)
        .limit(1)
        .execute()
    )

    lines = []
    lines.append(f"=== YouTube Tracker - Riepilogo {today.strftime('%d/%m/%Y')} ===\n")

    # New recommendations
    lines.append("--- NUOVE RACCOMANDAZIONI ---")
    if recos.data:
        for r in recos.data:
            ch = r.get("videos", {}).get("channels", {}).get("name", "?")
            lines.append(f"  {r['action'].upper()} {r['asset_name']} ({r['ticker'] or '?'}) - {ch}")
    else:
        lines.append("  Nessuna nuova raccomandazione.")
    lines.append("")

    # Evaluations matured
    lines.append("--- ESITI MATURATI ---")
    if evals.data:
        for e in evals.data:
            rec = e.get("recommendations", {})
            ch = rec.get("videos", {}).get("channels", {}).get("name", "?")
            hit_str = "HIT" if e["hit"] else ("MISS" if e["hit"] is not None else "HOLD")
            excess = float(e["excess_return_pct"] or 0)
            lines.append(
                f"  {rec.get('action', '?').upper()} {rec.get('asset_name', '?')} "
                f"({rec.get('ticker', '?')}) {e['horizon_days']}g: "
                f"{hit_str} (excess: {excess:+.1f}%) - {ch}"
            )
    else:
        lines.append("  Nessun esito maturato oggi.")
    lines.append("")

    # Rankings
    lines.append("--- CLASSIFICA CANALI (7 giorni) ---")
    if ratings.data:
        for i, r in enumerate(ratings.data):
            ch = r.get("channels", {}).get("name", "?")
            hit_rate = float(r["hit_rate"] or 0) * 100
            lines.append(
                f"  #{i+1} {ch}: {hit_rate:.0f}% hit rate "
                f"({r['n_recos']} reco, Wilson={float(r['score'] or 0):.3f})"
            )
    lines.append("")

    # Job status
    if jobs.data:
        job = jobs.data[0]
        lines.append(f"--- ULTIMO JOB: {job['status']} ({job['started_at'][:16]}) ---")
        if job.get("notes"):
            lines.append(f"  Note: {job['notes']}")
    lines.append("")

    lines.append("Dashboard: (link disponibile dopo il deploy su Streamlit Cloud)")
    lines.append("")
    lines.append("---")
    lines.append("YouTube Recommendation Tracker - Report automatico")

    return "\n".join(lines)


def send_daily_email() -> bool:
    """Send the daily summary email. Returns True on success."""
    config = _get_smtp_config()

    if not config["sender"] or not config["password"] or not config["recipient"]:
        print("[EMAIL] Configurazione email incompleta, skip invio.")
        return False

    body = build_daily_summary()

    msg = MIMEMultipart()
    msg["From"] = config["sender"]
    msg["To"] = config["recipient"]
    msg["Subject"] = f"YT Tracker - Riepilogo {date.today().strftime('%d/%m/%Y')}"
    msg.attach(MIMEText(body, "plain", "utf-8"))

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

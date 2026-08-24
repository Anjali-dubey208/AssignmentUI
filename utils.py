import csv
import io
import json
import os
import re
import uuid
from datetime import datetime

from config import Config

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def allowed_file(filename):
    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower() in Config.ALLOWED_EXTENSIONS
    )


def extract_emails_from_csv(filepath):
    """Read a CSV and pull out every valid, de-duplicated email address,
    regardless of which column they live in or what the header is called."""
    emails = []
    seen = set()

    with open(filepath, newline="", encoding="utf-8-sig", errors="ignore") as f:
        sample = f.read(2048)
        f.seek(0)
        try:
            dialect = csv.Sniffer().sniff(sample)
        except csv.Error:
            dialect = csv.excel
        reader = csv.reader(f, dialect)

        for row in reader:
            for cell in row:
                cell = cell.strip()
                if EMAIL_RE.match(cell):
                    key = cell.lower()
                    if key not in seen:
                        seen.add(key)
                        emails.append(cell)
    return emails


# ---------------------------------------------------------------------------
# Lightweight JSON "database" — enough for an assignment without needing a
# real DB. Structure:
# {
#   "batches": {batch_id: {filename, uploaded_at, emails: [...]}},
#   "classified": {batch_id: {business: [...], individual: [...]}},
#   "campaigns": [ {id, subject, audience, sent_at, total, delivered, failed} ]
# }
# ---------------------------------------------------------------------------

def _load():
    if not os.path.exists(Config.DATA_FILE):
        return {"batches": {}, "classified": {}, "campaigns": []}
    with open(Config.DATA_FILE, "r") as f:
        return json.load(f)


def _save(data):
    with open(Config.DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)


def save_batch(filename, emails):
    data = _load()
    batch_id = uuid.uuid4().hex[:8]
    data["batches"][batch_id] = {
        "filename": filename,
        "uploaded_at": datetime.now().isoformat(timespec="seconds"),
        "emails": emails,
    }
    _save(data)
    return batch_id


def get_batch(batch_id):
    return _load()["batches"].get(batch_id)


def list_batches():
    data = _load()
    return sorted(
        data["batches"].items(), key=lambda kv: kv[1]["uploaded_at"], reverse=True
    )


def save_classification(batch_id, business, individual):
    data = _load()
    data["classified"][batch_id] = {"business": business, "individual": individual}
    _save(data)


def get_classification(batch_id):
    return _load()["classified"].get(batch_id)


def save_campaign(record):
    data = _load()
    record["id"] = uuid.uuid4().hex[:8]
    record["sent_at"] = datetime.now().isoformat(timespec="seconds")
    data["campaigns"].append(record)
    _save(data)
    return record


def list_campaigns():
    data = _load()
    return list(reversed(data["campaigns"]))


def report_summary():
    campaigns = list_campaigns()
    total_sent = sum(c["total"] for c in campaigns)
    total_delivered = sum(c["delivered"] for c in campaigns)
    total_failed = sum(c["failed"] for c in campaigns)
    rate = round((total_delivered / total_sent) * 100, 1) if total_sent else 0.0
    return {
        "campaigns": campaigns,
        "total_sent": total_sent,
        "total_delivered": total_delivered,
        "total_failed": total_failed,
        "delivery_rate": rate,
    }

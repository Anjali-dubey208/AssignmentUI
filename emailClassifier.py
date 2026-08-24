"""
Classifies a list of emails as BUSINESS or INDIVIDUAL.

Primary path: ask Gemini to classify in a single batched prompt.
Fallback path: if no GEMINI_API_KEY is configured (or the call fails),
fall back to a rule-based heuristic so the rest of the app is still
fully testable without an API key.
"""
import json
import re
import urllib.request
import urllib.error

from config import Config

FREE_PROVIDERS = {
    "gmail.com", "yahoo.com", "outlook.com", "hotmail.com", "icloud.com",
    "aol.com", "live.com", "protonmail.com", "mail.com", "rediffmail.com",
    "yandex.com", "zoho.com",
}


def _heuristic_classify(email):
    domain = email.split("@")[-1].lower()
    local = email.split("@")[0].lower()

    if domain in FREE_PROVIDERS:
        return "INDIVIDUAL"

    # Business-y local parts: info@, sales@, contact@, support@, hr@, admin@
    business_prefixes = ("info", "sales", "contact", "support", "hr",
                          "admin", "office", "team", "help", "billing")
    if local in business_prefixes or any(local.startswith(p) for p in business_prefixes):
        return "BUSINESS"

    # Custom domain that isn't a free provider -> assume business
    return "BUSINESS"


def _call_gemini(emails):
    prompt = (
        "Classify each email address below as exactly BUSINESS or INDIVIDUAL.\n"
        "BUSINESS = company/organization domain or role-based address "
        "(info@, sales@, hr@, etc). INDIVIDUAL = personal address, usually on "
        "a free provider like gmail/yahoo/outlook.\n"
        "Return ONLY a JSON object mapping each email to its label, no prose, "
        "no markdown fences.\n\n"
        "Emails:\n" + "\n".join(emails)
    )

    url = Config.GEMINI_URL.format(model=Config.GEMINI_MODEL, key=Config.GEMINI_API_KEY)
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0, "responseMimeType": "application/json"},
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        body = json.loads(resp.read().decode("utf-8"))

    text = body["candidates"][0]["content"]["parts"][0]["text"]
    text = re.sub(r"^```(json)?|```$", "", text.strip(), flags=re.MULTILINE).strip()
    return json.loads(text)


def classify_emails(emails):
    """Returns (business_list, individual_list)."""
    labels = {}

    if Config.GEMINI_API_KEY:
        try:
            labels = _call_gemini(emails)
        except (urllib.error.URLError, KeyError, ValueError, json.JSONDecodeError):
            labels = {}

    business, individual = [], []
    for email in emails:
        label = labels.get(email) if labels else None
        if not label:
            label = _heuristic_classify(email)
        if str(label).upper().startswith("BUS"):
            business.append(email)
        else:
            individual.append(email)

    return business, individual

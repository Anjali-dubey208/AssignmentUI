# EmailPro

A bulk email marketing tool: upload a CSV of addresses, classify them as
BUSINESS or INDIVIDUAL, send a targeted campaign, and see delivery reports.

## Setup

```bash
pip install -r requirements.txt
python app.py
```

Then open http://localhost:5000 — it redirects to the Upload page.

## Flow

1. **Upload** — pick a `.csv` file. Any column can hold the email address;
   duplicates are removed automatically. A sample file is in
   `sample_data/SampleEmails.csv`.
2. **Classify** — click "Run AI classification" to sort the list into
   Business vs Individual addresses.
3. **Send** — pick the classified list, an audience (business / individual /
   everyone), write a subject + message, optionally attach a file, and send.
4. **Report** — see aggregate stats (total, delivered, failed, delivery
   rate) and a table of every campaign sent.
5. **Settings** — shows which integrations are currently configured.

## Configuration (optional — the app works without any of this)

Set these as environment variables:

| Variable | Purpose | If unset |
|---|---|---|
| `GEMINI_API_KEY` | Uses Google Gemini to classify emails | Falls back to a rule-based classifier (free-mail domains → Individual, role addresses/company domains → Business) |
| `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_HOST`, `SMTP_PORT` | Sends real email via SMTP | Sends are **simulated** (randomized ~95% delivery) so the Send → Report flow is still fully testable |

Example:

```bash
export GEMINI_API_KEY="your-key-here"
export SMTP_USER="you@gmail.com"
export SMTP_PASSWORD="app-password"
python app.py
```

## Project structure

```
app.py              Flask routes (upload, classify, send, report, settings)
config.py           App configuration / environment variables
utils.py            CSV parsing, dedup, JSON data store
emailClassifier.py  Gemini-based classifier + heuristic fallback
mailer.py           SMTP sender + simulate mode
templates/          Jinja templates for each page
static/css/         Stylesheet
sample_data/        Sample CSV for testing
```

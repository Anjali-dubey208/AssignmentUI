import os

from flask import (
    Flask, render_template, request, redirect, url_for, flash, session, jsonify
)

from config import Config
from utils import (
    allowed_file, extract_emails_from_csv, save_batch, get_batch, list_batches,
    save_classification, get_classification, save_campaign, report_summary,
)
from emailClassifier import classify_emails
from mailer import send_campaign

app = Flask(__name__)
app.config.from_object(Config)
os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)


@app.route("/")
def index():
    return redirect(url_for("upload"))


# ---------------------------------------------------------------- Upload ---
@app.route("/upload", methods=["GET", "POST"])
def upload():
    if request.method == "POST":
        file = request.files.get("csv_file")
        if not file or file.filename == "":
            flash("Please choose a CSV file first.", "error")
            return redirect(url_for("upload"))

        if not allowed_file(file.filename):
            flash("Only .csv files are supported.", "error")
            return redirect(url_for("upload"))

        save_path = os.path.join(Config.UPLOAD_FOLDER, file.filename)
        file.save(save_path)

        emails = extract_emails_from_csv(save_path)
        if not emails:
            flash("No valid email addresses found in that file.", "error")
            return redirect(url_for("upload"))

        batch_id = save_batch(file.filename, emails)
        flash(f"Found {len(emails)} unique email(s) in {file.filename}.", "success")
        return redirect(url_for("classify", batch_id=batch_id))

    return render_template("upload.html", batches=list_batches())


# -------------------------------------------------------------- Classify ---
@app.route("/classify/<batch_id>", methods=["GET", "POST"])
def classify(batch_id):
    batch = get_batch(batch_id)
    if not batch:
        flash("That upload batch was not found.", "error")
        return redirect(url_for("upload"))

    result = get_classification(batch_id)

    if request.method == "POST":
        business, individual = classify_emails(batch["emails"])
        save_classification(batch_id, business, individual)
        result = {"business": business, "individual": individual}
        flash("Classification complete.", "success")

    return render_template(
        "classify.html", batch=batch, batch_id=batch_id, result=result
    )


# ------------------------------------------------------------------ Send ---
@app.route("/send", methods=["GET", "POST"])
def send():
    batches = list_batches()
    classified_batches = [
        (bid, b) for bid, b in batches if get_classification(bid)
    ]

    if request.method == "POST":
        batch_id = request.form.get("batch_id")
        audience = request.form.get("audience")  # business / individual / both
        subject = request.form.get("subject", "").strip()
        body = request.form.get("body", "").strip()

        result = get_classification(batch_id) if batch_id else None
        if not result:
            flash("Choose a classified batch to send to.", "error")
            return redirect(url_for("send"))
        if not subject or not body:
            flash("Subject and message body are required.", "error")
            return redirect(url_for("send"))

        if audience == "business":
            recipients = result["business"]
        elif audience == "individual":
            recipients = result["individual"]
        else:
            recipients = result["business"] + result["individual"]

        attachment = None
        file = request.files.get("attachment")
        if file and file.filename:
            attachment = {
                "filename": file.filename,
                "data": file.read(),
                "mimetype": file.mimetype,
            }

        outcome = send_campaign(recipients, subject, body, attachment)

        record = save_campaign({
            "subject": subject,
            "audience": audience,
            "batch_id": batch_id,
            "total": len(recipients),
            "delivered": len(outcome["delivered"]),
            "failed": len(outcome["failed"]),
            "simulated": outcome.get("simulated", False),
        })

        flash(
            f"Campaign sent: {record['delivered']} delivered, "
            f"{record['failed']} failed.", "success"
        )
        return redirect(url_for("report"))

    return render_template("send.html", batches=classified_batches)


# ---------------------------------------------------------------- Report ---
@app.route("/report")
def report():
    return render_template("report.html", summary=report_summary())


# -------------------------------------------------------------- Settings ---
@app.route("/settings", methods=["GET", "POST"])
def settings():
    if request.method == "POST":
        # In a real app these would persist to env/secret storage.
        flash("Settings saved for this session.", "success")
        return redirect(url_for("settings"))

    current = {
        "gemini_key_set": bool(Config.GEMINI_API_KEY),
        "smtp_user": Config.SMTP_USER or "(not configured — sends will simulate)",
        "sender_name": Config.SENDER_NAME,
    }
    return render_template("settings.html", current=current)


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)

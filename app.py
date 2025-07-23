from flask import Flask, request, jsonify, render_template_string
from flask_mail import Mail, Message
import os
import uuid

app = Flask(__name__)

# === Email Configuration ===
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'Justiceofficial0010@gmail.com'
app.config['MAIL_PASSWORD'] = 'zogo itjd vjdr yshl'
app.config['MAIL_DEFAULT_SENDER'] = ('My Lifeline', 'Justiceofficial0010@gmail.com')

mail = Mail(app)

# === In-Memory Submission Store ===
SUBMISSIONS = {}

# === Field Definitions ===
individual_fields = [
    "Full Name", "Age", "Phone Number", "Email", "Location", "Occupation",
    "Monthly Income Range", "Number Of Dependents", "Existing Medical Conditions",
    "Regular Medications", "Frequency of Hospital Visits", "Preferred Hospitals/Clinics",
    "Family Medical History", "Preferred Monthly Premium Range", "Priority",
    "Specific Coverage Needs", "Preferred Payment Frequency", "International Coverage Needs",
    "Current Insurance", "Past Insurance Claims", "Maternity Coverage Needs",
    "Emergency Services Priority", "Preferred Mode of Healthcare"
]

company_fields = [
    "Company Name", "Industry Type", "Number of Employees Seeking Coverage",
    "Preferred Coverage Start Date", "Budget Range (Per Employee, Per Month)",
    "Existing Insurance Provider (if any)", "Contact Person Name", "Contact Email",
    "Contact Phone Number", "Existing Medical Conditions", "Regular Medications",
    "Frequency of Hospital Visits", "Preferred Hospitals/Clinics", "Family Medical History",
    "Preferred Monthly Premium Range", "Priority", "Specific Coverage Needs",
    "Preferred Payment Frequency", "International Coverage Needs", "Current Insurance",
    "Past Insurance Claims", "Maternity Coverage Needs", "Emergency Services Priority",
    "Preferred Mode of Healthcare"
]

# === Build Email With View Link ===
def build_email_html_link(submission_id):
    view_link = f"http://localhost:5000/submission/{submission_id}"
    return f"""
    <div style="font-family:Arial, sans-serif;max-width:600px;margin:auto;text-align:center;padding:30px;background:#f9f9f9;">
        <img src="https://i.imgur.com/i6Lfiku.png" width="100" style="margin-bottom:20px;" alt="LifeLine Logo" />
        <h2 style="color:#333;">New Insurance Request</h2>
        <p style="color:#555;">A new insurance request has been submitted via LifeLine Africa.</p>
        <a href="{view_link}" style="display:inline-block;margin-top:20px;padding:12px 25px;background:#e99407;color:white;text-decoration:none;border-radius:6px;">
            View Submission
        </a>
        <p style="margin-top:40px;color:#888;">LifeLine Africa Team</p>
    </div>
    """

# === Build Submission View Page ===
def build_submission_html(data_type, data):
    fields = individual_fields if data_type == "individual" else company_fields
    rows = ""

    for field in fields:
        field_key = (
            field.replace("(", "")
                 .replace(")", "")
                 .replace("/", "")
                 .replace(",", "")
                 .replace("  ", " ")
                 .replace(" ", "_")
                 .lower()
        )
        value = data.get(field_key, 'N/A')
        rows += f"""
            <tr>
                <td style='padding:10px;font-weight:bold;color:#333;border-bottom:1px solid #eee;'>{field}</td>
                <td style='padding:10px;color:#555;border-bottom:1px solid #eee;'>{value}</td>
            </tr>
        """

    return f"""
    <div style="font-family:Arial,sans-serif;max-width:700px;margin:auto;padding:30px;">
        <img src="https://i.imgur.com/i6Lfiku.png" width="100" alt="LifeLine Logo" style="display:block;margin:auto;margin-bottom:20px;" />
        <h2 style="text-align:center;color:#222;">{data_type.title()} Insurance Submission</h2>
        <table style="width:100%;border-collapse:collapse;margin-top:30px;">
            {rows}
        </table>
        <p style="margin-top:30px;color:#777;text-align:center;">Submitted via LifeLine Africa</p>
    </div>
    """

# === Email Submission API ===
@app.route("/submit", methods=["POST"])
def submit():
    content = request.json
    data_type = content.get("type")
    data = content.get("data")

    if data_type not in ["individual", "company"]:
        return jsonify({"error": "Invalid 'type'. Must be 'individual' or 'company'."}), 400
    if not data:
        return jsonify({"error": "Missing 'data' field"}), 400

    # Store submission with UUID
    submission_id = str(uuid.uuid4())
    SUBMISSIONS[submission_id] = {"type": data_type, "data": data}

    # Build email with link
    email_html = build_email_html_link(submission_id)

    msg = Message(
        subject=f"New {data_type.title()} Insurance Request",
        recipients=[
            "j.chukwuony@alustudent.com",
            "kingdavidscloud@gmail.com "
        ],
        cc=["cc_insurer@example.com"],
        html=email_html
    )

    try:
        mail.send(msg)
        return jsonify({"message": "Email sent!", "submission_id": submission_id}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# === Route to View Submission ===
@app.route("/submission/<submission_id>")
def view_submission(submission_id):
    submission = SUBMISSIONS.get(submission_id)
    if not submission:
        return "<h2 style='color:red;text-align:center;'>Submission not found.</h2>", 404

    html = build_submission_html(submission["type"], submission["data"])
    return render_template_string(html)

# === Run App ===
if __name__ == "__main__":
    app.run(debug=True)
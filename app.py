from flask import Flask, request, jsonify
from flask_mail import Mail, Message
import os

app = Flask(__name__)

# === Email Configuration for Custom SMTP ===
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587  # or 465 for SSL
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'Justiceofficial0010@gmail.com'  # or custom domain email
app.config['MAIL_PASSWORD'] = 'zogo itjd vjdr yshl'
app.config['MAIL_DEFAULT_SENDER'] = ('My Lifeline', 'Justiceofficial0010@gmail.com')

mail = Mail(app)

# === Load logo image in base64 ===
with open("logo_base64.txt", "r") as f:
    logo_base64 = f.read()

# === Fields for Each Type ===
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

# === HTML Email Builder ===
def build_email_html(data_type, data):
    fields = individual_fields if data_type == "individual" else company_fields

    rows = "".join(
        f"<tr><td style='padding:8px;border:1px solid #ccc;'><strong>{field}</strong></td>"
        f"<td style='padding:8px;border:1px solid #ccc;'>{data.get(field.replace(' ', '_').lower(), 'N/A')}</td></tr>"
        for field in fields
    )

    return f"""
    <div style="font-family:sans-serif;max-width:600px;margin:auto;border:1px solid #eaeaea;border-radius:10px;">
        <div style="background:#fff;padding:20px;text-align:center;border-bottom:1px solid #eaeaea;">
            <img src="data:image/png;base64,{logo_base64}" width="70" style="margin-bottom:10px;" />
            <h2 style="margin:0;color:#333;">New Insurance Request</h2>
        </div>
        <div style="padding:20px;">
            <p>Dear Insurance Partner,</p>
            <p>We have received a new <strong>{data_type.title()}</strong> insurance interest form via the LifeLine Africa platform.</p>
            <p>Kindly find the client’s submitted details below:</p>
            <table style="width:100%;border-collapse:collapse;margin-top:10px;">{rows}</table>
            <p style="margin-top:20px;">Warm regards,<br><strong>LifeLine Africa Team</strong></p>
        </div>
    </div>
    """

# === API Route ===
@app.route("/submit", methods=["POST"])
def submit():
    content = request.json
    data_type = content.get("type")
    data = content.get("data")

    if data_type not in ["individual", "company"]:
        return jsonify({"error": "Invalid 'type'. Must be 'individual' or 'company'."}), 400
    if not data:
        return jsonify({"error": "Missing 'data' field"}), 400

    email_html = build_email_html(data_type, data)

    msg = Message(
        subject=f"New {data_type.title()} Insurance Request from LifeLine Africa",
        recipients=[
            "j.chukwuony@alustudents.com", "insurer2@example.com", "insurer3@example.com",
            "insurer4@example.com", "insurer5@example.com"
        ],
        cc=["cc_insurer@example.com"],
        html=email_html
    )

    try:
        mail.send(msg)
        return jsonify({"message": "Email sent successfully!"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True)
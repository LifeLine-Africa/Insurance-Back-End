from flask import Flask, request, jsonify
from flask_mail import Mail, Message
import os

app = Flask(__name__)

# === Email Configuration for Custom SMTP ===
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'Justiceofficial0010@gmail.com'
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

# === Modern Email HTML Builder ===
def build_email_html(data_type, data):
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
        rows += (
            f"<tr>"
            f"<td style='padding:10px 15px;font-weight:600;color:#333;border-bottom:1px solid #eee;width:45%;'>{field}</td>"
            f"<td style='padding:10px 15px;color:#555;border-bottom:1px solid #eee;'>{value}</td>"
            f"</tr>"
        )

    return f"""
    <div style="background:#f4f4f7;padding:40px 20px;">
        <div style="max-width:650px;margin:0 auto;background:#ffffff;border-radius:10px;overflow:hidden;box-shadow:0 2px 10px rgba(0,0,0,0.05);font-family:sans-serif;">
            <div style="text-align:center;padding:30px 20px 10px;">
                <img src="data:image/png;base64,{logo_base64}" width="70" alt="LifeLine Logo" style="margin-bottom:15px;" />
                <h2 style="font-size:22px;margin:0;color:#222;">New Insurance Request</h2>
            </div>
            <div style="padding:20px 30px;">
                <p style="font-size:15px;color:#444;">Dear Insurance Partner,</p>
                <p style="font-size:15px;color:#444;">
                    We have received a new <strong>{data_type.title()}</strong> insurance interest form via the LifeLine Africa platform.
                    Kindly find the client’s submitted details below:
                </p>
                <table style="width:100%;margin-top:20px;border-collapse:collapse;border-radius:6px;overflow:hidden;background:#fff;">
                    {rows}
                </table>
                <p style="font-size:14px;color:#555;margin-top:30px;">Warm regards,<br><strong>LifeLine Africa Team</strong></p>
            </div>
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
            "j.chukwuony@alustudent.com", "insurer2@example.com", "insurer3@example.com",
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
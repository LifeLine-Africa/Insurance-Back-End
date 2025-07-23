from flask import Flask, request, jsonify, render_template_string, send_file
from flask_sqlalchemy import SQLAlchemy
import os
import uuid
import json
from datetime import datetime
import logging
from typing import Dict, Any, Optional
import io
from reportlab.lib.pagesizes import A4, inch
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
import click
from flask.cli import with_appcontext
from dotenv import load_dotenv
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

load_dotenv()

# Initialize extensions
db = SQLAlchemy()

# Email configuration
SMTP_SERVER = 'smtp.gmail.com'
SMTP_PORT = 465
SMTP_USERNAME = 'J.chukwuony@alustudent.com'
SMTP_PASSWORD = 'ljol rjet wgyg fgbe'

# Email recipients configuration
PRIMARY_RECIPIENTS = [
    "recipient1@example.com",
    "recipient2@example.com",
    "recipient3@example.com",
    "recipient4@example.com",
    "recipient5@example.com"
]
CC_RECIPIENT = "j.chukwuony@alustudent.com"

# === Database Models ===
class InsuranceSubmission(db.Model):
    __tablename__ = 'insurance_submissions'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    submission_type = db.Column(db.String(20), nullable=False)
    submission_data = db.Column(db.JSON, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    email_sent = db.Column(db.Boolean, default=False)
    pdf_generated = db.Column(db.Boolean, default=False)
    
    def __repr__(self):
        return f'<InsuranceSubmission {self.id}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'submission_type': self.submission_type,
            'submission_data': self.submission_data,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'email_sent': self.email_sent,
            'pdf_generated': self.pdf_generated
        }

# === Field Definitions ===
INDIVIDUAL_FIELDS = [
    "Full Name", "Age", "Phone Number", "Email", "Location", "Occupation",
    "Monthly Income Range", "Number Of Dependents", "Existing Medical Conditions",
    "Regular Medications", "Frequency of Hospital Visits", "Preferred Hospitals/Clinics",
    "Family Medical History", "Preferred Monthly Premium Range", "Priority",
    "Specific Coverage Needs", "Preferred Payment Frequency", "International Coverage Needs",
    "Current Insurance", "Past Insurance Claims", "Maternity Coverage Needs",
    "Emergency Services Priority", "Preferred Mode of Healthcare"
]

COMPANY_FIELDS = [
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

logger = logging.getLogger(__name__)

def create_app():
    """Application factory function."""
    app = Flask(__name__)
    
    # Configuration
    app.config.update(
        SQLALCHEMY_DATABASE_URI='sqlite:///' + os.path.join(app.instance_path, 'insurance.db'),
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        SQLALCHEMY_ENGINE_OPTIONS={
            'pool_pre_ping': True,
            'pool_recycle': 300,
        },
        SECRET_KEY=os.getenv('SECRET_KEY', 'your-secret-key-change-in-production')
    )
    
    # Initialize extensions with app
    db.init_app(app)
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s %(levelname)s %(name)s %(message)s'
    )
    
    # Register CLI commands
    app.cli.add_command(init_db_command)
    
    # Register routes
    register_routes(app)
    
    return app

def normalize_field_key(field: str) -> str:
    """Normalize field names to match form data keys."""
    return (field.replace("(", "")
                .replace(")", "")
                .replace("/", "")
                .replace(",", "")
                .replace("  ", " ")
                .replace(" ", "_")
                .lower())

def get_fields_for_type(submission_type: str) -> list:
    """Get field list based on submission type."""
    return INDIVIDUAL_FIELDS if submission_type == "individual" else COMPANY_FIELDS

def validate_submission_data(submission_type: str, data: Dict[str, Any]) -> tuple[bool, str]:
    """Validate submission data."""
    if submission_type not in ["individual", "company"]:
        return False, "Invalid submission type. Must be 'individual' or 'company'."
    
    if not data:
        return False, "Submission data cannot be empty."
    
    required_fields = ["full_name"] if submission_type == "individual" else ["company_name"]
    
    for field in required_fields:
        if not data.get(field):
            return False, f"Required field '{field}' is missing."
    
    return True, ""

def send_email(subject: str, html_content: str, recipients: list, cc: list = None):
    """Send email using SMTP_SSL."""
    msg = MIMEMultipart()
    msg['From'] = f"My Lifeline Africa <{SMTP_USERNAME}>"
    msg['To'] = ", ".join(recipients)
    msg['Subject'] = subject
    
    if cc:
        msg['Cc'] = ", ".join(cc)
        recipients = recipients + cc
    
    msg.attach(MIMEText(html_content, 'html'))
    
    try:
        with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT, timeout=30) as server:
            server.login(SMTP_USERNAME, SMTP_PASSWORD)
            server.send_message(msg)
        logger.info("Email sent successfully")
        return True
    except Exception as e:
        logger.error(f"Failed to send email: {str(e)}")
        return False

def build_email_html_with_data(submission_type: str, data: Dict[str, Any], submission_id: str) -> str:
    """Build HTML email with submission data included."""
    fields = get_fields_for_type(submission_type)
    
    data_rows = ""
    for field in fields:
        field_key = normalize_field_key(field)
        value = data.get(field_key, 'N/A')
        data_rows += f"""
            <tr>
                <td style="padding:12px;font-weight:bold;color:#333;border-bottom:1px solid #eee;background:#f8f9fa;">{field}</td>
                <td style="padding:12px;color:#555;border-bottom:1px solid #eee;">{value}</td>
            </tr>
        """
    
    pdf_link = f"http://localhost:5000/download-pdf/{submission_id}"
    
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Insurance Submission - LifeLine Africa</title>
    </head>
    <body style="margin:0;padding:0;font-family:Arial,sans-serif;background:#f5f5f5;">
        <div style="max-width:700px;margin:20px auto;background:white;border-radius:8px;overflow:hidden;box-shadow:0 4px 6px rgba(0,0,0,0.1);">
    <div style="background:white;padding:20px 30px 15px 30px;text-align:center;">
        <img src="https://i.imgur.com/i6Lfiku.png" width="80" alt="LifeLine Logo" style="display:block;margin:0 auto 5px auto;" />
        <h1 style="color:linear-gradient(135deg,#fea601,#ff8c00);margin:0;font-size:24px;line-height:1.3;">New Insurance Request</h1>
        <p style="linear-gradient(135deg,#fea601,#ff8c00);margin:5px 0 0 0;font-size:14px;">Submission Type: {submission_type.title()}</p>
    </div>
            <div style="padding:30px;">
                <p style="color:#555;margin-bottom:25px;font-size:16px;">
                    A new {submission_type} insurance request has been submitted via LifeLine Africa. 
                    Please find the details below:
                </p>
                <table style="width:100%;border-collapse:collapse;margin:20px 0;border:1px solid #eee;border-radius:6px;overflow:hidden;">
                    {data_rows}
                </table>
                <div style="text-align:center;margin:30px 0;">
                    <a href="{pdf_link}" 
                       style="display:inline-block;margin:0 10px;padding:12px 25px;background:#fea601;color:white;text-decoration:none;border-radius:6px;font-weight:bold;">
                        Download PDF
                    </a>
                </div>
                <div style="background:#f8f9fa;padding:20px;border-radius:6px;margin-top:25px;">
                    <p style="margin:0;color:#666;font-size:14px;">
                        <strong>Submission ID:</strong> {submission_id}<br>
                        <strong>Submitted:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} UTC
                    </p>
                </div>
            </div>
            <div style="background:#f8f9fa;padding:20px;text-align:center;border-top:1px solid #eee;">
                <p style="margin:0;color:#888;font-size:14px;">
                    LifeLine Africa Insurance Services<br>
                    This is an automated notification. Please do not reply to this email.
                </p>
            </div>
        </div>
    </body>
    </html>
    """

class PDFGenerator:
    def __init__(self):
        self.styles = getSampleStyleSheet()
        self.setup_custom_styles()
    
    def setup_custom_styles(self):
        """Setup custom paragraph styles."""
        self.styles.add(ParagraphStyle(
            name='CustomTitle',
            parent=self.styles['Heading1'],
            fontSize=24,
            spaceAfter=30,
            alignment=TA_CENTER,
            textColor=colors.HexColor('#333333')
        ))
        
        self.styles.add(ParagraphStyle(
            name='CustomSubtitle',
            parent=self.styles['Heading2'],
            fontSize=16,
            spaceAfter=20,
            alignment=TA_CENTER,
            textColor=colors.HexColor('#666666')
        ))
    
    def generate_pdf(self, submission_type: str, data: Dict[str, Any], submission_id: str) -> io.BytesIO:
        """Generate PDF document for submission."""
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=18
        )
        
        story = []
        
        try:
            logo_url = "https://i.imgur.com/i6Lfiku.png"
        except:
            pass
        
        title = Paragraph(f"{submission_type.title()} Insurance Submission", self.styles['CustomTitle'])
        story.append(title)
        
        subtitle = Paragraph(f"Submission ID: {submission_id}", self.styles['CustomSubtitle'])
        story.append(subtitle)
        
        date_para = Paragraph(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} UTC", self.styles['Normal'])
        story.append(date_para)
        story.append(Spacer(1, 30))
        
        fields = get_fields_for_type(submission_type)
        table_data = [['Field', 'Value']]
        
        for field in fields:
            field_key = normalize_field_key(field)
            value = str(data.get(field_key, 'N/A'))
            table_data.append([field, value])
        
        table = Table(table_data, colWidths=[3*inch, 4*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#fea601')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTNAME', (0, 1), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (1, 1), (1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 10),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey])
        ]))
        
        story.append(table)
        story.append(Spacer(1, 30))
        
        footer = Paragraph("Generated by LifeLine Africa Insurance Services", self.styles['Normal'])
        story.append(footer)
        
        doc.build(story)
        buffer.seek(0)
        return buffer

def register_routes(app):
    @app.route("/submit", methods=["POST"])
    def submit():
        """Handle insurance submission with email, PDF, and database storage."""
        try:
            content = request.json
            submission_type = content.get("type")
            data = content.get("data")
            
            is_valid, error_message = validate_submission_data(submission_type, data)
            if not is_valid:
                return jsonify({"error": error_message}), 400
            
            # Save to database
            submission = InsuranceSubmission(
                submission_type=submission_type,
                submission_data=data
            )
            db.session.add(submission)
            db.session.commit()
            
            # Generate and send email with data
            email_html = build_email_html_with_data(submission_type, data, submission.id)
            
            email_sent = send_email(
                subject=f"New {submission_type.title()} Insurance Request - {submission.id[:8]}",
                html_content=email_html,
                recipients=PRIMARY_RECIPIENTS,
                cc=[CC_RECIPIENT]
            )
            
            if email_sent:
                submission.email_sent = True
                db.session.commit()
            
            logger.info(f"Submission {submission.id} processed successfully")
            
            return jsonify({
                "message": "Submission processed successfully!",
                "submission_id": submission.id,
                "pdf_download_url": f"/download-pdf/{submission.id}",
                "view_url": f"/submission/{submission.id}"
            }), 200
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error processing submission: {str(e)}")
            return jsonify({"error": "Internal server error occurred"}), 500

    @app.route("/download-pdf/<submission_id>")
    def download_pdf(submission_id):
        """Download PDF for a submission."""
        submission = InsuranceSubmission.query.get_or_404(submission_id)
        
        if not submission.pdf_generated:
            pdf_generator = PDFGenerator()
            pdf_buffer = pdf_generator.generate_pdf(
                submission.submission_type,
                submission.submission_data,
                submission_id
            )
            
            # Store the PDF in the database or filesystem in a real app
            # For this example, we'll just mark it as generated
            submission.pdf_generated = True
            db.session.commit()
            
            return send_file(
                pdf_buffer,
                as_attachment=True,
                download_name=f"insurance_submission_{submission_id}.pdf",
                mimetype='application/pdf'
            )
        
        # In a real app, you would retrieve the stored PDF here
        return "PDF not yet generated", 404

    @app.route("/submission/<submission_id>")
    def view_submission(submission_id):
        """View submission details in HTML."""
        submission = InsuranceSubmission.query.get_or_404(submission_id)
        fields = get_fields_for_type(submission.submission_type)
        
        return render_template_string('''
            <!DOCTYPE html>
            <html>
            <head>
                <title>Submission {{ submission.id }}</title>
                <style>
                    body { font-family: Arial, sans-serif; margin: 20px; }
                    h1 { color: #333; }
                    table { border-collapse: collapse; width: 100%; margin-top: 20px; }
                    th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
                    th { background-color: #f2f2f2; }
                </style>
            </head>
            <body>
                <h1>{{ submission.submission_type|title }} Insurance Submission</h1>
                <p>Submission ID: {{ submission.id }}</p>
                <p>Submitted: {{ submission.created_at }}</p>
                
                <table>
                    <tr>
                        <th>Field</th>
                        <th>Value</th>
                    </tr>
                    {% for field in fields %}
                    <tr>
                        <td>{{ field }}</td>
                        <td>{{ submission.submission_data.get(field.lower().replace(' ', '_'), 'N/A') }}</td>
                    </tr>
                    {% endfor %}
                </table>
                
                <p><a href="/download-pdf/{{ submission.id }}">Download PDF</a></p>
            </body>
            </html>
        ''', submission=submission, fields=fields)

    @app.route("/")
    def index():
        """Show a simple welcome page."""
        return """
            <h1>LifeLine Africa Insurance Services</h1>
            <p>Welcome to the insurance submission API.</p>
        """

@click.command("init-db")
@with_appcontext
def init_db_command():
    """Initialize the database."""
    db.create_all()
    click.echo("Initialized the database.")

if __name__ == "__main__":
    app = create_app()
    
    # Create tables if they don't exist
    with app.app_context():
        db.create_all()
    
    app.run(
        debug=os.getenv('FLASK_ENV') == 'development',
        host='0.0.0.0',
        port=int(os.getenv('PORT', 5000))
    )
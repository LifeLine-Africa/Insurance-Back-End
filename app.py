from flask import Flask, request, jsonify, render_template_string, send_file
from flask_mail import Mail, Message
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash
import os
import uuid
import json
from datetime import datetime
import logging
from typing import Dict, Any, Optional
import io
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.pdfgen import canvas
import base64
import urllib.request

# === Application Configuration ===
app = Flask(__name__)

# Database Configuration
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv(
    'DATABASE_URL', 
    'postgresql://username:password@server.postgres.database.azure.com:5432/database_name'
)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'pool_pre_ping': True,
    'pool_recycle': 300,
}

# Email Configuration
app.config.update(
    MAIL_SERVER='smtp.gmail.com',
    MAIL_PORT=587,
    MAIL_USE_TLS=True,
    MAIL_USERNAME=os.getenv('MAIL_USERNAME', 'Justiceofficial0010@gmail.com'),
    MAIL_PASSWORD=os.getenv('MAIL_PASSWORD', 'zogo itjd vjdr yshl'),
    MAIL_DEFAULT_SENDER=('My Lifeline Africa', os.getenv('MAIL_USERNAME', 'Justiceofficial0010@gmail.com'))
)

# Security Configuration
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'your-secret-key-change-in-production')

# Initialize Extensions
db = SQLAlchemy(app)
mail = Mail(app)

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(name)s %(message)s'
)
logger = logging.getLogger(__name__)

# === Database Models ===
class InsuranceSubmission(db.Model):
    __tablename__ = 'insurance_submissions'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    submission_type = db.Column(db.String(20), nullable=False)  # 'individual' or 'company'
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

# === Utility Functions ===
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
    
    # Add more specific validation as needed
    required_fields = ["full_name"] if submission_type == "individual" else ["company_name"]
    
    for field in required_fields:
        if not data.get(field):
            return False, f"Required field '{field}' is missing."
    
    return True, ""

# === Email HTML Generation ===
def build_email_html_with_data(submission_type: str, data: Dict[str, Any], submission_id: str) -> str:
    """Build HTML email with submission data included."""
    fields = get_fields_for_type(submission_type)
    
    # Build data rows
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
    
    # PDF download link
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
            
            <!-- Header -->
            <div style="background:linear-gradient(135deg,#fea601,#ff8c00);padding:30px;text-align:center;">
                <img src="https://i.imgur.com/i6Lfiku.png" width="80" alt="LifeLine Logo" style="margin-bottom:15px;" />
                <h1 style="color:white;margin:0;font-size:24px;">New Insurance Request</h1>
                <p style="color:rgba(255,255,255,0.9);margin:10px 0 0 0;">Submission Type: {submission_type.title()}</p>
            </div>
            
            <!-- Content -->
            <div style="padding:30px;">
                <p style="color:#555;margin-bottom:25px;font-size:16px;">
                    A new {submission_type} insurance request has been submitted via LifeLine Africa. 
                    Please find the details below:
                </p>
                
                <!-- Data Table -->
                <table style="width:100%;border-collapse:collapse;margin:20px 0;border:1px solid #eee;border-radius:6px;overflow:hidden;">
                    {data_rows}
                </table>
                
                <!-- Action Buttons -->
                <div style="text-align:center;margin:30px 0;">
                    <a href="{pdf_link}" 
                       style="display:inline-block;margin:0 10px;padding:12px 25px;background:#fea601;color:white;text-decoration:none;border-radius:6px;font-weight:bold;">
                        📄 Download PDF
                    </a>
                    <a href="http://localhost:5000/submission/{submission_id}" 
                       style="display:inline-block;margin:0 10px;padding:12px 25px;background:#28a745;color:white;text-decoration:none;border-radius:6px;font-weight:bold;">
                        👁️ View Online
                    </a>
                </div>
                
                <!-- Submission Info -->
                <div style="background:#f8f9fa;padding:20px;border-radius:6px;margin-top:25px;">
                    <p style="margin:0;color:#666;font-size:14px;">
                        <strong>Submission ID:</strong> {submission_id}<br>
                        <strong>Submitted:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} UTC
                    </p>
                </div>
            </div>
            
            <!-- Footer -->
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

# === PDF Generation ===
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
        
        # Build document content
        story = []
        
        # Header with logo (if available)
        try:
            # You can replace this with a local logo file path
            logo_url = "https://i.imgur.com/i6Lfiku.png"
            # For production, store logo locally and use file path
            # logo = Image(logo_path, width=2*inch, height=1*inch)
            # story.append(logo)
            # story.append(Spacer(1, 20))
        except:
            pass
        
        # Title
        title = Paragraph(f"{submission_type.title()} Insurance Submission", self.styles['CustomTitle'])
        story.append(title)
        
        # Submission info
        subtitle = Paragraph(f"Submission ID: {submission_id}", self.styles['CustomSubtitle'])
        story.append(subtitle)
        
        date_para = Paragraph(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} UTC", self.styles['Normal'])
        story.append(date_para)
        story.append(Spacer(1, 30))
        
        # Data table
        fields = get_fields_for_type(submission_type)
        table_data = [['Field', 'Value']]  # Header row
        
        for field in fields:
            field_key = normalize_field_key(field)
            value = str(data.get(field_key, 'N/A'))
            table_data.append([field, value])
        
        # Create table
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
        
        # Footer
        footer = Paragraph("Generated by LifeLine Africa Insurance Services", self.styles['Normal'])
        story.append(footer)
        
        # Build PDF
        doc.build(story)
        buffer.seek(0)
        return buffer

# === Database Operations ===
class DatabaseService:
    @staticmethod
    def save_submission(submission_type: str, data: Dict[str, Any]) -> str:
        """Save submission to database."""
        try:
            submission = InsuranceSubmission(
                submission_type=submission_type,
                submission_data=data
            )
            db.session.add(submission)
            db.session.commit()
            logger.info(f"Submission saved with ID: {submission.id}")
            return submission.id
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error saving submission: {str(e)}")
            raise
    
    @staticmethod
    def get_submission(submission_id: str) -> Optional[InsuranceSubmission]:
        """Retrieve submission by ID."""
        try:
            return InsuranceSubmission.query.get(submission_id)
        except Exception as e:
            logger.error(f"Error retrieving submission {submission_id}: {str(e)}")
            return None
    
    @staticmethod
    def update_submission_status(submission_id: str, email_sent: bool = None, pdf_generated: bool = None):
        """Update submission status flags."""
        try:
            submission = InsuranceSubmission.query.get(submission_id)
            if submission:
                if email_sent is not None:
                    submission.email_sent = email_sent
                if pdf_generated is not None:
                    submission.pdf_generated = pdf_generated
                submission.updated_at = datetime.utcnow()
                db.session.commit()
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error updating submission status: {str(e)}")

# === API Routes ===
@app.route("/submit", methods=["POST"])
def submit():
    """Handle insurance submission with email, PDF, and database storage."""
    try:
        content = request.json
        submission_type = content.get("type")
        data = content.get("data")
        
        # Validate input
        is_valid, error_message = validate_submission_data(submission_type, data)
        if not is_valid:
            return jsonify({"error": error_message}), 400
        
        # Save to database
        submission_id = DatabaseService.save_submission(submission_type, data)
        
        # Generate and send email with data
        email_html = build_email_html_with_data(submission_type, data, submission_id)
        
        msg = Message(
            subject=f"New {submission_type.title()} Insurance Request - {submission_id[:8]}",
            recipients=[
                "j.chukwuony@alustudent.com"
                # "kingdavidscloud@gmail.com"
            ],
            cc=["cc_insurer@example.com"],
            html=email_html
        )
        
        # Send email
        mail.send(msg)
        DatabaseService.update_submission_status(submission_id, email_sent=True)
        
        logger.info(f"Submission {submission_id} processed successfully")
        
        return jsonify({
            "message": "Submission processed successfully!",
            "submission_id": submission_id,
            "pdf_download_url": f"/download-pdf/{submission_id}",
            "view_url": f"/submission/{submission_id}"
        }), 200
        
    except Exception as e:
        logger.error(f"Error processing submission: {str(e)}")
        return jsonify({"error": "Internal server error occurred"}), 500

@app.route("/submission/<submission_id>")
def view_submission(submission_id: str):
    """View submission details online."""
    submission = DatabaseService.get_submission(submission_id)
    if not submission:
        return "<h2 style='color:red;text-align:center;'>Submission not found.</h2>", 404
    
    # Generate HTML view
    fields = get_fields_for_type(submission.submission_type)
    rows = ""
    
    for field in fields:
        field_key = normalize_field_key(field)
        value = submission.submission_data.get(field_key, 'N/A')
        rows += f"""
            <tr>
                <td style='padding:12px;font-weight:bold;color:#333;border-bottom:1px solid #eee;background:#f8f9fa;'>{field}</td>
                <td style='padding:12px;color:#555;border-bottom:1px solid #eee;'>{value}</td>
            </tr>
        """
    
    html_template = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Submission Details - LifeLine Africa</title>
    </head>
    <body style="font-family:Arial,sans-serif;background:#f5f5f5;margin:0;padding:20px;">
        <div style="max-width:800px;margin:auto;background:white;border-radius:8px;overflow:hidden;box-shadow:0 4px 6px rgba(0,0,0,0.1);">
            <div style="background:linear-gradient(135deg,#fea601,#ff8c00);padding:30px;text-align:center;">
                <img src="https://i.imgur.com/i6Lfiku.png" width="80" alt="LifeLine Logo" style="margin-bottom:15px;" />
                <h1 style="color:white;margin:0;font-size:24px;">{submission.submission_type.title()} Insurance Submission</h1>
                <p style="color:rgba(255,255,255,0.9);margin:10px 0 0 0;">Submission ID: {submission_id}</p>
            </div>
            <div style="padding:30px;">
                <table style="width:100%;border-collapse:collapse;border:1px solid #eee;border-radius:6px;overflow:hidden;">
                    {rows}
                </table>
                <div style="text-align:center;margin-top:30px;">
                    <a href="/download-pdf/{submission_id}" 
                       style="display:inline-block;padding:12px 25px;background:#fea601;color:white;text-decoration:none;border-radius:6px;font-weight:bold;">
                        📄 Download PDF
                    </a>
                </div>
                <div style="background:#f8f9fa;padding:20px;border-radius:6px;margin-top:25px;">
                    <p style="margin:0;color:#666;font-size:14px;">
                        <strong>Submitted:</strong> {submission.created_at.strftime('%Y-%m-%d %H:%M:%S')} UTC<br>
                        <strong>Email Sent:</strong> {'Yes' if submission.email_sent else 'No'}<br>
                        <strong>PDF Generated:</strong> {'Yes' if submission.pdf_generated else 'No'}
                    </p>
                </div>
            </div>
        </div>
    </body>
    </html>
    """
    
    return render_template_string(html_template)

@app.route("/download-pdf/<submission_id>")
def download_pdf(submission_id: str):
    """Generate and download PDF for submission."""
    submission = DatabaseService.get_submission(submission_id)
    if not submission:
        return jsonify({"error": "Submission not found"}), 404
    
    try:
        # Generate PDF
        pdf_generator = PDFGenerator()
        pdf_buffer = pdf_generator.generate_pdf(
            submission.submission_type,
            submission.submission_data,
            submission_id
        )
        
        # Update database status
        DatabaseService.update_submission_status(submission_id, pdf_generated=True)
        
        # Return PDF file
        return send_file(
            pdf_buffer,
            as_attachment=True,
            download_name=f"insurance_submission_{submission_id[:8]}.pdf",
            mimetype='application/pdf'
        )
        
    except Exception as e:
        logger.error(f"Error generating PDF for {submission_id}: {str(e)}")
        return jsonify({"error": "Error generating PDF"}), 500

@app.route("/submissions", methods=["GET"])
def list_submissions():
    """List all submissions (for admin purposes)."""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        
        submissions = InsuranceSubmission.query.paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        return jsonify({
            "submissions": [sub.to_dict() for sub in submissions.items],
            "total": submissions.total,
            "pages": submissions.pages,
            "current_page": page
        })
        
    except Exception as e:
        logger.error(f"Error listing submissions: {str(e)}")
        return jsonify({"error": "Error retrieving submissions"}), 500

@app.route("/health")
def health_check():
    """Health check endpoint."""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "database": "connected" if db.engine.pool.checked_in() > 0 else "disconnected"
    })

# === Error Handlers ===
@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Not found"}), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return jsonify({"error": "Internal server error"}), 500

# === Database Initialization ===
def init_db():
    """Initialize database tables."""
    try:
        db.create_all()
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Error creating database tables: {str(e)}")

# === Application Startup ===
if __name__ == "__main__":
    with app.app_context():
        init_db()
    
    # Run the application
    app.run(
        debug=os.getenv('FLASK_ENV') == 'development',
        host='0.0.0.0',
        port=int(os.getenv('PORT', 5000))
    )
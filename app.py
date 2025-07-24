from flask import Flask, request, jsonify, render_template_string, send_file
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
import os
import uuid
import json
from datetime import datetime, timezone
import logging
from typing import Dict, Any, Optional, List
import io
from reportlab.lib.pagesizes import A4, inch
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
import click
from flask.cli import with_appcontext
from dotenv import load_dotenv
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
import requests
import urllib.request
from PIL import Image as PILImage

load_dotenv()

# Initialize extensions
db = SQLAlchemy()

# Email configuration
SMTP_SERVER = 'smtp.gmail.com'
SMTP_PORT = 465
SMTP_USERNAME = 'SMTP_USERNAME'
SMTP_PASSWORD = 'SMTP_PASSWORD'

# Email recipients configuration (5 primary recipients + CC)
PRIMARY_RECIPIENTS = [
    "admin@lifelineafrica.com",
    "operations@lifelineafrica.com", 
    "underwriting@lifelineafrica.com",
    "customer.service@lifelineafrica.com",
    "kingdavidscloud@gmail.com "
]
CC_RECIPIENT = "justiceofficial0010@gmail.com"

# Brand configuration
LOGO_URL = "https://i.imgur.com/i6Lfiku.png"
BRAND_COLOR = "#fea601"
BRAND_COLOR_SECONDARY = "#ff8c00"

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
    pdf_path = db.Column(db.String(255), nullable=True)
    
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
    "Contact Phone Number", "Company Address", "Registration Number", "Years in Operation",
    "Annual Revenue", "Employee Categories", "Previous Claims History", "Risk Assessment Details",
    "Safety Protocols", "Compliance Certifications", "Coverage Type", "Coverage Amount",
    "Policy Duration", "Deductible Amount", "Additional Benefits", "Special Requirements"
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
        SECRET_KEY=os.getenv('SECRET_KEY', 'your-secret-key-change-in-production'),
        MAX_CONTENT_LENGTH=16 * 1024 * 1024  # 16MB max file size
    )
    
    # Create instance folder if it doesn't exist
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass
    
    # Initialize extensions with app
    db.init_app(app)
    migrate = Migrate(app, db)
    
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

def get_fields_for_type(submission_type: str) -> List[str]:
    """Get field list based on submission type."""
    return INDIVIDUAL_FIELDS if submission_type == "individual" else COMPANY_FIELDS

def validate_submission_data(submission_type: str, data: Dict[str, Any]) -> tuple[bool, str]:
    """Validate submission data."""
    if submission_type not in ["individual", "company"]:
        return False, "Invalid submission type. Must be 'individual' or 'company'."
    
    if not data:
        return False, "Submission data cannot be empty."
    
    # Define required fields based on type
    if submission_type == "individual":
        required_fields = ["full_name", "email", "phone_number"]
    else:
        required_fields = ["company_name", "contact_email", "contact_phone_number"]
    
    for field in required_fields:
        if not data.get(field, '').strip():
            return False, f"Required field '{field}' is missing or empty."
    
    # Email validation
    email_field = "email" if submission_type == "individual" else "contact_email"
    email = data.get(email_field, '').strip()
    if email and '@' not in email:
        return False, f"Invalid email format in field: {email_field}"
    
    return True, ""

def send_email_with_attachment(subject: str, html_content: str, recipients: List[str], 
                              cc: List[str] = None, pdf_attachment: Optional[io.BytesIO] = None) -> bool:
    """Send email with PDF attachment using SMTP_SSL."""
    
    # Ensure CC recipient is always included
    if not cc:
        cc = []
    if CC_RECIPIENT not in cc:
        cc.append(CC_RECIPIENT)
    
    msg = MIMEMultipart('mixed')
    msg['From'] = f"LifeLine Africa Insurance <{SMTP_USERNAME}>"
    msg['To'] = ", ".join(recipients)
    msg['Subject'] = subject
    
    all_recipients = recipients[:]
    if cc:
        msg['Cc'] = ", ".join(cc)
        all_recipients.extend(cc)
    
    # Attach HTML content
    msg.attach(MIMEText(html_content, 'html', 'utf-8'))
    
    # Attach PDF if provided
    if pdf_attachment:
        pdf_attachment.seek(0)
        part = MIMEApplication(
            pdf_attachment.read(),
            Name=f"insurance_submission_{datetime.now().date()}.pdf"
        )
        part['Content-Disposition'] = f'attachment; filename="insurance_submission_{datetime.now().date()}.pdf"'
        msg.attach(part)
    
    try:
        with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT, timeout=30) as server:
            server.login(SMTP_USERNAME, SMTP_PASSWORD)
            server.send_message(msg, to_addrs=all_recipients)
        
        logger.info(f"Email sent successfully to {len(recipients)} primary recipients and {len(cc)} CC recipients")
        logger.info(f"Primary recipients: {', '.join(recipients)}")
        logger.info(f"CC recipients: {', '.join(cc)}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to send email: {str(e)}")
        return False

def build_email_html_with_data(submission_type: str, data: Dict[str, Any], submission_id: str) -> str:
    """Build professional HTML email with submission data using brand styling."""
    fields = get_fields_for_type(submission_type)
    
    data_rows = ""
    for field in fields:
        field_key = normalize_field_key(field)
        value = str(data.get(field_key, 'N/A'))
        # Truncate long values for email display
        if len(value) > 100:
            value = value[:97] + "..."
        
        data_rows += f"""
            <tr>
                <td style="padding:12px;font-weight:bold;color:#333;border-bottom:1px solid #eee;background:#f8f9fa;width:40%;">{field}</td>
                <td style="padding:12px;color:#555;border-bottom:1px solid #eee;width:60%;">{value}</td>
            </tr>
        """
    
    pdf_link = f"http://localhost:5000/download-pdf/{submission_id}"
    view_link = f"http://localhost:5000/submission/{submission_id}"
    
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Insurance Submission - LifeLine Africa</title>
    </head>
    <body style="margin:0;padding:0;font-family:Arial,sans-serif;background:#f5f5f5;">
        <div style="max-width:800px;margin:20px auto;background:white;border-radius:8px;overflow:hidden;box-shadow:0 4px 6px rgba(0,0,0,0.1);">
            <!-- Header with Logo -->
            <div style="background:white;padding:30px;text-align:center;">
                <img src="{LOGO_URL}" width="80" alt="LifeLine Logo" style="display:block;margin:0 auto 15px auto;" />
                <h1 style="color:linear-gradient(135deg,{BRAND_COLOR},{BRAND_COLOR_SECONDARY});margin:0;font-size:28px;line-height:1.3;text-shadow:0 2px 4px rgba(0,0,0,0.3);">New Insurance Request</h1>
                <p style="color:linear-gradient(135deg,{BRAND_COLOR},{BRAND_COLOR_SECONDARY});margin:8px 0 0 0;font-size:16px;">Submission Type: {submission_type.title()}</p>
            </div>
            
            <!-- Content -->
            <div style="padding:40px 30px;">
                <div style="background:linear-gradient(135deg,#f8f9fa,#e9ecef);padding:20px;border-radius:8px;margin-bottom:30px;border-left:4px solid {BRAND_COLOR};">
                    <h2 style="color:#333;margin:0 0 10px 0;font-size:18px;">📋 Submission Details</h2>
                    <p style="color:#666;margin:0;font-size:14px;">
                        <strong>Submission ID:</strong> {submission_id}<br>
                        <strong>Submitted:</strong> {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')} UTC<br>
                        <strong>Type:</strong> {submission_type.title()} Insurance Application
                    </p>
                </div>
                
                <p style="color:#555;margin-bottom:25px;font-size:16px;line-height:1.6;">
                    A new <strong>{submission_type}</strong> insurance request has been submitted via LifeLine Africa Insurance Services. 
                    Please review the complete details below and take appropriate action.
                </p>
                
                <!-- Data Table -->
                <div style="overflow-x:auto;margin:25px 0;">
                    <table style="width:100%;border-collapse:collapse;border:1px solid #ddd;border-radius:8px;overflow:hidden;background:white;">
                        <thead>
                            <tr style="background:linear-gradient(135deg,{BRAND_COLOR},{BRAND_COLOR_SECONDARY});">
                                <th style="padding:15px;color:white;text-align:left;font-size:14px;font-weight:bold;">Field</th>
                                <th style="padding:15px;color:white;text-align:left;font-size:14px;font-weight:bold;">Value</th>
                            </tr>
                        </thead>
                        <tbody>
                            {data_rows}
                        </tbody>
                    </table>
                </div>
                
                <!-- Action Buttons -->
                <div style="text-align:center;margin:40px 0;">
                    <a href="{pdf_link}" 
                       style="display:inline-block;margin:0 10px 10px 10px;padding:15px 30px;background:{BRAND_COLOR};color:white;text-decoration:none;border-radius:6px;font-weight:bold;box-shadow:0 2px 4px rgba(0,0,0,0.2);transition:all 0.2s;">
                        Download PDF
                    </a>
                </div>
                
                <!-- Important Notice -->
                <div style="background:#fff3cd;border:1px solid #ffeaa7;border-radius:6px;padding:15px;margin:25px 0;">
                    <p style="margin:0;color:#856404;font-size:14px;">
                        <strong>⚠️ Action Required:</strong> Please review this submission and contact the applicant within 24-48 hours 
                        to confirm receipt and provide next steps in the application process.
                    </p>
                </div>
            </div>
            
            <!-- Footer -->
            <div style="background:#f8f9fa;padding:25px;text-align:center;border-top:1px solid #eee;">
                <div style="margin-bottom:15px;">
                    <img src="{LOGO_URL}" width="40" alt="LifeLine Logo" style="opacity:0.7;" />
                </div>
                <p style="margin:0;color:#888;font-size:14px;line-height:1.5;">
                    <strong>LifeLine Africa Insurance Services</strong><br>
                    Professional Insurance Solutions | Trusted Coverage<br>
                    This is an automated notification. Please do not reply to this email.
                </p>
                <p style="margin:10px 0 0 0;color:#aaa;font-size:12px;">
                    © {datetime.now().year} LifeLine Africa Insurance Services. All rights reserved.
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
        self.logo_path = self.download_logo()
    
    def download_logo(self) -> Optional[str]:
        """Download and save logo for PDF use."""
        try:
            logo_path = "Logo.png"
            urllib.request.urlretrieve(LOGO_URL, logo_path)
            return logo_path
        except Exception as e:
            logger.warning(f"Could not download logo: {str(e)}")
            return None
    
    def setup_custom_styles(self):
        """Setup custom paragraph styles matching the brand."""
        self.styles.add(ParagraphStyle(
            name='CustomTitle',
            parent=self.styles['Heading1'],
            fontSize=28,
            spaceAfter=20,
            alignment=TA_CENTER,
            textColor=colors.HexColor(BRAND_COLOR),
            fontName='Helvetica-Bold'
        ))
        
        self.styles.add(ParagraphStyle(
            name='CustomSubtitle',
            parent=self.styles['Heading2'],
            fontSize=18,
            spaceAfter=15,
            alignment=TA_CENTER,
            textColor=colors.HexColor('#666666'),
            fontName='Helvetica'
        ))
        
        self.styles.add(ParagraphStyle(
            name='BrandHeader',
            parent=self.styles['Normal'],
            fontSize=12,
            alignment=TA_CENTER,
            textColor=colors.HexColor('#888888'),
            fontName='Helvetica'
        ))
    
    def generate_pdf(self, submission_type: str, data: Dict[str, Any], submission_id: str) -> io.BytesIO:
        """Generate professional PDF document with brand styling."""
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=72,
            leftMargin=72,
            topMargin=50,
            bottomMargin=50,
            title=f"{submission_type.title()} Insurance Submission - LifeLine Africa"
        )
        
        story = []
        
        try:
            # Add Logo
            if self.logo_path and os.path.exists(self.logo_path):
                logo = Image(self.logo_path, width=80, height=80)
                logo.hAlign = 'CENTER'
                story.append(logo)
                story.append(Spacer(1, 20))
        except Exception as e:
            logger.warning(f"Could not add logo to PDF: {str(e)}")
        
        # Header
        company_name = Paragraph("LifeLine Africa Insurance Services", self.styles['BrandHeader'])
        story.append(company_name)
        story.append(Spacer(1, 10))
        
        title = Paragraph(f"{submission_type.title()} Insurance Submission", self.styles['CustomTitle'])
        story.append(title)
        
        subtitle = Paragraph(f"Submission ID: {submission_id}", self.styles['CustomSubtitle'])
        story.append(subtitle)
        
        # Submission info box
        submission_info = f"""
        <para align="center" fontSize="10" textColor="#666666">
        Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')} UTC<br/>
        Document Type: Official Insurance Application<br/>
        Status: Pending Review
        </para>
        """
        story.append(Paragraph(submission_info, self.styles['Normal']))
        story.append(Spacer(1, 30))
        
        # Data table with brand styling
        fields = get_fields_for_type(submission_type)
        table_data = [['Field', 'Value']]
        
        for field in fields:
            field_key = normalize_field_key(field)
            value = str(data.get(field_key, 'N/A'))
            # Handle long values in PDF
            if len(value) > 60:
                # Split long text into multiple lines
                words = value.split(' ')
                lines = []
                current_line = []
                current_length = 0
                
                for word in words:
                    if current_length + len(word) + 1 <= 60:
                        current_line.append(word)
                        current_length += len(word) + 1
                    else:
                        if current_line:
                            lines.append(' '.join(current_line))
                        current_line = [word]
                        current_length = len(word)
                
                if current_line:
                    lines.append(' '.join(current_line))
                
                value = '<br/>'.join(lines)
            
            table_data.append([field, Paragraph(value, self.styles['Normal'])])
        
        # Create professional table
        table = Table(table_data, colWidths=[2.8*inch, 4.2*inch], repeatRows=1)
        table.setStyle(TableStyle([
            # Header styling
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor(BRAND_COLOR)),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 15),
            ('TOPPADDING', (0, 0), (-1, 0), 15),
            
            # Data rows styling
            ('BACKGROUND', (0, 1), (-1, -1), colors.white),
            ('FONTNAME', (0, 1), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (1, 1), (1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 10),
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#CCCCCC')),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 12),
            ('RIGHTPADDING', (0, 0), (-1, -1), 12),
            ('TOPPADDING', (0, 1), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 10),
            
            # Alternating row colors
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F8F9FA')])
        ]))
        
        story.append(table)
        story.append(Spacer(1, 40))
        
        # Footer with branding
        footer_text = f"""
        <para align="center" fontSize="10" textColor="#888888">
        <b>LifeLine Africa Insurance Services</b><br/>
        Professional Insurance Solutions | Trusted Coverage<br/>
        This document was generated automatically on {datetime.now().strftime('%Y-%m-%d at %H:%M:%S')} UTC<br/>
        For inquiries, please contact our customer service team.
        </para>
        """
        story.append(Paragraph(footer_text, self.styles['Normal']))
        
        story.append(Spacer(1, 20))
        
        copyright_text = f"""
        <para align="center" fontSize="8" textColor="#AAAAAA">
        © {datetime.now().year} LifeLine Africa Insurance Services. All rights reserved.<br/>
        This document contains confidential information and is intended solely for the addressee.
        </para>
        """
        story.append(Paragraph(copyright_text, self.styles['Normal']))
        
        # Build PDF
        doc.build(story)
        buffer.seek(0)
        
        # Clean up temp logo file
        if self.logo_path and os.path.exists(self.logo_path):
            try:
                os.remove(self.logo_path)
            except Exception:
                pass
        
        return buffer

def register_routes(app):
    @app.route("/health")
    def health_check():
        """Health check endpoint with email configuration status."""
        try:
            # Test database connection
            db.session.execute('SELECT 1')
            
            return jsonify({
                "status": "healthy",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "database": "connected",
                "email_configured": True,
                "email_recipients": {
                    "primary_recipients": len(PRIMARY_RECIPIENTS),
                    "cc_recipients": 1,
                    "total_recipients": len(PRIMARY_RECIPIENTS) + 1,
                    "j_chukwuony_cc": CC_RECIPIENT in [CC_RECIPIENT]
                },
                "version": "2.0.0"
            }), 200
            
        except Exception as e:
            logger.error(f"Health check failed: {str(e)}")
            return jsonify({
                "status": "unhealthy",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "database": "disconnected",
                "error": str(e)
            }), 500

    @app.route("/submit", methods=["POST"])
    def submit():
        """Handle insurance submission with enhanced email, PDF, and database storage."""
        request_id = str(uuid.uuid4())[:8]
        logger.info(f"[{request_id}] Processing new submission")
        
        try:
            if not request.is_json:
                return jsonify({"error": "Content-Type must be application/json"}), 400
            
            content = request.json
            if not content:
                return jsonify({"error": "Request body cannot be empty"}), 400
            
            submission_type = content.get("type", "").strip().lower()
            data = content.get("data", {})
            
            # Validate submission data
            is_valid, error_message = validate_submission_data(submission_type, data)
            if not is_valid:
                logger.warning(f"[{request_id}] Validation failed: {error_message}")
                return jsonify({"error": error_message}), 400
            
            # Save to database
            submission = InsuranceSubmission(
                submission_type=submission_type,
                submission_data=data
            )
            db.session.add(submission)
            db.session.commit()
            
            logger.info(f"[{request_id}] Submission {submission.id} saved to database")
            
            # Generate PDF
            pdf_generator = PDFGenerator()
            pdf_buffer = pdf_generator.generate_pdf(submission_type, data, submission.id)
            
            # Save PDF path (in production, you'd save to file system or cloud storage)
            pdf_filename = f"insurance_submission_{submission.id}.pdf"
            pdf_path = os.path.join(app.instance_path, 'pdfs', pdf_filename)
            
            # Create PDFs directory if it doesn't exist
            os.makedirs(os.path.dirname(pdf_path), exist_ok=True)
            
            # Save PDF to file
            with open(pdf_path, 'wb') as f:
                f.write(pdf_buffer.getvalue())
            
            submission.pdf_generated = True
            submission.pdf_path = pdf_path
            db.session.commit()
            
            logger.info(f"[{request_id}] PDF generated and saved for submission {submission.id}")
            
            # Generate and send email with data and PDF attachment
            email_html = build_email_html_with_data(submission_type, data, submission.id)
            
            # Reset buffer for email attachment
            pdf_buffer.seek(0)
            
            email_sent = send_email_with_attachment(
                subject=f"New {submission_type.title()} Insurance Request - {submission.id[:8]}",
                html_content=email_html,
                recipients=PRIMARY_RECIPIENTS,
                cc=[CC_RECIPIENT],
                pdf_attachment=pdf_buffer
            )
            
            if email_sent:
                submission.email_sent = True
                db.session.commit()
                logger.info(f"[{request_id}] Email sent successfully for submission {submission.id}")
            else:
                logger.warning(f"[{request_id}] Email sending failed for submission {submission.id}")
            
            # Close PDF buffer
            pdf_buffer.close()
            
            logger.info(f"[{request_id}] Successfully processed submission {submission.id}")
            
            return jsonify({
                "message": "Submission processed successfully!",
                "submission_id": submission.id,
                "request_id": request_id,
                "status": "processed",
                "email_sent": email_sent,
                "pdf_generated": True,
                "links": {
                    "pdf_download": f"/download-pdf/{submission.id}",
                    "view_submission": f"/submission/{submission.id}"
                }
            }), 201
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"[{request_id}] Error processing submission: {str(e)}", exc_info=True)
            return jsonify({
                "error": "Internal server error occurred",
                "request_id": request_id
            }), 500

    @app.route("/download-pdf/<submission_id>")
    def download_pdf(submission_id):
        """Download PDF for a submission with proper error handling."""
        try:
            submission = InsuranceSubmission.query.get_or_404(submission_id)
            
            if not submission.pdf_generated or not submission.pdf_path:
                # Generate PDF on demand if not exists
                pdf_generator = PDFGenerator()
                pdf_buffer = pdf_generator.generate_pdf(
                    submission.submission_type,
                    submission.submission_data,
                    submission_id
                )
                
                return send_file(
                    pdf_buffer,
                    as_attachment=True,
                    download_name=f"insurance_submission_{submission_id[:8]}.pdf",
                    mimetype='application/pdf'
                )
            
            # Serve existing PDF file
            if os.path.exists(submission.pdf_path):
                return send_file(
                    submission.pdf_path,
                    as_attachment=True,
                    download_name=f"insurance_submission_{submission_id[:8]}.pdf",
                    mimetype='application/pdf'
                )
            else:
                return jsonify({"error": "PDF file not found"}), 404
                
        except Exception as e:
            logger.error(f"Error downloading PDF for {submission_id}: {str(e)}")
            return jsonify({"error": "Failed to retrieve PDF"}), 500

    @app.route("/submission/<submission_id>")
    def view_submission(submission_id):
        """View submission details with enhanced HTML template."""
        try:
            submission = InsuranceSubmission.query.get_or_404(submission_id)
            fields = get_fields_for_type(submission.submission_type)
            
            # Build data rows for display
            data_rows = ""
            for field in fields:
                field_key = normalize_field_key(field)
                value = str(submission.submission_data.get(field_key, 'N/A'))
                data_rows += f"""
                    <tr>
                        <td class="field-name">{field}</td>
                        <td class="field-value">{value}</td>
                    </tr>
                """
            
            return render_template_string(f'''
                <!DOCTYPE html>
                <html lang="en">
                <head>
                    <meta charset="UTF-8">
                    <meta name="viewport" content="width=device-width, initial-scale=1.0">
                    <title>Submission {submission.id[:8]} - LifeLine Africa</title>
                    <style>
                        * {{
                            margin: 0;
                            padding: 0;
                            box-sizing: border-box;
                        }}
                        
                        body {{
                            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                            background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
                            min-height: 100vh;
                            padding: 20px;
                        }}
                        
                        .container {{
                            max-width: 1000px;
                            margin: 0 auto;
                            background: white;
                            border-radius: 12px;
                            box-shadow: 0 10px 30px rgba(0,0,0,0.1);
                            overflow: hidden;
                        }}
                        
                        .header {{
                            background: linear-gradient(135deg, {BRAND_COLOR}, {BRAND_COLOR_SECONDARY});
                            color: white;
                            padding: 40px 30px;
                            text-align: center;
                            position: relative;
                        }}
                        
                        .header::before {{
                            content: '';
                            position: absolute;
                            top: 0;
                            left: 0;
                            right: 0;
                            bottom: 0;
                            background: rgba(0,0,0,0.1);
                            background-image: 
                                radial-gradient(circle at 20% 50%, rgba(255,255,255,0.1) 0%, transparent 50%),
                                radial-gradient(circle at 80% 20%, rgba(255,255,255,0.1) 0%, transparent 50%);
                        }}
                        
                        .header-content {{
                            position: relative;
                            z-index: 1;
                        }}
                        
                        .logo {{
                            width: 80px;
                            height: 80px;
                            margin: 0 auto 20px;
                            display: block;
                            border-radius: 50%;
                            box-shadow: 0 4px 15px rgba(0,0,0,0.2);
                        }}
                        
                        .title {{
                            font-size: 32px;
                            font-weight: bold;
                            margin-bottom: 10px;
                            text-shadow: 0 2px 4px rgba(0,0,0,0.3);
                        }}
                        
                        .subtitle {{
                            font-size: 18px;
                            opacity: 0.9;
                            margin-bottom: 5px;
                        }}
                        
                        .submission-id {{
                            font-size: 14px;
                            opacity: 0.8;
                            font-family: 'Courier New', monospace;
                        }}
                        
                        .content {{
                            padding: 40px 30px;
                        }}
                        
                        .info-card {{
                            background: linear-gradient(135deg, #f8f9fa, #e9ecef);
                            border-left: 4px solid {BRAND_COLOR};
                            border-radius: 8px;
                            padding: 20px;
                            margin-bottom: 30px;
                        }}
                        
                        .info-card h3 {{
                            color: #333;
                            margin-bottom: 10px;
                            font-size: 18px;
                        }}
                        
                        .info-grid {{
                            display: grid;
                            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                            gap: 15px;
                            margin-top: 15px;
                        }}
                        
                        .info-item {{
                            background: white;
                            padding: 15px;
                            border-radius: 6px;
                            border: 1px solid #e9ecef;
                        }}
                        
                        .info-label {{
                            font-size: 12px;
                            color: #666;
                            text-transform: uppercase;
                            letter-spacing: 0.5px;
                            margin-bottom: 5px;
                        }}
                        
                        .info-value {{
                            font-size: 14px;
                            color: #333;
                            font-weight: 600;
                        }}
                        
                        .data-table {{
                            width: 100%;
                            border-collapse: collapse;
                            margin: 20px 0;
                            background: white;
                            border-radius: 8px;
                            overflow: hidden;
                            box-shadow: 0 2px 10px rgba(0,0,0,0.05);
                        }}
                        
                        .data-table thead {{
                            background: linear-gradient(135deg, {BRAND_COLOR}, {BRAND_COLOR_SECONDARY});
                        }}
                        
                        .data-table th {{
                            color: white;
                            padding: 20px 15px;
                            text-align: left;
                            font-weight: bold;
                            font-size: 14px;
                            text-transform: uppercase;
                            letter-spacing: 0.5px;
                        }}
                        
                        .field-name {{
                            padding: 15px;
                            font-weight: 600;
                            color: #333;
                            background: #f8f9fa;
                            border-bottom: 1px solid #e9ecef;
                            width: 40%;
                        }}
                        
                        .field-value {{
                            padding: 15px;
                            color: #555;
                            border-bottom: 1px solid #e9ecef;
                            word-break: break-word;
                        }}
                        
                        .data-table tbody tr:hover {{
                            background: #f1f3f4;
                            transition: background 0.2s ease;
                        }}
                        
                        .actions {{
                            text-align: center;
                            margin: 40px 0;
                        }}
                        
                        .btn {{
                            display: inline-block;
                            padding: 15px 30px;
                            margin: 0 10px 10px 0;
                            text-decoration: none;
                            border-radius: 8px;
                            font-weight: bold;
                            font-size: 14px;
                            transition: all 0.3s ease;
                            text-transform: uppercase;
                            letter-spacing: 0.5px;
                            box-shadow: 0 4px 15px rgba(0,0,0,0.1);
                        }}
                        
                        .btn-primary {{
                            background: linear-gradient(135deg, {BRAND_COLOR}, {BRAND_COLOR_SECONDARY});
                            color: white;
                        }}
                        
                        .btn-primary:hover {{
                            transform: translateY(-2px);
                            box-shadow: 0 6px 20px rgba(254,166,1,0.3);
                        }}
                        
                        .btn-secondary {{
                            background: #6c757d;
                            color: white;
                        }}
                        
                        .btn-secondary:hover {{
                            background: #5a6268;
                            transform: translateY(-2px);
                            box-shadow: 0 6px 20px rgba(108,117,125,0.3);
                        }}
                        
                        .footer {{
                            background: #f8f9fa;
                            padding: 30px;
                            text-align: center;
                            border-top: 1px solid #e9ecef;
                        }}
                        
                        .footer-logo {{
                            width: 40px;
                            height: 40px;
                            opacity: 0.7;
                            margin-bottom: 15px;
                        }}
                        
                        .footer-text {{
                            color: #888;
                            font-size: 14px;
                            line-height: 1.6;
                            margin-bottom: 10px;
                        }}
                        
                        .footer-copyright {{
                            color: #aaa;
                            font-size: 12px;
                        }}
                        
                        @media (max-width: 768px) {{
                            .container {{
                                margin: 10px;
                                border-radius: 8px;
                            }}
                            
                            .header {{
                                padding: 30px 20px;
                            }}
                            
                            .title {{
                                font-size: 24px;
                            }}
                            
                            .content {{
                                padding: 30px 20px;
                            }}
                            
                            .data-table {{
                                font-size: 13px;
                            }}
                            
                            .field-name,
                            .field-value {{
                                padding: 12px 10px;
                            }}
                            
                            .btn {{
                                padding: 12px 20px;
                                margin: 5px;
                                display: block;
                                width: calc(100% - 10px);
                            }}
                        }}
                    </style>
                </head>
                <body>
                    <div class="container">
                        <div class="header">
                            <div class="header-content">
                                <img src="{LOGO_URL}" alt="LifeLine Africa Logo" class="logo">
                                <h1 class="title">Insurance Submission</h1>
                                <p class="subtitle">{submission.submission_type.title()} Application</p>
                                <p class="submission-id">ID: {submission.id}</p>
                            </div>
                        </div>
                        
                        <div class="content">
                            <div class="info-card">
                                <h3>Submission Information</h3>
                                <div class="info-grid">
                                    <div class="info-item">
                                        <div class="info-label">Submission Type</div>
                                        <div class="info-value">{submission.submission_type.title()} Insurance</div>
                                    </div>
                                    <div class="info-item">
                                        <div class="info-label">Submitted</div>
                                        <div class="info-value">{submission.created_at.strftime('%Y-%m-%d %H:%M:%S')} UTC</div>
                                    </div>
                                    <div class="info-item">
                                        <div class="info-label">Email Status</div>
                                        <div class="info-value">{'✅ Sent' if submission.email_sent else '❌ Not Sent'}</div>
                                    </div>
                                    <div class="info-item">
                                        <div class="info-label">PDF Status</div>
                                        <div class="info-value">{'✅ Generated' if submission.pdf_generated else '❌ Not Generated'}</div>
                                    </div>
                                </div>
                            </div>
                            
                            <h2 style="color: #333; margin-bottom: 20px; font-size: 24px;">📝 Application Details</h2>
                            
                            <table class="data-table">
                                <thead>
                                    <tr>
                                        <th>Field</th>
                                        <th>Value</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {data_rows}
                                </tbody>
                            </table>
                            
                            <div class="actions">
                                <a href="/download-pdf/{submission.id}" class="btn btn-primary">
                                    Download PDF
                                </a>
                                <a href="/" class="btn btn-secondary">
                                    🏠 Home
                                </a>
                            </div>
                        </div>
                        
                        <div class="footer">
                            <img src="{LOGO_URL}" alt="LifeLine Africa Logo" class="footer-logo">
                            <p class="footer-text">
                                <strong>LifeLine Africa Insurance Services</strong><br>
                                Professional Insurance Solutions | Trusted Coverage
                            </p>
                            <p class="footer-copyright">
                                © {datetime.now().year} LifeLine Africa Insurance Services. All rights reserved.
                            </p>
                        </div>
                    </div>
                </body>
                </html>
            ''', submission=submission, fields=fields)
            
        except Exception as e:
            logger.error(f"Error viewing submission {submission_id}: {str(e)}")
            return jsonify({"error": "Failed to retrieve submission"}), 500

    @app.route("/")
    def index():
        """Enhanced API documentation homepage with brand styling."""
        return render_template_string(f'''
            <!DOCTYPE html>
            <html lang="en">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>LifeLine Africa Insurance Services API</title>
                <style>
                    * {{
                        margin: 0;
                        padding: 0;
                        box-sizing: border-box;
                    }}
                    
                    body {{
                        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                        min-height: 100vh;
                        padding: 20px;
                    }}
                    
                    .container {{
                        max-width: 1200px;
                        margin: 0 auto;
                    }}
                    
                    .hero {{
                        background: white;
                        border-radius: 16px;
                        padding: 60px 40px;
                        text-align: center;
                        box-shadow: 0 20px 60px rgba(0,0,0,0.1);
                        margin-bottom: 40px;
                    }}
                    
                    .logo {{
                        width: 120px;
                        height: 120px;
                        margin: 0 auto 30px;
                        display: block;
                        border-radius: 50%;
                        box-shadow: 0 8px 25px rgba(0,0,0,0.15);
                    }}
                    
                    .hero h1 {{
                        font-size: 48px;
                        color: #333;
                        margin-bottom: 20px;
                        background: linear-gradient(135deg, {BRAND_COLOR}, {BRAND_COLOR_SECONDARY});
                        -webkit-background-clip: text;
                        -webkit-text-fill-color: transparent;
                        background-clip: text;
                    }}
                    
                    .hero p {{
                        font-size: 20px;
                        color: #666;
                        margin-bottom: 40px;
                        line-height: 1.6;
                    }}
                    
                    .stats {{
                        display: grid;
                        grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                        gap: 20px;
                        margin-bottom: 40px;
                    }}
                    
                    .stat {{
                        background: white;
                        border-radius: 12px;
                        padding: 30px;
                        text-align: center;
                        box-shadow: 0 8px 25px rgba(0,0,0,0.1);
                        transition: transform 0.3s ease;
                    }}
                    
                    .stat:hover {{
                        transform: translateY(-5px);
                    }}
                    
                    .stat-icon {{
                        font-size: 48px;
                        margin-bottom: 15px;
                    }}
                    
                    .stat-title {{
                        font-size: 18px;
                        color: #333;
                        margin-bottom: 10px;
                        font-weight: bold;
                    }}
                    
                    .stat-desc {{
                        color: #666;
                        font-size: 14px;
                        line-height: 1.5;
                    }}
                    
                    .endpoints {{
                        background: white;
                        border-radius: 16px;
                        padding: 40px;
                        box-shadow: 0 20px 60px rgba(0,0,0,0.1);
                    }}
                    
                    .endpoints h2 {{
                        font-size: 32px;
                        color: #333;
                        margin-bottom: 30px;
                        text-align: center;
                    }}
                    
                    .endpoint {{
                        border: 1px solid #e9ecef;
                        border-radius: 8px;
                        margin-bottom: 20px;
                        overflow: hidden;
                    }}
                    
                    .endpoint-header {{
                        background: linear-gradient(135deg, #f8f9fa, #e9ecef);
                        padding: 20px;
                        border-bottom: 1px solid #e9ecef;
                    }}
                    
                    .method {{
                        display: inline-block;
                        padding: 6px 12px;
                        border-radius: 4px;
                        font-size: 12px;
                        font-weight: bold;
                        text-transform: uppercase;
                        margin-right: 15px;
                    }}
                    
                    .method.post {{
                        background: #28a745;
                        color: white;
                    }}
                    
                    .method.get {{
                        background: #007bff;
                        color: white;
                    }}
                    
                    .endpoint-url {{
                        font-family: 'Courier New', monospace;
                        font-size: 16px;
                        color: #333;
                        font-weight: bold;
                    }}
                    
                    .endpoint-desc {{
                        padding: 20px;
                        color: #666;
                        line-height: 1.6;
                    }}
                    
                    .footer {{
                        text-align: center;
                        margin-top: 60px;
                        color: rgba(255,255,255,0.8);
                    }}
                    
                    .footer img {{
                        width: 40px;
                        height: 40px;
                        opacity: 0.8;
                        margin-bottom: 15px;
                    }}
                    
                    @media (max-width: 768px) {{
                        .hero {{
                            padding: 40px 20px;
                        }}
                        
                        .hero h1 {{
                            font-size: 32px;
                        }}
                        
                        .endpoints {{
                            padding: 20px;
                        }}
                        
                        .endpoint-header {{
                            padding: 15px;
                        }}
                        
                        .method {{
                            display: block;
                            margin-bottom: 10px;
                            text-align: center;
                        }}
                    }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="hero">
                        <img src="{LOGO_URL}" alt="LifeLine Africa Logo" class="logo">
                        <h1>LifeLine Africa Insurance Services</h1>
                        <p>Professional Insurance API for seamless application processing and management</p>
                    </div>
                    
                    <div class="stats">
                        <div class="stat">
                            <div class="stat-icon"></div>
                            <div class="stat-title">Smart Processing</div>
                            <div class="stat-desc">Automated validation and processing of insurance applications</div>
                        </div>
                        <div class="stat">
                            <div class="stat-icon"></div>
                            <div class="stat-title">Email Notifications</div>
                            <div class="stat-desc">Instant notifications to 5 recipients plus CC to stakeholders</div>
                        </div>
                        <div class="stat">
                            <div class="stat-icon"></div>
                            <div class="stat-title">PDF Generation</div>
                            <div class="stat-desc">Professional PDF documents with branded styling</div>
                        </div>
                        <div class="stat">
                            <div class="stat-icon">🔒</div>
                            <div class="stat-title">Secure & Reliable</div>
                            <div class="stat-desc">Enterprise-grade security with comprehensive error handling</div>
                        </div>
                    </div>
                    
                    <div class="endpoints">
                        <h2>🚀 API Endpoints</h2>
                        
                        <div class="endpoint">
                            <div class="endpoint-header">
                                <span class="method post">POST</span>
                                <span class="endpoint-url">/submit</span>
                            </div>
                            <div class="endpoint-desc">
                                Submit a new insurance application. Supports both individual and company submissions with automatic PDF generation and email notifications.
                            </div>
                        </div>
                        
                        <div class="endpoint">
                            <div class="endpoint-header">
                                <span class="method get">GET</span>
                                <span class="endpoint-url">/download-pdf/&lt;submission_id&gt;</span>
                            </div>
                            <div class="endpoint-desc">
                                Download the generated PDF document for a specific submission with professional branding and formatting.
                            </div>
                        </div>
                        
                        <div class="endpoint">
                            <div class="endpoint-header">
                                <span class="method get">GET</span>
                                <span class="endpoint-url">/submission/&lt;submission_id&gt;</span>
                            </div>
                            <div class="endpoint-desc">
                                View detailed submission information in a beautifully formatted web interface with full application data.
                            </div>
                        </div>
                        
                        <div class="endpoint">
                            <div class="endpoint-header">
                                <span class="method get">GET</span>
                                <span class="endpoint-url">/health</span>
                            </div>
                            <div class="endpoint-desc">
                                Check API health status including database connectivity and email configuration status.
                            </div>
                        </div>
                    </div>
                    
                    <div class="footer">
                        <img src="{LOGO_URL}" alt="LifeLine Africa Logo">
                        <p><strong>LifeLine Africa Insurance Services API v2.0.0</strong></p>
                        <p>© {datetime.now().year} LifeLine Africa Insurance Services. All rights reserved.</p>
                    </div>
                </div>
            </body>
            </html>
        ''')

    @app.errorhandler(404)
    def not_found(error):
        return jsonify({
            "error": "Endpoint not found",
            "message": "The requested resource could not be found on this server.",
            "available_endpoints": ["/", "/submit", "/download-pdf/<id>", "/submission/<id>", "/health"]
        }), 404

    @app.errorhandler(405)
    def method_not_allowed(error):
        return jsonify({
            "error": "Method not allowed",
            "message": "The method is not allowed for the requested URL."
        }), 405

    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        logger.error(f"Internal server error: {str(error)}")
        return jsonify({
            "error": "Internal server error",
            "message": "An unexpected error occurred. Please try again later."
        }), 500

@click.command("init-db")
@with_appcontext
def init_db_command():
    """Initialize the database with proper tables."""
    db.create_all()
    click.echo("✅ Database initialized successfully!")
    click.echo("📊 Tables created:")
    click.echo("   - insurance_submissions")
    click.echo("🚀 API is ready to use!")

if __name__ == "__main__":
    app = create_app()
    
    # Create tables if they don't exist
    with app.app_context():
        db.create_all()
        logger.info("Database tables created successfully")
    
    print("🚀 Starting LifeLine Africa Insurance Services API...")
    print(f"📧 Email notifications configured for {len(PRIMARY_RECIPIENTS)} primary recipients")
    print(f"📋 CC notifications will be sent to: {CC_RECIPIENT}")
    print("🌐 Server starting on http://localhost:5000")
    
    app.run(
        debug=os.getenv('FLASK_ENV') == 'development',
        host='0.0.0.0',
        port=int(os.getenv('PORT', 5000))
    )
"""
Comprehensive test suite for LifeLine Africa Insurance API
Tests all endpoints, validation, error handling, and edge cases
"""

import pytest
import json
import io
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone
import uuid

from app import create_app, PDFGenerator, EmailService, Config


class TestConfig(Config):
    """Test configuration with in-memory database"""
    TESTING = True
    MONGO_URI = 'mongodb://localhost:27017/insurance_test_db'
    SECRET_KEY = 'test-secret-key'
    SMTP_USERNAME = 'j.chukwuony@alustudent.com'
    SMTP_PASSWORD = 'ljol rjet wgyg fgbe'


@pytest.fixture
def app():
    """Create test application instance"""
    app = create_app()
    app.config.from_object(TestConfig)
    return app


@pytest.fixture
def client(app):
    """Create test client"""
    return app.test_client()


@pytest.fixture
def sample_individual_data():
    """Sample individual insurance data"""
    return {
        "type": "individual",
        "data": {
            "full_name": "John Doe",
            "email_address": "john.doe@example.com",
            "phone_number": "+1234567890",
            "age": "30",
            "gender": "Male",
            "address": "123 Main St",
            "city": "Lagos",
            "state": "Lagos",
            "country": "Nigeria",
            "occupation": "Software Engineer",
            "annual_income": "50000",
            "coverage_type": "Life Insurance",
            "coverage_amount": "100000",
            "policy_duration": "20 years"
        }
    }


@pytest.fixture
def sample_company_data():
    """Sample company insurance data"""
    return {
        "type": "company",
        "data": {
            "company_name": "Tech Solutions Ltd",
            "registration_number": "RC123456",
            "industry_type": "Technology",
            "company_size": "50-100",
            "years_in_operation": "10",
            "annual_revenue": "1000000",
            "company_address": "456 Business Ave",
            "city": "Lagos",
            "state": "Lagos",
            "country": "Nigeria",
            "primary_contact_name": "Jane Smith",
            "primary_contact_email": "jane@techsolutions.com",
            "primary_contact_phone": "+1234567891",
            "number_of_employees": "75",
            "coverage_type": "General Liability",
            "coverage_amount": "500000"
        }
    }


class TestHealthEndpoint:
    """Test health check endpoint"""
    
    def test_health_check_success(self, client):
        """Test successful health check"""
        with patch('app.mongo.db.command') as mock_command:
            mock_command.return_value = {'ok': 1}
            
            response = client.get('/health')
            
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['status'] == 'healthy'
            assert data['database'] == 'connected'
            assert 'timestamp' in data
            assert 'version' in data
    
    def test_health_check_database_failure(self, client):
        """Test health check with database failure"""
        with patch('app.mongo.db.command') as mock_command:
            mock_command.side_effect = Exception("Database connection failed")
            
            response = client.get('/health')
            
            assert response.status_code == 500
            data = json.loads(response.data)
            assert data['status'] == 'unhealthy'
            assert data['database'] == 'disconnected'


class TestValidationService:
    """Test validation service"""
    
    def test_valid_individual_data(self, sample_individual_data):
        """Test validation of valid individual data"""
        is_valid, message = ValidationService.validate_submission_data(
            "individual",
            sample_individual_data["data"]
        )
        assert is_valid is True
        assert message == ""
    
    def test_valid_company_data(self, sample_company_data):
        """Test validation of valid company data"""
        is_valid, message = ValidationService.validate_submission_data(
            "company",
            sample_company_data["data"]
        )
        assert is_valid is True
        assert message == ""
    
    def test_invalid_submission_type(self):
        """Test validation with invalid submission type"""
        is_valid, message = ValidationService.validate_submission_data(
            "invalid_type",
            {"name": "Test"}
        )
        assert is_valid is False
        assert "Invalid submission type" in message
    
    def test_missing_required_fields_individual(self):
        """Test validation with missing required fields for individual"""
        data = {"age": "30"}  # Missing full_name, email_address, phone_number
        
        is_valid, message = ValidationService.validate_submission_data("individual", data)
        assert is_valid is False
        assert "Missing required fields" in message
    
    def test_missing_required_fields_company(self):
        """Test validation with missing required fields for company"""
        data = {"industry_type": "Tech"}  # Missing company_name, primary_contact_email, primary_contact_phone
        
        is_valid, message = ValidationService.validate_submission_data("company", data)
        assert is_valid is False
        assert "Missing required fields" in message
    
    def test_invalid_age(self):
        """Test validation with invalid age"""
        data = {
            "full_name": "John Doe",
            "email_address": "john@example.com",
            "phone_number": "+1234567890",
            "age": "150"  # Invalid age
        }
        
        is_valid, message = ValidationService.validate_submission_data("individual", data)
        assert is_valid is False
        assert "Age must be between 18 and 120" in message
    
    def test_invalid_email_format(self):
        """Test validation with invalid email format"""
        data = {
            "full_name": "John Doe",
            "email_address": "invalid-email",  # Invalid email
            "phone_number": "+1234567890"
        }
        
        is_valid, message = ValidationService.validate_submission_data("individual", data)
        assert is_valid is False
        assert "Invalid email format" in message
    
    def test_non_dict_data(self):
        """Test validation with non-dictionary data"""
        is_valid, message = ValidationService.validate_submission_data("individual", "not a dict")
        assert is_valid is False
        assert "Invalid data format" in message


class TestSubmissionEndpoint:
    """Test submission endpoint"""
    
    @patch('app.mongo.db')
    @patch('app.mongo.cx.start_session')
    @patch('app.mongo.save_file')
    def test_successful_individual_submission(self, mock_save_file, mock_session, mock_db, client, sample_individual_data):
        """Test successful individual submission"""
        # Mock database operations
        mock_session_instance = MagicMock()
        mock_session.return_value.__enter__.return_value = mock_session_instance
        mock_save_file.return_value = str(uuid.uuid4())
        
        with patch('app.EmailService.send_email') as mock_email:
            mock_email.return_value = True
            
            response = client.post('/submit',
                                 data=json.dumps(sample_individual_data),
                                 content_type='application/json')
            
            assert response.status_code == 201
            data = json.loads(response.data)
            assert data['message'] == 'Submission processed successfully'
            assert 'submission_id' in data
            assert 'request_id' in data
            assert data['status'] == 'processed'
            assert 'links' in data
    
    @patch('app.mongo.db')
    @patch('app.mongo.cx.start_session')
    @patch('app.mongo.save_file')
    def test_successful_company_submission(self, mock_save_file, mock_session, mock_db, client, sample_company_data):
        """Test successful company submission"""
        # Mock database operations
        mock_session_instance = MagicMock()
        mock_session.return_value.__enter__.return_value = mock_session_instance
        mock_save_file.return_value = str(uuid.uuid4())
        
        with patch('app.EmailService.send_email') as mock_email:
            mock_email.return_value = True
            
            response = client.post('/submit',
                                 data=json.dumps(sample_company_data),
                                 content_type='application/json')
            
            assert response.status_code == 201
            data = json.loads(response.data)
            assert data['message'] == 'Submission processed successfully'
            assert 'submission_id' in data
    
    def test_submission_invalid_json(self, client):
        """Test submission with invalid JSON"""
        response = client.post('/submit',
                             data='invalid json',
                             content_type='application/json')
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data
    
    def test_submission_no_content_type(self, client, sample_individual_data):
        """Test submission without proper content type"""
        response = client.post('/submit',
                             data=json.dumps(sample_individual_data))
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'Content-Type must be application/json' in data['error']
    
    def test_submission_empty_body(self, client):
        """Test submission with empty body"""
        response = client.post('/submit',
                             data='',
                             content_type='application/json')
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'Request body cannot be empty' in data['error']
    
    def test_submission_validation_error(self, client):
        """Test submission with validation error"""
        invalid_data = {
            "type": "individual",
            "data": {
                "age": "30"  # Missing required fields
            }
        }
        
        response = client.post('/submit',
                             data=json.dumps(invalid_data),
                             content_type='application/json')
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'Missing required fields' in data['error']
    
    @patch('app.mongo.db')
    def test_submission_database_error(self, mock_db, client, sample_individual_data):
        """Test submission with database error"""
        mock_db.side_effect = Exception("Database error")
        
        response = client.post('/submit',
                             data=json.dumps(sample_individual_data),
                             content_type='application/json')
        
        assert response.status_code == 500
        data = json.loads(response.data)
        assert 'error' in data


class TestPDFGenerator:
    """Test PDF generation"""
    
    def test_pdf_generation_individual(self, sample_individual_data):
        """Test PDF generation for individual submission"""
        generator = PDFGenerator()
        submission_id = str(uuid.uuid4())
        
        pdf_buffer = generator.generate_pdf(
            "individual",
            sample_individual_data["data"],
            submission_id
        )
        
        assert isinstance(pdf_buffer, io.BytesIO)
        assert pdf_buffer.tell() > 0  # Buffer has content
        
        # Check PDF starts with PDF header
        pdf_buffer.seek(0)
        content = pdf_buffer.read(4)
        assert content == b'%PDF'
        
        pdf_buffer.close()
    
    def test_pdf_generation_company(self, sample_company_data):
        """Test PDF generation for company submission"""
        generator = PDFGenerator()
        submission_id = str(uuid.uuid4())
        
        pdf_buffer = generator.generate_pdf(
            "company",
            sample_company_data["data"],
            submission_id
        )
        
        assert isinstance(pdf_buffer, io.BytesIO)
        assert pdf_buffer.tell() > 0
        
        pdf_buffer.close()
    
    def test_pdf_generation_with_missing_data(self):
        """Test PDF generation with minimal data"""
        generator = PDFGenerator()
        submission_id = str(uuid.uuid4())
        
        minimal_data = {"full_name": "John Doe"}
        
        pdf_buffer = generator.generate_pdf(
            "individual",
            minimal_data,
            submission_id
        )
        
        assert isinstance(pdf_buffer, io.BytesIO)
        pdf_buffer.close()


class TestEmailService:
    """Test email service"""
    
    def test_email_service_initialization(self):
        """Test email service initialization"""
        config = TestConfig()
        email_service = EmailService(config)
        
        assert email_service.config == config
    
    def test_send_email_missing_credentials(self):
        """Test email sending with missing credentials"""
        config = TestConfig()
        config.SMTP_USERNAME = None
        config.SMTP_PASSWORD = None
        
        email_service = EmailService(config)
        
        with pytest.raises(ValueError, match="SMTP credentials not configured"):
            email_service.send_email(
                "Test Subject",
                "<p>Test Content</p>",
                ["test@example.com"]
            )
    
    def test_send_email_no_recipients(self):
        """Test email sending with no recipients"""
        config = TestConfig()
        email_service = EmailService(config)
        
        with pytest.raises(ValueError, match="No recipients specified"):
            email_service.send_email(
                "Test Subject",
                "<p>Test Content</p>",
                []
            )
    
    @patch('smtplib.SMTP_SSL')
    def test_send_email_success(self, mock_smtp):
        """Test successful email sending"""
        config = TestConfig()
        email_service = EmailService(config)
        
        # Mock SMTP server
        mock_server = MagicMock()
        mock_smtp.return_value.__enter__.return_value = mock_server
        
        result = email_service.send_email(
            "Test Subject",
            "<p>Test Content</p>",
            ["test@example.com"]
        )
        
        assert result is True
        mock_server.login.assert_called_once()
        mock_server.send_message.assert_called_once()
    
    @patch('smtplib.SMTP_SSL')
    def test_send_email_with_pdf_attachment(self, mock_smtp):
        """Test email sending with PDF attachment"""
        config = TestConfig()
        email_service = EmailService(config)
        
        # Mock SMTP server
        mock_server = MagicMock()
        mock_smtp.return_value.__enter__.return_value = mock_server
        
        # Create mock PDF buffer
        pdf_buffer = io.BytesIO(b'%PDF-1.4 fake pdf content')
        
        result = email_service.send_email(
            "Test Subject",
            "<p>Test Content</p>",
            ["test@example.com"],
            pdf_attachment=pdf_buffer
        )
        
        assert result is True
        pdf_buffer.close()


class TestDownloadEndpoint:
    """Test PDF download endpoint"""
    
    @patch('app.mongo.db')
    @patch('app.mongo.send_file')
    def test_download_pdf_success(self, mock_send_file, mock_db, client):
        """Test successful PDF download"""
        submission_id = str(uuid.uuid4())
        
        # Mock database response
        mock_db.__getitem__.return_value.find_one.return_value = {
            "_id": submission_id,
            "pdf_generated": True,
            "pdf_id": str(uuid.uuid4()),
            "updated_at": datetime.now(timezone.utc)
        }
        
        # Mock file response
        mock_send_file.return_value = io.BytesIO(b'%PDF fake content')
        
        response = client.get(f'/download-pdf/{submission_id}')
        
        assert response.status_code == 200
        assert response.content_type == 'application/pdf'
    
    def test_download_pdf_invalid_id(self, client):
        """Test PDF download with invalid submission ID"""
        response = client.get('/download-pdf/invalid-id')
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'Invalid submission ID format' in data['error']
    
    @patch('app.mongo.db')
    def test_download_pdf_not_found(self, mock_db, client):
        """Test PDF download for non-existent submission"""
        submission_id = str(uuid.uuid4())
        
        mock_db.__getitem__.return_value.find_one.return_value = None
        
        response = client.get(f'/download-pdf/{submission_id}')
        
        assert response.status_code == 404
        data = json.loads(response.data)
        assert 'Submission not found' in data['error']
    
    @patch('app.mongo.db')
    def test_download_pdf_not_generated(self, mock_db, client):
        """Test PDF download when PDF not generated"""
        submission_id = str(uuid.uuid4())
        
        mock_db.__getitem__.return_value.find_one.return_value = {
            "_id": submission_id,
            "pdf_generated": False
        }
        
        response = client.get(f'/download-pdf/{submission_id}')
        
        assert response.status_code == 404
        data = json.loads(response.data)
        assert 'PDF not available' in data['error']


class TestViewSubmissionEndpoint:
    """Test view submission endpoint"""
    
    @patch('app.mongo.db')
    def test_view_submission_success(self, mock_db, client, sample_individual_data):
        """Test successful submission viewing"""
        submission_id = str(uuid.uuid4())
        
        mock_db.__getitem__.return_value.find_one.return_value = {
            "_id": submission_id,
            "submission_type": "individual",
            "submission_data": sample_individual_data["data"],
            "created_at": datetime.now(timezone.utc),
            "status": "processed",
            "pdf_generated": True
        }
        
        response = client.get(f'/submission/{submission_id}')
        
        assert response.status_code == 200
        assert 'text/html' in response.content_type
        assert 'Individual Insurance Submission' in response.data.decode()
    
    def test_view_submission_invalid_id(self, client):
        """Test viewing submission with invalid ID"""
        response = client.get('/submission/invalid-id')
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'Invalid submission ID format' in data['error']
    
    @patch('app.mongo.db')
    def test_view_submission_not_found(self, mock_db, client):
        """Test viewing non-existent submission"""
        submission_id = str(uuid.uuid4())
        
        mock_db.__getitem__.return_value.find_one.return_value = None
        
        response = client.get(f'/submission/{submission_id}')
        
        assert response.status_code == 404
        data = json.loads(response.data)
        assert 'Submission not found' in data['error']


class TestErrorHandling:
    """Test error handling"""
    
    def test_404_error(self, client):
        """Test 404 error handling"""
        response = client.get('/nonexistent-endpoint')
        
        assert response.status_code == 404
        assert 'Endpoint not found' in json.loads(response.data)['error']
    
    def test_405_error(self, client):
        """Test 405 method not allowed error"""
        response = client.put('/submit')
        
        assert response.status_code == 405
        data = json.loads(response.data)
        assert 'Method not allowed' in data['error']


class TestRateLimiting:
    """Test rate limiting (requires Redis in test environment)"""
    
    @pytest.mark.skip(reason="Requires Redis for rate limiting tests")
    def test_rate_limiting(self, client, sample_individual_data):
        """Test rate limiting on submit endpoint"""
        # This test would require a Redis instance
        # Make multiple requests to trigger rate limit
        for i in range(15):  # Exceed 10 per minute limit
            response = client.post('/submit',
                                 data=json.dumps(sample_individual_data),
                                 content_type='application/json')
            
            if i < 10:
                assert response.status_code in [201, 400, 500]  # Various valid responses
            else:
                assert response.status_code == 429  # Rate limited


# Integration Tests
class TestIntegration:
    """Integration tests for complete workflows"""
    
    @patch('app.mongo.db')
    @patch('app.mongo.cx.start_session')
    @patch('app.mongo.save_file')
    @patch('app.EmailService.send_email')
    def test_complete_submission_workflow(self, mock_email, mock_save_file, mock_session, mock_db, client, sample_individual_data):
        """Test complete submission workflow from start to finish"""
        # Mock all external dependencies
        mock_session_instance = MagicMock()
        mock_session.return_value.__enter__.return_value = mock_session_instance
        mock_save_file.return_value = str(uuid.uuid4())
        mock_email.return_value = True
        
        # Submit data
        response = client.post('/submit',
                             data=json.dumps(sample_individual_data),
                             content_type='application/json')
        
        assert response.status_code == 201
        data = json.loads(response.data)
        
        # Verify database operations were called
        assert mock_db.__getitem__.return_value.insert_one.called
        assert mock_db.__getitem__.return_value.update_one.called
        assert mock_save_file.called
        assert mock_email.called


if __name__ == '__main__':
    # Run tests with coverage
    pytest.main([
        '--verbose',
        '--tb=short',
        '--cov=app',
        '--cov-report=html',
        '--cov-report=term-missing',
        __file__
    ])
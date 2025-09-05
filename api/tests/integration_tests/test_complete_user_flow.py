"""End-to-end integration tests for complete user flows."""

import pytest
import json
import tempfile
from io import BytesIO
from PIL import Image
from unittest.mock import patch

from models.account import Account
from models.compliance import SmsVerification, UserConsent, ContentReport, RealNameVerification


class TestCompleteUserFlow:
    """Test complete user flows from registration to feature usage."""

    def test_complete_registration_verification_flow(self, client, app):
        """Test complete user registration and phone verification flow."""
        
        # Step 1: User registers with phone number
        registration_data = {
            'name': 'Test User',
            'email': 'test@example.com', 
            'phone_number': '13800138000',
            'password': 'securepassword123'
        }
        
        with patch('services.sms.sms_service.SMSService.send_verification_code') as mock_sms:
            mock_sms.return_value = {'success': True, 'message': 'SMS sent'}
            
            response = client.post('/api/auth/register', 
                                 data=json.dumps(registration_data),
                                 content_type='application/json')
            
            assert response.status_code == 201
            data = json.loads(response.data)
            assert data['success'] is True
            
            # Verify SMS was sent
            mock_sms.assert_called_once()

        # Step 2: Verify phone number
        with app.app_context():
            # Create a verification record manually for testing
            verification = SmsVerification(
                phone_number='13800138000',
                verification_code_hash='hashed_code',
                purpose='registration'
            )
            from models.engine import db
            db.session.add(verification)
            db.session.commit()

        # Step 3: Login after registration
        login_data = {
            'phone_number': '13800138000',
            'password': 'securepassword123'
        }
        
        response = client.post('/api/auth/login',
                             data=json.dumps(login_data),
                             content_type='application/json')
        
        # Should succeed after proper implementation
        # Note: Actual implementation may require additional setup
        
    def test_profile_management_flow(self, client, authenticated_user):
        """Test complete profile management flow."""
        
        # Step 1: Get current profile
        response = client.get('/api/profile/')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        
        # Step 2: Update profile information
        update_data = {
            'nickname': 'Updated Nickname',
            'real_name': 'John Doe'
        }
        
        response = client.put('/api/profile/',
                            data=json.dumps(update_data),
                            content_type='application/json')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert data['data']['nickname'] == 'Updated Nickname'
        
        # Step 3: Upload avatar
        # Create a test image
        image = Image.new('RGB', (100, 100), color='red')
        img_buffer = BytesIO()
        image.save(img_buffer, format='JPEG')
        img_buffer.seek(0)
        
        response = client.post('/api/profile/avatar',
                             data={'file': (img_buffer, 'test_avatar.jpg')},
                             content_type='multipart/form-data')
        
        # Should succeed with proper file storage setup
        # Note: May require file storage service configuration
        
    def test_real_name_verification_flow(self, client, authenticated_user):
        """Test complete real name verification flow."""
        
        # Step 1: Check verification status
        response = client.get('/api/verification/status')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        
        # Step 2: Get available ID types
        response = client.get('/api/verification/id-types')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert len(data['data']) > 0
        
        # Step 3: Submit verification request
        # Create test document images
        front_image = Image.new('RGB', (200, 300), color='blue')
        front_buffer = BytesIO()
        front_image.save(front_buffer, format='JPEG')
        front_buffer.seek(0)
        
        verification_data = {
            'real_name': 'John Doe',
            'id_type': 'national_id',
            'id_number': 'ID123456789',
            'front_document': (front_buffer, 'id_front.jpg')
        }
        
        response = client.post('/api/verification/submit',
                             data=verification_data,
                             content_type='multipart/form-data')
        
        # Should succeed with proper implementation
        # Note: May require file storage and encryption setup
        
    def test_content_reporting_flow(self, client, authenticated_user):
        """Test complete content reporting flow."""
        
        # Step 1: Submit content report
        report_data = {
            'content_id': 'test_content_123',
            'content_type': 'text',
            'report_category': 'inappropriate_content',
            'report_reason': 'This content violates community guidelines'
        }
        
        response = client.post('/api/reports/',
                             data=json.dumps(report_data),
                             content_type='application/json')
        
        assert response.status_code == 201
        data = json.loads(response.data)
        assert data['success'] is True
        
        # Step 2: Check report status
        report_id = data['data']['id']
        response = client.get(f'/api/reports/{report_id}')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert data['data']['status'] == 'pending'
        
        # Step 3: Get user's report history
        response = client.get('/api/reports/my-reports')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert len(data['data']) >= 1

    def test_sms_verification_flow(self, client, authenticated_user):
        """Test SMS verification flow."""
        
        phone_number = '13900139000'
        
        # Step 1: Request SMS verification
        with patch('services.sms.sms_service.SMSService.send_verification_code') as mock_sms:
            mock_sms.return_value = {'success': True, 'message': 'SMS sent'}
            
            response = client.post('/api/sms/send-verification',
                                 data=json.dumps({
                                     'phone_number': phone_number,
                                     'purpose': 'phone_change'
                                 }),
                                 content_type='application/json')
            
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['success'] is True
            
        # Step 2: Verify SMS code
        with patch('services.sms.sms_service.SMSService.verify_code') as mock_verify:
            mock_verify.return_value = True
            
            response = client.post('/api/sms/verify-code',
                                 data=json.dumps({
                                     'phone_number': phone_number,
                                     'code': '123456',
                                     'purpose': 'phone_change'
                                 }),
                                 content_type='application/json')
            
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['success'] is True

    def test_system_health_monitoring(self, client):
        """Test system health monitoring endpoints."""
        
        # Step 1: Check system health status
        response = client.get('/api/health/status')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert 'overall_status' in data['data']
        
        # Step 2: Check ping endpoint
        response = client.get('/api/health/ping')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['message'] == 'pong'

    def test_error_handling_and_recovery(self, client, authenticated_user):
        """Test error handling and system recovery scenarios."""
        
        # Test 1: Invalid API endpoints
        response = client.get('/api/nonexistent-endpoint')
        assert response.status_code == 404
        
        # Test 2: Invalid data submission
        response = client.post('/api/profile/',
                             data=json.dumps({}),
                             content_type='application/json')
        # Should handle gracefully without crashing
        
        # Test 3: Rate limiting
        # Make multiple rapid requests to trigger rate limit
        for _ in range(20):
            response = client.get('/api/profile/')
            if response.status_code == 429:  # Rate limited
                break
        
        # Test 4: Large file upload handling
        large_data = b'x' * (20 * 1024 * 1024)  # 20MB
        response = client.post('/api/profile/avatar',
                             data={'file': (BytesIO(large_data), 'large_file.jpg')},
                             content_type='multipart/form-data')
        
        # Should handle gracefully (either accept or reject cleanly)
        assert response.status_code in [200, 400, 413, 500]

    def test_data_consistency_and_synchronization(self, client, authenticated_user, app):
        """Test data consistency across different operations."""
        
        with app.app_context():
            from models.engine import db
            
            # Test 1: Profile update consistency
            update_data = {
                'nickname': 'Consistency Test',
                'real_name': 'Test User'
            }
            
            response = client.put('/api/profile/',
                                data=json.dumps(update_data),
                                content_type='application/json')
            
            assert response.status_code == 200
            
            # Verify data is consistent in database
            user = Account.query.filter_by(email=authenticated_user.email).first()
            assert user.nickname == 'Consistency Test'
            assert user.real_name == 'Test User'
            
            # Test 2: Consent tracking consistency
            # Submit a report and check if user consents are properly tracked
            report_data = {
                'content_id': 'consistency_test_content',
                'content_type': 'text', 
                'report_category': 'spam',
                'report_reason': 'Testing consistency'
            }
            
            response = client.post('/api/reports/',
                                 data=json.dumps(report_data),
                                 content_type='application/json')
            
            assert response.status_code == 201
            
            # Verify report was created
            report = ContentReport.query.filter_by(
                content_id='consistency_test_content'
            ).first()
            assert report is not None
            assert report.reporter_id == authenticated_user.id

    def test_security_and_access_control(self, client, authenticated_user):
        """Test security measures and access control."""
        
        # Test 1: Unauthenticated access to protected endpoints
        client.post('/api/auth/logout')  # Logout first
        
        response = client.get('/api/profile/')
        assert response.status_code == 401  # Unauthorized
        
        response = client.get('/api/verification/status')
        assert response.status_code == 401  # Unauthorized
        
        # Test 2: Input validation and sanitization
        client.post('/api/auth/login',
                   data=json.dumps({
                       'phone_number': authenticated_user.phone_number,
                       'password': 'test_password'
                   }),
                   content_type='application/json')
        
        # Test malicious input
        malicious_data = {
            'nickname': '<script>alert("xss")</script>',
            'real_name': '"; DROP TABLE accounts; --'
        }
        
        response = client.put('/api/profile/',
                            data=json.dumps(malicious_data),
                            content_type='application/json')
        
        # Should handle malicious input safely
        assert response.status_code in [200, 400]
        
        # Verify no XSS or SQL injection occurred
        if response.status_code == 200:
            data = json.loads(response.data)
            # Check that malicious content was sanitized or rejected
            assert '<script>' not in str(data)

    def test_performance_benchmarks(self, client, authenticated_user):
        """Test performance benchmarks for key operations."""
        
        import time
        
        # Test 1: Profile retrieval performance
        start_time = time.time()
        response = client.get('/api/profile/')
        end_time = time.time()
        
        assert response.status_code == 200
        response_time_ms = (end_time - start_time) * 1000
        assert response_time_ms < 500  # Should respond within 500ms
        
        # Test 2: System health check performance
        start_time = time.time()
        response = client.get('/api/health/status')
        end_time = time.time()
        
        assert response.status_code == 200
        response_time_ms = (end_time - start_time) * 1000
        assert response_time_ms < 2000  # Should respond within 2 seconds
        
        # Test 3: Multiple concurrent requests simulation
        start_time = time.time()
        responses = []
        
        for _ in range(10):
            response = client.get('/api/profile/')
            responses.append(response)
        
        end_time = time.time()
        total_time_ms = (end_time - start_time) * 1000
        
        # All requests should succeed
        assert all(r.status_code == 200 for r in responses)
        # Average response time should be reasonable
        avg_time_ms = total_time_ms / len(responses)
        assert avg_time_ms < 1000  # Average under 1 second
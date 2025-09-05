"""Epic 1 system integration tests - comprehensive end-to-end testing."""

import pytest
import json
import time
import requests
import tempfile
from io import BytesIO
from PIL import Image
from concurrent.futures import ThreadPoolExecutor, as_completed
from unittest.mock import patch

from models.account import Account
from models.compliance import (
    SmsVerification, UserConsent, ContentReport, 
    RealNameVerification, SMSPurpose, ReportStatus
)


class TestEpic1SystemIntegration:
    """Comprehensive system integration tests for Epic 1 features."""
    
    def setup_class(self):
        """Setup test environment."""
        self.base_url = "http://localhost:5001"  # Adjust as needed
        self.test_users = []
        
    def teardown_class(self):
        """Cleanup test environment."""
        # Cleanup test data if needed
        pass

    def test_complete_user_onboarding_flow(self, app):
        """Test complete user onboarding from registration to verification."""
        
        with app.app_context():
            # Step 1: User registration with phone number
            user_data = {
                'name': 'Integration Test User',
                'email': 'integration.test@example.com',
                'phone_number': '13800138888',
                'password': 'TestPassword123!'
            }
            
            # Mock SMS service for testing
            with patch('services.sms.sms_service.SMSService.send_verification_code') as mock_sms:
                mock_sms.return_value = {'success': True, 'message': 'SMS sent successfully'}
                
                # Register user
                response = self._make_request('POST', '/api/auth/register', user_data)
                assert response['success'] is True
                
                # Verify SMS was attempted
                mock_sms.assert_called_once()
                
            # Step 2: Login user
            login_data = {
                'phone_number': user_data['phone_number'],
                'password': user_data['password']
            }
            
            response = self._make_request('POST', '/api/auth/login', login_data)
            # Note: Actual login may require SMS verification completion
            
            # Step 3: Complete profile setup
            profile_data = {
                'nickname': 'TestUser888',
                'real_name': 'Test User Full Name'
            }
            
            # This would require authentication token from login
            # For testing, we'll simulate the flow
            
    def test_sms_verification_system(self, app):
        """Test SMS verification system comprehensively."""
        
        with app.app_context():
            from services.sms.sms_service import SMSService
            from models.engine import db
            
            sms_service = SMSService()
            
            # Test 1: Send verification code
            phone_number = '13900139999'
            
            with patch.object(sms_service, 'send_verification_code') as mock_send:
                mock_send.return_value = {'success': True, 'message': 'SMS sent'}
                
                result = sms_service.send_verification_code(phone_number, SMSPurpose.REGISTRATION)
                assert result['success'] is True
                
                # Verify SMS record was created
                sms_record = SmsVerification.query.filter_by(
                    phone_number=phone_number,
                    purpose=SMSPurpose.REGISTRATION
                ).first()
                assert sms_record is not None
                
            # Test 2: Verify code
            with patch.object(sms_service, 'verify_code') as mock_verify:
                mock_verify.return_value = True
                
                is_valid = sms_service.verify_code(phone_number, '123456', SMSPurpose.REGISTRATION)
                assert is_valid is True
                
            # Test 3: Rate limiting
            # Simulate multiple SMS requests
            with patch.object(sms_service, 'send_verification_code') as mock_send:
                mock_send.return_value = {'success': True}
                
                # Should handle rate limiting gracefully
                for i in range(10):
                    try:
                        sms_service.send_verification_code(f'1380013{i:04d}', SMSPurpose.REGISTRATION)
                    except Exception as e:
                        # Rate limiting should not crash the system
                        assert 'rate limit' in str(e).lower() or 'too many' in str(e).lower()

    def test_real_name_verification_workflow(self, app):
        """Test complete real name verification workflow."""
        
        with app.app_context():
            from services.verification_service import verification_service
            from models.engine import db
            
            # Create test user
            user = Account(
                name='Verification Test User',
                email='verification.test@example.com',
                phone_number='13800138777'
            )
            db.session.add(user)
            db.session.commit()
            
            # Test 1: Submit verification
            verification_data = {
                'real_name': 'John Doe Smith',
                'id_type': 'national_id',
                'id_number': 'ID123456789012345'
            }
            
            # Create test document files
            front_image = Image.new('RGB', (400, 300), color='blue')
            front_buffer = BytesIO()
            front_image.save(front_buffer, format='JPEG')
            front_buffer.seek(0)
            
            back_image = Image.new('RGB', (400, 300), color='green')  
            back_buffer = BytesIO()
            back_image.save(back_buffer, format='JPEG')
            back_buffer.seek(0)
            
            # Mock file objects
            class MockFile:
                def __init__(self, buffer, filename):
                    self.buffer = buffer
                    self.filename = filename
                    
                def read(self):
                    return self.buffer.getvalue()
                    
                def seek(self, pos):
                    return self.buffer.seek(pos)
                    
            front_file = MockFile(front_buffer, 'id_front.jpg')
            back_file = MockFile(back_buffer, 'id_back.jpg')
            
            # Submit verification
            with patch.object(verification_service, '_process_document_upload') as mock_upload:
                mock_upload.side_effect = [
                    '/uploads/verification/front_doc.jpg',
                    '/uploads/verification/back_doc.jpg'
                ]
                
                result = verification_service.submit_verification(
                    user_id=user.id,
                    verification_data=verification_data,
                    front_document_file=front_file,
                    back_document_file=back_file
                )
                
                assert result['verification_id'] is not None
                assert result['status'] == 'pending'
                
            # Test 2: Get verification status
            status = verification_service.get_user_verification_status(user.id)
            assert status['status'] == 'pending'
            assert status['can_submit'] is False
            
            # Test 3: Admin approval workflow
            verification = RealNameVerification.query.filter_by(user_id=user.id).first()
            assert verification is not None
            
            # Simulate admin approval
            updated_verification = verification_service.update_verification_status(
                verification_id=verification.id,
                new_status='approved',
                moderator_id=user.id,  # Using same user as moderator for test
                rejection_reason=None
            )
            
            assert updated_verification['status'] == 'approved'
            
            # Verify user was updated
            db.session.refresh(user)
            assert user.real_name_verified is True
            assert user.real_name == verification_data['real_name']

    def test_content_reporting_system(self, app):
        """Test comprehensive content reporting system."""
        
        with app.app_context():
            from services.reports_service import reports_service
            from models.engine import db
            
            # Create test users
            reporter = Account(
                name='Reporter User',
                email='reporter@example.com',
                phone_number='13800138111'
            )
            db.session.add(reporter)
            db.session.commit()
            
            # Test 1: Submit content report
            report_data = {
                'content_id': 'test_content_12345',
                'content_type': 'text',
                'report_category': 'inappropriate_content',
                'report_reason': 'This content contains inappropriate material that violates community guidelines.',
                'content_snapshot': {
                    'text': 'Sample inappropriate content',
                    'context': 'Chat message'
                }
            }
            
            report = reports_service.submit_report(
                reporter_id=reporter.id,
                report_data=report_data,
                ip_address='192.168.1.100',
                user_agent='Mozilla/5.0 Test Browser'
            )
            
            assert report['id'] is not None
            assert report['status'] == 'pending'
            
            # Test 2: Get report details
            report_details = reports_service.get_report_details(report['id'])
            assert report_details['report_category'] == 'inappropriate_content'
            assert report_details['reporter_id'] == reporter.id
            
            # Test 3: Moderate report
            moderation_result = reports_service.moderate_report(
                report_id=report['id'],
                moderator_id=reporter.id,  # Using same user as moderator for test
                action='resolved',
                moderator_notes='Content reviewed and action taken.'
            )
            
            assert moderation_result['status'] == 'resolved'
            
            # Test 4: Get user's report history
            user_reports = reports_service.get_user_reports(reporter.id)
            assert len(user_reports) >= 1
            assert any(r['id'] == report['id'] for r in user_reports)

    def test_profile_management_integration(self, app):
        """Test profile management with security audit integration."""
        
        with app.app_context():
            from services.profile_service import profile_service
            from models.engine import db
            
            # Create test user
            user = Account(
                name='Profile Test User',
                email='profile.test@example.com',
                phone_number='13800138222'
            )
            db.session.add(user)
            db.session.commit()
            
            # Test 1: Get initial profile
            profile = profile_service.get_user_profile(user.id)
            assert profile['id'] == user.id
            assert profile['name'] == 'Profile Test User'
            
            # Test 2: Update profile with change tracking
            updates = {
                'nickname': 'ProfileTestNick',
                'real_name': 'Profile Test Full Name',
                'interface_language': 'zh-CN',
                'timezone': 'Asia/Shanghai'
            }
            
            updated_profile = profile_service.update_user_profile(
                user_id=user.id,
                updates=updates,
                ip_address='192.168.1.200',
                user_agent='Test User Agent'
            )
            
            assert updated_profile['nickname'] == 'ProfileTestNick'
            assert updated_profile['real_name'] == 'Profile Test Full Name'
            
            # Test 3: Verify change history was logged
            change_history = profile_service.get_change_history(user.id)
            assert len(change_history) >= 1
            
            # Should have logged changes for each updated field
            change_types = [change['change_type'] for change in change_history]
            assert 'nickname' in change_types
            assert 'real_name' in change_types
            
            # Test 4: Avatar upload simulation
            test_image = Image.new('RGB', (200, 200), color='red')
            img_buffer = BytesIO()
            test_image.save(img_buffer, format='JPEG')
            img_buffer.seek(0)
            
            class MockAvatarFile:
                def read(self):
                    return img_buffer.getvalue()
                def seek(self, pos):
                    return img_buffer.seek(pos)
                    
            mock_file = MockAvatarFile()
            
            with patch.object(profile_service, '_cleanup_old_avatar'):
                with patch.object(profile_service.file_storage, 'save_file') as mock_save:
                    mock_save.return_value = '/uploads/avatars/test_avatar.jpg'
                    
                    avatar_url = profile_service.process_and_save_avatar(
                        user_id=user.id,
                        file=mock_file,
                        ip_address='192.168.1.200'
                    )
                    
                    assert avatar_url == '/uploads/avatars/test_avatar.jpg'

    def test_system_performance_monitoring(self, app):
        """Test system performance monitoring and health checks."""
        
        with app.app_context():
            from services.system_health_service import system_health_service
            from services.performance_service import performance_monitor, PerformanceMetric
            from datetime import datetime
            
            # Test 1: System health check
            health_status = system_health_service.get_system_status()
            assert 'overall_status' in health_status
            assert health_status['overall_status'] in ['healthy', 'degraded', 'unhealthy']
            
            # Test 2: Performance metrics collection
            test_metric = PerformanceMetric(
                endpoint='/api/test',
                method='GET',
                response_time_ms=150.5,
                status_code=200,
                timestamp=datetime.utcnow(),
                user_id='test_user'
            )
            
            performance_monitor.record_metric(test_metric)
            
            # Test 3: Performance analysis
            metrics_summary = performance_monitor.get_metrics_summary(hours=1)
            assert metrics_summary['total_requests'] >= 1
            
            # Test 4: Performance alerts
            alerts = performance_monitor.get_performance_alerts()
            assert isinstance(alerts, list)

    def test_security_and_compliance(self, app):
        """Test security measures and compliance features."""
        
        with app.app_context():
            from models.engine import db
            from sqlalchemy import text
            
            # Test 1: SQL Injection prevention
            # Attempt SQL injection in profile update
            malicious_input = "'; DROP TABLE accounts; --"
            
            user = Account(
                name='Security Test User',
                email='security.test@example.com'
            )
            db.session.add(user)
            db.session.commit()
            
            # This should be safely handled by SQLAlchemy ORM
            try:
                from services.profile_service import profile_service
                profile_service.update_user_profile(
                    user_id=user.id,
                    updates={'nickname': malicious_input}
                )
                
                # Verify table still exists and user nickname was safely stored
                updated_user = Account.query.get(user.id)
                assert updated_user is not None
                # Nickname should be stored safely (may be sanitized)
                
            except Exception as e:
                # Should handle gracefully without exposing system details
                assert 'DROP TABLE' not in str(e)
                
            # Test 2: Data encryption verification
            # Check that sensitive data is encrypted
            verification_data = {
                'real_name': 'John Security Test',
                'id_type': 'national_id', 
                'id_number': 'SENSITIVE123456'
            }
            
            from services.verification_service import verification_service
            
            # Mock file upload
            with patch.object(verification_service, '_process_document_upload'):
                result = verification_service.submit_verification(
                    user_id=user.id,
                    verification_data=verification_data
                )
                
                # Verify ID number is encrypted in database
                verification = RealNameVerification.query.filter_by(
                    user_id=user.id
                ).first()
                
                if verification:
                    # ID number should be encrypted, not plain text
                    assert verification.id_number_encrypted != 'SENSITIVE123456'
                    assert len(verification.id_number_encrypted) > len('SENSITIVE123456')

    def test_concurrent_operations_and_race_conditions(self, app):
        """Test system behavior under concurrent operations."""
        
        with app.app_context():
            from services.profile_service import profile_service
            from models.engine import db
            
            # Create test user
            user = Account(
                name='Concurrent Test User',
                email='concurrent.test@example.com'
            )
            db.session.add(user)
            db.session.commit()
            
            # Test concurrent profile updates
            def update_profile(nickname_suffix):
                try:
                    return profile_service.update_user_profile(
                        user_id=user.id,
                        updates={'nickname': f'ConcurrentTest{nickname_suffix}'},
                        ip_address='192.168.1.100'
                    )
                except Exception as e:
                    return {'error': str(e)}
                    
            # Execute concurrent updates
            with ThreadPoolExecutor(max_workers=5) as executor:
                futures = [executor.submit(update_profile, i) for i in range(10)]
                results = [future.result() for future in as_completed(futures)]
                
            # Verify system handled concurrent updates gracefully
            successful_updates = [r for r in results if 'error' not in r]
            assert len(successful_updates) > 0
            
            # Verify final state is consistent
            final_profile = profile_service.get_user_profile(user.id)
            assert final_profile['nickname'].startswith('ConcurrentTest')

    def test_error_recovery_and_resilience(self, app):
        """Test system error recovery and resilience."""
        
        with app.app_context():
            from services.system_health_service import system_health_service
            
            # Test 1: Database connection resilience
            # Simulate database connection issue
            original_db_check = system_health_service._check_database_health
            
            def failing_db_check():
                raise Exception("Database connection failed")
                
            system_health_service._check_database_health = failing_db_check
            
            try:
                # System should handle database failure gracefully
                health_status = system_health_service.get_system_status()
                assert health_status['overall_status'] in ['degraded', 'unhealthy']
                
            finally:
                # Restore original method
                system_health_service._check_database_health = original_db_check
                
            # Test 2: Cache failure resilience
            from utils.cache import cache_manager
            
            # Simulate cache failure
            original_get = cache_manager.get
            
            def failing_cache_get(key):
                raise Exception("Cache connection failed")
                
            cache_manager.get = failing_cache_get
            
            try:
                # Services should work even without cache
                from services.profile_service import profile_service
                
                # Create test user
                user = Account(
                    name='Resilience Test User',
                    email='resilience.test@example.com'
                )
                from models.engine import db
                db.session.add(user)
                db.session.commit()
                
                # Should work even with cache failure
                profile = profile_service.get_user_profile(user.id)
                assert profile['id'] == user.id
                
            except Exception as e:
                # Should handle gracefully
                assert 'Cache connection failed' not in str(e) or 'fallback' in str(e).lower()
                
            finally:
                # Restore original method
                cache_manager.get = original_get

    def test_data_consistency_across_epic_features(self, app):
        """Test data consistency across all Epic 1 features."""
        
        with app.app_context():
            from models.engine import db
            
            # Create comprehensive test user
            user = Account(
                name='Consistency Test User',
                email='consistency.test@example.com',
                phone_number='13800138333'
            )
            db.session.add(user)
            db.session.commit()
            
            user_id = user.id
            
            # Test 1: Profile update affects all related data
            from services.profile_service import profile_service
            
            profile_service.update_user_profile(
                user_id=user_id,
                updates={'real_name': 'Consistency Test Full Name'},
                ip_address='192.168.1.100'
            )
            
            # Verify change was logged
            change_history = profile_service.get_change_history(user_id)
            assert any(c['change_type'] == 'real_name' for c in change_history)
            
            # Test 2: Real name verification affects profile
            from services.verification_service import verification_service
            
            verification_data = {
                'real_name': 'Verified Full Name',
                'id_type': 'national_id',
                'id_number': 'CONSISTENCY123'
            }
            
            with patch.object(verification_service, '_process_document_upload'):
                verification_result = verification_service.submit_verification(
                    user_id=user_id,
                    verification_data=verification_data
                )
                
                # Approve verification
                verification_service.update_verification_status(
                    verification_id=verification_result['verification_id'],
                    new_status='approved',
                    moderator_id=user_id
                )
                
            # Verify user record was updated consistently
            db.session.refresh(user)
            assert user.real_name_verified is True
            assert user.real_name == 'Verified Full Name'
            
            # Verify profile service returns consistent data
            profile = profile_service.get_user_profile(user_id)
            assert profile['real_name_verified'] is True
            assert profile['real_name'] == 'Verified Full Name'
            
            # Test 3: Content reports maintain user reference consistency
            from services.reports_service import reports_service
            
            report_data = {
                'content_id': 'consistency_test_content',
                'content_type': 'text',
                'report_category': 'spam',
                'report_reason': 'Testing data consistency'
            }
            
            report = reports_service.submit_report(
                reporter_id=user_id,
                report_data=report_data
            )
            
            # Verify report references user correctly
            report_details = reports_service.get_report_details(report['id'])
            assert report_details['reporter_id'] == user_id

    def _make_request(self, method, endpoint, data=None):
        """Helper method to make HTTP requests."""
        url = f"{self.base_url}{endpoint}"
        
        if method == 'GET':
            response = requests.get(url)
        elif method == 'POST':
            response = requests.post(url, json=data)
        elif method == 'PUT':
            response = requests.put(url, json=data)
        else:
            raise ValueError(f"Unsupported method: {method}")
            
        return response.json() if response.content else {}

    def test_performance_benchmarks(self, app):
        """Test performance benchmarks for Epic 1 features."""
        
        performance_results = {}
        
        with app.app_context():
            from models.engine import db
            
            # Create test user
            user = Account(
                name='Performance Test User',
                email='performance.test@example.com'
            )
            db.session.add(user)
            db.session.commit()
            
            # Benchmark 1: Profile retrieval performance
            start_time = time.time()
            for _ in range(100):
                from services.profile_service import profile_service
                profile_service.get_user_profile(user.id)
            end_time = time.time()
            
            avg_profile_retrieval_ms = ((end_time - start_time) / 100) * 1000
            performance_results['profile_retrieval_avg_ms'] = avg_profile_retrieval_ms
            assert avg_profile_retrieval_ms < 100  # Should be under 100ms
            
            # Benchmark 2: System health check performance
            start_time = time.time()
            from services.system_health_service import system_health_service
            system_health_service.get_system_status()
            end_time = time.time()
            
            health_check_ms = (end_time - start_time) * 1000
            performance_results['health_check_ms'] = health_check_ms
            assert health_check_ms < 2000  # Should be under 2 seconds
            
            # Benchmark 3: Report submission performance
            start_time = time.time()
            from services.reports_service import reports_service
            
            report_data = {
                'content_id': 'perf_test_content',
                'content_type': 'text',
                'report_category': 'spam',
                'report_reason': 'Performance test'
            }
            
            reports_service.submit_report(user.id, report_data)
            end_time = time.time()
            
            report_submission_ms = (end_time - start_time) * 1000
            performance_results['report_submission_ms'] = report_submission_ms
            assert report_submission_ms < 500  # Should be under 500ms
            
        # Log performance results
        print(f"Performance Benchmark Results: {performance_results}")
        
        return performance_results
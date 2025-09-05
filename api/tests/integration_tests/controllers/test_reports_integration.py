"""Integration tests for report functionality."""

import json
import pytest
from datetime import datetime, timedelta

from extensions.ext_database import db
from models.compliance import ContentReport, ReportStatus, ReportCategory
from models.account import Account


class TestReportIntegration:
    """Integration tests for the complete report workflow."""

    @pytest.fixture(autouse=True)
    def setup_database(self, app_context):
        """Set up test database."""
        db.create_all()
        yield
        db.session.rollback()
        db.drop_all()

    @pytest.fixture
    def test_user(self):
        """Create a test user."""
        user = Account(
            id="test_user_123",
            email="test@example.com",
            name="Test User"
        )
        db.session.add(user)
        db.session.commit()
        return user

    @pytest.fixture
    def admin_user(self):
        """Create a test admin user."""
        admin = Account(
            id="admin_user_123", 
            email="admin@example.com",
            name="Admin User"
        )
        db.session.add(admin)
        db.session.commit()
        return admin

    def test_complete_report_workflow(self, client, test_user, admin_user):
        """Test the complete report lifecycle from submission to resolution."""
        
        # Step 1: Submit a report
        submit_response = client.post('/api/reports/submit', data={
            'content_id': 'test_content_123',
            'content_type': 'text',
            'report_category': 'inappropriate_content',
            'report_reason': 'This content contains inappropriate language and should be reviewed.'
        })
        
        assert submit_response.status_code == 200
        submit_data = json.loads(submit_response.data)
        assert submit_data['success'] is True
        report_id = submit_data['report_id']
        
        # Verify report was created in database
        report = db.session.query(ContentReport).filter(ContentReport.id == report_id).first()
        assert report is not None
        assert report.content_id == 'test_content_123'
        assert report.content_type == 'text'
        assert report.report_category == 'inappropriate_content'
        assert report.status == 'pending'
        
        # Step 2: Get user's reports
        my_reports_response = client.get('/api/reports/my-reports')
        assert my_reports_response.status_code == 200
        
        my_reports_data = json.loads(my_reports_response.data)
        assert my_reports_data['success'] is True
        assert my_reports_data['total'] == 1
        assert len(my_reports_data['reports']) == 1
        assert my_reports_data['reports'][0]['id'] == report_id
        
        # Step 3: Admin views pending reports
        admin_reports_response = client.get('/api/reports/admin/reports?status=pending')
        assert admin_reports_response.status_code == 200
        
        admin_data = json.loads(admin_reports_response.data)
        assert admin_data['success'] is True
        assert admin_data['total'] == 1
        assert len(admin_data['reports']) == 1
        
        # Step 4: Admin updates report to reviewing
        review_response = client.put(f'/api/reports/admin/reports/{report_id}/status', 
                                   json={
                                       'status': 'reviewing',
                                       'notes': 'Under review by moderation team'
                                   })
        
        assert review_response.status_code == 200
        review_data = json.loads(review_response.data)
        assert review_data['success'] is True
        assert review_data['status'] == 'reviewing'
        
        # Verify status updated in database
        updated_report = db.session.query(ContentReport).filter(ContentReport.id == report_id).first()
        assert updated_report.status == 'reviewing'
        assert updated_report.moderator_notes == 'Under review by moderation team'
        
        # Step 5: Admin resolves the report
        resolve_response = client.put(f'/api/reports/admin/reports/{report_id}/status',
                                    json={
                                        'status': 'resolved',
                                        'notes': 'Content has been reviewed and appropriate action taken'
                                    })
        
        assert resolve_response.status_code == 200
        resolve_data = json.loads(resolve_response.data)
        assert resolve_data['success'] is True
        assert resolve_data['status'] == 'resolved'
        
        # Verify final status in database
        final_report = db.session.query(ContentReport).filter(ContentReport.id == report_id).first()
        assert final_report.status == 'resolved'
        assert final_report.resolved_at is not None
        assert final_report.moderator_notes == 'Content has been reviewed and appropriate action taken'
        
        # Step 6: Check user's reports shows resolved status
        final_user_reports = client.get('/api/reports/my-reports')
        final_data = json.loads(final_user_reports.data)
        assert final_data['reports'][0]['status'] == 'resolved'
        assert final_data['reports'][0]['resolved_at'] is not None

    def test_rate_limiting(self, client, test_user):
        """Test that rate limiting prevents spam reports."""
        
        # Submit maximum allowed reports (default is 10 per 24 hours)
        for i in range(10):
            response = client.post('/api/reports/submit', data={
                'content_id': f'content_{i}',
                'content_type': 'text',
                'report_category': 'spam',
                'report_reason': f'Spam report number {i}'
            })
            assert response.status_code == 200
        
        # The 11th report should be rate limited
        rate_limited_response = client.post('/api/reports/submit', data={
            'content_id': 'content_11',
            'content_type': 'text', 
            'report_category': 'spam',
            'report_reason': 'This should be rate limited'
        })
        
        assert rate_limited_response.status_code == 429
        data = json.loads(rate_limited_response.data)
        assert data['success'] is False
        assert data['error'] == 'rate_limit'

    def test_duplicate_report_prevention(self, client, test_user):
        """Test that duplicate reports for the same content are prevented."""
        
        # Submit initial report
        first_response = client.post('/api/reports/submit', data={
            'content_id': 'duplicate_test_content',
            'content_type': 'image',
            'report_category': 'inappropriate_content',
            'report_reason': 'First report for this content'
        })
        
        assert first_response.status_code == 200
        
        # Try to submit duplicate report
        duplicate_response = client.post('/api/reports/submit', data={
            'content_id': 'duplicate_test_content',
            'content_type': 'image',
            'report_category': 'inappropriate_content', 
            'report_reason': 'Duplicate report for same content'
        })
        
        assert duplicate_response.status_code == 409
        data = json.loads(duplicate_response.data)
        assert data['success'] is False
        assert data['error'] == 'duplicate_report'

    def test_report_filtering_and_pagination(self, client, test_user, admin_user):
        """Test report filtering and pagination functionality."""
        
        # Create multiple reports with different categories and statuses
        test_reports = [
            {'content_id': 'content_1', 'category': 'spam', 'status': 'pending'},
            {'content_id': 'content_2', 'category': 'inappropriate_content', 'status': 'pending'},
            {'content_id': 'content_3', 'category': 'spam', 'status': 'reviewing'},
            {'content_id': 'content_4', 'category': 'misinformation', 'status': 'resolved'},
            {'content_id': 'content_5', 'category': 'spam', 'status': 'dismissed'},
        ]
        
        report_ids = []
        for report_data in test_reports:
            # Submit report
            response = client.post('/api/reports/submit', data={
                'content_id': report_data['content_id'],
                'content_type': 'text',
                'report_category': report_data['category'],
                'report_reason': f'Test report for {report_data["content_id"]}'
            })
            
            assert response.status_code == 200
            data = json.loads(response.data)
            report_id = data['report_id']
            report_ids.append(report_id)
            
            # Update status if not pending
            if report_data['status'] != 'pending':
                client.put(f'/api/reports/admin/reports/{report_id}/status',
                          json={'status': report_data['status']})
        
        # Test filtering by status
        pending_response = client.get('/api/reports/admin/reports?status=pending')
        pending_data = json.loads(pending_response.data)
        assert pending_data['total'] == 2  # 2 pending reports
        
        # Test filtering by category
        spam_response = client.get('/api/reports/admin/reports?category=spam')
        spam_data = json.loads(spam_response.data)
        assert spam_data['total'] == 3  # 3 spam reports
        
        # Test combined filtering
        pending_spam_response = client.get('/api/reports/admin/reports?status=pending&category=spam')
        pending_spam_data = json.loads(pending_spam_response.data)
        assert pending_spam_data['total'] == 1  # 1 pending spam report
        
        # Test pagination
        page1_response = client.get('/api/reports/admin/reports?page=1&page_size=2')
        page1_data = json.loads(page1_response.data)
        assert len(page1_data['reports']) == 2
        assert page1_data['page'] == 1
        assert page1_data['total'] == 5
        
        page2_response = client.get('/api/reports/admin/reports?page=2&page_size=2')
        page2_data = json.loads(page2_response.data)
        assert len(page2_data['reports']) == 2
        assert page2_data['page'] == 2

    def test_report_content_snapshot(self, client, test_user):
        """Test that content snapshots are properly stored and retrieved."""
        
        content_snapshot = {
            'text_content': 'This is the original content that was reported',
            'timestamp': datetime.utcnow().isoformat(),
            'metadata': {
                'length': 50,
                'language': 'en'
            }
        }
        
        response = client.post('/api/reports/submit', data={
            'content_id': 'snapshot_test_content',
            'content_type': 'text',
            'report_category': 'misinformation',
            'report_reason': 'This content contains false information',
            'content_snapshot': json.dumps(content_snapshot)
        })
        
        assert response.status_code == 200
        data = json.loads(response.data)
        report_id = data['report_id']
        
        # Verify snapshot stored in database
        report = db.session.query(ContentReport).filter(ContentReport.id == report_id).first()
        assert report.content_snapshot is not None
        assert report.content_snapshot['text_content'] == content_snapshot['text_content']
        assert report.content_snapshot['metadata']['language'] == 'en'

    def test_error_handling(self, client):
        """Test various error conditions and proper error responses."""
        
        # Test missing required fields
        missing_fields_response = client.post('/api/reports/submit', data={
            'content_id': 'test_content'
            # Missing other required fields
        })
        
        assert missing_fields_response.status_code == 400
        data = json.loads(missing_fields_response.data)
        assert data['success'] is False
        assert data['error'] == 'validation_error'
        
        # Test invalid content type
        invalid_type_response = client.post('/api/reports/submit', data={
            'content_id': 'test_content',
            'content_type': 'invalid_type',
            'report_category': 'spam',
            'report_reason': 'Test reason'
        })
        
        assert invalid_type_response.status_code == 400
        
        # Test invalid report category
        invalid_category_response = client.post('/api/reports/submit', data={
            'content_id': 'test_content',
            'content_type': 'text',
            'report_category': 'invalid_category',
            'report_reason': 'Test reason'
        })
        
        assert invalid_category_response.status_code == 400
        
        # Test updating non-existent report
        nonexistent_response = client.put('/api/reports/admin/reports/nonexistent_id/status',
                                        json={'status': 'resolved'})
        
        assert nonexistent_response.status_code == 404
        data = json.loads(nonexistent_response.data)
        assert data['success'] is False
        assert data['error'] == 'not_found'

    def test_report_timestamps(self, client, test_user, admin_user):
        """Test that report timestamps are correctly managed."""
        
        # Record time before submission
        before_submit = datetime.utcnow()
        
        # Submit report
        response = client.post('/api/reports/submit', data={
            'content_id': 'timestamp_test',
            'content_type': 'text',
            'report_category': 'spam',
            'report_reason': 'Testing timestamp functionality'
        })
        
        after_submit = datetime.utcnow()
        
        assert response.status_code == 200
        data = json.loads(response.data)
        report_id = data['report_id']
        
        # Check report creation timestamp
        report = db.session.query(ContentReport).filter(ContentReport.id == report_id).first()
        assert before_submit <= report.created_at <= after_submit
        assert report.resolved_at is None
        
        # Record time before resolution
        before_resolve = datetime.utcnow()
        
        # Resolve the report
        resolve_response = client.put(f'/api/reports/admin/reports/{report_id}/status',
                                    json={'status': 'resolved'})
        
        after_resolve = datetime.utcnow()
        
        assert resolve_response.status_code == 200
        
        # Check resolution timestamp
        updated_report = db.session.query(ContentReport).filter(ContentReport.id == report_id).first()
        assert before_resolve <= updated_report.resolved_at <= after_resolve
        
        # Verify resolution time calculation
        resolution_time = updated_report.resolution_time_hours
        assert resolution_time is not None
        assert resolution_time > 0
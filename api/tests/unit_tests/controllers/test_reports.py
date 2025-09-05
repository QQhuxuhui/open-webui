"""Unit tests for report controllers."""

import json
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from controllers.reports import ReportService, bp
from models.compliance import ContentReport, ReportStatus, ReportCategory, ContentType


class TestReportService:
    """Test cases for ReportService."""

    def setup_method(self):
        """Set up test fixtures."""
        self.service = ReportService()

    @patch('controllers.reports.db.session')
    def test_check_rate_limit_within_limit(self, mock_db):
        """Test rate limiting when user is within limits."""
        # Mock query to return 5 reports
        mock_query = Mock()
        mock_query.filter.return_value.count.return_value = 5
        mock_db.query.return_value = mock_query

        result = self.service.check_rate_limit("user123")
        
        assert result is True
        mock_db.query.assert_called_once_with(ContentReport)

    @patch('controllers.reports.db.session')
    def test_check_rate_limit_exceeded(self, mock_db):
        """Test rate limiting when user exceeds limits."""
        # Mock query to return 15 reports (exceeds default limit of 10)
        mock_query = Mock()
        mock_query.filter.return_value.count.return_value = 15
        mock_db.query.return_value = mock_query

        result = self.service.check_rate_limit("user123")
        
        assert result is False

    @patch('controllers.reports.db.session')
    def test_check_duplicate_report_none_exists(self, mock_db):
        """Test duplicate check when no existing report."""
        # Mock query to return None
        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = None
        mock_db.query.return_value = mock_query

        result = self.service.check_duplicate_report("user123", "content456", "text")
        
        assert result is True

    @patch('controllers.reports.db.session')
    def test_check_duplicate_report_exists(self, mock_db):
        """Test duplicate check when existing report found."""
        # Mock query to return existing report
        mock_report = Mock()
        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = mock_report
        mock_db.query.return_value = mock_query

        result = self.service.check_duplicate_report("user123", "content456", "text")
        
        assert result is False

    @patch('controllers.reports.db.session')
    @patch('controllers.reports.logger')
    def test_create_report_success(self, mock_logger, mock_db):
        """Test successful report creation."""
        mock_report = Mock()
        mock_report.id = "report123"
        mock_db.add.return_value = None
        mock_db.commit.return_value = None
        mock_db.refresh.return_value = None

        with patch('controllers.reports.ContentReport', return_value=mock_report):
            result = self.service.create_report(
                user_id="user123",
                content_id="content456", 
                content_type="text",
                report_category="inappropriate_content",
                report_reason="This is inappropriate content"
            )

        assert result == mock_report
        mock_db.add.assert_called_once_with(mock_report)
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once_with(mock_report)
        mock_logger.info.assert_called_once()

    @patch('controllers.reports.db.session')
    def test_get_user_reports(self, mock_db):
        """Test getting user reports with pagination."""
        # Mock reports data
        mock_reports = [Mock() for _ in range(5)]
        mock_query = Mock()
        mock_query.filter.return_value.order_by.return_value = mock_query
        mock_query.count.return_value = 25
        mock_query.offset.return_value.limit.return_value.all.return_value = mock_reports
        mock_db.query.return_value = mock_query

        reports, total = self.service.get_user_reports("user123", page=2, page_size=10)
        
        assert len(reports) == 5
        assert total == 25
        mock_query.offset.assert_called_with(10)  # page 2 offset
        mock_query.limit.assert_called_with(10)

    @patch('controllers.reports.db.session')
    def test_get_reports_for_moderation_with_filters(self, mock_db):
        """Test getting reports for moderation with status and category filters."""
        mock_reports = [Mock() for _ in range(3)]
        mock_query = Mock()
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.count.return_value = 3
        mock_query.offset.return_value.limit.return_value.all.return_value = mock_reports
        mock_db.query.return_value = mock_query

        reports, total = self.service.get_reports_for_moderation(
            status="pending", 
            category="spam",
            page=1,
            page_size=20
        )
        
        assert len(reports) == 3
        assert total == 3
        # Should be called twice for status and category filters
        assert mock_query.filter.call_count == 2

    @patch('controllers.reports.db.session')
    @patch('controllers.reports.logger')
    def test_update_report_status_success(self, mock_logger, mock_db):
        """Test successful report status update."""
        mock_report = Mock()
        mock_report.id = "report123"
        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = mock_report
        mock_db.query.return_value = mock_query

        result = self.service.update_report_status(
            report_id="report123",
            new_status="resolved",
            moderator_id="moderator456",
            moderator_notes="Issue resolved"
        )

        assert result == mock_report
        assert mock_report.status == "resolved"
        assert mock_report.moderator_id == "moderator456"
        assert mock_report.moderator_notes == "Issue resolved"
        assert mock_report.resolved_at is not None
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once_with(mock_report)
        mock_logger.info.assert_called_once()

    @patch('controllers.reports.db.session')
    def test_update_report_status_not_found(self, mock_db):
        """Test updating non-existent report."""
        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = None
        mock_db.query.return_value = mock_query

        with pytest.raises(ValueError, match="Report not found"):
            self.service.update_report_status(
                report_id="nonexistent",
                new_status="resolved", 
                moderator_id="moderator456"
            )


class TestReportEndpoints:
    """Test cases for report API endpoints."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        from flask import Flask
        from flask.testing import FlaskClient
        
        app = Flask(__name__)
        app.register_blueprint(bp)
        app.config['TESTING'] = True
        
        return app.test_client()

    @patch('controllers.reports.ReportService')
    def test_submit_report_success(self, mock_service_class, client):
        """Test successful report submission."""
        # Mock service instance
        mock_service = Mock()
        mock_service.check_rate_limit.return_value = True
        mock_service.check_duplicate_report.return_value = True
        mock_report = Mock()
        mock_report.id = "report123"
        mock_service.create_report.return_value = mock_report
        mock_service_class.return_value = mock_service

        response = client.post('/api/reports/submit', data={
            'content_id': 'content123',
            'content_type': 'text',
            'report_category': 'inappropriate_content',
            'report_reason': 'This content is inappropriate'
        })

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert data['report_id'] == "report123"
        assert data['status'] == "submitted"

    @patch('controllers.reports.ReportService')
    def test_submit_report_rate_limited(self, mock_service_class, client):
        """Test report submission when rate limited."""
        # Mock service to return rate limit exceeded
        mock_service = Mock()
        mock_service.check_rate_limit.return_value = False
        mock_service_class.return_value = mock_service

        response = client.post('/api/reports/submit', data={
            'content_id': 'content123',
            'content_type': 'text',
            'report_category': 'spam',
            'report_reason': 'This is spam'
        })

        assert response.status_code == 429
        data = json.loads(response.data)
        assert data['success'] is False
        assert data['error'] == 'rate_limit'

    @patch('controllers.reports.ReportService')
    def test_submit_report_duplicate(self, mock_service_class, client):
        """Test report submission when duplicate exists."""
        mock_service = Mock()
        mock_service.check_rate_limit.return_value = True
        mock_service.check_duplicate_report.return_value = False
        mock_service_class.return_value = mock_service

        response = client.post('/api/reports/submit', data={
            'content_id': 'content123',
            'content_type': 'text', 
            'report_category': 'misinformation',
            'report_reason': 'This is misinformation'
        })

        assert response.status_code == 409
        data = json.loads(response.data)
        assert data['success'] is False
        assert data['error'] == 'duplicate_report'

    def test_submit_report_missing_fields(self, client):
        """Test report submission with missing required fields."""
        response = client.post('/api/reports/submit', data={
            'content_id': 'content123',
            # Missing required fields
        })

        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] is False
        assert data['error'] == 'validation_error'

    @patch('controllers.reports.ReportService')
    def test_get_my_reports_success(self, mock_service_class, client):
        """Test successful retrieval of user reports."""
        # Mock service and reports
        mock_service = Mock()
        mock_reports = [
            Mock(
                id="report1",
                content_id="content1", 
                content_type="text",
                report_category="spam",
                report_reason="Spam content",
                status="pending",
                created_at=datetime.now(),
                resolved_at=None
            ),
            Mock(
                id="report2",
                content_id="content2",
                content_type="image", 
                report_category="inappropriate_content",
                report_reason="Inappropriate image",
                status="resolved",
                created_at=datetime.now(),
                resolved_at=datetime.now()
            )
        ]
        mock_service.get_user_reports.return_value = (mock_reports, 2)
        mock_service_class.return_value = mock_service

        response = client.get('/api/reports/my-reports?page=1&page_size=10')

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert len(data['reports']) == 2
        assert data['total'] == 2
        assert data['page'] == 1
        assert data['page_size'] == 10

    def test_get_my_reports_invalid_pagination(self, client):
        """Test reports retrieval with invalid pagination parameters."""
        response = client.get('/api/reports/my-reports?page=0')

        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] is False
        assert data['error'] == 'validation_error'

    @patch('controllers.reports.ReportService')
    def test_get_admin_reports_success(self, mock_service_class, client):
        """Test successful admin reports retrieval."""
        mock_service = Mock()
        mock_reports = [Mock(
            id="report1",
            content_id="content1",
            content_type="text", 
            report_category="spam",
            report_reason="Spam content",
            status="pending",
            created_at=datetime.now(),
            resolved_at=None
        )]
        mock_service.get_reports_for_moderation.return_value = (mock_reports, 1)
        mock_service_class.return_value = mock_service

        response = client.get('/api/reports/admin/reports?status=pending')

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert len(data['reports']) == 1

    @patch('controllers.reports.ReportService') 
    def test_update_report_status_success(self, mock_service_class, client):
        """Test successful report status update."""
        mock_service = Mock()
        mock_report = Mock()
        mock_report.id = "report123"
        mock_report.status = "resolved"
        mock_report.updated_at = datetime.now()
        mock_service.update_report_status.return_value = mock_report
        mock_service_class.return_value = mock_service

        response = client.put('/api/reports/admin/reports/report123/status',
                             json={
                                 'status': 'resolved',
                                 'notes': 'Issue has been resolved'
                             })

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert data['report_id'] == "report123" 
        assert data['status'] == "resolved"

    @patch('controllers.reports.ReportService')
    def test_update_report_status_not_found(self, mock_service_class, client):
        """Test updating status of non-existent report."""
        mock_service = Mock()
        mock_service.update_report_status.side_effect = ValueError("Report not found")
        mock_service_class.return_value = mock_service

        response = client.put('/api/reports/admin/reports/nonexistent/status',
                             json={'status': 'resolved'})

        assert response.status_code == 404
        data = json.loads(response.data)
        assert data['success'] is False
        assert data['error'] == 'not_found'

    def test_update_report_status_invalid_status(self, client):
        """Test updating report with invalid status."""
        response = client.put('/api/reports/admin/reports/report123/status',
                             json={'status': 'invalid_status'})

        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] is False
        assert data['error'] == 'validation_error'

    def test_update_report_status_missing_data(self, client):
        """Test updating report status without request body."""
        response = client.put('/api/reports/admin/reports/report123/status')

        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] is False
        assert data['error'] == 'validation_error'
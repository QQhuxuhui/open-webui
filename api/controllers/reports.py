"""Report management controllers for content reporting system."""

import json
import logging
import os
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from werkzeug.datastructures import FileStorage

from flask import Blueprint, request, jsonify, current_app
from pydantic import BaseModel, Field, validator
from extensions.ext_database import db
from models.compliance import ContentReport, ReportCategory, ReportStatus, ContentType
from models.account import Account
from services.report_notification_service import ReportNotificationService

logger = logging.getLogger(__name__)
bp = Blueprint('reports', __name__, url_prefix='/api/reports')


class ReportSubmissionRequest(BaseModel):
    """Request model for content report submission."""
    content_id: str = Field(..., description="ID of the content being reported")
    content_type: str = Field(..., description="Type of content (text, image, video, audio)")
    report_category: str = Field(..., description="Category of the report")
    report_reason: str = Field(..., description="Detailed reason for the report", min_length=10, max_length=1000)
    content_snapshot: Optional[Dict[str, Any]] = Field(None, description="Snapshot of the reported content")

    @validator('content_type')
    def validate_content_type(cls, v):
        if v not in [ct.value for ct in ContentType]:
            raise ValueError(f'Invalid content type: {v}')
        return v

    @validator('report_category')
    def validate_report_category(cls, v):
        if v not in [rc.value for rc in ReportCategory]:
            raise ValueError(f'Invalid report category: {v}')
        return v


class ReportResponse(BaseModel):
    """Response model for report operations."""
    id: str
    content_id: str
    content_type: str
    report_category: str
    report_reason: str
    status: str
    created_at: datetime
    resolved_at: Optional[datetime] = None


class ReportListResponse(BaseModel):
    """Response model for report list operations."""
    reports: List[ReportResponse]
    total: int
    page: int
    page_size: int


class ReportService:
    """Service class for report operations."""
    
    def __init__(self):
        pass
    
    def check_rate_limit(self, user_id: str, time_window_hours: int = 24, max_reports: int = 10) -> bool:
        """Check if user has exceeded report rate limit."""
        since = datetime.utcnow() - timedelta(hours=time_window_hours)
        recent_reports_count = db.session.query(ContentReport).filter(
            ContentReport.reporter_id == user_id,
            ContentReport.created_at >= since
        ).count()
        return recent_reports_count < max_reports
    
    def check_duplicate_report(self, user_id: str, content_id: str, content_type: str) -> bool:
        """Check if user has already reported this specific content."""
        existing_report = db.session.query(ContentReport).filter(
            ContentReport.reporter_id == user_id,
            ContentReport.content_id == content_id,
            ContentReport.content_type == content_type,
            ContentReport.status.in_([ReportStatus.PENDING, ReportStatus.REVIEWING])
        ).first()
        return existing_report is None
    
    def create_report(
        self, 
        user_id: str, 
        content_id: str,
        content_type: str,
        report_category: str,
        report_reason: str,
        content_snapshot: Optional[Dict[str, Any]] = None,
        attachments: Optional[List[str]] = None
    ) -> ContentReport:
        """Create a new content report."""
        
        # Add attachment URLs to content snapshot if provided
        if attachments:
            if not content_snapshot:
                content_snapshot = {}
            content_snapshot['attachments'] = attachments
        
        report = ContentReport(
            reporter_id=user_id,
            content_id=content_id,
            content_type=content_type,
            report_category=report_category,
            report_reason=report_reason,
            content_snapshot=content_snapshot,
            status=ReportStatus.PENDING
        )
        
        db.session.add(report)
        db.session.commit()
        db.session.refresh(report)
        
        logger.info(f"Content report created: {report.id} by user {user_id} for content {content_id}")
        return report
    
    def get_user_reports(
        self, 
        user_id: str, 
        page: int = 1, 
        page_size: int = 20
    ) -> tuple[List[ContentReport], int]:
        """Get reports submitted by a specific user."""
        offset = (page - 1) * page_size
        
        query = db.session.query(ContentReport).filter(
            ContentReport.reporter_id == user_id
        ).order_by(ContentReport.created_at.desc())
        
        total = query.count()
        reports = query.offset(offset).limit(page_size).all()
        
        return reports, total
    
    def get_reports_for_moderation(
        self,
        status: Optional[str] = None,
        category: Optional[str] = None,
        page: int = 1,
        page_size: int = 20
    ) -> tuple[List[ContentReport], int]:
        """Get reports for moderation (admin use)."""
        offset = (page - 1) * page_size
        
        query = db.session.query(ContentReport)
        
        if status:
            query = query.filter(ContentReport.status == status)
        if category:
            query = query.filter(ContentReport.report_category == category)
            
        query = query.order_by(ContentReport.created_at.desc())
        
        total = query.count()
        reports = query.offset(offset).limit(page_size).all()
        
        return reports, total
    
    def update_report_status(
        self,
        report_id: str,
        new_status: str,
        moderator_id: str,
        moderator_notes: Optional[str] = None
    ) -> ContentReport:
        """Update report status and add moderator notes."""
        report = db.session.query(ContentReport).filter(ContentReport.id == report_id).first()
        if not report:
            raise ValueError("Report not found")
        
        old_status = report.status
        report.status = new_status
        report.moderator_id = moderator_id
        if moderator_notes:
            report.moderator_notes = moderator_notes
        
        if new_status in [ReportStatus.RESOLVED, ReportStatus.DISMISSED]:
            report.resolved_at = datetime.utcnow()
        
        db.session.commit()
        db.session.refresh(report)
        
        # Send notification about status change
        try:
            notification_service = ReportNotificationService()
            notification_service.notify_report_status_change(
                report=report,
                old_status=old_status,
                new_status=new_status,
                moderator_notes=moderator_notes
            )
        except Exception as e:
            logger.error(f"Failed to send notification for report {report_id}: {str(e)}")
            # Don't fail the status update if notification fails
        
        logger.info(f"Report {report_id} status updated to {new_status} by moderator {moderator_id}")
        return report


def handle_file_uploads(attachments: List[FileStorage]) -> List[str]:
    """Handle file uploads for report attachments."""
    # This is a simplified implementation - in production you'd want to:
    # 1. Store files in a secure location (S3, GCS, etc.)
    # 2. Scan files for malware
    # 3. Resize/optimize images
    # 4. Generate secure URLs
    
    uploaded_files = []
    max_files = 5
    max_file_size = 10 * 1024 * 1024  # 10MB
    allowed_types = {'image/jpeg', 'image/png', 'image/gif', 'image/webp', 'application/pdf', 'text/plain'}
    
    if len(attachments) > max_files:
        raise ValueError(f"Maximum {max_files} attachments allowed")
    
    for attachment in attachments:
        # Get file size by seeking to the end
        attachment.seek(0, 2)
        file_size = attachment.tell()
        attachment.seek(0)
        
        if file_size > max_file_size:
            raise ValueError(f"File {attachment.filename} exceeds 10MB limit")
        
        if attachment.content_type not in allowed_types:
            raise ValueError(f"File type {attachment.content_type} not allowed")
        
        # In a real implementation, you would store the file and return its URL
        # For now, we'll just return a placeholder URL
        file_url = f"/uploads/reports/{attachment.filename}"
        uploaded_files.append(file_url)
    
    return uploaded_files


@bp.route('/submit', methods=['POST'])
def submit_report():
    """Submit a new content report."""
    try:
        # TODO: Add proper authentication
        # For now using a mock user_id
        current_user_id = "mock_user_id"
        
        # Get form data
        content_id = request.form.get('content_id')
        content_type = request.form.get('content_type')
        report_category = request.form.get('report_category')
        report_reason = request.form.get('report_reason')
        content_snapshot = request.form.get('content_snapshot')
        
        if not all([content_id, content_type, report_category, report_reason]):
            return jsonify({
                'success': False,
                'error': 'validation_error',
                'message': 'Required fields missing'
            }), 400
        
        # Validate form data
        try:
            request_data = ReportSubmissionRequest(
                content_id=content_id,
                content_type=content_type,
                report_category=report_category,
                report_reason=report_reason,
                content_snapshot=json.loads(content_snapshot) if content_snapshot else None
            )
        except Exception as e:
            return jsonify({
                'success': False,
                'error': 'validation_error',
                'message': f"Invalid request data: {str(e)}"
            }), 400
        
        service = ReportService()
        
        # Check rate limiting
        if not service.check_rate_limit(current_user_id):
            return jsonify({
                'success': False,
                'error': 'rate_limit',
                'message': "Too many reports submitted. Please wait before submitting another report."
            }), 429
        
        # Check for duplicate reports
        if not service.check_duplicate_report(current_user_id, content_id, content_type):
            return jsonify({
                'success': False,
                'error': 'duplicate_report',
                'message': "You have already reported this content."
            }), 409
        
        # Handle file attachments
        attachment_urls = []
        attachments = request.files.getlist('attachments')
        if attachments:
            try:
                attachment_urls = handle_file_uploads(attachments)
            except ValueError as e:
                return jsonify({
                    'success': False,
                    'error': 'file_upload_error',
                    'message': str(e)
                }), 400
            except Exception as e:
                logger.error(f"File upload error: {str(e)}")
                return jsonify({
                    'success': False,
                    'error': 'internal_error',
                    'message': "Failed to process attachments"
                }), 500
        
        # Create the report
        try:
            report = service.create_report(
                user_id=current_user_id,
                content_id=request_data.content_id,
                content_type=request_data.content_type,
                report_category=request_data.report_category,
                report_reason=request_data.report_reason,
                content_snapshot=request_data.content_snapshot,
                attachments=attachment_urls if attachment_urls else None
            )
            
            return jsonify({
                'success': True,
                'report_id': report.id,
                'status': 'submitted'
            }), 200
        
        except Exception as e:
            logger.error(f"Failed to create report: {str(e)}")
            return jsonify({
                'success': False,
                'error': 'internal_error',
                'message': "Failed to submit report"
            }), 500
    
    except Exception as e:
        logger.error(f"Unexpected error in submit_report: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'internal_error',
            'message': "An unexpected error occurred"
        }), 500


@bp.route('/my-reports', methods=['GET'])
def get_my_reports():
    """Get reports submitted by the current user."""
    try:
        # TODO: Add proper authentication
        current_user_id = "mock_user_id"
        
        page = int(request.args.get('page', 1))
        page_size = int(request.args.get('page_size', 20))
        
        if page < 1:
            return jsonify({
                'success': False,
                'error': 'validation_error',
                'message': "Page must be >= 1"
            }), 400
        
        if page_size < 1 or page_size > 100:
            return jsonify({
                'success': False,
                'error': 'validation_error',
                'message': "Page size must be between 1 and 100"
            }), 400
        
        service = ReportService()
        reports, total = service.get_user_reports(current_user_id, page, page_size)
        
        report_responses = []
        for report in reports:
            report_responses.append({
                'id': report.id,
                'content_id': report.content_id,
                'content_type': report.content_type,
                'report_category': report.report_category,
                'report_reason': report.report_reason,
                'status': report.status,
                'created_at': report.created_at.isoformat(),
                'resolved_at': report.resolved_at.isoformat() if report.resolved_at else None
            })
        
        return jsonify({
            'success': True,
            'reports': report_responses,
            'total': total,
            'page': page,
            'page_size': page_size
        }), 200
    
    except Exception as e:
        logger.error(f"Error getting user reports: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'internal_error',
            'message': "Failed to get reports"
        }), 500


# Admin endpoints (will be moved to admin router in production)
@bp.route('/admin/reports', methods=['GET'])
def get_reports_for_admin():
    """Get reports for admin moderation."""
    try:
        # TODO: Add proper admin role check
        current_user_id = "mock_admin_user_id"
        
        status = request.args.get('status')
        category = request.args.get('category')
        page = int(request.args.get('page', 1))
        page_size = int(request.args.get('page_size', 20))
        
        service = ReportService()
        reports, total = service.get_reports_for_moderation(status, category, page, page_size)
        
        report_responses = []
        for report in reports:
            report_responses.append({
                'id': report.id,
                'content_id': report.content_id,
                'content_type': report.content_type,
                'report_category': report.report_category,
                'report_reason': report.report_reason,
                'status': report.status,
                'created_at': report.created_at.isoformat(),
                'resolved_at': report.resolved_at.isoformat() if report.resolved_at else None
            })
        
        return jsonify({
            'success': True,
            'reports': report_responses,
            'total': total,
            'page': page,
            'page_size': page_size
        }), 200
    
    except Exception as e:
        logger.error(f"Error getting reports for admin: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'internal_error',
            'message': "Failed to get reports"
        }), 500


@bp.route('/admin/reports/<report_id>/status', methods=['PUT'])
def update_report_status(report_id: str):
    """Update report status (admin only)."""
    try:
        # TODO: Add proper admin role check
        current_user_id = "mock_admin_user_id"
        
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'error': 'validation_error',
                'message': 'Request body required'
            }), 400
        
        status = data.get('status')
        notes = data.get('notes')
        
        if not status:
            return jsonify({
                'success': False,
                'error': 'validation_error',
                'message': 'Status is required'
            }), 400
        
        if status not in [rs.value for rs in ReportStatus]:
            return jsonify({
                'success': False,
                'error': 'validation_error',
                'message': f"Invalid status: {status}"
            }), 400
        
        service = ReportService()
        
        try:
            report = service.update_report_status(
                report_id=report_id,
                new_status=status,
                moderator_id=current_user_id,
                moderator_notes=notes
            )
            
            return jsonify({
                'success': True,
                'report_id': report.id,
                'status': report.status,
                'updated_at': report.updated_at.isoformat()
            }), 200
        
        except ValueError as e:
            return jsonify({
                'success': False,
                'error': 'not_found',
                'message': str(e)
            }), 404
    
    except Exception as e:
        logger.error(f"Failed to update report status: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'internal_error',
            'message': "Failed to update report"
        }), 500


@bp.route('/statistics', methods=['GET'])
def get_report_statistics():
    """Get report statistics for dashboard."""
    try:
        # TODO: Add proper admin role check
        current_user_id = "mock_admin_user_id"
        
        time_window = int(request.args.get('days', 30))
        
        notification_service = ReportNotificationService()
        stats = notification_service.get_report_statistics(time_window_days=time_window)
        
        return jsonify({
            'success': True,
            'statistics': stats
        }), 200
    
    except Exception as e:
        logger.error(f"Error getting report statistics: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'internal_error',
            'message': "Failed to get statistics"
        }), 500


@bp.route('/user-feedback/<user_id>', methods=['GET'])
def get_user_feedback(user_id: str):
    """Get feedback summary for a specific user."""
    try:
        # TODO: Add proper authorization check
        current_user_id = "mock_admin_user_id"
        
        notification_service = ReportNotificationService()
        feedback = notification_service.get_user_feedback_summary(user_id)
        
        return jsonify({
            'success': True,
            'feedback': feedback
        }), 200
    
    except Exception as e:
        logger.error(f"Error getting user feedback for {user_id}: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'internal_error',
            'message': "Failed to get user feedback"
        }), 500
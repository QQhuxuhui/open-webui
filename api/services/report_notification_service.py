"""Report notification service for handling report status updates and user feedback."""

import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta

from extensions.ext_database import db
from models.compliance import ContentReport, ReportStatus
from models.account import Account

logger = logging.getLogger(__name__)


class ReportNotificationService:
    """Service for managing report notifications and feedback."""

    def __init__(self):
        """Initialize the notification service."""
        pass

    def notify_report_status_change(
        self,
        report: ContentReport,
        old_status: str,
        new_status: str,
        moderator_notes: Optional[str] = None
    ) -> bool:
        """
        Notify reporter about status change.
        
        Args:
            report: The ContentReport instance
            old_status: Previous status
            new_status: New status
            moderator_notes: Optional notes from moderator
            
        Returns:
            bool: True if notification was sent successfully
        """
        try:
            # Get reporter information
            reporter = db.session.query(Account).filter(Account.id == report.reporter_id).first()
            if not reporter:
                logger.warning(f"Reporter not found for report {report.id}")
                return False

            # Determine notification type based on status change
            notification_data = self._get_notification_data(old_status, new_status, report, moderator_notes)
            
            if not notification_data:
                logger.debug(f"No notification needed for status change {old_status} -> {new_status}")
                return True

            # Send notification (in a real implementation, this would integrate with your notification system)
            success = self._send_notification(
                user=reporter,
                notification_type=notification_data['type'],
                title=notification_data['title'],
                message=notification_data['message'],
                report_id=report.id,
                metadata={
                    'old_status': old_status,
                    'new_status': new_status,
                    'content_id': report.content_id,
                    'content_type': report.content_type,
                    'report_category': report.report_category,
                    'moderator_notes': moderator_notes
                }
            )

            if success:
                logger.info(f"Notification sent to user {reporter.id} for report {report.id} status change")
            else:
                logger.error(f"Failed to send notification to user {reporter.id} for report {report.id}")

            return success

        except Exception as e:
            logger.error(f"Error sending notification for report {report.id}: {str(e)}")
            return False

    def _get_notification_data(
        self,
        old_status: str,
        new_status: str,
        report: ContentReport,
        moderator_notes: Optional[str] = None
    ) -> Optional[Dict[str, str]]:
        """
        Get notification data based on status change.
        
        Args:
            old_status: Previous status
            new_status: New status
            report: The ContentReport instance
            moderator_notes: Optional moderator notes
            
        Returns:
            Dict with notification type, title, and message, or None if no notification needed
        """
        # Map status changes to notification templates
        status_change_templates = {
            ('pending', 'reviewing'): {
                'type': 'report_under_review',
                'title': 'Report Under Review',
                'message': 'Your report is now being reviewed by our moderation team. We will update you when a decision is made.'
            },
            ('pending', 'resolved'): {
                'type': 'report_resolved',
                'title': 'Report Resolved',
                'message': 'Thank you for your report. We have reviewed the content and taken appropriate action.'
            },
            ('pending', 'dismissed'): {
                'type': 'report_dismissed',
                'title': 'Report Dismissed',
                'message': 'We have reviewed your report and determined that no action is required at this time.'
            },
            ('reviewing', 'resolved'): {
                'type': 'report_resolved',
                'title': 'Report Resolved',
                'message': 'Your report has been resolved. Thank you for helping us maintain content quality.'
            },
            ('reviewing', 'dismissed'): {
                'type': 'report_dismissed',
                'title': 'Report Dismissed',
                'message': 'After review, we have determined that no action is required for your report.'
            }
        }

        template = status_change_templates.get((old_status, new_status))
        if not template:
            return None

        # Customize message with moderator notes if provided
        message = template['message']
        if moderator_notes and new_status in ['resolved', 'dismissed']:
            message += f"\n\nModeration team notes: {moderator_notes}"

        return {
            'type': template['type'],
            'title': template['title'],
            'message': message
        }

    def _send_notification(
        self,
        user: Account,
        notification_type: str,
        title: str,
        message: str,
        report_id: str,
        metadata: Dict[str, Any]
    ) -> bool:
        """
        Send notification to user.
        
        In a production implementation, this would integrate with your notification system
        (email, push notifications, in-app notifications, etc.).
        
        Args:
            user: User to notify
            notification_type: Type of notification
            title: Notification title
            message: Notification message
            report_id: Related report ID
            metadata: Additional metadata
            
        Returns:
            bool: True if notification was sent successfully
        """
        # This is a mock implementation. In production, you would:
        # 1. Check user notification preferences
        # 2. Send via email, push notification, or in-app notification
        # 3. Store notification in database
        # 4. Handle delivery failures and retries

        logger.info(f"Mock notification sent to {user.email}:")
        logger.info(f"  Type: {notification_type}")
        logger.info(f"  Title: {title}")
        logger.info(f"  Message: {message}")
        logger.info(f"  Report ID: {report_id}")
        logger.info(f"  Metadata: {metadata}")

        # Simulate successful delivery
        return True

    def get_report_statistics(self, time_window_days: int = 30) -> Dict[str, Any]:
        """
        Get report statistics for the specified time window.
        
        Args:
            time_window_days: Number of days to look back
            
        Returns:
            Dict with report statistics
        """
        try:
            since = datetime.utcnow() - timedelta(days=time_window_days)
            
            # Total reports in time window
            total_reports = db.session.query(ContentReport).filter(
                ContentReport.created_at >= since
            ).count()

            # Reports by status
            status_counts = {}
            for status in ReportStatus:
                count = db.session.query(ContentReport).filter(
                    ContentReport.created_at >= since,
                    ContentReport.status == status.value
                ).count()
                status_counts[status.value] = count

            # Reports by category
            category_counts = db.session.query(
                ContentReport.report_category,
                db.func.count(ContentReport.id).label('count')
            ).filter(
                ContentReport.created_at >= since
            ).group_by(ContentReport.report_category).all()

            category_stats = {cat: count for cat, count in category_counts}

            # Average resolution time for resolved reports
            resolved_reports = db.session.query(ContentReport).filter(
                ContentReport.created_at >= since,
                ContentReport.status == ReportStatus.RESOLVED,
                ContentReport.resolved_at.isnot(None)
            ).all()

            avg_resolution_time = None
            if resolved_reports:
                total_time = sum(report.resolution_time_hours or 0 for report in resolved_reports)
                avg_resolution_time = total_time / len(resolved_reports)

            return {
                'time_window_days': time_window_days,
                'total_reports': total_reports,
                'status_breakdown': status_counts,
                'category_breakdown': category_stats,
                'average_resolution_time_hours': avg_resolution_time,
                'resolution_rate': (
                    (status_counts.get('resolved', 0) + status_counts.get('dismissed', 0)) / 
                    max(total_reports, 1) * 100
                ),
                'pending_reports': status_counts.get('pending', 0),
                'active_reports': status_counts.get('reviewing', 0)
            }

        except Exception as e:
            logger.error(f"Error calculating report statistics: {str(e)}")
            return {}

    def get_user_feedback_summary(self, reporter_id: str) -> Dict[str, Any]:
        """
        Get feedback summary for a specific reporter.
        
        Args:
            reporter_id: ID of the reporter
            
        Returns:
            Dict with user's reporting history and feedback
        """
        try:
            # Get all reports by this user
            user_reports = db.session.query(ContentReport).filter(
                ContentReport.reporter_id == reporter_id
            ).order_by(ContentReport.created_at.desc()).all()

            if not user_reports:
                return {
                    'reporter_id': reporter_id,
                    'total_reports': 0,
                    'reports_by_status': {},
                    'reports_by_category': {},
                    'recent_reports': []
                }

            # Calculate statistics
            total_reports = len(user_reports)
            
            status_breakdown = {}
            category_breakdown = {}
            
            for report in user_reports:
                # Status breakdown
                status_breakdown[report.status] = status_breakdown.get(report.status, 0) + 1
                
                # Category breakdown
                category_breakdown[report.report_category] = category_breakdown.get(report.report_category, 0) + 1

            # Get recent reports (last 5)
            recent_reports = []
            for report in user_reports[:5]:
                recent_reports.append({
                    'id': report.id,
                    'content_id': report.content_id,
                    'content_type': report.content_type,
                    'category': report.report_category,
                    'status': report.status,
                    'created_at': report.created_at.isoformat(),
                    'resolved_at': report.resolved_at.isoformat() if report.resolved_at else None
                })

            return {
                'reporter_id': reporter_id,
                'total_reports': total_reports,
                'reports_by_status': status_breakdown,
                'reports_by_category': category_breakdown,
                'recent_reports': recent_reports,
                'last_report_date': user_reports[0].created_at.isoformat() if user_reports else None
            }

        except Exception as e:
            logger.error(f"Error getting user feedback summary for {reporter_id}: {str(e)}")
            return {'error': str(e)}

    def send_bulk_notifications(
        self,
        report_ids: List[str],
        notification_type: str,
        title: str,
        message: str
    ) -> Dict[str, Any]:
        """
        Send bulk notifications for multiple reports.
        
        Args:
            report_ids: List of report IDs
            notification_type: Type of notification
            title: Notification title
            message: Notification message
            
        Returns:
            Dict with summary of notification results
        """
        try:
            sent_count = 0
            failed_count = 0
            failed_reports = []

            for report_id in report_ids:
                report = db.session.query(ContentReport).filter(ContentReport.id == report_id).first()
                if not report:
                    failed_count += 1
                    failed_reports.append({'report_id': report_id, 'error': 'Report not found'})
                    continue

                reporter = db.session.query(Account).filter(Account.id == report.reporter_id).first()
                if not reporter:
                    failed_count += 1
                    failed_reports.append({'report_id': report_id, 'error': 'Reporter not found'})
                    continue

                success = self._send_notification(
                    user=reporter,
                    notification_type=notification_type,
                    title=title,
                    message=message,
                    report_id=report_id,
                    metadata={'bulk_notification': True}
                )

                if success:
                    sent_count += 1
                else:
                    failed_count += 1
                    failed_reports.append({'report_id': report_id, 'error': 'Notification delivery failed'})

            return {
                'total_reports': len(report_ids),
                'notifications_sent': sent_count,
                'notifications_failed': failed_count,
                'failed_reports': failed_reports
            }

        except Exception as e:
            logger.error(f"Error sending bulk notifications: {str(e)}")
            return {'error': str(e)}
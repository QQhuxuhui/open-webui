"""AI Labels Configuration API Controllers."""

import logging
from typing import Optional, Dict, Any
from flask import Blueprint, request, jsonify
from pydantic import BaseModel, validator

from services.ai_labeling_service import AILabelingService
from models.model import Message
from extensions.ext_database import db

logger = logging.getLogger(__name__)

bp = Blueprint('ai_labels_config', __name__, url_prefix='/api/config')


class AILabelRequest(BaseModel):
    """Request model for AI labeling operations."""
    message_id: str
    language: Optional[str] = 'en'
    force_ai_generated: Optional[bool] = None
    
    @validator('language')
    def validate_language(cls, v):
        """Validate language code."""
        if v and len(v) > 10:
            raise ValueError('Language code too long')
        return v


class BulkLabelRequest(BaseModel):
    """Request model for bulk labeling operations."""
    message_ids: list
    model_provider: Optional[str] = None
    language: str = 'en'
    batch_size: Optional[int] = 100
    
    @validator('message_ids')
    def validate_message_ids(cls, v):
        """Validate message IDs list."""
        if not v:
            raise ValueError('Message IDs list cannot be empty')
        if len(v) > 1000:
            raise ValueError('Cannot process more than 1000 messages at once')
        return v
    
    @validator('batch_size')
    def validate_batch_size(cls, v):
        """Validate batch size."""
        if v and (v < 1 or v > 500):
            raise ValueError('Batch size must be between 1 and 500')
        return v


@bp.route('/ai-labels', methods=['GET'])
def get_ai_labels():
    """
    Get AI content labels configuration.
    
    Query Parameters:
    - language: Language code (optional, defaults to 'en')
    
    Returns:
        JSON response with AI labels in requested language
    """
    try:
        language = request.args.get('language', 'en')
        
        ai_labeling_service = AILabelingService()
        labels = ai_labeling_service.get_ai_labels(language)
        
        return jsonify({
            'success': True,
            'language': language,
            'labels': labels,
            'supported_languages': list(ai_labeling_service.DEFAULT_LABELS.keys())
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting AI labels: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'internal_error',
            'message': 'Failed to get AI labels configuration'
        }), 500


@bp.route('/ai-labels/all', methods=['GET'])
def get_all_ai_labels():
    """
    Get AI content labels for all supported languages.
    
    Returns:
        JSON response with AI labels in all languages
    """
    try:
        ai_labeling_service = AILabelingService()
        
        all_labels = {}
        for language in ai_labeling_service.DEFAULT_LABELS.keys():
            all_labels[language] = ai_labeling_service.get_ai_labels(language)
        
        return jsonify({
            'success': True,
            'labels': all_labels,
            'supported_languages': list(ai_labeling_service.DEFAULT_LABELS.keys())
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting all AI labels: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'internal_error',
            'message': 'Failed to get AI labels configuration'
        }), 500


@bp.route('/ai-labels/apply', methods=['POST'])
def apply_ai_labeling():
    """
    Apply AI labeling to a specific message.
    
    Expected JSON payload:
    {
        "message_id": "uuid",
        "language": "en",
        "force_ai_generated": true
    }
    
    Returns:
        JSON response with labeling result
    """
    try:
        # Parse and validate request
        try:
            data = AILabelRequest(**request.json)
        except ValueError as e:
            return jsonify({
                'success': False,
                'error': 'validation_error',
                'message': str(e)
            }), 400
        
        ai_labeling_service = AILabelingService()
        
        # Apply labeling to message
        success = ai_labeling_service.apply_ai_labeling(
            message_id=data.message_id,
            language=data.language,
            force_ai_generated=data.force_ai_generated
        )
        
        if success:
            # Get updated label information
            label_info = ai_labeling_service.get_message_labels(
                data.message_id, 
                data.language
            )
            
            return jsonify({
                'success': True,
                'message': 'AI labeling applied successfully',
                'label_info': label_info
            }), 200
        else:
            return jsonify({
                'success': False,
                'error': 'labeling_failed',
                'message': 'Failed to apply AI labeling'
            }), 500
        
    except Exception as e:
        logger.error(f"Error applying AI labeling: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'internal_error',
            'message': 'Failed to apply AI labeling'
        }), 500


@bp.route('/ai-labels/bulk-apply', methods=['POST'])
def bulk_apply_ai_labeling():
    """
    Apply AI labeling to multiple messages.
    
    Expected JSON payload:
    {
        "message_ids": ["uuid1", "uuid2"],
        "model_provider": "openai",
        "language": "en",
        "batch_size": 100
    }
    
    Returns:
        JSON response with bulk labeling results
    """
    try:
        # Parse and validate request
        try:
            data = BulkLabelRequest(**request.json)
        except ValueError as e:
            return jsonify({
                'success': False,
                'error': 'validation_error',
                'message': str(e)
            }), 400
        
        ai_labeling_service = AILabelingService()
        
        # Apply bulk labeling
        results = ai_labeling_service.bulk_apply_labeling(
            message_ids=data.message_ids,
            model_provider=data.model_provider,
            language=data.language,
            batch_size=data.batch_size or 100
        )
        
        return jsonify({
            'success': True,
            'message': 'Bulk AI labeling completed',
            'results': results
        }), 200
        
    except Exception as e:
        logger.error(f"Error in bulk AI labeling: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'internal_error',
            'message': 'Failed to apply bulk AI labeling'
        }), 500


@bp.route('/ai-labels/message/<message_id>', methods=['GET'])
def get_message_labels(message_id: str):
    """
    Get AI labels for a specific message.
    
    Path Parameters:
    - message_id: Message UUID
    
    Query Parameters:
    - language: Language code (optional)
    
    Returns:
        JSON response with message AI labels
    """
    try:
        language = request.args.get('language')
        
        ai_labeling_service = AILabelingService()
        label_info = ai_labeling_service.get_message_labels(message_id, language)
        
        if label_info is None:
            return jsonify({
                'success': False,
                'error': 'not_found',
                'message': 'Message not found or not AI-generated'
            }), 404
        
        return jsonify({
            'success': True,
            'message_id': message_id,
            'label_info': label_info
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting message labels: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'internal_error',
            'message': 'Failed to get message labels'
        }), 500


@bp.route('/ai-labels/stats', methods=['GET'])
def get_labeling_stats():
    """
    Get AI content labeling statistics.
    
    Returns:
        JSON response with labeling statistics
    """
    try:
        ai_labeling_service = AILabelingService()
        stats = ai_labeling_service.get_labeling_stats()
        
        return jsonify({
            'success': True,
            'stats': stats,
            'timestamp': db.func.current_timestamp()
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting labeling stats: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'internal_error',
            'message': 'Failed to get labeling statistics'
        }), 500


@bp.route('/ai-labels/detect', methods=['POST'])
def detect_ai_content():
    """
    Detect if content is AI-generated.
    
    Expected JSON payload:
    {
        "content": "Text content to analyze",
        "model_provider": "openai",
        "model_id": "gpt-4"
    }
    
    Returns:
        JSON response with detection result
    """
    try:
        data = request.json
        content = data.get('content', '')
        model_provider = data.get('model_provider')
        model_id = data.get('model_id')
        
        if not content:
            return jsonify({
                'success': False,
                'error': 'validation_error',
                'message': 'Content is required'
            }), 400
        
        ai_labeling_service = AILabelingService()
        is_ai_generated = ai_labeling_service.detect_ai_content(
            content=content,
            model_provider=model_provider,
            model_id=model_id
        )
        
        return jsonify({
            'success': True,
            'content_preview': content[:100] + ('...' if len(content) > 100 else ''),
            'is_ai_generated': is_ai_generated,
            'detection_factors': {
                'has_model_provider': bool(model_provider),
                'has_model_id': bool(model_id),
                'content_length': len(content)
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Error detecting AI content: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'internal_error',
            'message': 'Failed to detect AI content'
        }), 500


@bp.route('/ai-labels/health', methods=['GET'])
def ai_labeling_health():
    """
    Health check endpoint for AI labeling service.
    
    Returns:
        JSON response with service health status
    """
    try:
        ai_labeling_service = AILabelingService()
        
        # Test basic functionality
        test_labels = ai_labeling_service.get_ai_labels('en')
        test_detection = ai_labeling_service.detect_ai_content(
            'Test content', 'test_provider', 'test_model'
        )
        
        return jsonify({
            'success': True,
            'service': 'ai_labeling_service',
            'status': 'healthy',
            'features': {
                'multi_language_support': len(ai_labeling_service.DEFAULT_LABELS),
                'content_detection': bool(test_detection),
                'label_generation': bool(test_labels)
            },
            'supported_languages': list(ai_labeling_service.DEFAULT_LABELS.keys())
        }), 200
        
    except Exception as e:
        logger.error(f"AI labeling health check failed: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'service': 'ai_labeling_service',
            'status': 'unhealthy',
            'error': str(e)
        }), 500
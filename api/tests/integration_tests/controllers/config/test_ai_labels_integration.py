"""Integration tests for AI Labels Configuration API."""

import pytest
import json
from datetime import datetime
from unittest.mock import patch

from controllers.config.ai_labels import bp
from models.model import Message
from services.ai_labeling_service import AILabelingService
from extensions.ext_database import db


class TestAILabelsIntegration:
    """Integration tests for AI labels API endpoints."""
    
    @pytest.fixture(autouse=True)
    def setup_method(self, app_with_db):
        """Set up test method."""
        self.app = app_with_db
        self.client = app_with_db.test_client()
        
        with app_with_db.app_context():
            # Clean up database
            db.session.query(Message).delete()
            db.session.commit()
    
    def test_get_ai_labels_default_language(self):
        """Test getting AI labels for default language."""
        response = self.client.get('/api/config/ai-labels')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        
        assert data['success'] is True
        assert 'labels' in data
        assert 'supported_languages' in data
        assert 'text_notice' in data['labels']
        assert 'watermark_text' in data['labels']
    
    def test_get_ai_labels_specific_language(self):
        """Test getting AI labels for specific language."""
        response = self.client.get('/api/config/ai-labels?language=zh')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        
        assert data['success'] is True
        assert data['language'] == 'zh'
        assert '内容由AI生成' in data['labels']['text_notice']
    
    def test_get_all_ai_labels(self):
        """Test getting all AI labels."""
        response = self.client.get('/api/config/ai-labels/all')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        
        assert data['success'] is True
        assert 'labels' in data
        assert 'en' in data['labels']
        assert 'zh' in data['labels']
        assert len(data['supported_languages']) > 0
    
    @patch('controllers.config.ai_labels.AILabelingService')
    def test_apply_ai_labeling_success(self, mock_service_class):
        """Test successful AI labeling application."""
        # Mock service
        mock_service = mock_service_class.return_value
        mock_service.apply_ai_labeling.return_value = True
        mock_service.get_message_labels.return_value = {
            'ai_generated': True,
            'ai_model_info': {'provider': 'openai', 'model_id': 'gpt-4'},
            'content_labels': {'generated_content_notice': 'AI generated content'}
        }
        
        request_data = {
            'message_id': 'test-message-id',
            'language': 'en',
            'force_ai_generated': True
        }
        
        response = self.client.post(
            '/api/config/ai-labels/apply',
            data=json.dumps(request_data),
            content_type='application/json'
        )
        
        assert response.status_code == 200
        data = json.loads(response.data)
        
        assert data['success'] is True
        assert 'label_info' in data
        assert data['label_info']['ai_generated'] is True
    
    def test_apply_ai_labeling_invalid_request(self):
        """Test AI labeling application with invalid request."""
        request_data = {
            'message_id': '',  # Invalid empty message ID
            'language': 'en'
        }
        
        response = self.client.post(
            '/api/config/ai-labels/apply',
            data=json.dumps(request_data),
            content_type='application/json'
        )
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] is False
        assert data['error'] == 'validation_error'
    
    @patch('controllers.config.ai_labels.AILabelingService')
    def test_bulk_apply_ai_labeling_success(self, mock_service_class):
        """Test successful bulk AI labeling."""
        # Mock service
        mock_service = mock_service_class.return_value
        mock_service.bulk_apply_labeling.return_value = {
            'total_processed': 3,
            'total_labeled': 2,
            'total_errors': 1
        }
        
        request_data = {
            'message_ids': ['msg1', 'msg2', 'msg3'],
            'model_provider': 'openai',
            'language': 'en'
        }
        
        response = self.client.post(
            '/api/config/ai-labels/bulk-apply',
            data=json.dumps(request_data),
            content_type='application/json'
        )
        
        assert response.status_code == 200
        data = json.loads(response.data)
        
        assert data['success'] is True
        assert data['results']['total_processed'] == 3
        assert data['results']['total_labeled'] == 2
    
    def test_bulk_apply_ai_labeling_invalid_request(self):
        """Test bulk AI labeling with invalid request."""
        request_data = {
            'message_ids': [],  # Empty list
            'language': 'en'
        }
        
        response = self.client.post(
            '/api/config/ai-labels/bulk-apply',
            data=json.dumps(request_data),
            content_type='application/json'
        )
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] is False
        assert data['error'] == 'validation_error'
    
    def test_bulk_apply_too_many_messages(self):
        """Test bulk labeling with too many messages."""
        # Generate list of 1001 message IDs (exceeds limit)
        message_ids = [f'msg{i}' for i in range(1001)]
        
        request_data = {
            'message_ids': message_ids,
            'language': 'en'
        }
        
        response = self.client.post(
            '/api/config/ai-labels/bulk-apply',
            data=json.dumps(request_data),
            content_type='application/json'
        )
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] is False
        assert 'Cannot process more than 1000' in data['message']
    
    @patch('controllers.config.ai_labels.AILabelingService')
    def test_get_message_labels_success(self, mock_service_class):
        """Test getting message labels successfully."""
        # Mock service
        mock_service = mock_service_class.return_value
        mock_service.get_message_labels.return_value = {
            'ai_generated': True,
            'ai_model_info': {'provider': 'openai'},
            'content_labels': {'generated_content_notice': 'AI content'}
        }
        
        response = self.client.get('/api/config/ai-labels/message/test-message-id')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        
        assert data['success'] is True
        assert data['message_id'] == 'test-message-id'
        assert data['label_info']['ai_generated'] is True
    
    @patch('controllers.config.ai_labels.AILabelingService')
    def test_get_message_labels_not_found(self, mock_service_class):
        """Test getting labels for non-existent or non-AI message."""
        # Mock service
        mock_service = mock_service_class.return_value
        mock_service.get_message_labels.return_value = None
        
        response = self.client.get('/api/config/ai-labels/message/nonexistent-id')
        
        assert response.status_code == 404
        data = json.loads(response.data)
        assert data['success'] is False
        assert data['error'] == 'not_found'
    
    @patch('controllers.config.ai_labels.AILabelingService')
    def test_get_labeling_stats(self, mock_service_class):
        """Test getting labeling statistics."""
        # Mock service
        mock_service = mock_service_class.return_value
        mock_service.get_labeling_stats.return_value = {
            'total_messages': 100,
            'ai_generated_messages': 75,
            'labeled_messages': 80,
            'labeling_rate': 80.0,
            'ai_detection_rate': 75.0
        }
        
        response = self.client.get('/api/config/ai-labels/stats')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        
        assert data['success'] is True
        assert data['stats']['total_messages'] == 100
        assert data['stats']['labeling_rate'] == 80.0
    
    @patch('controllers.config.ai_labels.AILabelingService')
    def test_detect_ai_content_success(self, mock_service_class):
        """Test AI content detection."""
        # Mock service
        mock_service = mock_service_class.return_value
        mock_service.detect_ai_content.return_value = True
        
        request_data = {
            'content': 'As an AI, I can help you with that task.',
            'model_provider': 'openai',
            'model_id': 'gpt-4'
        }
        
        response = self.client.post(
            '/api/config/ai-labels/detect',
            data=json.dumps(request_data),
            content_type='application/json'
        )
        
        assert response.status_code == 200
        data = json.loads(response.data)
        
        assert data['success'] is True
        assert data['is_ai_generated'] is True
        assert 'detection_factors' in data
        assert 'content_preview' in data
    
    def test_detect_ai_content_missing_content(self):
        """Test AI detection with missing content."""
        request_data = {
            'model_provider': 'openai'
        }
        
        response = self.client.post(
            '/api/config/ai-labels/detect',
            data=json.dumps(request_data),
            content_type='application/json'
        )
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] is False
        assert data['error'] == 'validation_error'
        assert 'Content is required' in data['message']
    
    def test_ai_labeling_health_check(self):
        """Test AI labeling service health check."""
        response = self.client.get('/api/config/ai-labels/health')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        
        assert data['success'] is True
        assert data['service'] == 'ai_labeling_service'
        assert data['status'] == 'healthy'
        assert 'features' in data
        assert 'supported_languages' in data
    
    def test_complete_ai_labeling_workflow(self):
        """Test complete AI labeling workflow from detection to display."""
        with self.app.app_context():
            # 1. Create a test message
            test_message = Message(
                app_id='test-app',
                conversation_id='test-conversation',
                query='Test query',
                answer='As an AI language model, I can help you with coding tasks.',
                message_tokens=10,
                answer_tokens=15,
                message_unit_price=0.001,
                answer_unit_price=0.002,
                total_price=0.003,
                currency='USD',
                from_source='api',
                model_provider='openai',
                model_id='gpt-4',
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            
            db.session.add(test_message)
            db.session.commit()
            message_id = test_message.id
        
        # 2. Detect AI content
        detect_data = {
            'content': test_message.answer,
            'model_provider': 'openai',
            'model_id': 'gpt-4'
        }
        
        response = self.client.post(
            '/api/config/ai-labels/detect',
            data=json.dumps(detect_data),
            content_type='application/json'
        )
        
        assert response.status_code == 200
        detect_result = json.loads(response.data)
        assert detect_result['is_ai_generated'] is True
        
        # 3. Apply labeling
        label_data = {
            'message_id': message_id,
            'language': 'en'
        }
        
        response = self.client.post(
            '/api/config/ai-labels/apply',
            data=json.dumps(label_data),
            content_type='application/json'
        )
        
        assert response.status_code == 200
        label_result = json.loads(response.data)
        assert label_result['success'] is True
        
        # 4. Retrieve labels
        response = self.client.get(f'/api/config/ai-labels/message/{message_id}')
        
        assert response.status_code == 200
        get_result = json.loads(response.data)
        assert get_result['success'] is True
        assert get_result['label_info']['ai_generated'] is True
        assert 'generated_content_notice' in get_result['label_info']['content_labels']
        
        # 5. Get updated stats
        response = self.client.get('/api/config/ai-labels/stats')
        
        assert response.status_code == 200
        stats_result = json.loads(response.data)
        assert stats_result['stats']['ai_generated_messages'] >= 1
    
    def test_multilingual_labeling_consistency(self):
        """Test that labeling works consistently across languages."""
        languages = ['en', 'zh', 'ja', 'ko']
        
        for language in languages:
            # Get labels for each language
            response = self.client.get(f'/api/config/ai-labels?language={language}')
            
            assert response.status_code == 200
            data = json.loads(response.data)
            
            assert data['success'] is True
            assert data['language'] == language
            
            # Verify required fields exist
            required_fields = ['text_notice', 'media_notice', 'watermark_text']
            for field in required_fields:
                assert field in data['labels']
                assert data['labels'][field]  # Not empty
                
            # Verify text is appropriate for language
            if language in ['zh', 'zh-CN']:
                assert 'AI生成' in data['labels']['watermark_text']
            elif language == 'en':
                assert 'AI Generated' in data['labels']['watermark_text']
    
    def test_performance_bulk_labeling(self):
        """Test performance of bulk labeling operations."""
        with self.app.app_context():
            # Create multiple test messages
            message_ids = []
            for i in range(10):
                message = Message(
                    app_id='test-app',
                    conversation_id=f'test-conversation-{i}',
                    query=f'Test query {i}',
                    answer=f'As an AI, I will help with task {i}.',
                    message_tokens=10,
                    answer_tokens=15,
                    message_unit_price=0.001,
                    answer_unit_price=0.002,
                    total_price=0.003,
                    currency='USD',
                    from_source='api',
                    model_provider='openai',
                    model_id='gpt-4',
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                )
                
                db.session.add(message)
                message_ids.append(message.id)
            
            db.session.commit()
        
        # Test bulk labeling
        import time
        start_time = time.time()
        
        bulk_data = {
            'message_ids': message_ids,
            'model_provider': 'openai',
            'language': 'en',
            'batch_size': 5
        }
        
        response = self.client.post(
            '/api/config/ai-labels/bulk-apply',
            data=json.dumps(bulk_data),
            content_type='application/json'
        )
        
        end_time = time.time()
        processing_time = end_time - start_time
        
        assert response.status_code == 200
        data = json.loads(response.data)
        
        assert data['success'] is True
        assert data['results']['total_processed'] == 10
        
        # Performance assertion (should complete within reasonable time)
        assert processing_time < 10.0  # 10 seconds max for 10 messages
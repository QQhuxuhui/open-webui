"""Integration tests for AI Labels system with chat history and export functionality."""

import pytest
import json
from datetime import datetime
from unittest.mock import patch

from controllers.config.ai_labels import bp
from models.model import Message
from services.ai_labeling_service import AILabelingService
from extensions.ext_database import db


class TestAILabelsChatIntegration:
    """Integration tests for AI labels with chat history and export functionality."""
    
    @pytest.fixture(autouse=True)
    def setup_method(self, app_with_db):
        """Set up test method."""
        self.app = app_with_db
        self.client = app_with_db.test_client()
        
        with app_with_db.app_context():
            # Clean up database
            db.session.query(Message).delete()
            db.session.commit()
    
    def create_test_messages(self, count=5):
        """Create test messages with mixed AI and human content."""
        messages = []
        
        with self.app.app_context():
            for i in range(count):
                is_ai = i % 2 == 0  # Alternate between AI and human content
                
                message = Message(
                    app_id='test-app',
                    conversation_id=f'test-conversation-{i // 2}',
                    query=f'Test query {i}',
                    answer=f'{"As an AI, I can help you with" if is_ai else "I personally think this is"} task {i}.',
                    message_tokens=10 + i,
                    answer_tokens=15 + i,
                    message_unit_price=0.001,
                    answer_unit_price=0.002,
                    total_price=0.003,
                    currency='USD',
                    from_source='api',
                    model_provider='openai' if is_ai else None,
                    model_id='gpt-4' if is_ai else None,
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                )
                
                db.session.add(message)
                messages.append(message)
            
            db.session.commit()
            
            # Return message IDs
            return [msg.id for msg in messages]
    
    def test_chat_history_with_ai_labels(self):
        """Test that AI labels are properly applied to chat history."""
        message_ids = self.create_test_messages(4)
        
        # Apply AI labeling to messages
        labeling_service = AILabelingService()
        
        with self.app.app_context():
            for message_id in message_ids:
                success = labeling_service.apply_ai_labeling(message_id, language='en')
                assert success is True
            
            # Verify labels were applied correctly
            messages = db.session.query(Message).all()
            ai_labeled_count = 0
            human_count = 0
            
            for message in messages:
                if message.ai_generated:
                    ai_labeled_count += 1
                    assert message.ai_model_info is not None
                    assert message.content_labels is not None
                    assert 'generated_content_notice' in message.content_labels
                else:
                    human_count += 1
                    assert message.ai_model_info is None
                    assert message.content_labels is None
            
            # Should have 2 AI messages and 2 human messages
            assert ai_labeled_count == 2
            assert human_count == 2
    
    def test_bulk_labeling_chat_conversations(self):
        """Test bulk labeling of entire chat conversations."""
        message_ids = self.create_test_messages(6)
        
        # Apply bulk labeling
        request_data = {
            'message_ids': message_ids,
            'model_provider': 'openai',
            'language': 'en',
            'batch_size': 3
        }
        
        response = self.client.post(
            '/api/config/ai-labels/bulk-apply',
            data=json.dumps(request_data),
            content_type='application/json'
        )
        
        assert response.status_code == 200
        data = json.loads(response.data)
        
        assert data['success'] is True
        assert data['results']['total_processed'] == 6
        assert data['results']['total_labeled'] >= 3  # At least 3 AI messages
    
    def test_chat_export_includes_ai_labels(self):
        """Test that chat export functionality includes AI labels."""
        message_ids = self.create_test_messages(4)
        
        # Apply labeling first
        labeling_service = AILabelingService()
        with self.app.app_context():
            for message_id in message_ids:
                labeling_service.apply_ai_labeling(message_id, language='en')
        
        # Simulate chat export by fetching messages with labels
        export_data = []
        
        with self.app.app_context():
            messages = db.session.query(Message).order_by(Message.created_at).all()
            
            for message in messages:
                message_data = {
                    'id': message.id,
                    'query': message.query,
                    'answer': message.answer,
                    'created_at': message.created_at.isoformat(),
                    'ai_generated': message.ai_generated,
                    'ai_model_info': message.ai_model_info,
                    'content_labels': message.content_labels
                }
                export_data.append(message_data)
        
        # Verify export includes AI labeling information
        ai_messages = [msg for msg in export_data if msg['ai_generated']]
        human_messages = [msg for msg in export_data if not msg['ai_generated']]
        
        assert len(ai_messages) == 2
        assert len(human_messages) == 2
        
        # Check AI message labels
        for ai_msg in ai_messages:
            assert ai_msg['ai_model_info'] is not None
            assert ai_msg['content_labels'] is not None
            assert 'generated_content_notice' in ai_msg['content_labels']
            assert ai_msg['content_labels']['language'] == 'en'
            assert ai_msg['content_labels']['content_type'] == 'text'
        
        # Check human messages don't have AI labels
        for human_msg in human_messages:
            assert human_msg['ai_model_info'] is None
            assert human_msg['content_labels'] is None
    
    def test_multilingual_chat_history_labeling(self):
        """Test AI labeling in multilingual chat conversations."""
        languages = ['en', 'zh', 'ja']
        
        for lang in languages:
            # Create messages for each language
            message_ids = self.create_test_messages(2)
            
            # Apply labeling in specific language
            request_data = {
                'message_ids': message_ids,
                'language': lang
            }
            
            response = self.client.post(
                '/api/config/ai-labels/bulk-apply',
                data=json.dumps(request_data),
                content_type='application/json'
            )
            
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['success'] is True
            
            # Verify language-specific labels
            with self.app.app_context():
                ai_messages = db.session.query(Message).filter(
                    Message.ai_generated == True,
                    Message.id.in_(message_ids)
                ).all()
                
                for message in ai_messages:
                    assert message.content_labels['language'] == lang
                    
                    # Verify language-specific text
                    notice = message.content_labels['generated_content_notice']
                    if lang == 'zh':
                        assert '内容由AI生成' in notice
                    elif lang == 'en':
                        assert 'Content generated by AI' in notice
            
            # Clean up for next iteration
            with self.app.app_context():
                db.session.query(Message).delete()
                db.session.commit()
    
    @patch('controllers.config.ai_labels.AILabelingService')
    def test_chat_history_performance_optimization(self, mock_service_class):
        """Test performance optimization for large chat histories."""
        # Mock service for performance testing
        mock_service = mock_service_class.return_value
        mock_service.bulk_apply_labeling.return_value = {
            'total_processed': 1000,
            'total_labeled': 750,
            'total_errors': 0
        }
        
        # Generate large number of message IDs
        message_ids = [f'msg-{i}' for i in range(1000)]
        
        request_data = {
            'message_ids': message_ids,
            'model_provider': 'openai',
            'language': 'en',
            'batch_size': 100  # Large batch size for performance
        }
        
        import time
        start_time = time.time()
        
        response = self.client.post(
            '/api/config/ai-labels/bulk-apply',
            data=json.dumps(request_data),
            content_type='application/json'
        )
        
        end_time = time.time()
        processing_time = end_time - start_time
        
        assert response.status_code == 200
        data = json.loads(response.data)
        
        assert data['success'] is True
        assert data['results']['total_processed'] == 1000
        
        # Performance assertion - should handle 1000 messages reasonably fast
        assert processing_time < 5.0  # 5 seconds max for 1000 messages
        
        # Verify service was called with correct batch size
        mock_service.bulk_apply_labeling.assert_called_once()
        call_args = mock_service.bulk_apply_labeling.call_args[1]
        assert call_args.get('batch_size') == 100
    
    def test_chat_conversation_grouping_with_labels(self):
        """Test that AI labels work correctly with conversation grouping."""
        # Create messages across multiple conversations
        conversation_messages = {}
        
        with self.app.app_context():
            for conv_id in range(3):
                conv_name = f'conversation-{conv_id}'
                conversation_messages[conv_name] = []
                
                for i in range(3):
                    is_ai = i % 2 == 0
                    
                    message = Message(
                        app_id='test-app',
                        conversation_id=conv_name,
                        query=f'Query {i} in {conv_name}',
                        answer=f'{"As an AI assistant," if is_ai else "I think"} response {i}.',
                        message_tokens=10,
                        answer_tokens=15,
                        message_unit_price=0.001,
                        answer_unit_price=0.002,
                        total_price=0.003,
                        currency='USD',
                        from_source='api',
                        model_provider='openai' if is_ai else None,
                        model_id='gpt-4' if is_ai else None,
                        created_at=datetime.utcnow(),
                        updated_at=datetime.utcnow()
                    )
                    
                    db.session.add(message)
                    conversation_messages[conv_name].append(message)
            
            db.session.commit()
            
            # Apply labeling to all messages
            labeling_service = AILabelingService()
            all_messages = db.session.query(Message).all()
            
            for message in all_messages:
                labeling_service.apply_ai_labeling(message.id, language='en')
            
            # Verify conversation-grouped export includes labels
            conversations_export = {}
            
            for conv_name in conversation_messages.keys():
                conv_messages = db.session.query(Message).filter_by(
                    conversation_id=conv_name
                ).order_by(Message.created_at).all()
                
                conversations_export[conv_name] = []
                
                for message in conv_messages:
                    message_data = {
                        'id': message.id,
                        'query': message.query,
                        'answer': message.answer,
                        'ai_generated': message.ai_generated,
                        'ai_labels': message.content_labels if message.ai_generated else None
                    }
                    conversations_export[conv_name].append(message_data)
            
            # Verify each conversation has correct AI labeling
            for conv_name, messages in conversations_export.items():
                ai_count = sum(1 for msg in messages if msg['ai_generated'])
                human_count = sum(1 for msg in messages if not msg['ai_generated'])
                
                # Each conversation should have 2 AI messages and 1 human message
                assert ai_count == 2
                assert human_count == 1
                
                # Verify AI messages have labels
                for message in messages:
                    if message['ai_generated']:
                        assert message['ai_labels'] is not None
                        assert 'generated_content_notice' in message['ai_labels']
                    else:
                        assert message['ai_labels'] is None
    
    def test_ai_labels_statistics_across_chat_history(self):
        """Test AI labeling statistics across entire chat history."""
        # Create diverse message set
        message_ids = self.create_test_messages(10)
        
        # Apply labeling
        labeling_service = AILabelingService()
        
        with self.app.app_context():
            for message_id in message_ids:
                labeling_service.apply_ai_labeling(message_id)
        
        # Get labeling statistics
        response = self.client.get('/api/config/ai-labels/stats')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        
        assert data['success'] is True
        stats = data['stats']
        
        # Verify statistics are accurate
        assert stats['total_messages'] == 10
        assert stats['ai_generated_messages'] == 5  # Half should be AI
        assert stats['labeled_messages'] == 10  # All should be labeled
        assert stats['labeling_rate'] == 100.0  # 100% labeling rate
        assert stats['ai_detection_rate'] == 50.0  # 50% AI detection rate
    
    def test_ai_label_cleanup_on_message_deletion(self):
        """Test that AI labels are cleaned up when messages are deleted."""
        message_ids = self.create_test_messages(4)
        
        # Apply labeling
        labeling_service = AILabelingService()
        
        with self.app.app_context():
            for message_id in message_ids:
                labeling_service.apply_ai_labeling(message_id)
            
            # Verify labels exist
            labeled_messages = db.session.query(Message).filter(
                Message.ai_generated == True
            ).count()
            assert labeled_messages == 2
            
            # Delete some messages (simulating chat history cleanup)
            messages_to_delete = db.session.query(Message).limit(2).all()
            for message in messages_to_delete:
                db.session.delete(message)
            db.session.commit()
            
            # Verify statistics are updated correctly
            response = self.client.get('/api/config/ai-labels/stats')
            data = json.loads(response.data)
            stats = data['stats']
            
            # Should have 2 messages remaining
            assert stats['total_messages'] == 2
            
            # Verify the remaining messages still have correct labels
            remaining_messages = db.session.query(Message).all()
            for message in remaining_messages:
                if message.ai_generated:
                    assert message.ai_model_info is not None
                    assert message.content_labels is not None
                else:
                    assert message.ai_model_info is None
                    assert message.content_labels is None
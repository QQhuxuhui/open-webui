"""
Integration tests for profile management functionality.
Tests the complete flow from API endpoints to database operations.
"""
import pytest
import json
from io import BytesIO
from PIL import Image
from unittest.mock import patch

from models.account import Account
from models.profile_history import ProfileModificationHistory
from extensions.ext_database import db
from tests.integration_tests.base import BaseIntegrationTest


class TestProfileIntegration(BaseIntegrationTest):
    
    def setUp(self):
        super().setUp()
        
        # Create test account
        self.account = Account(
            id="test-profile-user",
            name="Profile Test User",
            email="profile-test@example.com",
            nickname="OriginalNick",
            phone_number="+1234567890",
            phone_verified=True,
            status="active",
            initialized_at=db.func.now()
        )
        db.session.add(self.account)
        db.session.commit()
        
        # Setup authentication
        self.setup_account_mock(self.account)

    def tearDown(self):
        """Clean up test data."""
        # Clean up profile history
        db.session.query(ProfileModificationHistory).filter_by(user_id=self.account.id).delete()
        # Clean up account
        db.session.query(Account).filter_by(id=self.account.id).delete()
        db.session.commit()
        super().tearDown()

    def test_nickname_update_creates_history(self):
        """Test that updating nickname creates a history record."""
        response = self.client.post(
            '/console/api/account/nickname',
            data=json.dumps({'nickname': 'NewNickname'}),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        
        # Verify account was updated
        updated_account = db.session.query(Account).filter_by(id=self.account.id).first()
        self.assertEqual(updated_account.nickname, 'NewNickname')
        
        # Verify history record was created
        history_records = db.session.query(ProfileModificationHistory)\
            .filter_by(user_id=self.account.id, field_name='nickname')\
            .all()
        
        self.assertEqual(len(history_records), 1)
        history = history_records[0]
        self.assertEqual(history.old_value, 'OriginalNick')
        self.assertEqual(history.new_value, 'NewNickname')
        self.assertIsNotNone(history.ip_address)
        self.assertIsNotNone(history.user_agent)
        self.assertFalse(history.verification_required)

    def test_nickname_validation_errors(self):
        """Test nickname validation in API."""
        # Test empty nickname
        response = self.client.post(
            '/console/api/account/nickname',
            data=json.dumps({'nickname': ''}),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 400)
        response_data = json.loads(response.data)
        self.assertIn('Nickname must be between 1 and 50 characters', response_data['message'])
        
        # Test nickname too long
        response = self.client.post(
            '/console/api/account/nickname',
            data=json.dumps({'nickname': 'a' * 51}),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 400)

    @patch('services.account_service.storage')
    def test_avatar_upload_integration(self, mock_storage):
        """Test complete avatar upload flow."""
        mock_storage.save.return_value = "https://example.com/avatars/test.jpg"
        
        # Create a small test image
        img = Image.new('RGB', (100, 100), color='red')
        img_bytes = BytesIO()
        img.save(img_bytes, format='JPEG')
        img_bytes.seek(0)
        
        response = self.client.post(
            '/console/api/account/avatar/upload',
            data={'avatar': (img_bytes, 'test_avatar.jpg', 'image/jpeg')},
            content_type='multipart/form-data'
        )
        
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.data)
        self.assertEqual(response_data['avatar_url'], "https://example.com/avatars/test.jpg")
        
        # Verify account was updated
        updated_account = db.session.query(Account).filter_by(id=self.account.id).first()
        self.assertEqual(updated_account.avatar_url, "https://example.com/avatars/test.jpg")
        
        # Verify history record was created
        history_records = db.session.query(ProfileModificationHistory)\
            .filter_by(user_id=self.account.id, field_name='avatar_url')\
            .all()
        
        self.assertEqual(len(history_records), 1)

    def test_avatar_upload_validation_errors(self):
        """Test avatar upload validation."""
        # Test invalid file type
        text_file = BytesIO(b"This is not an image")
        response = self.client.post(
            '/console/api/account/avatar/upload',
            data={'avatar': (text_file, 'test.txt', 'text/plain')},
            content_type='multipart/form-data'
        )
        
        self.assertEqual(response.status_code, 400)
        response_data = json.loads(response.data)
        self.assertIn('Invalid image format', response_data['message'])

    @patch('services.sms.sms_service.SmsService.verify_code')
    def test_phone_change_integration(self, mock_verify_code):
        """Test phone number change with SMS verification."""
        mock_verify_code.return_value = True
        
        response = self.client.post(
            '/console/api/account/phone/change',
            data=json.dumps({
                'old_phone': '+1234567890',
                'new_phone': '+0987654321',
                'old_phone_code': '123456',
                'new_phone_code': '654321'
            }),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        
        # Verify account phone was updated
        updated_account = db.session.query(Account).filter_by(id=self.account.id).first()
        self.assertEqual(updated_account.phone_number, '+0987654321')
        self.assertTrue(updated_account.phone_verified)
        
        # Verify SMS verification was called correctly
        self.assertEqual(mock_verify_code.call_count, 2)
        
        # Verify history record was created
        history_records = db.session.query(ProfileModificationHistory)\
            .filter_by(user_id=self.account.id, field_name='phone_number')\
            .all()
        
        self.assertEqual(len(history_records), 1)
        history = history_records[0]
        self.assertEqual(history.old_value, '+1234567890')
        self.assertEqual(history.new_value, '+0987654321')
        self.assertTrue(history.verification_required)

    @patch('services.sms.sms_service.SmsService.verify_code')
    def test_phone_change_verification_failure(self, mock_verify_code):
        """Test phone change with failed SMS verification."""
        mock_verify_code.return_value = False
        
        response = self.client.post(
            '/console/api/account/phone/change',
            data=json.dumps({
                'old_phone': '+1234567890',
                'new_phone': '+0987654321',
                'old_phone_code': '123456',
                'new_phone_code': '654321'
            }),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 400)
        
        # Verify account phone was not updated
        account = db.session.query(Account).filter_by(id=self.account.id).first()
        self.assertEqual(account.phone_number, '+1234567890')

    def test_profile_history_retrieval(self):
        """Test retrieving profile modification history."""
        # Create some history records first
        history1 = ProfileModificationHistory(
            user_id=self.account.id,
            field_name='nickname',
            old_value='Nick1',
            new_value='Nick2',
            ip_address='127.0.0.1',
            user_agent='Test Browser'
        )
        history2 = ProfileModificationHistory(
            user_id=self.account.id,
            field_name='phone_number',
            old_value='+1111111111',
            new_value='+2222222222',
            ip_address='127.0.0.1',
            user_agent='Test Browser',
            verification_required=True
        )
        
        db.session.add_all([history1, history2])
        db.session.commit()
        
        response = self.client.get('/console/api/account/profile/history?page=1&limit=10')
        
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.data)
        
        self.assertEqual(response_data['total'], 2)
        self.assertEqual(len(response_data['data']), 2)
        self.assertEqual(response_data['page'], 1)
        self.assertFalse(response_data['has_next'])
        
        # Verify data structure
        history_item = response_data['data'][0]
        self.assertIn('id', history_item)
        self.assertIn('field_name', history_item)
        self.assertIn('old_value', history_item)
        self.assertIn('new_value', history_item)
        self.assertIn('ip_address', history_item)
        self.assertIn('user_agent', history_item)
        self.assertIn('created_at', history_item)
        self.assertIn('verification_required', history_item)

    def test_profile_history_pagination(self):
        """Test profile history pagination."""
        # Create multiple history records
        for i in range(25):
            history = ProfileModificationHistory(
                user_id=self.account.id,
                field_name='nickname',
                old_value=f'Nick{i}',
                new_value=f'Nick{i+1}',
                ip_address='127.0.0.1',
                user_agent='Test Browser'
            )
            db.session.add(history)
        
        db.session.commit()
        
        # Test first page
        response = self.client.get('/console/api/account/profile/history?page=1&limit=20')
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.data)
        
        self.assertEqual(response_data['total'], 25)
        self.assertEqual(len(response_data['data']), 20)
        self.assertEqual(response_data['page'], 1)
        self.assertTrue(response_data['has_next'])
        
        # Test second page
        response = self.client.get('/console/api/account/profile/history?page=2&limit=20')
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.data)
        
        self.assertEqual(response_data['total'], 25)
        self.assertEqual(len(response_data['data']), 5)
        self.assertEqual(response_data['page'], 2)
        self.assertFalse(response_data['has_next'])

    def test_multiple_profile_changes_create_separate_history(self):
        """Test that multiple profile changes create separate history records."""
        # Update nickname
        self.client.post(
            '/console/api/account/nickname',
            data=json.dumps({'nickname': 'FirstChange'}),
            content_type='application/json'
        )
        
        # Update nickname again
        self.client.post(
            '/console/api/account/nickname',
            data=json.dumps({'nickname': 'SecondChange'}),
            content_type='application/json'
        )
        
        # Verify separate history records
        history_records = db.session.query(ProfileModificationHistory)\
            .filter_by(user_id=self.account.id, field_name='nickname')\
            .order_by(ProfileModificationHistory.created_at)\
            .all()
        
        self.assertEqual(len(history_records), 2)
        
        # First change
        self.assertEqual(history_records[0].old_value, 'OriginalNick')
        self.assertEqual(history_records[0].new_value, 'FirstChange')
        
        # Second change
        self.assertEqual(history_records[1].old_value, 'FirstChange')
        self.assertEqual(history_records[1].new_value, 'SecondChange')


if __name__ == '__main__':
    pytest.main([__file__])
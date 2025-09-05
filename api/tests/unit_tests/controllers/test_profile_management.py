"""
Unit tests for profile management functionality.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from io import BytesIO

from controllers.console.workspace.account import (
    AccountNicknameApi, 
    AccountAvatarUploadApi, 
    PhoneChangeRequestApi,
    ProfileHistoryApi
)
from models.account import Account
from services.account_service import AccountService
from tests.unit_tests.base import BaseUnitTest


class TestProfileManagement(BaseUnitTest):
    
    def setUp(self):
        super().setUp()
        self.account = Account(
            id="test-user-id",
            name="Test User",
            email="test@example.com",
            nickname="TestNick",
            phone_number="+1234567890",
            phone_verified=True
        )

    @patch('controllers.console.workspace.account.current_user')
    @patch.object(AccountService, 'update_account')
    def test_update_nickname_success(self, mock_update_account, mock_current_user):
        """Test successful nickname update."""
        mock_current_user.return_value = self.account
        mock_update_account.return_value = self.account
        
        api = AccountNicknameApi()
        
        with self.app.test_request_context(
            '/account/nickname',
            method='POST',
            json={'nickname': 'NewNickname'}
        ):
            result = api.post()
            
        mock_update_account.assert_called_once_with(
            self.account, 
            nickname='NewNickname'
        )
        self.assertEqual(result.nickname, 'TestNick')  # Returns updated account

    @patch('controllers.console.workspace.account.current_user')
    def test_update_nickname_too_short(self, mock_current_user):
        """Test nickname validation - too short."""
        mock_current_user.return_value = self.account
        
        api = AccountNicknameApi()
        
        with self.app.test_request_context(
            '/account/nickname',
            method='POST',
            json={'nickname': ''}
        ):
            with pytest.raises(ValueError, match="Nickname must be between 1 and 50 characters"):
                api.post()

    @patch('controllers.console.workspace.account.current_user')
    def test_update_nickname_too_long(self, mock_current_user):
        """Test nickname validation - too long."""
        mock_current_user.return_value = self.account
        
        api = AccountNicknameApi()
        
        with self.app.test_request_context(
            '/account/nickname',
            method='POST',
            json={'nickname': 'a' * 51}
        ):
            with pytest.raises(ValueError, match="Nickname must be between 1 and 50 characters"):
                api.post()

    @patch('controllers.console.workspace.account.current_user')
    @patch.object(AccountService, 'upload_avatar')
    def test_avatar_upload_success(self, mock_upload_avatar, mock_current_user):
        """Test successful avatar upload."""
        mock_current_user.return_value = self.account
        mock_upload_avatar.return_value = "https://example.com/avatar.jpg"
        
        # Create a mock file
        mock_file = MagicMock()
        mock_file.filename = "avatar.jpg"
        mock_file.content_type = "image/jpeg"
        mock_file.seek = Mock()
        mock_file.tell = Mock(return_value=1024)  # 1KB file
        
        api = AccountAvatarUploadApi()
        
        with self.app.test_request_context(
            '/account/avatar/upload',
            method='POST',
            files={'avatar': mock_file}
        ):
            result = api.post()
            
        mock_upload_avatar.assert_called_once_with(self.account, mock_file)
        self.assertEqual(result['avatar_url'], "https://example.com/avatar.jpg")

    @patch('controllers.console.workspace.account.current_user')
    def test_avatar_upload_invalid_type(self, mock_current_user):
        """Test avatar upload with invalid file type."""
        mock_current_user.return_value = self.account
        
        # Create a mock file with invalid type
        mock_file = MagicMock()
        mock_file.filename = "document.pdf"
        mock_file.content_type = "application/pdf"
        
        api = AccountAvatarUploadApi()
        
        with self.app.test_request_context(
            '/account/avatar/upload',
            method='POST',
            files={'avatar': mock_file}
        ):
            with pytest.raises(ValueError, match="Invalid image format"):
                api.post()

    @patch('controllers.console.workspace.account.current_user')
    def test_avatar_upload_too_large(self, mock_current_user):
        """Test avatar upload with file too large."""
        mock_current_user.return_value = self.account
        
        # Create a mock file that's too large
        mock_file = MagicMock()
        mock_file.filename = "avatar.jpg"
        mock_file.content_type = "image/jpeg"
        mock_file.seek = Mock()
        mock_file.tell = Mock(return_value=6 * 1024 * 1024)  # 6MB file
        
        api = AccountAvatarUploadApi()
        
        with self.app.test_request_context(
            '/account/avatar/upload',
            method='POST',
            files={'avatar': mock_file}
        ):
            with pytest.raises(ValueError, match="Image file too large"):
                api.post()

    @patch('controllers.console.workspace.account.current_user')
    @patch('services.auth.phone_auth_service.PhoneAuthService.change_phone_number')
    def test_phone_change_success(self, mock_change_phone, mock_current_user):
        """Test successful phone number change."""
        mock_current_user.return_value = self.account
        mock_change_phone.return_value = True
        
        api = PhoneChangeRequestApi()
        
        with self.app.test_request_context(
            '/account/phone/change',
            method='POST',
            json={
                'old_phone': '+1234567890',
                'new_phone': '+0987654321',
                'old_phone_code': '123456',
                'new_phone_code': '654321'
            }
        ):
            result = api.post()
            
        mock_change_phone.assert_called_once_with(
            self.account,
            '+1234567890',
            '+0987654321',
            '123456',
            '654321'
        )
        self.assertEqual(result['result'], 'success')

    @patch('controllers.console.workspace.account.current_user')
    @patch('services.auth.phone_auth_service.PhoneAuthService.change_phone_number')
    def test_phone_change_failure(self, mock_change_phone, mock_current_user):
        """Test phone number change failure."""
        mock_current_user.return_value = self.account
        mock_change_phone.side_effect = ValueError("Phone verification failed")
        
        api = PhoneChangeRequestApi()
        
        with self.app.test_request_context(
            '/account/phone/change',
            method='POST',
            json={
                'old_phone': '+1234567890',
                'new_phone': '+0987654321',
                'old_phone_code': '123456',
                'new_phone_code': '654321'
            }
        ):
            with pytest.raises(ValueError, match="Phone verification failed"):
                api.post()

    @patch('controllers.console.workspace.account.current_user')
    @patch.object(AccountService, 'get_profile_history')
    def test_get_profile_history(self, mock_get_history, mock_current_user):
        """Test getting profile modification history."""
        mock_current_user.return_value = self.account
        
        mock_history_data = {
            'data': [
                {
                    'id': 'hist1',
                    'field_name': 'nickname',
                    'old_value': 'OldNick',
                    'new_value': 'NewNick',
                    'created_at': '2023-01-01T00:00:00Z',
                    'ip_address': '127.0.0.1'
                }
            ],
            'has_next': False,
            'page': 1,
            'total': 1
        }
        mock_get_history.return_value = mock_history_data
        
        api = ProfileHistoryApi()
        
        with self.app.test_request_context('/account/profile/history?page=1&limit=20'):
            result = api.get()
            
        mock_get_history.assert_called_once_with(self.account, page=1, limit=20)
        self.assertEqual(result['total'], 1)
        self.assertEqual(len(result['data']), 1)
        self.assertEqual(result['data'][0]['field_name'], 'nickname')

    @patch('controllers.console.workspace.account.current_user')
    @patch.object(AccountService, 'get_profile_history')
    def test_get_profile_history_with_pagination(self, mock_get_history, mock_current_user):
        """Test getting profile history with pagination parameters."""
        mock_current_user.return_value = self.account
        
        mock_history_data = {
            'data': [],
            'has_next': True,
            'page': 2,
            'total': 50
        }
        mock_get_history.return_value = mock_history_data
        
        api = ProfileHistoryApi()
        
        with self.app.test_request_context('/account/profile/history?page=2&limit=10'):
            result = api.get()
            
        mock_get_history.assert_called_once_with(self.account, page=2, limit=10)
        self.assertEqual(result['page'], 2)
        self.assertEqual(result['has_next'], True)
        self.assertEqual(result['total'], 50)


class TestAccountServiceProfileMethods(BaseUnitTest):
    
    def setUp(self):
        super().setUp()
        self.account = Account(
            id="test-user-id",
            name="Test User",
            email="test@example.com",
            nickname="TestNick"
        )

    @patch('services.account_service.storage')
    @patch('services.account_service.Image')
    def test_upload_avatar_success(self, mock_image_class, mock_storage):
        """Test successful avatar upload and processing."""
        # Mock PIL Image
        mock_image = MagicMock()
        mock_image_class.open.return_value = mock_image
        mock_image.mode = 'RGB'
        mock_image.thumbnail = Mock()
        mock_image.save = Mock()
        
        # Mock storage
        mock_storage.save.return_value = "https://example.com/avatar.jpg"
        
        # Mock file
        mock_file = MagicMock()
        mock_file.filename = "avatar.jpg"
        mock_file.stream = BytesIO(b"fake image data")
        
        result = AccountService.upload_avatar(self.account, mock_file)
        
        # Verify image processing
        mock_image.thumbnail.assert_called_once_with((400, 400), mock_image_class.Resampling.LANCZOS)
        mock_image.save.assert_called_once()
        mock_storage.save.assert_called_once()
        
        self.assertEqual(result, "https://example.com/avatar.jpg")

    @patch('models.profile_history.ProfileModificationHistory')
    @patch('services.account_service.db.session')
    def test_log_profile_modification(self, mock_session, mock_history_model):
        """Test profile modification logging."""
        mock_history_record = MagicMock()
        mock_history_model.create_history_record.return_value = mock_history_record
        
        with self.app.test_request_context('/', headers={'User-Agent': 'Test Browser'}):
            AccountService.log_profile_modification(
                account=self.account,
                field_name='nickname',
                old_value='OldNick',
                new_value='NewNick'
            )
        
        mock_history_model.create_history_record.assert_called_once()
        mock_session.add.assert_called_once_with(mock_history_record)
        mock_session.commit.assert_called_once()

    @patch('models.profile_history.ProfileModificationHistory')
    @patch('services.account_service.db.session')
    def test_get_profile_history(self, mock_session, mock_history_model):
        """Test getting profile modification history."""
        # Mock query results
        mock_query = MagicMock()
        mock_session.query.return_value = mock_query
        mock_query.filter_by.return_value = mock_query
        mock_query.count.return_value = 5
        mock_query.order_by.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        
        mock_history_item = MagicMock()
        mock_history_item.id = "hist1"
        mock_history_item.field_name = "nickname"
        mock_history_item.old_value = "OldNick"
        mock_history_item.new_value = "NewNick"
        mock_query.all.return_value = [mock_history_item]
        
        result = AccountService.get_profile_history(self.account, page=1, limit=20)
        
        self.assertEqual(result['total'], 5)
        self.assertEqual(len(result['data']), 1)
        self.assertEqual(result['data'][0]['field_name'], 'nickname')
        self.assertEqual(result['has_next'], False)  # (1-1) * 20 + 1 < 5 = False


if __name__ == '__main__':
    pytest.main([__file__])
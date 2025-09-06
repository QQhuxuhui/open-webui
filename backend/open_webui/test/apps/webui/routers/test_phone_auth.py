import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from open_webui.main import app
from open_webui.models.phone_auth import PhoneVerifications
from open_webui.models.users import Users

client = TestClient(app)

class TestPhoneAuth:
    """手机认证功能测试"""
    
    def test_send_code_invalid_phone(self):
        """测试无效手机号"""
        response = client.post("/api/v1/auths/phone/send-code", 
                             json={"phone": "123456"})
        assert response.status_code == 400
        assert "手机号格式不正确" in response.json()["detail"]
    
    def test_send_code_valid_phone(self):
        """测试有效手机号发送验证码"""
        with patch.object(PhoneVerifications, 'create_verification') as mock_create:
            mock_verification = MagicMock()
            mock_verification.code = "123456"
            mock_create.return_value = mock_verification
            
            with patch('open_webui.utils.sms.sms_service.send_verification_code') as mock_sms:
                mock_sms.return_value = (True, "发送成功")
                
                response = client.post("/api/v1/auths/phone/send-code", 
                                     json={"phone": "13800138000"})
                assert response.status_code == 200
                assert "验证码发送成功" in response.json()["message"]
    
    def test_signup_missing_agreement(self):
        """测试注册时未勾选协议"""
        response = client.post("/api/v1/auths/phone/signup", json={
            "phone": "13800138000",
            "code": "123456", 
            "name": "测试用户",
            "privacy_agreed": False,
            "terms_agreed": True
        })
        assert response.status_code == 400
        assert "必须同意隐私协议和服务协议" in response.json()["detail"]
    
    def test_signup_invalid_code(self):
        """测试注册时验证码错误"""
        with patch.object(PhoneVerifications, 'verify_code') as mock_verify:
            mock_verify.return_value = (False, "验证码无效")
            
            response = client.post("/api/v1/auths/phone/signup", json={
                "phone": "13800138000",
                "code": "123456",
                "name": "测试用户", 
                "privacy_agreed": True,
                "terms_agreed": True
            })
            assert response.status_code == 400
            assert "验证码无效" in response.json()["detail"]
    
    def test_signin_user_not_exists(self):
        """测试登录时用户不存在"""
        with patch.object(PhoneVerifications, 'verify_code') as mock_verify:
            mock_verify.return_value = (True, "验证成功")
            
            with patch.object(Users, 'get_user_by_phone') as mock_get_user:
                mock_get_user.return_value = None
                
                response = client.post("/api/v1/auths/phone/signin", json={
                    "phone": "13800138000",
                    "code": "123456"
                })
                assert response.status_code == 400
                assert "用户不存在" in response.json()["detail"]

@pytest.fixture
def mock_db():
    """模拟数据库"""
    with patch('open_webui.internal.db.get_db') as mock:
        yield mock

class TestPhoneVerifications:
    """验证码管理功能测试"""
    
    def test_generate_code(self):
        """测试验证码生成"""
        code = PhoneVerifications.generate_code()
        assert len(code) == 6
        assert code.isdigit()
    
    def test_code_format_validation(self):
        """测试验证码格式验证"""
        import re
        phone_pattern = r'^1[3-9]\d{9}$'
        
        # 有效手机号
        assert re.match(phone_pattern, '13800138000')
        assert re.match(phone_pattern, '18912345678')
        
        # 无效手机号
        assert not re.match(phone_pattern, '12345678901')  # 不以1开头的第二位不是3-9
        assert not re.match(phone_pattern, '1380013800')   # 长度不够
        assert not re.match(phone_pattern, '138001380000') # 长度过长
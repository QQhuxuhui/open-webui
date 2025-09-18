import os
import logging
import requests
from typing import Optional

log = logging.getLogger(__name__)

class SMSService:
    """短信发送服务 - 支持多个服务商"""
    
    def __init__(self):
        self.provider = os.getenv("SMS_PROVIDER", "mock")  # mock, aliyun, tencent
        self.app_id = os.getenv("SMS_APP_ID", "")
        self.app_key = os.getenv("SMS_APP_KEY", "")
        self.template_id = os.getenv("SMS_TEMPLATE_ID", "")
        self.sign_name = os.getenv("SMS_SIGN_NAME", "OpenWebUI")
    
    def send_verification_code(self, phone: str, code: str) -> tuple[bool, str]:
        """发送验证码短信"""
        if self.provider == "mock":
            return self._send_mock(phone, code)
        elif self.provider == "aliyun":
            return self._send_aliyun(phone, code)
        elif self.provider == "tencent":
            return self._send_tencent(phone, code)
        else:
            log.error(f"不支持的短信服务商: {self.provider}")
            return False, "不支持的短信服务商"
    
    def _send_mock(self, phone: str, code: str) -> tuple[bool, str]:
        """模拟短信发送 - 开发环境使用"""
        log.info(f"[MOCK SMS] 发送验证码到 {phone}: {code}")
        return True, "短信发送成功"
    
    def _send_aliyun(self, phone: str, code: str) -> tuple[bool, str]:
        """阿里云短信发送"""
        try:
            # 这里需要集成阿里云SMS SDK
            # 示例代码，实际使用需要安装 alibabacloud-dysmsapi20170525
            log.info(f"[ALIYUN SMS] 发送验证码到 {phone}")
            return True, "短信发送成功"
        except Exception as e:
            log.error(f"阿里云短信发送失败: {e}")
            return False, "短信发送失败"
    
    def _send_tencent(self, phone: str, code: str) -> tuple[bool, str]:
        """腾讯云短信发送"""
        try:
            # 这里需要集成腾讯云SMS SDK
            # 实际使用需要安装tencentcloud-sdk-python
            log.info(f"[TENCENT SMS] 发送验证码到 {phone}")
            return True, "短信发送成功"
        except Exception as e:
            log.error(f"腾讯云短信发送失败: {e}")
            return False, "短信发送失败"

# 单例实例
sms_service = SMSService()
"""Alibaba Cloud SMS adapter implementation."""

import json
import logging
import hashlib
import hmac
import base64
import urllib.parse
from typing import Optional, Dict, Any
from datetime import datetime
from uuid import uuid4
import asyncio
import aiohttp

from ..sms_adapter import SMSAdapter, SMSResult, SMSStatus
from models.compliance import SMSPurpose

logger = logging.getLogger(__name__)


class AlicloudSMSAdapter(SMSAdapter):
    """Alibaba Cloud SMS service adapter."""
    
    def __init__(self, config):
        """Initialize Alibaba Cloud SMS adapter."""
        super().__init__(config)
        self.endpoint = config.endpoint or "dysmsapi.aliyuncs.com"
        self.region = config.region or "cn-hangzhou"
    
    async def send_sms(
        self,
        phone_number: str,
        verification_code: str,
        purpose: SMSPurpose,
        template_vars: Optional[Dict[str, Any]] = None
    ) -> SMSResult:
        """
        Send SMS through Alibaba Cloud SMS API.
        
        Args:
            phone_number: Target phone number
            verification_code: Verification code to send
            purpose: Purpose of verification
            template_vars: Additional template variables
            
        Returns:
            SMSResult with Alibaba Cloud response
        """
        try:
            # Validate phone number
            if not self._validate_phone_number(phone_number):
                return SMSResult(
                    status=SMSStatus.INVALID_NUMBER,
                    error_message=f"Invalid phone number format: {phone_number}",
                    sent_at=datetime.utcnow()
                )
            
            # Normalize phone number
            normalized_phone = self._normalize_phone_number(phone_number)
            
            # Prepare template parameters
            template_params = {
                'code': verification_code,
                **(template_vars or {})
            }
            
            # Build API request
            params = {
                'Action': 'SendSms',
                'Version': '2017-05-25',
                'RegionId': self.region,
                'PhoneNumbers': normalized_phone,
                'SignName': self.config.sign_name,
                'TemplateCode': self.config.template_id,
                'TemplateParam': json.dumps(template_params),
                'OutId': str(uuid4()),
                'Format': 'JSON',
                'AccessKeyId': self.config.access_key,
                'SignatureMethod': 'HMAC-SHA1',
                'Timestamp': datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ'),
                'SignatureVersion': '1.0',
                'SignatureNonce': str(uuid4()).replace('-', ''),
            }
            
            # Generate signature
            signature = self._generate_signature(params)
            params['Signature'] = signature
            
            # Send HTTP request
            url = f"https://{self.endpoint}/"
            
            async with aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self.config.health_check_timeout)
            ) as session:
                async with session.post(url, data=params) as response:
                    response_data = await response.json()
            
            # Parse response
            if response_data.get('Code') == 'OK':
                return SMSResult(
                    status=SMSStatus.SUCCESS,
                    message_id=response_data.get('BizId'),
                    provider_response=response_data,
                    sent_at=datetime.utcnow()
                )
            else:
                # Handle specific error codes
                error_code = response_data.get('Code', 'Unknown')
                error_message = response_data.get('Message', 'Unknown error')
                
                status = self._map_error_status(error_code)
                
                return SMSResult(
                    status=status,
                    error_message=f"Alibaba Cloud error {error_code}: {error_message}",
                    provider_response=response_data,
                    sent_at=datetime.utcnow()
                )
                
        except asyncio.TimeoutError:
            return SMSResult(
                status=SMSStatus.NETWORK_ERROR,
                error_message="Alibaba Cloud SMS API timeout",
                sent_at=datetime.utcnow()
            )
        except Exception as e:
            logger.error(f"Alibaba Cloud SMS error: {e}")
            return SMSResult(
                status=SMSStatus.PROVIDER_ERROR,
                error_message=f"Alibaba Cloud SMS error: {str(e)}",
                sent_at=datetime.utcnow()
            )
    
    async def check_health(self) -> bool:
        """
        Check Alibaba Cloud SMS service health.
        
        Returns:
            True if service is healthy
        """
        try:
            # Use QuerySendDetails API to check service health
            params = {
                'Action': 'QuerySendDetails',
                'Version': '2017-05-25',
                'RegionId': self.region,
                'PhoneNumber': '+8613800000000',  # Dummy number for health check
                'SendDate': datetime.utcnow().strftime('%Y%m%d'),
                'PageSize': '1',
                'CurrentPage': '1',
                'Format': 'JSON',
                'AccessKeyId': self.config.access_key,
                'SignatureMethod': 'HMAC-SHA1',
                'Timestamp': datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ'),
                'SignatureVersion': '1.0',
                'SignatureNonce': str(uuid4()).replace('-', ''),
            }
            
            # Generate signature
            signature = self._generate_signature(params)
            params['Signature'] = signature
            
            # Send health check request
            url = f"https://{self.endpoint}/"
            
            async with aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self.config.health_check_timeout)
            ) as session:
                async with session.post(url, data=params) as response:
                    response_data = await response.json()
            
            # Check if API is responsive (even if no data found)
            is_healthy = 'Code' in response_data
            self._update_health_status(is_healthy)
            
            logger.debug(f"Alibaba Cloud SMS health check: {is_healthy}")
            return is_healthy
            
        except Exception as e:
            logger.error(f"Alibaba Cloud SMS health check failed: {e}")
            self._update_health_status(False)
            return False
    
    def _generate_signature(self, params: Dict[str, str]) -> str:
        """
        Generate Alibaba Cloud API signature.
        
        Args:
            params: API parameters
            
        Returns:
            Base64 encoded signature
        """
        # Sort parameters
        sorted_params = sorted(params.items())
        
        # Build canonical query string
        query_string = '&'.join([f"{k}={urllib.parse.quote_plus(str(v))}" for k, v in sorted_params])
        
        # Build string to sign
        string_to_sign = f"POST&{urllib.parse.quote_plus('/')}&{urllib.parse.quote_plus(query_string)}"
        
        # Generate signature
        signing_key = f"{self.config.secret_key}&"
        signature = hmac.new(
            signing_key.encode('utf-8'),
            string_to_sign.encode('utf-8'),
            hashlib.sha1
        ).digest()
        
        return base64.b64encode(signature).decode('utf-8')
    
    def _map_error_status(self, error_code: str) -> SMSStatus:
        """
        Map Alibaba Cloud error codes to SMS status.
        
        Args:
            error_code: Alibaba Cloud error code
            
        Returns:
            Mapped SMS status
        """
        error_mapping = {
            'isv.MOBILE_NUMBER_ILLEGAL': SMSStatus.INVALID_NUMBER,
            'isv.MOBILE_COUNT_OVER_LIMIT': SMSStatus.RATE_LIMITED,
            'isv.DAY_LIMIT_CONTROL': SMSStatus.RATE_LIMITED,
            'isv.SMS_CONTENT_ILLEGAL': SMSStatus.FAILED,
            'isv.SMS_SIGN_ILLEGAL': SMSStatus.FAILED,
            'isv.TEMPLATE_ILLEGAL': SMSStatus.FAILED,
            'isv.TEMPLATE_MISSING_PARAMETERS': SMSStatus.FAILED,
        }
        
        return error_mapping.get(error_code, SMSStatus.PROVIDER_ERROR)
    
    def get_provider_name(self) -> str:
        """Get provider name."""
        return "Alibaba Cloud SMS"
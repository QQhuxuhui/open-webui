"""Tencent Cloud SMS adapter implementation."""

import json
import logging
import hashlib
import hmac
from typing import Optional, Dict, Any
from datetime import datetime
import asyncio
import aiohttp

from ..sms_adapter import SMSAdapter, SMSResult, SMSStatus
from models.compliance import SMSPurpose

logger = logging.getLogger(__name__)


class TencentSMSAdapter(SMSAdapter):
    """Tencent Cloud SMS service adapter."""
    
    def __init__(self, config):
        """Initialize Tencent Cloud SMS adapter."""
        super().__init__(config)
        self.endpoint = config.endpoint or "sms.tencentcloudapi.com"
        self.region = config.region or "ap-beijing"
        self.service = "sms"
        self.version = "2021-01-11"
    
    async def send_sms(
        self,
        phone_number: str,
        verification_code: str,
        purpose: SMSPurpose,
        template_vars: Optional[Dict[str, Any]] = None
    ) -> SMSResult:
        """
        Send SMS through Tencent Cloud SMS API.
        
        Args:
            phone_number: Target phone number
            verification_code: Verification code to send
            purpose: Purpose of verification
            template_vars: Additional template variables
            
        Returns:
            SMSResult with Tencent Cloud response
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
            
            # Prepare request payload
            template_param_list = [verification_code]
            if template_vars:
                template_param_list.extend(template_vars.values())
            
            payload = {
                "PhoneNumberSet": [normalized_phone],
                "SmsSdkAppId": self.config.template_id.split(':')[0] if ':' in self.config.template_id else "1400000000",
                "SignName": self.config.sign_name,
                "TemplateId": self.config.template_id.split(':')[1] if ':' in self.config.template_id else self.config.template_id,
                "TemplateParamSet": template_param_list
            }
            
            # Generate headers with signature
            headers = self._generate_headers(json.dumps(payload))
            
            # Send HTTP request
            url = f"https://{self.endpoint}/"
            
            async with aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self.config.health_check_timeout)
            ) as session:
                async with session.post(url, json=payload, headers=headers) as response:
                    response_data = await response.json()
            
            # Parse response
            if 'Response' in response_data:
                response_body = response_data['Response']
                
                if 'Error' in response_body:
                    # Handle error response
                    error_code = response_body['Error'].get('Code', 'Unknown')
                    error_message = response_body['Error'].get('Message', 'Unknown error')
                    
                    status = self._map_error_status(error_code)
                    
                    return SMSResult(
                        status=status,
                        error_message=f"Tencent Cloud error {error_code}: {error_message}",
                        provider_response=response_data,
                        sent_at=datetime.utcnow()
                    )
                else:
                    # Success response
                    send_status_set = response_body.get('SendStatusSet', [])
                    if send_status_set:
                        send_status = send_status_set[0]
                        if send_status.get('Code') == 'Ok':
                            return SMSResult(
                                status=SMSStatus.SUCCESS,
                                message_id=send_status.get('SerialNo'),
                                provider_response=response_data,
                                cost=send_status.get('Fee', 0) / 10000.0,  # Convert from 万分之一 to yuan
                                sent_at=datetime.utcnow()
                            )
                        else:
                            return SMSResult(
                                status=SMSStatus.PROVIDER_ERROR,
                                error_message=f"SMS send failed: {send_status.get('Message', 'Unknown')}",
                                provider_response=response_data,
                                sent_at=datetime.utcnow()
                            )
                    else:
                        return SMSResult(
                            status=SMSStatus.SUCCESS,
                            provider_response=response_data,
                            sent_at=datetime.utcnow()
                        )
            else:
                return SMSResult(
                    status=SMSStatus.PROVIDER_ERROR,
                    error_message="Invalid response format from Tencent Cloud",
                    provider_response=response_data,
                    sent_at=datetime.utcnow()
                )
                
        except asyncio.TimeoutError:
            return SMSResult(
                status=SMSStatus.NETWORK_ERROR,
                error_message="Tencent Cloud SMS API timeout",
                sent_at=datetime.utcnow()
            )
        except Exception as e:
            logger.error(f"Tencent Cloud SMS error: {e}")
            return SMSResult(
                status=SMSStatus.PROVIDER_ERROR,
                error_message=f"Tencent Cloud SMS error: {str(e)}",
                sent_at=datetime.utcnow()
            )
    
    async def check_health(self) -> bool:
        """
        Check Tencent Cloud SMS service health.
        
        Returns:
            True if service is healthy
        """
        try:
            # Use DescribeSmsSignList API to check service health
            payload = {
                "SignIdSet": [1],  # Dummy sign ID
                "International": 0,
            }
            
            # Generate headers with signature
            headers = self._generate_headers(json.dumps(payload))
            
            # Send health check request
            url = f"https://{self.endpoint}/"
            
            async with aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self.config.health_check_timeout)
            ) as session:
                async with session.post(url, json=payload, headers=headers) as response:
                    response_data = await response.json()
            
            # Check if API is responsive
            is_healthy = 'Response' in response_data
            self._update_health_status(is_healthy)
            
            logger.debug(f"Tencent Cloud SMS health check: {is_healthy}")
            return is_healthy
            
        except Exception as e:
            logger.error(f"Tencent Cloud SMS health check failed: {e}")
            self._update_health_status(False)
            return False
    
    def _generate_headers(self, payload: str) -> Dict[str, str]:
        """
        Generate Tencent Cloud API headers with signature.
        
        Args:
            payload: Request payload JSON string
            
        Returns:
            Headers dictionary with authorization
        """
        import time
        
        # Current timestamp
        timestamp = int(time.time())
        date = datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d')
        
        # Canonical request
        http_request_method = "POST"
        canonical_uri = "/"
        canonical_querystring = ""
        canonical_headers = f"content-type:application/json; charset=utf-8\nhost:{self.endpoint}\nx-tc-action:SendSms\n"
        signed_headers = "content-type;host;x-tc-action"
        hashed_request_payload = hashlib.sha256(payload.encode('utf-8')).hexdigest()
        
        canonical_request = f"{http_request_method}\n{canonical_uri}\n{canonical_querystring}\n{canonical_headers}\n{signed_headers}\n{hashed_request_payload}"
        
        # String to sign
        algorithm = "TC3-HMAC-SHA256"
        credential_scope = f"{date}/{self.service}/tc3_request"
        hashed_canonical_request = hashlib.sha256(canonical_request.encode('utf-8')).hexdigest()
        string_to_sign = f"{algorithm}\n{timestamp}\n{credential_scope}\n{hashed_canonical_request}"
        
        # Calculate signature
        secret_date = hmac.new(
            f"TC3{self.config.secret_key}".encode('utf-8'),
            date.encode('utf-8'),
            hashlib.sha256
        ).digest()
        secret_service = hmac.new(secret_date, self.service.encode('utf-8'), hashlib.sha256).digest()
        secret_signing = hmac.new(secret_service, "tc3_request".encode('utf-8'), hashlib.sha256).digest()
        signature = hmac.new(secret_signing, string_to_sign.encode('utf-8'), hashlib.sha256).hexdigest()
        
        # Authorization header
        authorization = f"{algorithm} Credential={self.config.access_key}/{credential_scope}, SignedHeaders={signed_headers}, Signature={signature}"
        
        return {
            "Authorization": authorization,
            "Content-Type": "application/json; charset=utf-8",
            "Host": self.endpoint,
            "X-TC-Action": "SendSms",
            "X-TC-Timestamp": str(timestamp),
            "X-TC-Version": self.version,
            "X-TC-Region": self.region,
        }
    
    def _map_error_status(self, error_code: str) -> SMSStatus:
        """
        Map Tencent Cloud error codes to SMS status.
        
        Args:
            error_code: Tencent Cloud error code
            
        Returns:
            Mapped SMS status
        """
        error_mapping = {
            'InvalidParameterValue.IncorrectPhoneNumber': SMSStatus.INVALID_NUMBER,
            'LimitExceeded.PhoneNumberCountLimit': SMSStatus.RATE_LIMITED,
            'LimitExceeded.PhoneNumberDayLimit': SMSStatus.RATE_LIMITED,
            'LimitExceeded.PhoneNumberThirtySecondLimit': SMSStatus.RATE_LIMITED,
            'InvalidParameterValue.TemplateParameterFormatError': SMSStatus.FAILED,
            'InvalidParameterValue.TemplateParameterLengthLimit': SMSStatus.FAILED,
        }
        
        return error_mapping.get(error_code, SMSStatus.PROVIDER_ERROR)
    
    def get_provider_name(self) -> str:
        """Get provider name."""
        return "Tencent Cloud SMS"
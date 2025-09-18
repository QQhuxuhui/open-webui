import time
import random
import logging
from typing import Optional
from pydantic import BaseModel
from open_webui.internal.db import Base, get_db
from sqlalchemy import Column, String, BigInteger, Boolean

log = logging.getLogger(__name__)

####################
# Phone Auth DB Schema
####################

class PhoneVerification(Base):
    __tablename__ = "phone_verification"

    id = Column(String, primary_key=True)
    phone = Column(String(20), nullable=False, index=True)
    code = Column(String(6), nullable=False)
    created_at = Column(BigInteger)
    expires_at = Column(BigInteger)
    used = Column(Boolean, default=False)
    attempts = Column(BigInteger, default=0)

####################
# Pydantic Models
####################

class PhoneVerificationModel(BaseModel):
    id: str
    phone: str
    code: str
    created_at: int
    expires_at: int
    used: bool = False
    attempts: int = 0

class PhoneSignupForm(BaseModel):
    phone: str
    code: str
    name: str
    privacy_agreed: bool
    terms_agreed: bool

class PhoneSigninForm(BaseModel):
    phone: str
    code: str

class SendCodeForm(BaseModel):
    phone: str

class VerifyCodeResponse(BaseModel):
    valid: bool
    message: str

####################
# Phone Verification Table
####################

class PhoneVerificationTable:
    def generate_code(self) -> str:
        """生成6位验证码"""
        return str(random.randint(100000, 999999))
    
    def create_verification(self, phone: str) -> Optional[PhoneVerificationModel]:
        """创建手机验证码记录"""
        import uuid
        try:
            with get_db() as db:
                # 检查5分钟内是否已发送验证码
                current_time = int(time.time())
                recent_verification = db.query(PhoneVerification).filter(
                    PhoneVerification.phone == phone,
                    PhoneVerification.created_at > current_time - 300  # 5分钟
                ).first()
                
                if recent_verification:
                    return None
                    
                code = self.generate_code()
                verification = PhoneVerificationModel(
                    id=str(uuid.uuid4()),
                    phone=phone,
                    code=code,
                    created_at=current_time,
                    expires_at=current_time + 300,  # 5分钟过期
                    used=False,
                    attempts=0
                )
                
                result = PhoneVerification(**verification.model_dump())
                db.add(result)
                db.commit()
                db.refresh(result)
                
                return verification
        except Exception as e:
            log.error(f"创建验证码失败: {e}")
            return None
    
    def verify_code(self, phone: str, code: str) -> tuple[bool, str]:
        """验证手机验证码"""
        try:
            with get_db() as db:
                current_time = int(time.time())
                verification = db.query(PhoneVerification).filter(
                    PhoneVerification.phone == phone,
                    PhoneVerification.code == code,
                    PhoneVerification.used == False,
                    PhoneVerification.expires_at > current_time
                ).first()
                
                if not verification:
                    return False, "验证码无效或已过期"
                
                # 标记为已使用
                db.query(PhoneVerification).filter_by(id=verification.id).update({
                    "used": True,
                    "attempts": verification.attempts + 1
                })
                db.commit()
                
                return True, "验证成功"
        except Exception as e:
            log.error(f"验证码校验失败: {e}")
            return False, "验证失败"
    
    def cleanup_expired(self):
        """清理过期的验证码记录"""
        try:
            with get_db() as db:
                current_time = int(time.time())
                db.query(PhoneVerification).filter(
                    PhoneVerification.expires_at < current_time - 86400  # 1天前
                ).delete()
                db.commit()
        except Exception as e:
            log.error(f"清理过期验证码失败: {e}")

PhoneVerifications = PhoneVerificationTable()
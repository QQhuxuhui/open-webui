import time
import logging
from typing import Optional
from pydantic import BaseModel
from open_webui.internal.db import Base, get_db
from sqlalchemy import Column, String, BigInteger, Boolean, Text
from cryptography.fernet import Fernet
import os

log = logging.getLogger(__name__)

####################
# User Profile DB Schema
####################

class UserProfile(Base):
    __tablename__ = "user_profile"

    id = Column(String, primary_key=True)
    user_id = Column(String, nullable=False, index=True, unique=True)
    real_name_encrypted = Column(Text)  # 加密存储的真实姓名
    id_card_encrypted = Column(Text)    # 加密存储的身份证号
    verified = Column(Boolean, default=False)
    verification_status = Column(String, default="pending")  # pending, approved, rejected
    id_card_front_path = Column(String)  # 身份证正面照路径
    id_card_back_path = Column(String)   # 身份证背面照路径
    created_at = Column(BigInteger)
    updated_at = Column(BigInteger)
    verified_at = Column(BigInteger, nullable=True)

####################
# Pydantic Models
####################

class UserProfileModel(BaseModel):
    id: str
    user_id: str
    real_name_encrypted: Optional[str] = None
    id_card_encrypted: Optional[str] = None
    verified: bool = False
    verification_status: str = "pending"
    id_card_front_path: Optional[str] = None
    id_card_back_path: Optional[str] = None
    created_at: int
    updated_at: int
    verified_at: Optional[int] = None

class UserProfileForm(BaseModel):
    real_name: str
    id_card: str

class UserProfileUpdateForm(BaseModel):
    real_name: Optional[str] = None
    id_card: Optional[str] = None

class UserProfileResponse(BaseModel):
    user_id: str
    real_name: Optional[str] = None
    id_card_masked: Optional[str] = None  # 脱敏显示
    verified: bool
    verification_status: str
    has_id_card_photos: bool
    created_at: int
    updated_at: int
    verified_at: Optional[int] = None

####################
# Encryption Helper
####################

class EncryptionHelper:
    def __init__(self):
        # 从环境变量获取加密密钥，如果没有则生成新的
        key = os.getenv("PROFILE_ENCRYPTION_KEY")
        if not key:
            key = Fernet.generate_key().decode()
            log.warning("未设置PROFILE_ENCRYPTION_KEY环境变量，使用临时密钥")
        
        self.cipher = Fernet(key if isinstance(key, bytes) else key.encode())
    
    def encrypt(self, data: str) -> str:
        """加密字符串数据"""
        if not data:
            return ""
        return self.cipher.encrypt(data.encode()).decode()
    
    def decrypt(self, encrypted_data: str) -> str:
        """解密字符串数据"""
        if not encrypted_data:
            return ""
        try:
            return self.cipher.decrypt(encrypted_data.encode()).decode()
        except Exception as e:
            log.error(f"解密失败: {e}")
            return ""

####################
# User Profile Table
####################

class UserProfileTable:
    def __init__(self):
        self.encryption = EncryptionHelper()
    
    def mask_id_card(self, id_card: str) -> str:
        """身份证号脱敏显示"""
        if not id_card or len(id_card) < 8:
            return ""
        return id_card[:4] + "*" * (len(id_card) - 8) + id_card[-4:]
    
    def create_profile(self, user_id: str, real_name: str, id_card: str) -> Optional[UserProfileModel]:
        """创建用户实名认证资料"""
        import uuid
        try:
            with get_db() as db:
                # 检查是否已存在
                existing = db.query(UserProfile).filter_by(user_id=user_id).first()
                if existing:
                    return None
                
                current_time = int(time.time())
                profile = UserProfileModel(
                    id=str(uuid.uuid4()),
                    user_id=user_id,
                    real_name_encrypted=self.encryption.encrypt(real_name),
                    id_card_encrypted=self.encryption.encrypt(id_card),
                    verified=False,
                    verification_status="pending",
                    created_at=current_time,
                    updated_at=current_time
                )
                
                result = UserProfile(**profile.model_dump())
                db.add(result)
                db.commit()
                db.refresh(result)
                
                return profile
        except Exception as e:
            log.error(f"创建用户资料失败: {e}")
            return None
    
    def update_profile(self, user_id: str, update_data: UserProfileUpdateForm) -> bool:
        """更新用户实名认证资料"""
        try:
            with get_db() as db:
                profile = db.query(UserProfile).filter_by(user_id=user_id).first()
                if not profile:
                    return False
                
                current_time = int(time.time())
                update_dict = {"updated_at": current_time}
                
                if update_data.real_name:
                    update_dict["real_name_encrypted"] = self.encryption.encrypt(update_data.real_name)
                    # 更新信息后重置认证状态
                    update_dict["verified"] = False
                    update_dict["verification_status"] = "pending"
                    update_dict["verified_at"] = None
                
                if update_data.id_card:
                    update_dict["id_card_encrypted"] = self.encryption.encrypt(update_data.id_card)
                    # 更新信息后重置认证状态
                    update_dict["verified"] = False
                    update_dict["verification_status"] = "pending"
                    update_dict["verified_at"] = None
                
                db.query(UserProfile).filter_by(user_id=user_id).update(update_dict)
                db.commit()
                
                return True
        except Exception as e:
            log.error(f"更新用户资料失败: {e}")
            return False
    
    def get_profile(self, user_id: str) -> Optional[UserProfileResponse]:
        """获取用户实名认证资料"""
        try:
            with get_db() as db:
                profile = db.query(UserProfile).filter_by(user_id=user_id).first()
                if not profile:
                    return None
                
                # 解密敏感信息
                real_name = self.encryption.decrypt(profile.real_name_encrypted) if profile.real_name_encrypted else None
                id_card = self.encryption.decrypt(profile.id_card_encrypted) if profile.id_card_encrypted else None
                
                return UserProfileResponse(
                    user_id=profile.user_id,
                    real_name=real_name,
                    id_card_masked=self.mask_id_card(id_card) if id_card else None,
                    verified=profile.verified,
                    verification_status=profile.verification_status,
                    has_id_card_photos=bool(profile.id_card_front_path and profile.id_card_back_path),
                    created_at=profile.created_at,
                    updated_at=profile.updated_at,
                    verified_at=profile.verified_at
                )
        except Exception as e:
            log.error(f"获取用户资料失败: {e}")
            return None
    
    def update_id_card_photos(self, user_id: str, front_path: str = None, back_path: str = None) -> bool:
        """更新身份证照片路径"""
        try:
            with get_db() as db:
                update_dict = {
                    "updated_at": int(time.time())
                }
                
                if front_path:
                    update_dict["id_card_front_path"] = front_path
                
                if back_path:
                    update_dict["id_card_back_path"] = back_path
                
                db.query(UserProfile).filter_by(user_id=user_id).update(update_dict)
                db.commit()
                
                return True
        except Exception as e:
            log.error(f"更新身份证照片失败: {e}")
            return False
    
    def update_verification_status(self, user_id: str, status: str, verified: bool = False) -> bool:
        """更新认证状态（管理员操作）"""
        try:
            with get_db() as db:
                current_time = int(time.time())
                update_dict = {
                    "verification_status": status,
                    "verified": verified,
                    "updated_at": current_time
                }
                
                if verified:
                    update_dict["verified_at"] = current_time
                
                db.query(UserProfile).filter_by(user_id=user_id).update(update_dict)
                db.commit()
                
                return True
        except Exception as e:
            log.error(f"更新认证状态失败: {e}")
            return False

UserProfiles = UserProfileTable()
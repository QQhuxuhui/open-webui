"""Agreement management service."""

import logging
from typing import Optional, Dict, Any, List
from datetime import datetime

from models.compliance import ConsentType, UserConsent
from extensions.ext_database import db

logger = logging.getLogger(__name__)


class Agreement:
    """Agreement content and metadata."""
    
    def __init__(self, agreement_type: str, version: str, content: str, last_updated: datetime):
        self.type = agreement_type
        self.version = version
        self.content = content
        self.last_updated = last_updated


class AgreementService:
    """Service for managing agreements and user consents."""
    
    # Static agreement content (in production, this would be in a database)
    _agreements = {
        'privacy_policy': Agreement(
            agreement_type='privacy_policy',
            version='1.0',
            content="""
# 隐私政策

## 信息收集
我们收集您提供的信息，包括但不限于：
- 手机号码用于账户注册和身份验证
- 设备信息用于安全验证
- 使用日志用于服务改进

## 信息使用
您的信息将用于：
- 提供和维护服务
- 身份验证和账户安全
- 改进用户体验
- 符合法律法规要求

## 信息保护
我们采取行业标准的安全措施保护您的个人信息：
- 加密存储敏感数据
- 访问控制和审计日志
- 定期安全评估
- 员工隐私培训

## 信息共享
我们不会出售、交易或转让您的个人信息给第三方，除非：
- 获得您的明确同意
- 法律法规要求
- 保护我们的合法权益

## 联系我们
如有隐私相关问题，请联系：privacy@example.com

最后更新：2025年1月13日
            """.strip(),
            last_updated=datetime(2025, 1, 13, 0, 0, 0)
        ),
        'terms_of_service': Agreement(
            agreement_type='terms_of_service',
            version='1.0',
            content="""
# 服务条款

## 服务提供
本平台为用户提供AI聊天和相关服务。使用本服务即表示您同意遵守以下条款。

## 用户责任
作为用户，您同意：
- 提供真实准确的注册信息
- 不利用服务进行违法活动
- 尊重其他用户和平台规则
- 保护您的账户安全

## 服务限制
我们有权在以下情况下限制或终止服务：
- 违反服务条款
- 从事恶意或有害行为
- 技术维护需要
- 法律法规要求

## 知识产权
平台内容受知识产权法保护。用户生成的内容归用户所有，但授权平台使用。

## 免责声明
在法律允许范围内，我们对以下情况不承担责任：
- 服务中断或错误
- 用户内容或行为
- 第三方链接或内容
- 不可抗力因素

## 条款变更
我们可能会更新服务条款。重要变更将通过平台通知用户。

## 联系我们
如有服务相关问题，请联系：support@example.com

最后更新：2025年1月13日
            """.strip(),
            last_updated=datetime(2025, 1, 13, 0, 0, 0)
        )
    }
    
    def get_agreements(self) -> Dict[str, Dict[str, Any]]:
        """
        Get all available agreements with their current versions and content.
        
        Returns:
            Dictionary with agreement type as key and agreement info as value
        """
        try:
            result = {}
            
            for agreement_type, agreement in self._agreements.items():
                result[agreement_type] = {
                    'version': agreement.version,
                    'content': agreement.content,
                    'last_updated': agreement.last_updated.isoformat()
                }
            
            logger.info("Retrieved all agreements")
            return result
            
        except Exception as e:
            logger.error(f"Failed to get agreements: {e}", exc_info=True)
            return {}
    
    def get_agreement(self, agreement_type: str) -> Optional[Dict[str, Any]]:
        """
        Get a specific agreement by type.
        
        Args:
            agreement_type: Type of agreement to retrieve
            
        Returns:
            Agreement information or None if not found
        """
        try:
            if agreement_type not in self._agreements:
                logger.warning(f"Agreement type not found: {agreement_type}")
                return None
            
            agreement = self._agreements[agreement_type]
            return {
                'type': agreement.type,
                'version': agreement.version,
                'content': agreement.content,
                'last_updated': agreement.last_updated.isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to get agreement {agreement_type}: {e}", exc_info=True)
            return None
    
    def record_consent(
        self,
        account_id: str,
        consent_type: ConsentType,
        agreed: bool,
        version: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> bool:
        """
        Record user consent for an agreement.
        
        Args:
            account_id: User account ID
            consent_type: Type of consent
            agreed: Whether user agreed
            version: Version of the agreement
            ip_address: Client IP address
            user_agent: Client user agent
            
        Returns:
            True if consent recorded successfully, False otherwise
        """
        try:
            # Check if consent already exists for this type and account
            existing_consent = db.session.query(UserConsent).filter_by(
                account_id=account_id,
                consent_type=consent_type
            ).first()
            
            if existing_consent:
                # Update existing consent
                existing_consent.agreed = agreed
                existing_consent.version = version
                existing_consent.ip_address = ip_address
                existing_consent.user_agent = user_agent
                existing_consent.recorded_at = datetime.utcnow()
                existing_consent.updated_at = datetime.utcnow()
                
                logger.info(f"Updated consent for account {account_id}: {consent_type} -> {agreed}")
            else:
                # Create new consent record
                consent = UserConsent(
                    account_id=account_id,
                    consent_type=consent_type,
                    agreed=agreed,
                    version=version,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    recorded_at=datetime.utcnow(),
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                )
                
                db.session.add(consent)
                logger.info(f"Recorded new consent for account {account_id}: {consent_type} -> {agreed}")
            
            db.session.commit()
            return True
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Failed to record consent: {e}", exc_info=True)
            return False
    
    def get_user_consents(self, account_id: str) -> List[Dict[str, Any]]:
        """
        Get all consent records for a user.
        
        Args:
            account_id: User account ID
            
        Returns:
            List of consent records
        """
        try:
            consents = db.session.query(UserConsent).filter_by(account_id=account_id).all()
            
            result = []
            for consent in consents:
                result.append({
                    'id': consent.id,
                    'consent_type': consent.consent_type,
                    'agreed': consent.agreed,
                    'version': consent.version,
                    'ip_address': consent.ip_address,
                    'user_agent': consent.user_agent,
                    'recorded_at': consent.recorded_at.isoformat() if consent.recorded_at else None,
                    'created_at': consent.created_at.isoformat(),
                    'updated_at': consent.updated_at.isoformat()
                })
            
            logger.info(f"Retrieved {len(result)} consent records for account {account_id}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to get user consents: {e}", exc_info=True)
            return []
    
    def check_required_consents(self, account_id: str) -> Dict[str, bool]:
        """
        Check if user has agreed to all required consents.
        
        Args:
            account_id: User account ID
            
        Returns:
            Dictionary with consent types as keys and agreement status as values
        """
        try:
            required_consents = [ConsentType.PRIVACY_POLICY, ConsentType.TERMS_OF_SERVICE]
            result = {}
            
            for consent_type in required_consents:
                consent = db.session.query(UserConsent).filter_by(
                    account_id=account_id,
                    consent_type=consent_type,
                    agreed=True
                ).first()
                
                result[consent_type] = consent is not None
            
            logger.info(f"Checked required consents for account {account_id}: {result}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to check required consents: {e}", exc_info=True)
            return {consent_type: False for consent_type in [ConsentType.PRIVACY_POLICY, ConsentType.TERMS_OF_SERVICE]}
    
    def withdraw_consent(
        self,
        account_id: str,
        consent_type: ConsentType,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> bool:
        """
        Withdraw user consent for an agreement.
        
        Args:
            account_id: User account ID
            consent_type: Type of consent to withdraw
            ip_address: Client IP address
            user_agent: Client user agent
            
        Returns:
            True if consent withdrawn successfully, False otherwise
        """
        try:
            consent = db.session.query(UserConsent).filter_by(
                account_id=account_id,
                consent_type=consent_type
            ).first()
            
            if not consent:
                logger.warning(f"Consent not found for withdrawal: account={account_id}, type={consent_type}")
                return False
            
            consent.agreed = False
            consent.ip_address = ip_address
            consent.user_agent = user_agent
            consent.recorded_at = datetime.utcnow()
            consent.updated_at = datetime.utcnow()
            
            db.session.commit()
            
            logger.info(f"Withdrew consent for account {account_id}: {consent_type}")
            return True
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Failed to withdraw consent: {e}", exc_info=True)
            return False
    
    def get_consent_stats(self) -> Dict[str, Any]:
        """
        Get statistics about user consents.
        
        Returns:
            Dictionary with consent statistics
        """
        try:
            stats = {}
            
            for consent_type in ConsentType:
                agreed_count = db.session.query(UserConsent).filter_by(
                    consent_type=consent_type,
                    agreed=True
                ).count()
                
                total_count = db.session.query(UserConsent).filter_by(
                    consent_type=consent_type
                ).count()
                
                stats[consent_type] = {
                    'agreed_count': agreed_count,
                    'total_count': total_count,
                    'agreement_rate': round(agreed_count / total_count * 100, 2) if total_count > 0 else 0
                }
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get consent stats: {e}", exc_info=True)
            return {}
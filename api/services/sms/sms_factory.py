"""SMS adapter factory for creating provider instances."""

from typing import Dict, Type, Optional
import logging

from configs.sms import SMSConfig, SMSProvider
from .sms_adapter import SMSAdapter

logger = logging.getLogger(__name__)


class SMSProviderNotSupportedError(Exception):
    """Raised when requested SMS provider is not supported."""
    pass


class SMSFactory:
    """Factory for creating SMS adapter instances."""
    
    _adapters: Dict[SMSProvider, Type[SMSAdapter]] = {}
    _instances: Dict[SMSProvider, SMSAdapter] = {}
    
    @classmethod
    def register_adapter(cls, provider: SMSProvider, adapter_class: Type[SMSAdapter]) -> None:
        """
        Register an SMS adapter class for a provider.
        
        Args:
            provider: SMS provider enum
            adapter_class: Adapter class to register
        """
        cls._adapters[provider] = adapter_class
        logger.info(f"Registered SMS adapter for provider: {provider}")
    
    @classmethod
    def create_adapter(cls, config: Optional[SMSConfig] = None) -> SMSAdapter:
        """
        Create SMS adapter instance based on configuration.
        
        Args:
            config: SMS configuration (uses global config if None)
            
        Returns:
            SMS adapter instance
            
        Raises:
            SMSProviderNotSupportedError: If provider is not supported
        """
        if config is None:
            from configs.sms import sms_config
            config = sms_config
        
        provider = config.provider
        
        # Return cached instance if available
        if provider in cls._instances:
            return cls._instances[provider]
        
        # Get adapter class for provider
        if provider not in cls._adapters:
            # Auto-import provider adapters on first use
            cls._import_provider_adapters()
        
        if provider not in cls._adapters:
            raise SMSProviderNotSupportedError(
                f"SMS provider '{provider}' is not supported. "
                f"Available providers: {list(cls._adapters.keys())}"
            )
        
        # Create and cache adapter instance
        adapter_class = cls._adapters[provider]
        adapter = adapter_class(config)
        cls._instances[provider] = adapter
        
        logger.info(f"Created SMS adapter for provider: {provider}")
        return adapter
    
    @classmethod
    def get_supported_providers(cls) -> list[SMSProvider]:
        """Get list of supported SMS providers."""
        return list(cls._adapters.keys())
    
    @classmethod
    def clear_cache(cls) -> None:
        """Clear cached adapter instances."""
        cls._instances.clear()
        logger.info("Cleared SMS adapter cache")
    
    @classmethod 
    def _import_provider_adapters(cls) -> None:
        """Import and register all provider adapters."""
        try:
            # Import mock adapter (always available)
            from .providers.mock import MockSMSAdapter
            cls.register_adapter(SMSProvider.MOCK, MockSMSAdapter)
            
            # Import Alibaba Cloud adapter
            try:
                from .providers.alicloud import AlicloudSMSAdapter
                cls.register_adapter(SMSProvider.ALICLOUD, AlicloudSMSAdapter)
            except ImportError:
                logger.warning("Alibaba Cloud SMS adapter not available")
            
            # Import Tencent Cloud adapter
            try:
                from .providers.tencent import TencentSMSAdapter
                cls.register_adapter(SMSProvider.TENCENT, TencentSMSAdapter)
            except ImportError:
                logger.warning("Tencent Cloud SMS adapter not available")
                
            # Import Huawei Cloud adapter
            try:
                from .providers.huawei import HuaweiSMSAdapter
                cls.register_adapter(SMSProvider.HUAWEI, HuaweiSMSAdapter)
            except ImportError:
                logger.warning("Huawei Cloud SMS adapter not available")
                
        except Exception as e:
            logger.error(f"Error importing SMS provider adapters: {e}")


# Initialize factory on module import
SMSFactory._import_provider_adapters()
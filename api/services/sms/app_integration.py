"""SMS service Flask application integration."""

import logging
from flask import Flask

from controllers.auth.sms import bp as sms_auth_bp
from controllers.auth.phone import bp as phone_auth_bp
from controllers.system.sms import bp as sms_system_bp
from configs.sms import sms_config

logger = logging.getLogger(__name__)


def register_sms_blueprints(app: Flask) -> None:
    """
    Register SMS service blueprints with Flask application.
    
    Args:
        app: Flask application instance
    """
    try:
        # Register SMS authentication endpoints
        app.register_blueprint(sms_auth_bp)
        logger.info("Registered SMS auth endpoints: /api/auth/send-sms, /api/auth/verify-sms")
        
        # Register phone authentication endpoints
        app.register_blueprint(phone_auth_bp)
        logger.info("Registered phone auth endpoints: /api/auth/phone/register, /api/auth/phone/login")
        
        # Register SMS system monitoring endpoints  
        app.register_blueprint(sms_system_bp)
        logger.info("Registered SMS system endpoints: /api/system/sms/health, /api/system/sms/config")
        
    except Exception as e:
        logger.error(f"Failed to register SMS blueprints: {e}")
        raise


def validate_sms_configuration() -> bool:
    """
    Validate SMS configuration on application startup.
    
    Returns:
        True if configuration is valid, False otherwise
    """
    try:
        errors = sms_config.validate()
        
        if errors:
            logger.warning(f"SMS configuration validation errors: {errors}")
            if sms_config.provider != 'mock':
                logger.error("SMS service may not work properly with invalid configuration")
                return False
            else:
                logger.info("Using mock SMS provider, configuration warnings ignored")
        else:
            logger.info(f"SMS configuration validated successfully for provider: {sms_config.provider}")
        
        return True
        
    except Exception as e:
        logger.error(f"SMS configuration validation failed: {e}")
        return False


def initialize_sms_service(app: Flask) -> None:
    """
    Initialize SMS service with Flask application.
    
    Args:
        app: Flask application instance
    """
    with app.app_context():
        try:
            # Validate configuration
            config_valid = validate_sms_configuration()
            
            # Register blueprints
            register_sms_blueprints(app)
            
            # Log initialization status
            if config_valid:
                logger.info("SMS service initialized successfully")
            else:
                logger.warning("SMS service initialized with configuration warnings")
                
        except Exception as e:
            logger.error(f"Failed to initialize SMS service: {e}")
            raise


# Auto-initialization function for easy integration
def setup_sms_service(app: Flask) -> None:
    """
    Setup SMS service for Flask application.
    
    This is the main entry point for integrating SMS service.
    
    Args:
        app: Flask application instance
    """
    initialize_sms_service(app)
"""Production-ready configuration management with secrets handling.

This module provides enterprise-grade configuration management with:
- Environment variable loading
- Secrets management
- Configuration validation
- Default fallbacks
- Type safety
"""

import os
import json
import logging
from typing import Dict, Any, Optional, Union
from pathlib import Path
from dataclasses import dataclass, field

# Configure logging
logger = logging.getLogger(__name__)


@dataclass
class DatabaseConfig:
    """Database configuration settings."""
    url: str = field(default_factory=lambda: os.getenv('DATABASE_URL', 'sqlite:///production.db'))
    pool_size: int = field(default_factory=lambda: int(os.getenv('DB_POOL_SIZE', '5')))
    max_overflow: int = field(default_factory=lambda: int(os.getenv('DB_MAX_OVERFLOW', '10')))
    pool_timeout: int = field(default_factory=lambda: int(os.getenv('DB_POOL_TIMEOUT', '30')))
    echo: bool = field(default_factory=lambda: os.getenv('DB_ECHO', 'false').lower() == 'true')


@dataclass
class LLMConfig:
    """LLM configuration settings."""
    provider: str = field(default_factory=lambda: os.getenv('LLM_PROVIDER', 'openai'))
    model_name: str = field(default_factory=lambda: os.getenv('LLM_MODEL', 'gpt-3.5-turbo'))
    api_key: Optional[str] = field(default_factory=lambda: os.getenv('LLM_API_KEY'))
    max_tokens: int = field(default_factory=lambda: int(os.getenv('LLM_MAX_TOKENS', '1000')))
    temperature: float = field(default_factory=lambda: float(os.getenv('LLM_TEMPERATURE', '0.1')))
    timeout: int = field(default_factory=lambda: int(os.getenv('LLM_TIMEOUT', '30')))


@dataclass
class AgentConfig:
    """Agent configuration settings."""
    thread_id: str = field(default_factory=lambda: os.getenv('AGENT_THREAD_ID', 'default'))
    checkpoint_db_path: str = field(default_factory=lambda: os.getenv('CHECKPOINT_DB_PATH', 'checkpoint.db'))
    max_retries: int = field(default_factory=lambda: int(os.getenv('AGENT_MAX_RETRIES', '3')))
    request_timeout: int = field(default_factory=lambda: int(os.getenv('AGENT_REQUEST_TIMEOUT', '30')))
    enable_logging: bool = field(default_factory=lambda: os.getenv('AGENT_ENABLE_LOGGING', 'true').lower() == 'true')
    enable_monitoring: bool = field(default_factory=lambda: os.getenv('AGENT_ENABLE_MONITORING', 'true').lower() == 'true')
    rate_limit_per_minute: int = field(default_factory=lambda: int(os.getenv('AGENT_RATE_LIMIT_PER_MINUTE', '60')))


@dataclass
class SecurityConfig:
    """Security configuration settings."""
    enable_input_validation: bool = field(default_factory=lambda: os.getenv('SECURITY_ENABLE_INPUT_VALIDATION', 'true').lower() == 'true')
    enable_sql_injection_detection: bool = field(default_factory=lambda: os.getenv('SECURITY_ENABLE_SQL_INJECTION_DETECTION', 'true').lower() == 'true')
    max_query_length: int = field(default_factory=lambda: int(os.getenv('SECURITY_MAX_QUERY_LENGTH', '1000')))
    enable_rate_limiting: bool = field(default_factory=lambda: os.getenv('SECURITY_ENABLE_RATE_LIMITING', 'true').lower() == 'true')
    cors_enabled: bool = field(default_factory=lambda: os.getenv('SECURITY_CORS_ENABLED', 'true').lower() == 'true')
    cors_origins: str = field(default_factory=lambda: os.getenv('SECURITY_CORS_ORIGINS', '*'))


@dataclass
class MonitoringConfig:
    """Monitoring and observability configuration."""
    enable_metrics: bool = field(default_factory=lambda: os.getenv('MONITORING_ENABLE_METRICS', 'true').lower() == 'true')
    enable_tracing: bool = field(default_factory=lambda: os.getenv('MONITORING_ENABLE_TRACING', 'false').lower() == 'true')
    metrics_port: int = field(default_factory=lambda: int(os.getenv('MONITORING_METRICS_PORT', '8080')))
    health_check_port: int = field(default_factory=lambda: int(os.getenv('MONITORING_HEALTH_CHECK_PORT', '8081')))
    log_level: str = field(default_factory=lambda: os.getenv('LOG_LEVEL', 'INFO'))
    log_format: str = field(default_factory=lambda: os.getenv('LOG_FORMAT', 'json'))


@dataclass
class Config:
    """Main configuration class combining all sub-configurations."""
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    llm: LLMConfig = field(default_factory=LLMConfig)
    agent: AgentConfig = field(default_factory=AgentConfig)
    security: SecurityConfig = field(default_factory=SecurityConfig)
    monitoring: MonitoringConfig = field(default_factory=MonitoringConfig)
    
    # Environment
    environment: str = field(default_factory=lambda: os.getenv('ENVIRONMENT', 'development'))
    debug: bool = field(default_factory=lambda: os.getenv('DEBUG', 'false').lower() == 'true')
    
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.environment.lower() == 'production'
    
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.environment.lower() == 'development'


class ConfigManager:
    """Production-ready configuration manager with validation and secrets handling."""
    
    def __init__(self, config_file: Optional[str] = None):
        self.config_file = config_file
        self._config: Optional[Config] = None
        self._secrets: Dict[str, str] = {}
        
    def load_config(self) -> Config:
        """Load configuration from environment variables and optional config file."""
        logger.info("Loading configuration...")
        
        # Load from config file if provided
        config_data = {}
        if self.config_file and Path(self.config_file).exists():
            config_data = self._load_config_file()
            logger.info(f"Loaded configuration from {self.config_file}")
        
        # Override with environment variables
        config_data.update(self._load_env_config())
        
        # Create configuration instance
        self._config = Config()
        self._apply_config_overrides(config_data)
        
        # Load secrets
        self._load_secrets()
        
        # Validate configuration
        self._validate_config()
        
        logger.info(f"Configuration loaded successfully for environment: {self._config.environment}")
        return self._config
    
    def _load_config_file(self) -> Dict[str, Any]:
        """Load configuration from JSON file."""
        try:
            with open(self.config_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Failed to load config file {self.config_file}: {e}")
            return {}
    
    def _load_env_config(self) -> Dict[str, Any]:
        """Load configuration from environment variables."""
        env_config = {}
        
        # Database configuration
        for key in ['DATABASE_URL', 'DB_POOL_SIZE', 'DB_MAX_OVERFLOW', 'DB_POOL_TIMEOUT', 'DB_ECHO']:
            if os.getenv(key):
                env_config[key.lower()] = os.getenv(key)
        
        # LLM configuration
        for key in ['LLM_PROVIDER', 'LLM_MODEL', 'LLM_API_KEY', 'LLM_MAX_TOKENS', 'LLM_TEMPERATURE', 'LLM_TIMEOUT']:
            if os.getenv(key):
                env_config[key.lower()] = os.getenv(key)
        
        # Agent configuration
        for key in ['AGENT_THREAD_ID', 'CHECKPOINT_DB_PATH', 'AGENT_MAX_RETRIES', 'AGENT_REQUEST_TIMEOUT', 
                   'AGENT_ENABLE_LOGGING', 'AGENT_ENABLE_MONITORING', 'AGENT_RATE_LIMIT_PER_MINUTE']:
            if os.getenv(key):
                env_config[key.lower()] = os.getenv(key)
        
        # Security configuration
        for key in ['SECURITY_ENABLE_INPUT_VALIDATION', 'SECURITY_ENABLE_SQL_INJECTION_DETECTION', 
                   'SECURITY_MAX_QUERY_LENGTH', 'SECURITY_ENABLE_RATE_LIMITING', 'SECURITY_CORS_ENABLED', 'SECURITY_CORS_ORIGINS']:
            if os.getenv(key):
                env_config[key.lower()] = os.getenv(key)
        
        # Monitoring configuration
        for key in ['MONITORING_ENABLE_METRICS', 'MONITORING_ENABLE_TRACING', 'MONITORING_METRICS_PORT', 
                   'MONITORING_HEALTH_CHECK_PORT', 'LOG_LEVEL', 'LOG_FORMAT']:
            if os.getenv(key):
                env_config[key.lower()] = os.getenv(key)
        
        # General configuration
        for key in ['ENVIRONMENT', 'DEBUG']:
            if os.getenv(key):
                env_config[key.lower()] = os.getenv(key)
        
        return env_config
    
    def _apply_config_overrides(self, config_data: Dict[str, Any]):
        """Apply configuration overrides from file and environment."""
        if not config_data:
            return
        
        # Apply database overrides
        if 'database_url' in config_data:
            self._config.database.url = config_data['database_url']
        if 'db_pool_size' in config_data:
            self._config.database.pool_size = int(config_data['db_pool_size'])
        if 'db_max_overflow' in config_data:
            self._config.database.max_overflow = int(config_data['db_max_overflow'])
        if 'db_pool_timeout' in config_data:
            self._config.database.pool_timeout = int(config_data['db_pool_timeout'])
        if 'db_echo' in config_data:
            self._config.database.echo = str(config_data['db_echo']).lower() == 'true'
        
        # Apply LLM overrides
        if 'llm_provider' in config_data:
            self._config.llm.provider = config_data['llm_provider']
        if 'llm_model' in config_data:
            self._config.llm.model_name = config_data['llm_model']
        if 'llm_api_key' in config_data:
            self._config.llm.api_key = config_data['llm_api_key']
        if 'llm_max_tokens' in config_data:
            self._config.llm.max_tokens = int(config_data['llm_max_tokens'])
        if 'llm_temperature' in config_data:
            self._config.llm.temperature = float(config_data['llm_temperature'])
        if 'llm_timeout' in config_data:
            self._config.llm.timeout = int(config_data['llm_timeout'])
        
        # Apply agent overrides
        if 'agent_thread_id' in config_data:
            self._config.agent.thread_id = config_data['agent_thread_id']
        if 'checkpoint_db_path' in config_data:
            self._config.agent.checkpoint_db_path = config_data['checkpoint_db_path']
        if 'agent_max_retries' in config_data:
            self._config.agent.max_retries = int(config_data['agent_max_retries'])
        if 'agent_request_timeout' in config_data:
            self._config.agent.request_timeout = int(config_data['agent_request_timeout'])
        if 'agent_enable_logging' in config_data:
            self._config.agent.enable_logging = str(config_data['agent_enable_logging']).lower() == 'true'
        if 'agent_enable_monitoring' in config_data:
            self._config.agent.enable_monitoring = str(config_data['agent_enable_monitoring']).lower() == 'true'
        if 'agent_rate_limit_per_minute' in config_data:
            self._config.agent.rate_limit_per_minute = int(config_data['agent_rate_limit_per_minute'])
        
        # Apply security overrides
        if 'security_enable_input_validation' in config_data:
            self._config.security.enable_input_validation = str(config_data['security_enable_input_validation']).lower() == 'true'
        if 'security_enable_sql_injection_detection' in config_data:
            self._config.security.enable_sql_injection_detection = str(config_data['security_enable_sql_injection_detection']).lower() == 'true'
        if 'security_max_query_length' in config_data:
            self._config.security.max_query_length = int(config_data['security_max_query_length'])
        if 'security_enable_rate_limiting' in config_data:
            self._config.security.enable_rate_limiting = str(config_data['security_enable_rate_limiting']).lower() == 'true'
        if 'security_cors_enabled' in config_data:
            self._config.security.cors_enabled = str(config_data['security_cors_enabled']).lower() == 'true'
        if 'security_cors_origins' in config_data:
            self._config.security.cors_origins = config_data['security_cors_origins']
        
        # Apply monitoring overrides
        if 'monitoring_enable_metrics' in config_data:
            self._config.monitoring.enable_metrics = str(config_data['monitoring_enable_metrics']).lower() == 'true'
        if 'monitoring_enable_tracing' in config_data:
            self._config.monitoring.enable_tracing = str(config_data['monitoring_enable_tracing']).lower() == 'true'
        if 'monitoring_metrics_port' in config_data:
            self._config.monitoring.metrics_port = int(config_data['monitoring_metrics_port'])
        if 'monitoring_health_check_port' in config_data:
            self._config.monitoring.health_check_port = int(config_data['monitoring_health_check_port'])
        if 'log_level' in config_data:
            self._config.monitoring.log_level = config_data['log_level']
        if 'log_format' in config_data:
            self._config.monitoring.log_format = config_data['log_format']
        
        # Apply general overrides
        if 'environment' in config_data:
            self._config.environment = config_data['environment']
        if 'debug' in config_data:
            self._config.debug = str(config_data['debug']).lower() == 'true'
    
    def _load_secrets(self):
        """Load secrets from environment variables or secret management service."""
        logger.info("Loading secrets...")
        
        # Load API keys and sensitive data
        secret_keys = [
            'LLM_API_KEY',
            'DATABASE_PASSWORD',
            'SECRET_KEY',
            'JWT_SECRET',
            'ENCRYPTION_KEY'
        ]
        
        for key in secret_keys:
            value = os.getenv(key)
            if value:
                self._secrets[key] = value
                logger.info(f"Loaded secret: {key}")
        
        # Load from secret files if they exist
        secret_files = [
            '/run/secrets/llm_api_key',
            '/run/secrets/database_password',
            '/run/secrets/secret_key'
        ]
        
        for file_path in secret_files:
            if Path(file_path).exists():
                try:
                    with open(file_path, 'r') as f:
                        secret_name = Path(file_path).stem.upper()
                        self._secrets[secret_name] = f.read().strip()
                        logger.info(f"Loaded secret from file: {secret_name}")
                except Exception as e:
                    logger.warning(f"Failed to load secret from {file_path}: {e}")
    
    def _validate_config(self):
        """Validate configuration for production readiness."""
        logger.info("Validating configuration...")
        
        errors = []
        warnings = []
        
        # Validate database configuration
        if not self._config.database.url:
            errors.append("DATABASE_URL is required")
        
        # Validate LLM configuration
        if self._config.llm.provider == 'openai' and not self._config.llm.api_key:
            if self._config.is_production():
                errors.append("LLM_API_KEY is required for production")
            else:
                warnings.append("LLM_API_KEY not set - using development mode")
        
        # Validate security configuration
        if self._config.is_production():
            if not self._config.security.enable_input_validation:
                warnings.append("Input validation disabled in production")
            if not self._config.security.enable_sql_injection_detection:
                warnings.append("SQL injection detection disabled in production")
            if not self._config.security.enable_rate_limiting:
                warnings.append("Rate limiting disabled in production")
        
        # Validate monitoring configuration
        if self._config.monitoring.enable_tracing and not self._config.monitoring.enable_metrics:
            warnings.append("Tracing enabled but metrics disabled")
        
        # Log validation results
        if errors:
            logger.error(f"Configuration validation failed with {len(errors)} errors")
            for error in errors:
                logger.error(f"  - {error}")
            raise ValueError(f"Configuration validation failed: {'; '.join(errors)}")
        
        if warnings:
            logger.warning(f"Configuration validation completed with {len(warnings)} warnings")
            for warning in warnings:
                logger.warning(f"  - {warning}")
        
        logger.info("Configuration validation completed successfully")
    
    def get_config(self) -> Config:
        """Get the loaded configuration."""
        if self._config is None:
            self.load_config()
        return self._config
    
    def get_secret(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """Get a secret value."""
        return self._secrets.get(key, default)
    
    def reload_config(self):
        """Reload configuration from sources."""
        logger.info("Reloading configuration...")
        self._config = None
        self._secrets = {}
        self.load_config()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        config = self.get_config()
        return {
            'environment': config.environment,
            'debug': config.debug,
            'database': {
                'url': config.database.url,
                'pool_size': config.database.pool_size,
                'max_overflow': config.database.max_overflow,
                'pool_timeout': config.database.pool_timeout,
                'echo': config.database.echo
            },
            'llm': {
                'provider': config.llm.provider,
                'model_name': config.llm.model_name,
                'max_tokens': config.llm.max_tokens,
                'temperature': config.llm.temperature,
                'timeout': config.llm.timeout
            },
            'agent': {
                'thread_id': config.agent.thread_id,
                'checkpoint_db_path': config.agent.checkpoint_db_path,
                'max_retries': config.agent.max_retries,
                'request_timeout': config.agent.request_timeout,
                'enable_logging': config.agent.enable_logging,
                'enable_monitoring': config.agent.enable_monitoring,
                'rate_limit_per_minute': config.agent.rate_limit_per_minute
            },
            'security': {
                'enable_input_validation': config.security.enable_input_validation,
                'enable_sql_injection_detection': config.security.enable_sql_injection_detection,
                'max_query_length': config.security.max_query_length,
                'enable_rate_limiting': config.security.enable_rate_limiting,
                'cors_enabled': config.security.cors_enabled,
                'cors_origins': config.security.cors_origins
            },
            'monitoring': {
                'enable_metrics': config.monitoring.enable_metrics,
                'enable_tracing': config.monitoring.enable_tracing,
                'metrics_port': config.monitoring.metrics_port,
                'health_check_port': config.monitoring.health_check_port,
                'log_level': config.monitoring.log_level,
                'log_format': config.monitoring.log_format
            }
        }


# Global configuration manager instance
config_manager = ConfigManager()


def get_config() -> Config:
    """Get the global configuration instance."""
    return config_manager.get_config()


def reload_config():
    """Reload the global configuration."""
    config_manager.reload_config()


# Export main components
__all__ = ['ConfigManager', 'Config', 'DatabaseConfig', 'LLMConfig', 'AgentConfig', 'SecurityConfig', 'MonitoringConfig', 'get_config', 'reload_config']
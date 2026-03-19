"""
Centralized Configuration Management for Intent Engine.

This module provides a single source of truth for all configuration settings,
with validation, type safety, and environment variable management.

Usage:
    from app.config.settings import settings

    # Access settings
    db_url = settings.database.effective_url
    secret_key = settings.security.secret_key

    # Validate at startup
    settings.validate_production()
"""

import os
from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class DatabaseSettings(BaseSettings):
    """Database configuration settings."""

    model_config = SettingsConfigDict(
        env_prefix="DATABASE_",
        env_file=os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".env"
        ),
        extra="ignore",
    )

    # Individual connection parameters
    host: str = Field(default="localhost", description="Database host")
    port: int = Field(default=5432, description="Database port")
    name: str = Field(default="intent_engine", description="Database name")
    user: str = Field(default="intent_user", description="Database user")
    password: str = Field(
        default="change_this_password_in_production",
        description="Database password",
    )

    # Connection pool settings
    pool_size: int = Field(default=10, ge=1, le=100, description="Connection pool size")
    max_overflow: int = Field(
        default=20, ge=0, le=100, description="Max overflow connections"
    )
    pool_timeout: int = Field(
        default=30, ge=1, le=300, description="Pool timeout (seconds)"
    )
    pool_recycle: int = Field(
        default=1800, ge=60, le=7200, description="Pool recycle time (seconds)"
    )

    # Full connection URL (overrides individual params if set)
    url: str | None = Field(
        default=None,
        description="Full database URL (overrides individual settings)",
    )

    # PgBouncer settings
    pgbouncer_enabled: bool = Field(
        default=False, description="Enable PgBouncer connection pooling"
    )
    pgbouncer_host: str = Field(default="localhost", description="PgBouncer host")
    pgbouncer_port: int = Field(default=6543, description="PgBouncer port")

    @property
    def effective_url(self) -> str:
        """Get the effective database URL."""
        if self.url:
            return self.url

        if self.pgbouncer_enabled:
            host = self.pgbouncer_host
            port = self.pgbouncer_port
        else:
            host = self.host
            port = self.port

        return f"postgresql://{self.user}:{self.password}@{host}:{port}/{self.name}"

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        """Validate password strength in production."""
        env = os.getenv("ENVIRONMENT", "development")
        if env == "production":
            if v in (
                "change_this_password_in_production",
                "password",
                "admin",
                "intent_secure_password_change_in_prod",
            ):
                raise ValueError(
                    "Weak database password detected. "
                    "Please use a strong, unique password in production."
                )
            if len(v) < 12:
                raise ValueError(
                    "Database password must be at least 12 characters in production."
                )
        return v


class RedisSettings(BaseSettings):
    """Redis configuration settings."""

    model_config = SettingsConfigDict(
        env_prefix="REDIS_",
        env_file=os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".env"
        ),
        extra="ignore",
    )

    enabled: bool = Field(default=True, description="Enable Redis caching")
    host: str = Field(default="localhost", description="Redis host")
    port: int = Field(default=6379, description="Redis port")
    db: int = Field(default=0, ge=0, le=15, description="Redis database number")
    password: str | None = Field(default=None, description="Redis password")
    url: str | None = Field(
        default=None, description="Full Redis URL (overrides individual settings)"
    )

    # Connection pool settings
    max_connections: int = Field(
        default=50, ge=1, le=500, description="Max Redis connections"
    )
    timeout: float = Field(
        default=5.0, ge=0.1, le=60.0, description="Connection timeout (seconds)"
    )

    # SSL/TLS settings
    ssl: bool = Field(default=False, description="Enable SSL/TLS for Redis")
    ssl_cert_reqs: Literal["none", "optional", "required"] = Field(
        default="none", description="SSL certificate requirements"
    )

    @property
    def effective_url(self) -> str:
        """Get the effective Redis URL."""
        if self.url:
            return self.url

        scheme = "rediss" if self.ssl else "redis"
        auth = f":{self.password}@" if self.password else ""
        return f"{scheme}://{auth}{self.host}:{self.port}/{self.db}"

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str | None) -> str | None:
        """Warn about missing password in production."""
        if os.getenv("ENVIRONMENT") == "production" and not v:
            # Log warning but don't fail (Redis might be internal)
            pass
        return v


class SecuritySettings(BaseSettings):
    """Security configuration settings."""

    model_config = SettingsConfigDict(
        env_file=os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".env"
        ),
        extra="ignore",
    )

    secret_key: str = Field(
        default="change-this-to-a-secure-random-string-in-production",
        description="Application secret key for JWT signing",
    )
    algorithm: str = Field(default="HS256", description="JWT algorithm")
    access_token_expire_minutes: int = Field(
        default=30, ge=1, le=1440, description="Access token expiry (minutes)"
    )
    refresh_token_expire_days: int = Field(
        default=7, ge=1, le=365, description="Refresh token expiry (days)"
    )

    # CORS settings
    enable_cors: bool = Field(default=True, description="Enable CORS")
    cors_origins: str = Field(
        default="http://localhost:3000,http://localhost:8080",
        description="Allowed CORS origins (comma-separated)",
    )
    cors_allow_credentials: bool = Field(
        default=True, description="Allow CORS credentials"
    )
    cors_allow_methods: str = Field(
        default="GET,POST,PUT,DELETE,OPTIONS",
        description="Allowed CORS methods",
    )
    cors_allow_headers: str = Field(
        default="Authorization,Content-Type,X-Requested-With,X-Correlation-ID",
        description="Allowed CORS headers",
    )

    # Rate limiting
    rate_limit_enabled: bool = Field(default=True, description="Enable rate limiting")
    rate_limit_default: str = Field(
        default="100/minute", description="Default rate limit"
    )
    rate_limit_strict: str = Field(default="10/minute", description="Strict rate limit")
    rate_limit_storage_url: str = Field(
        default="memory://",
        description="Rate limit storage backend (use redis://... for production)",
    )

    @field_validator("secret_key")
    @classmethod
    def validate_secret_key(cls, v: str) -> str:
        """Validate secret key strength."""
        if os.getenv("ENVIRONMENT") == "production":
            if v in (
                "change-this-to-a-secure-random-string-in-production",
                "secret",
                "changeit",
            ):
                raise ValueError(
                    "Default SECRET_KEY detected. "
                    "Generate a secure random key for production: "
                    "python -c 'import secrets; print(secrets.token_urlsafe(32))'"
                )
            if len(v) < 32:
                raise ValueError(
                    "SECRET_KEY must be at least 32 characters in production."
                )
        return v

    @property
    def cors_origins_list(self) -> list[str]:
        """Parse CORS origins into list."""
        return [origin.strip() for origin in self.cors_origins.split(",")]

    @property
    def cors_allow_methods_list(self) -> list[str]:
        """Parse CORS methods into list."""
        return [method.strip() for method in self.cors_allow_methods.split(",")]

    @property
    def cors_allow_headers_list(self) -> list[str]:
        """Parse CORS headers into list."""
        return [header.strip() for header in self.cors_allow_headers.split(",")]


class SearXNGSettings(BaseSettings):
    """SearXNG search engine settings."""

    model_config = SettingsConfigDict(
        env_prefix="SEARXNG_",
        env_file=os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".env"
        ),
        extra="ignore",
    )

    enabled: bool = Field(default=True, description="Enable SearXNG")
    base_url: str = Field(default="http://localhost:8080", description="SearXNG URL")
    secret_key: str = Field(
        default="generate-with-openssl-rand-hex-32",
        description="SearXNG secret key",
    )
    limiter: bool = Field(default=False, description="Enable SearXNG rate limiting")
    image_proxy: bool = Field(default=True, description="Enable SearXNG image proxy")
    categories: str = Field(
        default="general,images,videos,news,science",
        description="SearXNG search categories",
    )

    @field_validator("secret_key")
    @classmethod
    def validate_secret_key(cls, v: str) -> str:
        """Warn about default secret key."""
        if os.getenv("ENVIRONMENT") == "production":
            if v in ("generate-with-openssl-rand-hex-32", "ultrasecret"):
                raise ValueError(
                    "Default SEARXNG_SECRET_KEY detected. "
                    "Generate a secure random key: "
                    "openssl rand -hex 32"
                )
        return v


class MLSettings(BaseSettings):
    """Machine learning model settings."""

    model_config = SettingsConfigDict(
        env_prefix="",
        env_file=os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".env"
        ),
        extra="ignore",
    )

    model_cache_dir: str = Field(
        default="./model_cache", description="Model cache directory"
    )
    sentence_transformers_model: str = Field(
        default="all-MiniLM-L6-v2", description="Sentence transformers model"
    )
    device: Literal["cpu", "cuda", "mps"] = Field(
        default="cpu", description="ML device (cpu, cuda, mps)"
    )
    transformers_cache: str = Field(
        default="./transformers_cache", description="Transformers cache directory"
    )
    hugging_face_token: str | None = Field(
        default=None, description="Hugging Face API token"
    )


class PrivacySettings(BaseSettings):
    """Privacy and GDPR compliance settings."""

    model_config = SettingsConfigDict(
        env_prefix="",
        env_file=os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".env"
        ),
        extra="ignore",
    )

    # Data retention (hours)
    session_data_retention_hours: int = Field(
        default=8, ge=1, le=720, description="Session data retention (hours)"
    )
    analytics_data_retention_days: int = Field(
        default=90, ge=1, le=730, description="Analytics data retention (days)"
    )
    audit_log_retention_days: int = Field(
        default=365, ge=30, le=2555, description="Audit log retention (days)"
    )

    # Consent management
    consent_required: bool = Field(default=True, description="Require user consent")
    consent_expiry_days: int = Field(
        default=365, ge=1, le=730, description="Consent expiry (days)"
    )

    # Anonymization
    enable_anonymization: bool = Field(
        default=True, description="Enable data anonymization"
    )
    anonymization_salt: str = Field(
        default="generate-random-salt-for-anonymization",
        description="Salt for anonymization",
    )

    @field_validator("anonymization_salt")
    @classmethod
    def validate_salt(cls, v: str) -> str:
        """Validate anonymization salt."""
        if os.getenv("ENVIRONMENT") == "production":
            if v in ("generate-random-salt-for-anonymization", "salt"):
                raise ValueError(
                    "Default ANONYMIZATION_SALT detected. "
                    "Generate a random salt for production."
                )
        return v


class MonitoringSettings(BaseSettings):
    """Monitoring and observability settings."""

    model_config = SettingsConfigDict(
        env_prefix="",
        env_file=os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".env"
        ),
        extra="ignore",
    )

    # Prometheus
    enable_metrics: bool = Field(default=True, description="Enable Prometheus metrics")
    metrics_port: int = Field(default=9090, description="Metrics port")

    # Grafana
    grafana_url: str = Field(default="http://localhost:3000", description="Grafana URL")
    grafana_user: str = Field(default="admin", description="Grafana admin user")
    grafana_password: str = Field(
        default="change_this_grafana_password",
        description="Grafana admin password",
    )

    # Health checks
    health_check_interval: int = Field(
        default=30, ge=5, le=300, description="Health check interval (seconds)"
    )
    health_check_timeout: int = Field(
        default=10, ge=1, le=60, description="Health check timeout (seconds)"
    )

    # Distributed tracing
    tracing_enabled: bool = Field(
        default=False, description="Enable distributed tracing"
    )
    tracing_endpoint: str = Field(
        default="http://localhost:4317", description="Tracing endpoint"
    )
    tracing_service_name: str = Field(
        default="intent-engine", description="Tracing service name"
    )


class ApplicationSettings(BaseSettings):
    """Main application settings."""

    model_config = SettingsConfigDict(
        env_prefix="",
        env_file=os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".env"
        ),
        extra="ignore",
    )

    # Environment
    environment: Literal["development", "staging", "production"] = Field(
        default="development",
        description="Deployment environment",
    )
    app_name: str = Field(default="intent-engine", description="Application name")

    # API settings
    api_host: str = Field(default="0.0.0.0", description="API host")
    api_port: int = Field(default=8000, description="API port")
    workers: int | None = Field(default=None, description="Number of workers (auto)")

    # Logging
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO", description="Logging level"
    )
    log_format: Literal["json", "console"] = Field(
        default="console", description="Log format"
    )

    # Development
    reload: bool = Field(default=False, description="Enable hot reload (dev only)")
    debug: bool = Field(default=False, description="Enable debug mode")
    ssl_verify: bool = Field(default=True, description="Enable SSL verification")

    # Feature flags
    feature_new_ranking_algorithm: bool = Field(
        default=False, description="Enable new ranking algorithm"
    )
    feature_advanced_fraud_detection: bool = Field(
        default=True, description="Enable advanced fraud detection"
    )
    feature_ab_testing: bool = Field(default=True, description="Enable A/B testing")
    feature_real_time_analytics: bool = Field(
        default=True, description="Enable real-time analytics"
    )

    @model_validator(mode="after")
    def validate_environment_config(self) -> "ApplicationSettings":
        """Validate environment-specific configuration."""
        if self.environment == "production":
            if self.debug:
                raise ValueError("DEBUG mode must be disabled in production")
            if self.reload:
                raise ValueError("Hot reload must be disabled in production")
        return self


class Settings(BaseSettings):
    """
    Centralized settings class for Intent Engine.

    All configuration is accessed through this single class, which aggregates
    settings from environment variables and .env files.

    Usage:
        settings = Settings()

        # Access nested settings
        db_url = settings.database.effective_url
        secret_key = settings.security.secret_key

        # Validate for production
        settings.validate_production()
    """

    model_config = SettingsConfigDict(
        env_file=os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".env"
        ),
        env_nested_delimiter="_",
        extra="ignore",
    )

    # Nested settings objects
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    redis: RedisSettings = Field(default_factory=RedisSettings)
    security: SecuritySettings = Field(default_factory=SecuritySettings)
    searxng: SearXNGSettings = Field(default_factory=SearXNGSettings)
    ml: MLSettings = Field(default_factory=MLSettings)
    privacy: PrivacySettings = Field(default_factory=PrivacySettings)
    monitoring: MonitoringSettings = Field(default_factory=MonitoringSettings)
    app: ApplicationSettings = Field(default_factory=ApplicationSettings)

    def validate_production(self) -> list[str]:
        """
        Validate settings for production deployment.

        Returns:
            List of validation errors (empty if valid)
        """
        errors = []

        if self.app.environment != "production":
            return errors

        # Check critical security settings
        if "change" in self.security.secret_key.lower():
            errors.append("SECRET_KEY must be changed in production")

        if "change" in self.database.password.lower():
            errors.append("DATABASE password must be changed in production")

        # Check rate limiting storage
        if self.security.rate_limit_storage_url == "memory://":
            errors.append(
                "RATE_LIMIT_STORAGE_URL should use Redis in production "
                "(memory:// doesn't work across multiple workers)"
            )

        # Check Redis configuration
        if self.redis.enabled and self.app.environment == "production":
            if "localhost" in self.redis.host:
                errors.append(
                    "Redis host should not be localhost in production "
                    "(use a dedicated Redis instance)"
                )

        return errors

    def validate_startup(self) -> None:
        """
        Validate critical settings at application startup.

        Raises:
            ValueError: If critical validation fails
        """
        errors = []

        # Always validate secret key
        if self.security.secret_key in (
            "change-this-to-a-secure-random-string-in-production",
            "secret",
            "changeit",
        ):
            if self.app.environment == "production":
                errors.append(
                    "CRITICAL: SECRET_KEY must be set in production. "
                    "Generate with: python -c 'import secrets; print(secrets.token_urlsafe(32))'"
                )
            else:
                # Log warning for development
                import logging

                logging.getLogger("settings").warning(
                    "Using default SECRET_KEY in development. "
                    "This is fine for local development but must be changed for production."
                )

        # Validate database connection
        if "change_this_password" in self.database.password:
            if self.app.environment == "production":
                errors.append(
                    "CRITICAL: DATABASE_PASSWORD must be changed in production"
                )

        if errors:
            raise ValueError("\n".join(errors))

    def get_rate_limit_storage_url(self) -> str:
        """
        Get the appropriate rate limit storage URL.

        In production with Redis enabled, use Redis. Otherwise, use memory.
        """
        if (
            self.app.environment == "production"
            and self.redis.enabled
            and self.security.rate_limit_storage_url == "memory://"
        ):
            # Override with Redis URL
            return self.redis.effective_url
        return self.security.rate_limit_storage_url


@lru_cache
def get_settings() -> Settings:
    """
    Get cached settings instance.

    This ensures settings are loaded once and reused throughout the application.
    """
    return Settings()


# Global settings instance
settings = get_settings()

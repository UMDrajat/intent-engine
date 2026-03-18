"""
Centralized Configuration Management for Intent Engine.

This module provides a single source of truth for all configuration settings,
with validation, type safety, and environment variable management.

Usage:
    from app.config.settings import settings
    
    # Access settings
    db_url = settings.database_url
    secret_key = settings.secret_key

    # Validate at startup
    settings.validate_production()
"""

import secrets
import os
from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

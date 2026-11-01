"""Validated application configuration at the environment boundary."""

from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Load settings from explicit values, the environment and dotenv, in that order."""

    model_config = SettingsConfigDict(
        env_prefix="GATHERLY_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="forbid",
        strict=True,
        frozen=True,
        hide_input_in_errors=True,
        validate_by_name=True,
    )

    environment: Literal["development", "production"] = "production"
    gemini_api_key: SecretStr = Field(
        default=SecretStr(""),
        validation_alias="GEMINI_API_KEY",
        exclude=True,
        repr=False,
    )
    gemini_model: str = Field(
        default="gemini-3.5-flash-lite",
        validation_alias="GEMINI_MODEL",
        min_length=1,
        max_length=100,
        pattern=r"^gemini-[a-z0-9.-]+$",
    )
    ai_timeout_seconds: int = Field(default=6, ge=1, le=6)
    ai_concurrency: int = Field(default=4, ge=1, le=16)
    cache_capacity: int = Field(default=128, ge=1, le=1024)
    cache_ttl_seconds: int = Field(default=300, ge=1, le=3600)

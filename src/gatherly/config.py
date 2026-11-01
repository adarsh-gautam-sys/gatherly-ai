"""Validated application configuration at the environment boundary."""

from typing import Literal
from urllib.parse import urlsplit

from pydantic import Field, SecretStr, field_validator
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
    max_body_bytes: int = Field(default=262_144, ge=1024, le=1_048_576)
    request_timeout_seconds: int = Field(default=14, ge=1, le=14)
    requests_per_minute: int = Field(default=60, ge=1, le=600)
    rate_limit_capacity: int = Field(default=4096, ge=1, le=65_536)
    allowed_origins: tuple[str, ...] = ()
    port: int = Field(default=8080, validation_alias="PORT", ge=1024, le=65535)
    external_https: bool = False

    @field_validator("allowed_origins", mode="before")
    @classmethod
    def validate_origins(cls, value: object) -> tuple[str, ...]:
        """Allow explicit HTTP origins only, never wildcard or credentialed URLs."""
        if not isinstance(value, (list, tuple)) or len(value) > 10:
            raise ValueError("Provide at most ten explicit origins.")
        origins: list[str] = []
        for origin in value:
            if not isinstance(origin, str):
                raise ValueError("Origins must be strings.")
            parts = urlsplit(origin)
            if (
                parts.scheme not in {"http", "https"}
                or not parts.hostname
                or parts.username is not None
                or parts.password is not None
                or parts.path
                or parts.query
                or parts.fragment
                or "*" in origin
                or any(char.isspace() for char in origin)
            ):
                raise ValueError("Use an exact HTTP origin without a path.")
            origins.append(origin)
        return tuple(origins)

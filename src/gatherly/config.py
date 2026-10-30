"""Validated application configuration at the environment boundary."""

from typing import Literal

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
    )

    environment: Literal["development", "production"] = "production"

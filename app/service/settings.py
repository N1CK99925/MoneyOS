"""Centralised application settings — loaded from env / .env via Pydantic."""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Razorpay
    razorpay_key_id: str = Field(default="", description="Razorpay test-mode key ID")
    razorpay_key_secret: str = Field(default="", description="Razorpay test-mode key secret")
    razorpay_webhook_secret: str = Field(default="", description="Razorpay webhook secret")

    # Database
    database_url: str = Field(
        default="postgresql://postgres:postgres@localhost:5432/moneyos",
    )

    # Audit
    audit_hmac_secret: str = Field(
        default="moneyos-dev-secret-change-in-prod",
    )

    # LLM (for buyer agent)
    llm_model: str = Field(
        default="openai/gpt-4o-mini",
        description="Primary LLM model for buyer agent (litellm model string)",
    )
    llm_api_key: str = Field(
        default="",
        description="API key for the primary LLM provider",
    )
    llm_fallback_models: str = Field(
        default="groq/llama-3.3-70b-versatile,gemini/gemini-2.0-flash",
        description="Comma-separated fallback models if primary fails",
    )
    llm_max_iterations: int = Field(
        default=10,
        description="Max tool-calling iterations before the agent gives up",
    )
    service_url: str = Field(
        default="http://localhost:8000",
        description="Base URL of the merchant agent API",
    )

    # Tavily Search (for Phase 4B stretch agent)
    tavily_api_key: str = Field(
        default="",
        description="Tavily Search API key for web search (free tier: 1000 queries/mo)",
    )

    # Spend policy — bounded spend (Phase: gated payments).
    # Demo policy: single per-transaction cap, in paise. No rolling windows.
    spend_policy_max_per_transaction_paise: int = Field(
        default=60000,
        description="Max per-transaction spend (paise). 0 disables the policy check.",
    )

    # Approval flow — gated payments.
    approval_ttl_seconds: int = Field(
        default=300,
        description="Seconds a pending approval token stays valid before expiring.",
    )


settings = Settings()

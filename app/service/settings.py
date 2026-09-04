"""Centralised application settings — loaded from env / .env via Pydantic."""

import os

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
    # Extra API key slots. Each pair of (model, key) gets routed through litellm.
    # litellm picks a provider by the model's prefix and reads that provider's
    # env var, so slot these onto the env vars for the providers you actually use.
    llm_api_key_1: str = Field(default="", description="API key slot 1")
    llm_api_key_2: str = Field(default="", description="API key slot 2")
    llm_api_key_3: str = Field(default="", description="API key slot 3")
    llm_max_iterations: int = Field(
        default=10,
        description="Max tool-calling iterations before the agent gives up",
    )
    service_url: str = Field(
        default="http://localhost:8000",
        description="Base URL of the merchant agent API",
    )

    # Telegram Bot — mobile delivery of payment links and approval cards.
    telegram_bot_token: str = Field(
        default="",
        description="Telegram bot token from @BotFather",
    )
    telegram_merchant_chat_id: str = Field(
        default="",
        description="Merchant Telegram chat ID for approval card delivery",
    )
    telegram_customer_chat_id: str = Field(
        default="",
        description="Customer Telegram chat ID for payment link delivery (blank = same as merchant)",
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


def _set_key(env_var: str, key: str) -> None:
    """Set a provider env var for litellm, without overwriting an earlier value."""
    if key:
        os.environ.setdefault(env_var, key)


# Expose API keys to litellm (which reads provider-specific env vars chosen by
# the model's prefix). Each key slot maps onto the providers you might use. A
# slot's key intentionally does NOT cascade to other providers, so each fallback
# uses its own real key/quota. Slots fall back to the shared ``llm_api_key``.
if settings.llm_api_key:
    os.environ.setdefault("GROQ_API_KEY", settings.llm_api_key)
    os.environ.setdefault("OPENAI_API_KEY", settings.llm_api_key)
    os.environ.setdefault("OPENROUTER_API_KEY", settings.llm_api_key)
    os.environ.setdefault("GEMINI_API_KEY", settings.llm_api_key)

# Key slot 1 -> Groq
_set_key("GROQ_API_KEY", settings.llm_api_key_1)
# Key slot 2 -> OpenRouter (routes to many models; point fallbacks here)
_set_key("OPENROUTER_API_KEY", settings.llm_api_key_2)
# Key slot 3 -> OpenAI / Gemini
_set_key("OPENAI_API_KEY", settings.llm_api_key_3)
_set_key("GEMINI_API_KEY", settings.llm_api_key_3)

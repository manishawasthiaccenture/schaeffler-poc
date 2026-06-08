"""Test configuration.

Force the deterministic MockLLMClient for the whole test session so tests never
hit the Anthropic API (no network, no token spend, fast). This must run before
app.main is imported, since that module loads .env and the orchestrator reads the
key at build time. Set ANTHROPIC_API_KEY in a real shell to run live integration
checks manually instead.
"""
import os

os.environ["ANTHROPIC_API_KEY"] = ""

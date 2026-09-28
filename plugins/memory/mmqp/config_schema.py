"""Declarative desktop configuration for MMQP Cathedral Memory."""

from plugins.memory.config_schema import (
    KIND_NUMBER,
    KIND_TEXT,
    ProviderConfigSchema,
    ProviderField,
)

CONFIG_SCHEMA = ProviderConfigSchema(
    name="mmqp",
    label="MMQP Cathedral Memory",
    fields=(
        ProviderField(
            key="db_path",
            label="Database path",
            kind=KIND_TEXT,
            default="$HERMES_HOME/mmqp.db",
            description="Profile-scoped SQLite database used by the MMQP Chronicle.",
            inline=True,
        ),
        ProviderField(
            key="prefetch_limit",
            label="Recall limit",
            kind=KIND_NUMBER,
            default="6",
            description="Maximum MMQP memories injected during pre-turn recall.",
            inline=True,
        ),
    ),
)

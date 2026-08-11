"""Tests for the config and options flows."""
from __future__ import annotations

from homeassistant import config_entries, data_entry_flow
from homeassistant.core import HomeAssistant

from custom_components.notify_mqtt.const import CONF_NAME, CONF_TOPIC, DOMAIN
from pytest_homeassistant_custom_component.common import MockConfigEntry


async def test_user_flow_creates_entry_named_after_topic(hass: HomeAssistant) -> None:
    """A valid topic with no friendly name creates an entry titled after the topic."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is data_entry_flow.FlowResultType.FORM

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_TOPIC: "home/notifications/alerts", CONF_NAME: ""}
    )

    assert result["type"] is data_entry_flow.FlowResultType.CREATE_ENTRY
    assert result["title"] == "home/notifications/alerts"
    assert result["data"] == {CONF_TOPIC: "home/notifications/alerts", CONF_NAME: ""}


async def test_user_flow_creates_entry_named_after_friendly_name(hass: HomeAssistant) -> None:
    """A friendly name, when given, becomes the entry title."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_TOPIC: "home/notifications/alerts", CONF_NAME: "Garage Alerts"},
    )

    assert result["type"] is data_entry_flow.FlowResultType.CREATE_ENTRY
    assert result["title"] == "Garage Alerts"


async def test_user_flow_rejects_wildcard_topic(hass: HomeAssistant) -> None:
    """Topics containing MQTT wildcards are rejected with invalid_topic."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_TOPIC: "home/notifications/#", CONF_NAME: ""}
    )

    assert result["type"] is data_entry_flow.FlowResultType.FORM
    assert result["errors"] == {CONF_TOPIC: "invalid_topic"}


async def test_user_flow_aborts_on_duplicate_topic(hass: HomeAssistant) -> None:
    """A second entry for the same topic aborts as already_configured."""
    existing = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_TOPIC: "home/notifications/alerts"},
        unique_id="home/notifications/alerts",
    )
    existing.add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_TOPIC: "home/notifications/alerts", CONF_NAME: ""}
    )

    assert result["type"] is data_entry_flow.FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_options_flow_updates_name(hass: HomeAssistant) -> None:
    """Changing only the friendly name via options keeps the same topic/unique_id."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_TOPIC: "home/notifications/alerts"},
        unique_id="home/notifications/alerts",
    )
    entry.add_to_hass(hass)

    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {CONF_TOPIC: "home/notifications/alerts", CONF_NAME: "Garage Alerts"},
    )

    assert result["type"] is data_entry_flow.FlowResultType.CREATE_ENTRY
    assert result["data"] == {
        CONF_TOPIC: "home/notifications/alerts",
        CONF_NAME: "Garage Alerts",
    }
    assert entry.unique_id == "home/notifications/alerts"


async def test_options_flow_updates_unique_id_on_topic_change(hass: HomeAssistant) -> None:
    """Changing the topic via options keeps the entry's unique_id in sync."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_TOPIC: "home/notifications/alerts"},
        unique_id="home/notifications/alerts",
    )
    entry.add_to_hass(hass)

    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {CONF_TOPIC: "home/notifications/other", CONF_NAME: ""},
    )

    assert result["type"] is data_entry_flow.FlowResultType.CREATE_ENTRY
    assert entry.unique_id == "home/notifications/other"


async def test_options_flow_rejects_duplicate_topic_across_entries(hass: HomeAssistant) -> None:
    """Options flow rejects a topic already used by a different entry."""
    other = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_TOPIC: "home/notifications/other"},
        unique_id="home/notifications/other",
    )
    other.add_to_hass(hass)

    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_TOPIC: "home/notifications/alerts"},
        unique_id="home/notifications/alerts",
    )
    entry.add_to_hass(hass)

    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {CONF_TOPIC: "home/notifications/other", CONF_NAME: ""},
    )

    assert result["type"] is data_entry_flow.FlowResultType.FORM
    assert result["errors"] == {CONF_TOPIC: "already_configured"}

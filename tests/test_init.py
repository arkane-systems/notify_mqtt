"""Tests for the notify_mqtt.publish service lifecycle across config entries."""
from __future__ import annotations

import json
from unittest.mock import AsyncMock, patch

import pytest

from custom_components.notify_mqtt.const import CONF_TOPIC, DOMAIN
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ServiceValidationError
from pytest_homeassistant_custom_component.common import MockConfigEntry

SERVICE_PUBLISH = "publish"


async def _setup_entry(hass: HomeAssistant, topic: str) -> MockConfigEntry:
    entry = MockConfigEntry(domain=DOMAIN, data={CONF_TOPIC: topic}, unique_id=topic)
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


async def test_service_registered_on_first_setup(hass: HomeAssistant) -> None:
    """The notify_mqtt.publish service is registered once the first entry is set up."""
    assert not hass.services.has_service(DOMAIN, SERVICE_PUBLISH)
    await _setup_entry(hass, "home/notifications/alerts")
    assert hass.services.has_service(DOMAIN, SERVICE_PUBLISH)


async def test_service_removed_only_after_last_entry_unloaded(hass: HomeAssistant) -> None:
    """The service stays registered while any entry remains, and is removed after the last."""
    entry_a = await _setup_entry(hass, "home/notifications/a")
    entry_b = await _setup_entry(hass, "home/notifications/b")

    assert await hass.config_entries.async_unload(entry_a.entry_id)
    await hass.async_block_till_done()
    assert hass.services.has_service(DOMAIN, SERVICE_PUBLISH)

    assert await hass.config_entries.async_unload(entry_b.entry_id)
    await hass.async_block_till_done()
    assert not hass.services.has_service(DOMAIN, SERVICE_PUBLISH)


async def test_publish_service_resolves_entity_across_multiple_entries(
    hass: HomeAssistant,
) -> None:
    """The service publishes to the topic of the entity matching the given entity_id."""
    await _setup_entry(hass, "home/notifications/a")
    entry_b = await _setup_entry(hass, "home/notifications/b")

    entity_b_id = hass.data[DOMAIN][entry_b.entry_id].entity_id

    with patch(
        "custom_components.notify_mqtt.mqtt.async_publish", new=AsyncMock()
    ) as mock_publish:
        await hass.services.async_call(
            DOMAIN,
            SERVICE_PUBLISH,
            {
                "entity_id": entity_b_id,
                "message": "hi",
                "title": "Hey",
                "data": {"severity": "high"},
            },
            blocking=True,
        )

    mock_publish.assert_awaited_once()
    call_hass, call_topic, call_payload = mock_publish.await_args.args
    assert call_topic == "home/notifications/b"
    assert json.loads(call_payload) == {
        "message": "hi",
        "title": "Hey",
        "severity": "high",
    }


async def test_publish_service_raises_for_unknown_entity(hass: HomeAssistant) -> None:
    """Publishing to an entity_id with no matching notify_mqtt entity raises."""
    await _setup_entry(hass, "home/notifications/alerts")

    with pytest.raises(ServiceValidationError):
        await hass.services.async_call(
            DOMAIN,
            SERVICE_PUBLISH,
            {"entity_id": "notify.does_not_exist", "message": "hi"},
            blocking=True,
        )

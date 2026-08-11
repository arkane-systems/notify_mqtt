"""Tests for the notify.py platform: _build_payload and both entity/service paths."""
from __future__ import annotations

import json
from unittest.mock import AsyncMock, patch

import pytest

from custom_components.notify_mqtt.const import CONF_NAME, CONF_TOPIC, DOMAIN
from custom_components.notify_mqtt.notify import MqttNotificationService, _build_payload
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry


def test_build_payload_message_only() -> None:
    """A bare message serializes to just the message key."""
    assert json.loads(_build_payload("hello")) == {"message": "hello"}


def test_build_payload_with_title() -> None:
    """Title is included when provided."""
    payload = json.loads(_build_payload("hello", title="Alert"))
    assert payload == {"message": "hello", "title": "Alert"}


def test_build_payload_omits_none_title() -> None:
    """A None title is not included in the payload."""
    payload = json.loads(_build_payload("hello", title=None))
    assert "title" not in payload


def test_build_payload_with_target() -> None:
    """Target is included only on the legacy (YAML) path."""
    payload = json.loads(_build_payload("hello", target="kitchen"))
    assert payload == {"message": "hello", "target": "kitchen"}


def test_build_payload_data_merges_top_level() -> None:
    """Keys in `data` are merged at the top level of the payload."""
    payload = json.loads(
        _build_payload("hello", title="Alert", data={"severity": "high", "room": "kitchen"})
    )
    assert payload == {
        "message": "hello",
        "title": "Alert",
        "severity": "high",
        "room": "kitchen",
    }


def test_build_payload_empty_data_is_ignored() -> None:
    """An empty data dict adds no extra keys."""
    payload = json.loads(_build_payload("hello", data={}))
    assert payload == {"message": "hello"}


async def test_legacy_service_publishes_full_payload(hass: HomeAssistant) -> None:
    """MqttNotificationService.async_send_message publishes message/title/target/data."""
    service = MqttNotificationService(hass, "home/notifications/alerts")

    with patch(
        "custom_components.notify_mqtt.notify.mqtt.async_publish", new=AsyncMock()
    ) as mock_publish:
        await service.async_send_message(
            "The garage door is open.",
            title="Garage Alert",
            target="kitchen",
            data={"severity": "high"},
        )

    mock_publish.assert_awaited_once()
    call_hass, call_topic, call_payload = mock_publish.await_args.args
    assert call_hass is hass
    assert call_topic == "home/notifications/alerts"
    assert json.loads(call_payload) == {
        "message": "The garage door is open.",
        "title": "Garage Alert",
        "target": "kitchen",
        "severity": "high",
    }


async def test_entity_publishes_and_uses_topic_as_default_name(hass: HomeAssistant) -> None:
    """MqttNotifyEntity publishes message/title and falls back to topic as its name."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_TOPIC: "home/notifications/alerts"},
        unique_id="home/notifications/alerts",
    )
    entry.add_to_hass(hass)

    with patch(
        "custom_components.notify_mqtt.notify.mqtt.async_publish", new=AsyncMock()
    ) as mock_publish:
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

        entity_id = hass.data[DOMAIN][entry.entry_id].entity_id
        state = hass.states.get(entity_id)
        assert state is not None
        assert state.name == "home/notifications/alerts"

        await hass.services.async_call(
            "notify",
            "send_message",
            {"entity_id": entity_id, "message": "hi", "title": "Hey"},
            blocking=True,
        )

    mock_publish.assert_awaited_once()
    call_hass, call_topic, call_payload = mock_publish.await_args.args
    assert call_topic == "home/notifications/alerts"
    assert json.loads(call_payload) == {"message": "hi", "title": "Hey"}


async def test_entity_uses_friendly_name_when_set(hass: HomeAssistant) -> None:
    """MqttNotifyEntity uses the configured friendly name over the topic."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_TOPIC: "home/notifications/alerts", CONF_NAME: "Garage Alerts"},
        unique_id="home/notifications/alerts",
    )
    entry.add_to_hass(hass)

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    entity = hass.data[DOMAIN][entry.entry_id]
    assert entity.name == "Garage Alerts"
    assert entry.state is ConfigEntryState.LOADED

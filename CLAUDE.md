# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project overview

`notify_mqtt` is a Home Assistant custom component (distributed via HACS) that bridges HA's notification system to MQTT. When a notification is sent, it serializes the payload to JSON and publishes it to a configured MQTT topic, for consumption by Node-RED or any other MQTT-aware system. Minimum supported Home Assistant version: 2023.4.0 (see `hacs.json`).

There is no build system, test suite, or linter configured in this repo. The only CI is the `hassfest` GitHub Action (`.github/workflows/hassfest.yml`), which validates the integration's manifest/structure against Home Assistant's core requirements on every push/PR. There is no local equivalent command to run — validation happens in CI.

## Architecture

Two parallel setup paths coexist in the same codebase — always consider both when changing shared code:

```
── UI / Config Flow path ──────────────────────────────────────────────
ConfigFlow (config_flow.py)
    → stores topic in ConfigEntry
    → async_setup_entry (__init__.py)
        → forwards to notify platform → MqttNotifyEntity (notify.py)
            → notify.send_message  (message + title only)
        → registers notify_mqtt.publish service (__init__.py)
            → _build_payload(message, title, data) → mqtt.async_publish

── YAML / Legacy path ─────────────────────────────────────────────────
configuration.yaml: notify: platform: notify_mqtt
    → get_service (notify.py)
        → MqttNotificationService (notify.py)
            → notify.NAME  (message + title + target + data dict)
                → _build_payload → mqtt.async_publish
```

`_build_payload()` in `notify.py` is the single shared JSON-serialization helper used by both paths — keep it that way rather than duplicating serialization logic.

### Config-entry path (new)
- `MqttNotifyEntity` inherits from `NotifyEntity`; implements `async_send_message(message, title=None)`.
- `_attr_supported_features = NotifyEntityFeature.TITLE` signals title support to HA.
- The entity instance is stored in `hass.data[DOMAIN]` keyed by `entry.entry_id` so the custom service handler in `__init__.py` can retrieve it by `entity_id`.
- MQTT is published via `await mqtt.async_publish(hass, topic, payload)`.
- Only supports `message`/`title` through the standard `notify.send_message` service. Arbitrary extra data requires the `notify_mqtt.publish` custom service, since HA's standard notify service doesn't expose a `data` dict to entity-based notifiers.

### YAML-legacy path (kept for backward compatibility)
- `MqttNotificationService` inherits from `BaseNotificationService`; implements `async_send_message(message, **kwargs)`.
- `PLATFORM_SCHEMA` extends HA's base with `vol.Required(CONF_TOPIC): valid_publish_topic`.
- `get_service(hass, config, discovery_info=None)` is the factory HA calls.
- Supports the full payload: `message`, `title`, `target`, and an arbitrary `data` dict (merged top-level into the JSON payload) — this is legacy behavior kept for compatibility and must not change.

### Custom service + multi-entry
- `notify_mqtt.publish` is registered on the **first** `async_setup_entry` call and removed only when the **last** entry is unloaded (i.e. `hass.data[DOMAIN]` becomes empty).
- All active entities are stored in `hass.data[DOMAIN]` keyed by `entry.entry_id`; the service handler resolves the target by matching `entity.entity_id` across all entries. This is what lets multiple topics (multiple config entries) share one service registration.

### Config flow
- `unique_id` = the MQTT topic string, which prevents duplicate entries for the same topic.
- Error key `"invalid_topic"` maps to the string in `strings.json`.
- `NotifyMqttOptionsFlow` handles editing an existing entry (topic + name); registered via `async_get_options_flow`. On save it checks for duplicate topics across *other* entries, then calls `async_update_entry(unique_id=...)` if the topic changed, then triggers `_async_options_updated` → `async_reload` so the entity immediately reflects new values.
- The entity reads effective config as `{**entry.data, **entry.options}` so options always override the original entry data.

## Key files

| File | Purpose |
|---|---|
| `custom_components/notify_mqtt/notify.py` | Both platforms: `MqttNotifyEntity` (config entry), `MqttNotificationService` (YAML legacy), `_build_payload` helper |
| `custom_components/notify_mqtt/__init__.py` | `async_setup_entry` / `async_unload_entry`; registers `notify_mqtt.publish` custom service |
| `custom_components/notify_mqtt/config_flow.py` | Config + options flow: prompts for MQTT topic/name, validates with `valid_publish_topic`, dedupes by topic |
| `custom_components/notify_mqtt/const.py` | `DOMAIN`, `CONF_TOPIC`, `CONF_NAME` constants |
| `custom_components/notify_mqtt/manifest.json` | Integration metadata: `config_flow: true`, `iot_class: local_push`, `integration_type: service` |
| `custom_components/notify_mqtt/services.yaml` | Defines the `notify_mqtt.publish` custom service schema (must stay in sync with `SERVICE_PUBLISH_SCHEMA` in `__init__.py`) |
| `custom_components/notify_mqtt/strings.json` | Config/options flow UI strings — source of truth |
| `custom_components/notify_mqtt/translations/en.json` | English translations — must mirror `strings.json` |

## JSON payload format

Both paths produce the same shape:
```json
{
  "message": "...",
  "title": "...",        // if provided
  "target": "...",       // YAML path only
  "key": "value"         // data dict keys, merged top-level (either path)
}
```

## Things to keep in sync when changing config flow strings or schema

`strings.json` and `translations/en.json` must be kept in sync manually — HA has no build step that generates one from the other in this repo. Likewise, `services.yaml`'s `publish` field definitions must match `SERVICE_PUBLISH_SCHEMA` in `__init__.py`.

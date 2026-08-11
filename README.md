# ![icon](assets/notify_mqtt-32px.png) MQTT notification service for Home Assistant.

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg?style=for-the-badge)](https://github.com/custom-components/hacs)

The `notify_mqtt` integration publishes Home Assistant notifications to an MQTT topic as a JSON payload. It is primarily intended for use with [Node-RED](https://nodered.org/) or any other MQTT-aware system that consumes notification events.

---

## Installation

Install via [HACS](https://hacs.xyz/) as a custom repository, or copy the `custom_components/notify_mqtt` directory into your Home Assistant `custom_components` folder.

---

## Setup (UI — recommended)

1. Go to **Settings → Devices & Services → Add Integration** and search for **Notify MQTT**.
2. Enter the MQTT topic to publish to (e.g. `home/notifications/alerts`) and an optional friendly name.
3. Repeat to add as many topics as you need.

Each configured topic becomes a `notify` entity. The entity's name (and therefore its service name, e.g. `notify.garage_alerts`) comes from the friendly name you set; if none is set, the topic string is used.

To change the topic or rename an entry after setup, go to **Settings → Devices & Services**, find the entry, and click **Configure**.

```yaml
service: notify.send_message
target:
  entity_id: notify.home_notifications_alerts
data:
  message: The garage door has been open for 10 minutes.
  title: Garage Alert
```

The published MQTT payload will be:

```json
{"message": "The garage door has been open for 10 minutes.", "title": "Garage Alert"}
```

### Sending extra data (UI-configured instances)

The standard `notify.send_message` service only supports `message` and `title`. If you need to merge additional keys into the JSON payload (e.g. routing hints, severity, icons), use the `notify_mqtt.publish` service instead:

```yaml
service: notify_mqtt.publish
data:
  entity_id: notify.home_notifications_alerts
  message: The garage door has been open for 10 minutes.
  title: Garage Alert
  data:
    severity: high
    room: kitchen
    icon: mdi:garage
```

The published MQTT payload will be:

```json
{
  "message": "The garage door has been open for 10 minutes.",
  "title": "Garage Alert",
  "severity": "high",
  "room": "kitchen",
  "icon": "mdi:garage"
}
```

---

## Setup (YAML — legacy, kept for backward compatibility)

Add the following to your `configuration.yaml`:

```yaml
notify:
  - name: NOTIFIER_NAME
    platform: notify_mqtt
    topic: home/notifications/alerts
```

**`name`** (optional, default: `notify`): Creates the service `notify.NOTIFIER_NAME`.

**`topic`** (required): The MQTT topic to publish to.

YAML-configured instances support the full `data:` dict (top-level merge) and `target:` field via the standard `notify.NOTIFIER_NAME` service, exactly as before:

```yaml
service: notify.NOTIFIER_NAME
data:
  message: The garage door has been open for 10 minutes.
  title: Garage Alert
  data:
    severity: high
    room: kitchen
```

---

## Breaking changes in v1.0.0

This release introduces UI-based configuration and migrates the integration to the current Home Assistant standards. **Existing YAML configurations continue to work without any changes.**

### What changed

| | Before (v0.x) | After (v1.0.0) |
|---|---|---|
| **Setup** | YAML `notify:` block only | UI (recommended) or YAML |
| **YAML config** | Supported | Still supported (unchanged) |
| **`data:` dict (top-level merge)** | Supported via `notify.NAME` | YAML: unchanged · UI: use `notify_mqtt.publish` |
| **`target:` field** | Echoed into payload | YAML: unchanged · UI: not available |
| **MQTT publish API** | `hass.components.mqtt.publish` (deprecated) | `mqtt.async_publish` (current) |

### Migrating from YAML to UI setup

If you want to switch an existing YAML-configured notifier to UI setup:

1. Add it via **Settings → Devices & Services → Add Integration → Notify MQTT**.
2. In your automations, replace:
   ```yaml
   service: notify.MY_NOTIFIER_NAME
   data:
     message: Hello
     data:
       severity: high
   ```
   with:
   ```yaml
   service: notify_mqtt.publish
   data:
     entity_id: notify.home_notifications_alerts   # entity name = your topic
     message: Hello
     data:
       severity: high
   ```
3. Remove the old `notify:` block from `configuration.yaml` and restart.

You do **not** have to migrate — YAML configuration will continue to work.


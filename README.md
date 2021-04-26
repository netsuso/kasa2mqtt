# kasa2mqtt

This is an adapter for TP-Link Kasa devices to work with MQTT. It's based on the
[python-kasa](https://github.com/python-kasa/python-kasa) library and
[paho-mqtt](https://www.eclipse.org/paho/).

## Supported devices

Currently it only supports plug devices, but adding other types should be fairly easy.

## Config

kasa2mqtt will try to read `config.yaml`, unless another file name is provided as the argument.

This is an example of the config file:

```yaml
mqtt:
  host: 10.0.0.1
  port: 1883

devices:
- name: device1
  type: plug
  address: 10.0.0.101
- name: device2
  type: plug
  address: 10.0.0.102
```

## Running

The easiest way to run kasa2mqtt is using a Python virtualenv:

- `python -m venv venv/`
- `venv/bin/pip install -r requirements.txt`
- Create a `config.yaml` for your network
- `venv/bin/python kasa2mqtt.py`

## MQTT

kasa2mqtt will publish to MQTT topics like `kasa/<device_name>/#`:

- kasa/device1/status: Either `on` or `off`
- kasa/device1/voltage: Millivolts (plugs with emeter only)
- kasa/device1/power: Milliwatts (plugs with emeter only)

It will also receive `on` or `off` commands on the topic `kasa/<device_name>`:

- kasa/device1: Command topic, just use `on` or `off` as the payload.

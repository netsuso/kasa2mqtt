#!/usr/bin/env python

import os
import sys
import time
import asyncio
import yaml
import janus
import paho.mqtt.client as mqtt
import kasa

def on_mqtt_connect(client, data, flags, rc):
    client.subscribe('kasa/+')

def on_mqtt_message(client, userdata, message):
    device_name = message.topic.split('/')[1]
    userdata[device_name].sync_q.put(message.payload.decode())

def init_mqtt(config):
    mqtt_client = mqtt.Client()
    mqtt_client.on_message = on_mqtt_message
    mqtt_client.on_connect = on_mqtt_connect
    if 'port' in config:
        port = config['port']
    else:
        port = 1883
    mqtt_client.connect(config['host'], port)
    return mqtt_client

def receive_message(queue):
    message = queue.get()
    return message

# This is the main task, managed by asyncio for every device. It will try to receive
# a command message from the queue. While no commands are received, a device status
# update is sent every 15 seconds
async def device_monitor(mqtt_client, name, device, msgq):
    while True:
        await device.update()
        topic = 'kasa/' + name + '/status'
        if device.is_on:
            payload = 'on'
        else:
            payload = 'off'
        mqtt_client.publish(topic, payload)

        if device.has_emeter:
            topic = 'kasa/' + name + '/voltage'
            mqtt_client.publish(topic, device.emeter_realtime['voltage_mv'])
            topic = 'kasa/' + name + '/power'
            mqtt_client.publish(topic, device.emeter_realtime['power_mw'])

        receiver = asyncio.create_task(receive_message(msgq.async_q))
        try:
            message = await asyncio.wait_for(receiver, timeout=15)
        except asyncio.TimeoutError:
            continue

        print("Command received for device {0}: {1}".format(name, message))

        if message == 'on':
            await device.turn_on()
        elif message == 'off':
            await device.turn_off()
        elif message == 'toggle':
            await device.update()
            if device.is_on:
                await device.turn_off()
            else:
                await device.turn_on()

def build_devices(config):
    devices = {}
    for device_config in config:
        device_name = device_config['name']
        address = device_config['address']
        if device_config['type'] == 'plug':
            devices[device_name] = kasa.SmartPlug(address)
        else:
            print('WARNING: Device type {0} not supported yet'.format(device_config['type']))
    return devices

def read_config():
    if len(sys.argv) > 1:
        config_file = sys.argv[1]
    else:
        config_file = 'config.yaml'

    if not os.path.exists(config_file):
        raise Exception('Cannot find config file {0}'.format(config_file))

    print('Reading config file {0}'.format(config_file))

    config_yaml = open(config_file, 'r')
    config = yaml.load(config_yaml, Loader=yaml.Loader)
    config_yaml.close()

    return config

async def main():
    config = read_config()
    devices = build_devices(config['devices'])

    # Create a queue for every device, so they can interact independently. This queue
    # will be used to send arriving MQTT commands to the device_monitor task.
    # Janus queues are used so they work both with threads (paho) and asyncio (python-kasa)
    device_queues = {}
    for name, device in devices.items():
        device_queues[name] = janus.Queue()

    mqtt_client = init_mqtt(config['mqtt'])
    mqtt_client.user_data_set(device_queues)
    mqtt_client.loop_start()

    tasks = []
    for name, device in devices.items():
        task = asyncio.create_task(device_monitor(mqtt_client, name, device, device_queues[name]))
        tasks.append(task)

    await asyncio.wait(tasks)

asyncio.run(main())

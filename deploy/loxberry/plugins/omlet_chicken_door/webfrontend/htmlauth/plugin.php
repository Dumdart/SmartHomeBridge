<?php
$pluginFolder = 'omletchickendoor';
$pluginTitle = 'OmletChickenDoorPlugin';
$pluginDisplayName = 'Omlet Chicken Door';
$pluginDescription = 'Door service status, safe manual controls, Omlet connection settings, and authenticated door-state webhooks.';
$fixedSettings = array('BRIDGE_DEVICES_ENABLED' => 'chicken_door');
$allowedDoorCommands = array('open_door', 'close_door', 'stop_door', 'get_door_state');
$statusCards = array(
    array('label' => 'Omlet credentials', 'setting' => 'DOOR_API_KEY', 'kind' => 'configured', 'tone' => 'good'),
    array('label' => 'Last known door state', 'value' => 'Awaiting telemetry'),
);
$diagnosticActions = array('test-door' => 'Test API & device', 'test-webhook' => 'Test webhook listener');
$webhookGuidance = 'Public URL: https://hooks.example.com/webhooks/omlet/door-state. Forward only this path through a trusted HTTPS reverse proxy or managed tunnel to the private listener below.';
$fieldSchema = array(
    'DOOR_API_KEY' => array('label' => 'Omlet API key', 'help' => 'API key for the Omlet account. Leave blank to keep the saved key.', 'type' => 'password', 'group' => 'Basic setup', 'sensitive' => true, 'required' => true),
    'DOOR_DEVICE_ID' => array('label' => 'Door device ID', 'help' => 'Unique device identifier shown in your Omlet account.', 'type' => 'text', 'group' => 'Basic setup', 'required' => true, 'placeholder' => 'Enter the Omlet device ID'),
    'OMLET_WEBHOOK_ENABLED' => array('label' => 'Door-state webhook', 'help' => 'Start the private webhook listener. A public HTTPS reverse proxy or tunnel is still required.', 'type' => 'toggle', 'group' => 'Webhook'),
    'OMLET_WEBHOOK_TOKEN' => array('label' => 'Webhook token', 'help' => 'A unique random token of at least 32 characters. Leave blank to keep the saved token.', 'type' => 'password', 'group' => 'Webhook', 'sensitive' => true, 'required_when' => array('OMLET_WEBHOOK_ENABLED' => 'true'), 'minlength' => 32),
    'HTTP_HOST' => array('label' => 'Listener address', 'help' => 'Private bind address for the bridge listener. Use 0.0.0.0 when a proxy or tunnel connects from another host.', 'type' => 'host', 'group' => 'Webhook', 'required' => true),
    'HTTP_PORT' => array('label' => 'Listener port', 'help' => 'Private HTTP port forwarded by the HTTPS proxy or tunnel.', 'type' => 'number', 'group' => 'Webhook', 'required' => true, 'min' => 1, 'max' => 65535),
    'MQTT_BASE_TOPIC' => array('label' => 'MQTT base topic', 'help' => 'Shared prefix for all bridge messages. Wildcards are not allowed.', 'type' => 'topic', 'group' => 'MQTT', 'required' => true),
    'CHICKEN_DOOR_COMMAND_TOPIC' => array('label' => 'Command topic', 'help' => 'Topic used to receive door commands.', 'type' => 'topic', 'group' => 'MQTT', 'required' => true),
    'CHICKEN_DOOR_STATUS_TOPIC' => array('label' => 'Door state topic', 'help' => 'Human-readable door state topic.', 'type' => 'topic', 'group' => 'MQTT', 'required' => true),
    'CHICKEN_DOOR_STATUS_CODE_TOPIC' => array('label' => 'Door state code topic', 'help' => 'Numeric door state topic used by automations.', 'type' => 'topic', 'group' => 'MQTT', 'required' => true),
    'CHICKEN_DOOR_FAULT_TOPIC' => array('label' => 'Fault topic', 'help' => 'Topic publishing active door faults.', 'type' => 'topic', 'group' => 'Advanced', 'required' => true),
    'CHICKEN_DOOR_CONNECTED_TOPIC' => array('label' => 'Connection topic', 'help' => 'Topic publishing whether the device is connected.', 'type' => 'topic', 'group' => 'Advanced', 'required' => true),
    'CHICKEN_DOOR_BATTERY_TOPIC' => array('label' => 'Battery topic', 'help' => 'Topic publishing the latest battery level.', 'type' => 'topic', 'group' => 'Advanced', 'required' => true),
    'CHICKEN_DOOR_LIGHT_LEVEL_TOPIC' => array('label' => 'Light level topic', 'help' => 'Topic publishing the door light sensor value.', 'type' => 'topic', 'group' => 'Advanced', 'required' => true),
    'LOG_LEVEL' => array('label' => 'Log level', 'help' => 'INFO is recommended. Use DEBUG only while troubleshooting.', 'type' => 'select', 'group' => 'Logging', 'options' => array('ERROR' => 'Errors only', 'WARNING' => 'Warnings and errors', 'INFO' => 'Information', 'DEBUG' => 'Debug')),
    'LOG_FILE_PATH' => array('label' => 'Log file path', 'help' => 'Path relative to the plugin runtime unless an absolute path is supplied.', 'type' => 'text', 'group' => 'Logging', 'required' => true),
);
$editableSettings = array_keys($fieldSchema);

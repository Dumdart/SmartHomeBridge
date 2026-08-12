<?php
$pluginFolder = 'omletchickendoor';
$pluginTitle = 'OmletChickenDoorPlugin';
$pluginDisplayName = 'Omlet Chicken Door';
$pluginDescription = 'Door service status, safe manual controls, and Omlet connection settings.';
$serviceStatusLabel = 'Plugin status';
$serviceActionNoun = 'plugin';
$showStatusDiagnosticDetails = false;
$showDoorSafetyReminder = false;
$fixedSettings = array('BRIDGE_DEVICES_ENABLED' => 'chicken_door');
$allowedDoorCommands = array('open_door', 'close_door', 'stop_door', 'get_door_state');
$statusCards = array(
    array('label' => 'Door polling', 'setting' => 'DOOR_POLL_INTERVAL_SECONDS', 'kind' => 'poll-interval', 'tone' => 'good'),
    array('label' => 'Latest polled state', 'kind' => 'door-poll-status', 'id' => 'door-poll-status'),
);
$diagnosticActions = array('test-door' => 'Test API & device');
$fieldSchema = array(
    'DOOR_API_KEY' => array('label' => 'Omlet API key', 'help' => 'API key for the Omlet account. Leave blank to keep the saved key.', 'type' => 'password', 'group' => 'Basic setup', 'sensitive' => true, 'required' => true),
    'DOOR_DEVICE_ID' => array('label' => 'Door device ID', 'help' => 'Unique device identifier shown in your Omlet account.', 'type' => 'text', 'group' => 'Basic setup', 'required' => true, 'placeholder' => 'Enter the Omlet device ID'),
    'DOOR_POLL_INTERVAL_SECONDS' => array('label' => 'Polling interval', 'help' => 'Seconds between Omlet door-state refreshes.', 'type' => 'number', 'group' => 'Basic setup', 'min' => 1, 'max' => 3600, 'required' => true),
    'MQTT_BASE_TOPIC' => array('label' => 'MQTT base topic', 'help' => 'Shared prefix for all bridge messages. Wildcards are not allowed.', 'type' => 'topic', 'group' => 'MQTT', 'required' => true),
    'CHICKEN_DOOR_COMMAND_TOPIC' => array('label' => 'Command topic', 'help' => 'Topic used to receive door commands.', 'type' => 'topic', 'group' => 'MQTT', 'required' => true),
    'CHICKEN_DOOR_STATUS_TOPIC' => array('label' => 'Door state topic', 'help' => 'Human-readable door state topic.', 'type' => 'topic', 'group' => 'MQTT', 'required' => true),
    'CHICKEN_DOOR_STATUS_CODE_TOPIC' => array('label' => 'Door state code topic', 'help' => 'Numeric door state topic used by automations.', 'type' => 'topic', 'group' => 'MQTT', 'required' => true),
    'CHICKEN_DOOR_FAULT_TOPIC' => array('label' => 'Fault topic', 'help' => 'Topic publishing active door faults.', 'type' => 'topic', 'group' => 'MQTT', 'required' => true),
    'CHICKEN_DOOR_CONNECTED_TOPIC' => array('label' => 'Connection topic', 'help' => 'Topic publishing whether the device is connected.', 'type' => 'topic', 'group' => 'MQTT', 'required' => true),
    'CHICKEN_DOOR_BATTERY_TOPIC' => array('label' => 'Battery topic', 'help' => 'Topic publishing the latest battery level.', 'type' => 'topic', 'group' => 'MQTT', 'required' => true),
    'CHICKEN_DOOR_LIGHT_LEVEL_TOPIC' => array('label' => 'Light level topic', 'help' => 'Topic publishing the door light sensor value.', 'type' => 'topic', 'group' => 'MQTT', 'required' => true),
    'CHICKEN_DOOR_USAGE_TOPIC' => array('label' => 'Usage event topic', 'help' => 'Topic publishing command usage as JSON. LoxBerry exposes its fields below this topic.', 'type' => 'topic', 'group' => 'MQTT', 'required' => true),
    'LOG_LEVEL' => array('label' => 'Log level', 'help' => 'INFO is recommended. Use DEBUG only while troubleshooting.', 'type' => 'select', 'group' => 'Logging', 'options' => array('ERROR' => 'Errors only', 'WARNING' => 'Warnings and errors', 'INFO' => 'Information', 'DEBUG' => 'Debug')),
    'LOG_FILE_PATH' => array('label' => 'Log file path', 'help' => 'Path relative to the plugin runtime unless an absolute path is supplied.', 'type' => 'text', 'group' => 'Logging', 'required' => true),
);
$editableSettings = array_keys($fieldSchema);

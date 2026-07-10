<?php
$pluginFolder = 'omletchickendoor';
$pluginTitle = 'OmletChickenDoorPlugin';
$fixedSettings = array(
    'BRIDGE_DEVICES_ENABLED' => 'chicken_door',
);
$editableSettings = array(
    'DOOR_API_KEY',
    'DOOR_DEVICE_ID',
    'MQTT_BASE_TOPIC',
    'CHICKEN_DOOR_COMMAND_TOPIC',
    'CHICKEN_DOOR_STATUS_TOPIC',
    'CHICKEN_DOOR_STATUS_CODE_TOPIC',
    'CHICKEN_DOOR_FAULT_TOPIC',
    'CHICKEN_DOOR_CONNECTED_TOPIC',
    'CHICKEN_DOOR_BATTERY_TOPIC',
    'CHICKEN_DOOR_LIGHT_LEVEL_TOPIC',
    'LOG_LEVEL',
    'LOG_FILE_PATH',
);
$allowedDoorCommands = array(
    'open_door',
    'close_door',
    'stop_door',
    'get_door_state',
);

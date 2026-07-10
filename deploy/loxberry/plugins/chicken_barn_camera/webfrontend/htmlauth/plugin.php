<?php
$pluginFolder = 'chickenbarncamera';
$pluginTitle = 'ChickenBarnCameraPlugin';
$fixedSettings = array(
    'BRIDGE_DEVICES_ENABLED' => 'chicken_thread_detector',
);
$editableSettings = array(
    'MQTT_BASE_TOPIC',
    'CHICKEN_THREAD_DETECTOR_TOPIC',
    'CAMERA_HOST',
    'CAMERA_PORT',
    'CAMERA_JPG_ENDPOINT',
    'CAMERA_HEALTH_ENDPOINT',
    'CAMERA_TIMEOUT_SECONDS',
    'CAMERA_MAX_JPEG_BYTES',
    'CAMERA_AUTH_TOKEN',
    'CHICKEN_THREAT_ENABLED',
    'CHICKEN_THREAT_INFERENCE_URL',
    'CHICKEN_THREAT_INFERENCE_TIMEOUT_SECONDS',
    'CHICKEN_THREAT_POLL_INTERVAL_SECONDS',
    'LOG_LEVEL',
    'LOG_FILE_PATH',
);
$allowedDoorCommands = array();

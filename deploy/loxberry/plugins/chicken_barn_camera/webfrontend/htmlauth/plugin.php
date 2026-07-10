<?php
$pluginFolder = 'chickenbarncamera';
$pluginTitle = 'ChickenBarnCameraPlugin';
$pluginDisplayName = 'Chicken Barn Camera';
$pluginDescription = 'Camera health, chicken-threat detection, and bridge diagnostics.';
$fixedSettings = array('BRIDGE_DEVICES_ENABLED' => 'chicken_thread_detector');
$allowedDoorCommands = array();
$statusCards = array(
    array('label' => 'Camera connection', 'value' => 'Run camera test'),
    array('label' => 'Threat detection', 'setting' => 'CHICKEN_THREAT_ENABLED', 'kind' => 'toggle', 'tone' => 'good'),
);
$diagnosticActions = array(
    'test-camera' => 'Test camera',
    'test-inference' => 'Test inference service',
);
$fieldSchema = array(
    'CAMERA_HOST' => array('label' => 'Camera address', 'help' => 'Hostname or IP address of the ESP32-CAM, for example 192.168.1.42.', 'type' => 'host', 'group' => 'Basic setup', 'required' => true, 'placeholder' => '192.168.1.42'),
    'CAMERA_PORT' => array('label' => 'Camera port', 'help' => 'HTTP port exposed by the camera. Usually 80.', 'type' => 'number', 'group' => 'Basic setup', 'required' => true, 'min' => 1, 'max' => 65535),
    'CAMERA_AUTH_TOKEN' => array('label' => 'Camera authentication token', 'help' => 'Bearer token used for camera requests. Leave blank to keep the saved token.', 'type' => 'password', 'group' => 'Basic setup', 'sensitive' => true),
    'CHICKEN_THREAT_ENABLED' => array('label' => 'Threat detection', 'help' => 'Enable periodic chicken-threat inference.', 'type' => 'toggle', 'group' => 'Detection'),
    'CHICKEN_THREAT_INFERENCE_URL' => array('label' => 'Inference service URL', 'help' => 'Complete HTTP endpoint used for inference, for example http://127.0.0.1:8090/v1/chicken-threat/infer.', 'type' => 'url', 'group' => 'Detection', 'required' => true),
    'CHICKEN_THREAT_INFERENCE_TIMEOUT_SECONDS' => array('label' => 'Inference timeout', 'help' => 'Maximum seconds to wait for one inference request.', 'type' => 'number', 'group' => 'Detection', 'min' => 1, 'max' => 120),
    'CHICKEN_THREAT_POLL_INTERVAL_SECONDS' => array('label' => 'Polling interval', 'help' => 'Seconds between camera checks. Use a longer interval on slower hardware.', 'type' => 'number', 'group' => 'Detection', 'min' => 1, 'max' => 3600),
    'MQTT_BASE_TOPIC' => array('label' => 'MQTT base topic', 'help' => 'Shared prefix for bridge messages. Wildcards are not allowed.', 'type' => 'topic', 'group' => 'MQTT', 'required' => true),
    'CHICKEN_THREAD_DETECTOR_TOPIC' => array('label' => 'Detector topic', 'help' => 'Topic below the base topic for detector state.', 'type' => 'topic', 'group' => 'MQTT', 'required' => true),
    'CAMERA_JPG_ENDPOINT' => array('label' => 'JPEG endpoint', 'help' => 'Camera path returning the current JPEG image, for example /jpg.', 'type' => 'endpoint', 'group' => 'Advanced', 'required' => true),
    'CAMERA_HEALTH_ENDPOINT' => array('label' => 'Health endpoint', 'help' => 'Camera path used by the connection test, for example /health.', 'type' => 'endpoint', 'group' => 'Advanced', 'required' => true),
    'CAMERA_TIMEOUT_SECONDS' => array('label' => 'Camera timeout', 'help' => 'Maximum seconds to wait for a camera response.', 'type' => 'number', 'group' => 'Advanced', 'min' => 1, 'max' => 60),
    'CAMERA_MAX_JPEG_BYTES' => array('label' => 'Maximum JPEG size', 'help' => 'Reject images larger than this number of bytes.', 'type' => 'number', 'group' => 'Advanced', 'min' => 1024, 'max' => 25000000),
    'LOG_LEVEL' => array('label' => 'Log level', 'help' => 'INFO is recommended. Use DEBUG only while troubleshooting.', 'type' => 'select', 'group' => 'Logging', 'options' => array('ERROR' => 'Errors only', 'WARNING' => 'Warnings and errors', 'INFO' => 'Information', 'DEBUG' => 'Debug')),
    'LOG_FILE_PATH' => array('label' => 'Log file path', 'help' => 'Path relative to the plugin runtime unless an absolute path is supplied.', 'type' => 'text', 'group' => 'Logging', 'required' => true),
);
$editableSettings = array_keys($fieldSchema);

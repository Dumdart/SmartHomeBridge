<?php
$pluginFolder = 'smarthomebridge';
$lbpbin = getenv('LBPBIN') ?: './bin';
$lbpconfig = getenv('LBPCONFIG') ?: './config';
$lbplog = getenv('LBPLOG') ?: './logs';
$bridgeConfig = $lbpconfig . '/' . $pluginFolder . '/smart-home-bridge.ini';
$bridgeCtl = $lbpbin . '/' . $pluginFolder . '/bridge_ctl.sh';
$logFile = $lbplog . '/' . $pluginFolder . '/smart-home-bridge.log';
$allowedCommands = array(
    'start',
    'stop',
    'restart',
    'status',
    'dump-config',
);
$allowedDoorCommands = array(
    'open_door',
    'close_door',
    'stop_door',
    'get_door_state',
);
$editableSettings = array(
    'DOOR_API_KEY',
    'DOOR_DEVICE_ID',
    'MQTT_BASE_TOPIC',
    'BRIDGE_DEVICES_ENABLED',
    'CHICKEN_DOOR_COMMAND_TOPIC',
    'CHICKEN_DOOR_STATUS_TOPIC',
    'CHICKEN_THREAD_DETECTOR_TOPIC',
    'CAMERA_HOST',
    'CAMERA_PORT',
    'CHICKEN_THREAT_ENABLED',
    'CHICKEN_THREAT_INFERENCE_URL',
    'CHICKEN_THREAT_INFERENCE_TIMEOUT_SECONDS',
    'CHICKEN_THREAT_POLL_INTERVAL_SECONDS',
    'LOG_LEVEL',
    'LOG_FILE_PATH',
);
$output = array();
$exitCode = 0;
$notice = '';

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $action = $_POST['action'] ?? 'status';
    if ($action === 'save-settings') {
        save_settings($bridgeConfig, $editableSettings);
        $notice = 'Settings saved. Restart the backend for runtime settings to apply.';
        $action = 'status';
    }

    if ($action === 'door-command') {
        $doorCommand = $_POST['door_command'] ?? '';
        if (!in_array($doorCommand, $allowedDoorCommands, true)) {
            http_response_code(400);
            exit('Invalid door command');
        }
        exec(
            escapeshellcmd($bridgeCtl) . ' door-command '
                . escapeshellarg($doorCommand),
            $output,
            $exitCode
        );
    } elseif ($action === 'log-tail') {
        $output = read_log_tail($logFile);
    } else {
        if (!in_array($action, $allowedCommands, true)) {
            http_response_code(400);
            exit('Invalid command');
        }
        exec(escapeshellcmd($bridgeCtl) . ' ' . escapeshellarg($action), $output, $exitCode);
    }
} else {
    exec(escapeshellcmd($bridgeCtl) . ' status', $output, $exitCode);
}

$settings = load_settings($bridgeConfig, $editableSettings);

function load_settings($path, $keys) {
    $settings = array_fill_keys($keys, '');
    if (is_file($path)) {
        $parsed = parse_ini_file($path, false, INI_SCANNER_RAW);
        if (is_array($parsed)) {
            foreach ($keys as $key) {
                if (array_key_exists($key, $parsed)) {
                    $settings[$key] = $parsed[$key];
                }
            }
        }
    }
    return $settings;
}

function save_settings($path, $keys) {
    $settings = load_settings($path, $keys);
    foreach ($keys as $key) {
        if (array_key_exists($key, $_POST)) {
            $settings[$key] = trim((string) $_POST[$key]);
        }
    }

    $directory = dirname($path);
    if (!is_dir($directory)) {
        mkdir($directory, 0750, true);
    }

    $lines = array('[smart-home-bridge]');
    foreach ($keys as $key) {
        $lines[] = $key . '=' . ini_value($settings[$key]);
    }
    file_put_contents($path, implode("\n", $lines) . "\n");
}

function ini_value($value) {
    if ($value === '' || preg_match('/[\s#;]/', $value)) {
        return '"' . str_replace(array('\\', '"'), array('\\\\', '\\"'), $value) . '"';
    }
    return $value;
}

function read_log_tail($path) {
    if (!is_file($path)) {
        return array('Log file not found: ' . $path);
    }
    $lines = file($path, FILE_IGNORE_NEW_LINES);
    if ($lines === false) {
        return array('Unable to read log file: ' . $path);
    }
    return array_slice($lines, -80);
}

function e($value) {
    return htmlspecialchars((string) $value, ENT_QUOTES, 'UTF-8');
}
?>
<!doctype html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <title>SmartHomeBridge</title>
</head>
<body>
    <h1>SmartHomeBridge</h1>
    <?php if ($notice !== ''): ?>
        <p><?php echo e($notice); ?></p>
    <?php endif; ?>

    <form method="post">
        <button name="action" value="status">Status</button>
        <button name="action" value="start">Start</button>
        <button name="action" value="stop">Stop</button>
        <button name="action" value="restart">Restart</button>
        <button name="action" value="dump-config">Config Check</button>
        <button name="action" value="log-tail">Log Tail</button>
    </form>

    <h2>Manual Door Commands</h2>
    <form method="post">
        <select name="door_command">
            <?php foreach ($allowedDoorCommands as $doorCommand): ?>
                <option value="<?php echo e($doorCommand); ?>"><?php echo e($doorCommand); ?></option>
            <?php endforeach; ?>
        </select>
        <button name="action" value="door-command">Publish</button>
    </form>

    <h2>Critical Settings</h2>
    <form method="post">
        <?php foreach ($editableSettings as $key): ?>
            <label>
                <?php echo e($key); ?>
                <input name="<?php echo e($key); ?>" value="<?php echo e($settings[$key]); ?>">
            </label>
            <br>
        <?php endforeach; ?>
        <button name="action" value="save-settings">Save Settings</button>
    </form>

    <h2>Output</h2>
    <pre><?php echo e(implode("\n", $output)); ?></pre>
    <?php if ($exitCode !== 0): ?>
        <p>Command exited with code <?php echo (int) $exitCode; ?></p>
    <?php endif; ?>
</body>
</html>

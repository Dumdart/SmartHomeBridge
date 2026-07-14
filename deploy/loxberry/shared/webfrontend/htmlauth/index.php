<?php
require __DIR__ . '/plugin.php';

if (session_status() !== PHP_SESSION_ACTIVE) {
    session_start();
}

$lbpbin = getenv('LBPBIN') ?: './bin';
$lbpconfig = getenv('LBPCONFIG') ?: './config';
$lbplog = getenv('LBPLOG') ?: './logs';
$bridgeConfig = $lbpconfig . '/' . $pluginFolder . '/smart-home-bridge.ini';
$bridgeCtl = $lbpbin . '/' . $pluginFolder . '/bridge_ctl.sh';
$logFile = $lbplog . '/' . $pluginFolder . '/smart-home-bridge.log';
$allowedCommands = array('start', 'stop', 'restart', 'status', 'dump-config');
$csrfToken = $_SESSION['csrf_token'] ?? bin2hex(random_bytes(24));
$_SESSION['csrf_token'] = $csrfToken;

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    if (!hash_equals($csrfToken, (string) ($_POST['csrf_token'] ?? ''))) {
        http_response_code(403);
        exit('The form expired. Reload the page and try again.');
    }

    $action = (string) ($_POST['action'] ?? 'status');
    $flash = array('type' => 'info', 'message' => '', 'output' => array(), 'exit_code' => 0);
    $redirectTab = 'status';

    if ($action === 'save-settings') {
        $existingSettings = load_settings($bridgeConfig, array_keys($fieldSchema));
        $errors = validate_settings($_POST, $fieldSchema, $existingSettings);
        if (count($errors) > 0) {
            $flash['type'] = 'error';
            $flash['message'] = 'Settings were not saved. Please correct the highlighted values.';
            $flash['errors'] = $errors;
            $flash['values'] = safe_posted_values($_POST, $fieldSchema);
            $redirectTab = 'settings';
        } else {
            save_settings($bridgeConfig, $fieldSchema, $fixedSettings);
            $flash['type'] = 'success';
            $flash['message'] = 'Settings saved. Restart the bridge to apply runtime changes.';
            $redirectTab = 'settings';
        }
    } elseif ($action === 'door-command') {
        $doorCommand = (string) ($_POST['door_command'] ?? '');
        if (!in_array($doorCommand, $allowedDoorCommands, true)) {
            http_response_code(400);
            exit('Invalid door command');
        }
        run_bridge_command($bridgeCtl, 'door-command', $doorCommand, $flash['output'], $flash['exit_code']);
        $flash['type'] = $flash['exit_code'] === 0 ? 'success' : 'error';
        $flash['message'] = door_command_message($doorCommand, $flash['exit_code']);
        $redirectTab = 'status';
    } elseif ($action === 'log-tail') {
        $flash['output'] = read_log_tail($logFile);
        $flash['message'] = count($flash['output']) > 0 ? 'Showing the latest log entries.' : 'The log is empty.';
        $redirectTab = 'log';
    } elseif ($action === 'test-camera' || $action === 'test-inference' || $action === 'test-door' || $action === 'test-webhook') {
        $currentSettings = load_settings($bridgeConfig, array_keys($fieldSchema));
        run_diagnostic($action, $currentSettings, $bridgeCtl, $flash['output'], $flash['exit_code']);
        $flash['type'] = $flash['exit_code'] === 0 ? 'success' : 'error';
        $flash['message'] = $flash['exit_code'] === 0 ? 'Diagnostic completed successfully.' : 'Diagnostic found a problem.';
        $redirectTab = 'status';
    } else {
        if (!in_array($action, $allowedCommands, true)) {
            http_response_code(400);
            exit('Invalid command');
        }
        run_bridge_command($bridgeCtl, $action, '', $flash['output'], $flash['exit_code']);
        $flash['type'] = $flash['exit_code'] === 0 ? 'success' : 'error';
        $flash['message'] = command_message($action, $flash['exit_code']);
        $redirectTab = $action === 'dump-config' ? 'status' : 'status';
    }

    $flash['output'] = redact_output($flash['output'], $fieldSchema);
    $_SESSION['bridge_flash'] = $flash;
    header('Location: ' . current_page_url() . '?tab=' . rawurlencode($redirectTab));
    exit;
}

$flash = $_SESSION['bridge_flash'] ?? null;
unset($_SESSION['bridge_flash']);
$requestedTab = (string) ($_GET['tab'] ?? 'status');
$activeTab = in_array($requestedTab, array('status', 'settings', 'log'), true)
    ? $requestedTab
    : 'status';
$settings = load_settings($bridgeConfig, array_keys($fieldSchema));
if (is_array($flash) && isset($flash['values'])) {
    $settings = array_merge($settings, $flash['values']);
}
$statusOutput = array();
$statusExitCode = 0;
run_bridge_command($bridgeCtl, 'status', '', $statusOutput, $statusExitCode);
$serviceRunning = $statusExitCode === 0;
$lastLogUpdate = is_file($logFile) ? date('Y-m-d H:i', filemtime($logFile)) : 'No log yet';

function current_page_url() {
    $path = parse_url((string) ($_SERVER['REQUEST_URI'] ?? 'index.php'), PHP_URL_PATH);
    return is_string($path) && $path !== '' ? $path : 'index.php';
}

function run_bridge_command($bridgeCtl, $command, $argument, &$output, &$exitCode) {
    $output = array();
    $shellCommand = escapeshellarg($bridgeCtl) . ' ' . escapeshellarg($command);
    if ($argument !== '') {
        $shellCommand .= ' ' . escapeshellarg($argument);
    }
    exec($shellCommand . ' 2>&1', $output, $exitCode);
}

function command_message($action, $exitCode) {
    if ($exitCode !== 0) {
        return ucfirst(str_replace('-', ' ', $action)) . ' failed. Open diagnostic details for more information.';
    }
    $messages = array(
        'start' => 'The bridge was started.',
        'stop' => 'The bridge was stopped.',
        'restart' => 'The bridge was restarted.',
        'status' => 'Service status refreshed.',
        'dump-config' => 'Configuration validation completed.',
    );
    return $messages[$action] ?? 'Action completed.';
}

function door_command_message($command, $exitCode) {
    if ($exitCode !== 0) {
        return 'The door command could not be sent. Review diagnostic details before trying again.';
    }
    $messages = array(
        'open_door' => 'Open command sent. Confirm the door is moving safely.',
        'close_door' => 'Close command sent. Confirm the doorway is clear.',
        'stop_door' => 'Stop command sent.',
        'get_door_state' => 'A fresh door state was requested.',
    );
    return $messages[$command] ?? 'Door command sent.';
}

function run_diagnostic($action, $settings, $bridgeCtl, &$output, &$exitCode) {
    if ($action === 'test-webhook') {
        $host = $settings['HTTP_HOST'] ?? '127.0.0.1';
        if ($host === '0.0.0.0' || $host === '::') {
            $host = '127.0.0.1';
        }
        $port = max(1, min(65535, (int) ($settings['HTTP_PORT'] ?? 8080)));
        $url = 'http://' . $host . ':' . $port . '/health';
        $command = 'curl --silent --show-error --fail --max-time 5 ' . escapeshellarg($url);
        exec($command . ' 2>&1', $output, $exitCode);
        return;
    }

    if ($action === 'test-camera') {
        $host = $settings['CAMERA_HOST'] ?? '';
        $port = (int) ($settings['CAMERA_PORT'] ?? 80);
        $endpoint = $settings['CAMERA_HEALTH_ENDPOINT'] ?? '/health';
        $timeout = max(1, min(30, (int) ($settings['CAMERA_TIMEOUT_SECONDS'] ?? 5)));
        if ($host === '' || !valid_host($host)) {
            $output = array('Camera host is missing or invalid.');
            $exitCode = 2;
            return;
        }
        $url = 'http://' . $host . ':' . $port . normalize_endpoint($endpoint);
        $command = 'curl --silent --show-error --output /dev/null --write-out ' . escapeshellarg('HTTP %{http_code} in %{time_total}s')
            . ' --max-time ' . $timeout;
        if (($settings['CAMERA_AUTH_TOKEN'] ?? '') !== '') {
            $command .= ' --header ' . escapeshellarg('Authorization: Bearer ' . $settings['CAMERA_AUTH_TOKEN']);
        }
        exec($command . ' ' . escapeshellarg($url) . ' 2>&1', $output, $exitCode);
        return;
    }

    if ($action === 'test-inference') {
        $url = $settings['CHICKEN_THREAT_INFERENCE_URL'] ?? '';
        $parts = parse_url($url);
        if (!is_array($parts) || !isset($parts['host']) || !in_array($parts['scheme'] ?? '', array('http', 'https'), true)) {
            $output = array('Inference URL is missing or invalid.');
            $exitCode = 2;
            return;
        }
        $port = isset($parts['port']) ? (int) $parts['port'] : (($parts['scheme'] ?? '') === 'https' ? 443 : 80);
        $timeout = max(1, min(30, (int) ($settings['CHICKEN_THREAT_INFERENCE_TIMEOUT_SECONDS'] ?? 10)));
        $errorNumber = 0;
        $errorMessage = '';
        $socket = @fsockopen((string) $parts['host'], $port, $errorNumber, $errorMessage, $timeout);
        if (is_resource($socket)) {
            fclose($socket);
            $output = array('Inference service accepted a connection on ' . $parts['host'] . ':' . $port . '.');
            $exitCode = 0;
        } else {
            $output = array('Could not connect to the inference service: ' . ($errorMessage ?: 'connection failed') . '.');
            $exitCode = $errorNumber ?: 1;
        }
        return;
    }

    run_bridge_command($bridgeCtl, 'dump-config', '', $output, $exitCode);
    if ($exitCode === 0) {
        $doorOutput = array();
        $doorExitCode = 0;
        run_bridge_command($bridgeCtl, 'door-command', 'get_door_state', $doorOutput, $doorExitCode);
        $output = array_merge($output, $doorOutput);
        $exitCode = $doorExitCode;
    }
}

function valid_host($host) {
    return filter_var($host, FILTER_VALIDATE_IP) !== false
        || preg_match('/^(?=.{1,253}$)(?!-)[A-Za-z0-9.-]+(?<!-)$/', $host) === 1;
}

function normalize_endpoint($endpoint) {
    return '/' . ltrim((string) $endpoint, '/');
}

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

function validate_settings($posted, $schema, $existingSettings) {
    $errors = array();
    foreach ($schema as $key => $field) {
        $value = trim((string) ($posted[$key] ?? ''));
        $required = (bool) ($field['required'] ?? false);
        foreach (($field['required_when'] ?? array()) as $dependency => $expected) {
            if (trim((string) ($posted[$dependency] ?? '')) === (string) $expected) {
                $required = true;
            }
        }
        if (($field['sensitive'] ?? false) && $value === '') {
            $savedValue = trim((string) ($existingSettings[$key] ?? ''));
            if ($required && $savedValue === '') {
                $errors[$key] = ($field['label'] ?? $key) . ' is required.';
            } elseif ($savedValue !== '' && isset($field['minlength']) && strlen($savedValue) < $field['minlength']) {
                $errors[$key] = 'Enter at least ' . $field['minlength'] . ' characters.';
            }
            continue;
        }
        if ($required && $value === '') {
            $errors[$key] = ($field['label'] ?? $key) . ' is required.';
            continue;
        }
        if ($value === '') {
            continue;
        }
        if (isset($field['minlength']) && strlen($value) < $field['minlength']) {
            $errors[$key] = 'Enter at least ' . $field['minlength'] . ' characters.';
            continue;
        }
        $type = $field['type'] ?? 'text';
        if ($type === 'number' && filter_var($value, FILTER_VALIDATE_INT) === false) {
            $errors[$key] = 'Enter a whole number.';
        } elseif ($type === 'number' && (isset($field['min']) && (int) $value < $field['min'] || isset($field['max']) && (int) $value > $field['max'])) {
            $errors[$key] = 'Enter a value between ' . $field['min'] . ' and ' . $field['max'] . '.';
        } elseif ($type === 'url' && filter_var($value, FILTER_VALIDATE_URL) === false) {
            $errors[$key] = 'Enter a complete http:// or https:// URL.';
        } elseif ($type === 'host' && !valid_host($value)) {
            $errors[$key] = 'Enter a valid hostname or IP address.';
        } elseif ($type === 'endpoint' && strpos($value, '/') !== 0) {
            $errors[$key] = 'Endpoint paths must begin with /.';
        } elseif ($type === 'topic' && (preg_match('/[\x00-\x1F#+]/', $value) || strlen($value) > 200)) {
            $errors[$key] = 'Use a topic without wildcards, control characters, or more than 200 characters.';
        } elseif ($type === 'select' && !array_key_exists($value, $field['options'] ?? array())) {
            $errors[$key] = 'Choose one of the available options.';
        }
    }
    return $errors;
}

function safe_posted_values($posted, $schema) {
    $values = array();
    foreach ($schema as $key => $field) {
        if (!($field['sensitive'] ?? false) && array_key_exists($key, $posted)) {
            $values[$key] = trim((string) $posted[$key]);
        }
    }
    return $values;
}

function save_settings($path, $schema, $fixedSettings) {
    $keys = array_keys($schema);
    $settings = load_settings($path, $keys);
    foreach ($schema as $key => $field) {
        if (!array_key_exists($key, $_POST)) {
            continue;
        }
        $value = trim((string) $_POST[$key]);
        if (($field['sensitive'] ?? false) && $value === '') {
            continue;
        }
        if (($field['type'] ?? '') === 'toggle') {
            $value = $value === 'true' ? 'true' : 'false';
        }
        $settings[$key] = $value;
    }

    $directory = dirname($path);
    if (!is_dir($directory)) {
        mkdir($directory, 0750, true);
    }
    $lines = array('[smart-home-bridge]');
    foreach (array_merge($fixedSettings, $settings) as $key => $value) {
        $lines[] = $key . '=' . ini_value($value);
    }
    file_put_contents($path, implode("\n", $lines) . "\n", LOCK_EX);
}

function ini_value($value) {
    if ($value === '' || preg_match('/[\s#;]/', $value)) {
        return '"' . str_replace(array('\\', '"'), array('\\\\', '\\"'), $value) . '"';
    }
    return $value;
}

function read_log_tail($path) {
    if (!is_file($path)) {
        return array('The bridge has not created a log file yet.');
    }
    $lines = file($path, FILE_IGNORE_NEW_LINES);
    if ($lines === false) {
        return array('The log file could not be read.');
    }
    return array_slice($lines, -120);
}

function redact_output($lines, $schema) {
    $secretKeys = array();
    foreach ($schema as $key => $field) {
        if ($field['sensitive'] ?? false) {
            $secretKeys[] = preg_quote($key, '/');
        }
    }
    $keyPattern = count($secretKeys) > 0 ? implode('|', $secretKeys) : 'API_KEY|TOKEN|PASSWORD';
    return array_map(function ($line) use ($keyPattern) {
        $line = preg_replace('/((' . $keyPattern . ')\s*[=:]\s*)[^\s,;]+/i', '$1********', (string) $line);
        return preg_replace('/(Bearer\s+)[A-Za-z0-9._~+\/-]+/i', '$1********', $line);
    }, $lines);
}

function group_fields($schema) {
    $groups = array();
    foreach ($schema as $key => $field) {
        $group = $field['group'] ?? 'Advanced';
        $groups[$group][$key] = $field;
    }
    return $groups;
}

function e($value) {
    return htmlspecialchars((string) $value, ENT_QUOTES, 'UTF-8');
}

$loxberryUi = false;
if (stream_resolve_include_path('loxberry_web.php') !== false) {
    require_once 'loxberry_web.php';
    $loxberryUi = class_exists('LBWeb');
}
if ($loxberryUi) {
    LBWeb::lbheader($pluginTitle, '', '', true);
} else {
    echo '<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>' . e($pluginTitle) . '</title></head><body>';
}
?>
<style>
    :root { --lb-green: #61ae14; --lb-green-dark: #4d8c0e; --lb-border: #a9a9a9; --lb-panel: #f4f4f4; --lb-text: #171717; --lb-muted: #666; --lb-error: #b42318; --lb-warning: #9a6700; }
    .shb-shell { max-width: 1380px; margin: 0 auto; padding: 22px 28px 44px; color: var(--lb-text); font-family: Arial, Helvetica, sans-serif; }
    .shb-heading { margin: 0 0 6px; font-size: 28px; line-height: 1.25; }
    .shb-lead { margin: 0 0 24px; color: var(--lb-muted); font-size: 15px; }
    .shb-tabs { display: flex; gap: 0; margin-bottom: 28px; border-bottom: 2px solid var(--lb-green); }
    .shb-tab { display: inline-block; min-width: 120px; padding: 12px 20px; color: #222 !important; text-align: center; text-decoration: none !important; border: 1px solid var(--lb-border); border-bottom: 0; background: #e9e9e9; font-weight: 700; }
    .shb-tab + .shb-tab { border-left: 0; }
    .shb-tab.is-active { color: #fff !important; background: var(--lb-green); border-color: var(--lb-green); }
    .shb-panel[hidden] { display: none; }
    .shb-notice { margin: 0 0 24px; padding: 13px 16px; border-left: 5px solid #3778a8; background: #eef6fc; }
    .shb-notice--success { border-color: var(--lb-green); background: #f1f8e9; }
    .shb-notice--error { border-color: var(--lb-error); background: #fff0ee; }
    .shb-status-grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); border: 1px solid var(--lb-border); }
    .shb-status { min-height: 100px; padding: 19px 20px; background: #fff; }
    .shb-status + .shb-status { border-left: 1px solid #d2d2d2; }
    .shb-eyebrow { display: block; margin-bottom: 9px; color: var(--lb-muted); font-size: 12px; font-weight: 700; letter-spacing: .05em; text-transform: uppercase; }
    .shb-badge { display: inline-block; padding: 5px 10px; border: 1px solid var(--lb-border); background: var(--lb-panel); font-size: 14px; font-weight: 700; }
    .shb-badge--good { color: #285d00; border-color: #85bd54; background: #edf7e4; }
    .shb-badge--bad { color: #8d2018; border-color: #e3a59e; background: #fff0ee; }
    .shb-section { margin-top: 30px; }
    .shb-section-title { margin: 0 0 12px; padding-bottom: 9px; border-bottom: 1px solid var(--lb-border); color: var(--lb-green-dark); font-size: 19px; font-weight: 400; }
    .shb-actions { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 5px; }
    .shb-button { min-height: 44px; padding: 9px 16px; border: 1px solid #8f8f8f; border-radius: 2px; background: #e8e8e8; color: #111; font: inherit; font-weight: 700; cursor: pointer; }
    .shb-button:hover, .shb-button:focus-visible { background: #ddd; outline: 3px solid rgba(97, 174, 20, .3); outline-offset: 1px; }
    .shb-button--primary { color: #fff; border-color: var(--lb-green-dark); background: var(--lb-green); }
    .shb-button--primary:hover { background: var(--lb-green-dark); }
    .shb-button--danger { color: #8d2018; border-color: #c87d75; background: #fff4f2; }
    .shb-warning { margin: 0 0 14px; padding: 12px 14px; border: 1px solid #d8b35b; background: #fff8df; color: #624500; }
    .shb-callout { margin: 0 0 22px; padding: 14px 16px; border-left: 5px solid var(--lb-green); background: #f1f8e9; }
    .shb-callout p { margin: 6px 0 0; }
    .shb-form-row { display: grid; grid-template-columns: minmax(220px, 29%) minmax(260px, 1fr) 34px; align-items: start; gap: 14px; padding: 9px 4px; }
    .shb-label { padding-top: 9px; font-weight: 400; }
    .shb-control input, .shb-control select { box-sizing: border-box; width: 100%; min-height: 41px; padding: 8px 10px; border: 1px solid #999; border-radius: 2px; background: #fff; color: #111; font: inherit; }
    .shb-control input:focus, .shb-control select:focus { border-color: var(--lb-green-dark); outline: 3px solid rgba(97, 174, 20, .25); }
    .shb-control input[aria-invalid="true"] { border-color: var(--lb-error); }
    .shb-help { margin: 5px 0 0; color: var(--lb-muted); font-size: 13px; line-height: 1.4; }
    .shb-error { margin: 5px 0 0; color: var(--lb-error); font-size: 13px; font-weight: 700; }
    .shb-help-button { width: 30px; height: 30px; margin-top: 5px; border: 0; border-bottom: 1px dotted #222; background: transparent; font-weight: 700; cursor: help; }
    .shb-toggle { display: flex; align-items: center; min-height: 41px; }
    .shb-toggle input { width: 20px; height: 20px; margin: 0 9px 0 0; accent-color: var(--lb-green); }
    .shb-advanced { margin-top: 22px; border-top: 1px solid var(--lb-border); }
    .shb-advanced summary { padding: 14px 4px; color: var(--lb-green-dark); font-size: 17px; cursor: pointer; }
    .shb-form-actions { display: flex; justify-content: flex-end; gap: 6px; margin-top: 24px; padding-top: 18px; border-top: 1px solid var(--lb-border); }
    .shb-form-actions .shb-button { min-width: 220px; }
    .shb-output { max-height: 420px; overflow: auto; margin: 14px 0 0; padding: 16px; border: 1px solid #aaa; background: #202124; color: #f4f4f4; font: 13px/1.55 Consolas, monospace; white-space: pre-wrap; }
    .shb-log-meta { display: flex; align-items: center; justify-content: space-between; gap: 16px; }
    @media (max-width: 800px) {
        .shb-shell { padding: 16px 12px 32px; }
        .shb-tabs { overflow-x: auto; }
        .shb-tab { min-width: 0; flex: 1; padding: 11px 12px; }
        .shb-status-grid, .shb-actions { grid-template-columns: 1fr; }
        .shb-status + .shb-status { border-left: 0; border-top: 1px solid #d2d2d2; }
        .shb-form-row { grid-template-columns: 1fr 34px; gap: 4px 10px; padding: 11px 0; }
        .shb-label { grid-column: 1 / -1; padding: 0; font-weight: 700; }
        .shb-form-actions { display: block; }
        .shb-form-actions .shb-button { width: 100%; min-width: 0; }
        .shb-log-meta { align-items: stretch; flex-direction: column; }
    }
</style>

<main class="shb-shell">
    <h1 class="shb-heading"><?php echo e($pluginDisplayName); ?></h1>
    <p class="shb-lead"><?php echo e($pluginDescription); ?></p>

    <nav class="shb-tabs" aria-label="Plugin sections">
        <?php foreach (array('status' => 'Status', 'settings' => 'Settings', 'log' => 'Log') as $tab => $label): ?>
            <a class="shb-tab<?php echo $activeTab === $tab ? ' is-active' : ''; ?>" href="?tab=<?php echo e($tab); ?>" data-tab="<?php echo e($tab); ?>" aria-current="<?php echo $activeTab === $tab ? 'page' : 'false'; ?>"><?php echo e($label); ?></a>
        <?php endforeach; ?>
    </nav>

    <?php if (is_array($flash) && ($flash['message'] ?? '') !== ''): ?>
        <div class="shb-notice shb-notice--<?php echo e($flash['type'] ?? 'info'); ?>" role="status"><?php echo e($flash['message']); ?></div>
    <?php endif; ?>

    <section class="shb-panel" data-panel="status"<?php echo $activeTab !== 'status' ? ' hidden' : ''; ?>>
        <div class="shb-status-grid">
            <div class="shb-status">
                <span class="shb-eyebrow">Bridge service</span>
                <span class="shb-badge <?php echo $serviceRunning ? 'shb-badge--good' : 'shb-badge--bad'; ?>"><?php echo $serviceRunning ? 'Running' : 'Stopped'; ?></span>
            </div>
            <?php foreach ($statusCards as $card): ?>
                <div class="shb-status">
                    <span class="shb-eyebrow"><?php echo e($card['label']); ?></span>
                    <span class="shb-badge<?php echo ($card['tone'] ?? '') === 'good' ? ' shb-badge--good' : ''; ?>"><?php echo e(status_card_value($card, $settings)); ?></span>
                </div>
            <?php endforeach; ?>
        </div>

        <div class="shb-section">
            <h2 class="shb-section-title">Service controls</h2>
            <form method="post" class="shb-actions">
                <input type="hidden" name="csrf_token" value="<?php echo e($csrfToken); ?>">
                <button class="shb-button shb-button--primary" name="action" value="start">Start bridge</button>
                <button class="shb-button" name="action" value="restart">Restart bridge</button>
                <button class="shb-button" name="action" value="status">Refresh status</button>
                <button class="shb-button shb-button--danger" name="action" value="stop" onclick="return confirm('Stop the bridge service? Device updates will pause until it is started again.')">Stop bridge</button>
            </form>
        </div>

        <?php if (count($allowedDoorCommands) > 0): ?>
            <div class="shb-section">
                <h2 class="shb-section-title">Manual door control</h2>
                <p class="shb-warning"><strong>Safety:</strong> Keep the doorway in view and clear of animals before sending a movement command.</p>
                <form method="post" class="shb-actions">
                    <input type="hidden" name="csrf_token" value="<?php echo e($csrfToken); ?>">
                    <button class="shb-button shb-button--primary" name="door_command" value="open_door" onclick="return confirm('Open the chicken door now? Confirm the doorway is clear.')">Open door</button>
                    <button class="shb-button shb-button--danger" name="door_command" value="close_door" onclick="return confirm('Close the chicken door now? Confirm no animal is in the doorway.')">Close door</button>
                    <button class="shb-button" name="door_command" value="stop_door">Stop movement</button>
                    <button class="shb-button" name="door_command" value="get_door_state">Refresh state</button>
                    <input type="hidden" name="action" value="door-command">
                </form>
            </div>
        <?php endif; ?>

        <div class="shb-section">
            <h2 class="shb-section-title">Diagnostics</h2>
            <form method="post" class="shb-actions">
                <input type="hidden" name="csrf_token" value="<?php echo e($csrfToken); ?>">
                <?php foreach ($diagnosticActions as $action => $label): ?>
                    <button class="shb-button" name="action" value="<?php echo e($action); ?>"><?php echo e($label); ?></button>
                <?php endforeach; ?>
                <button class="shb-button" name="action" value="dump-config">Validate configuration</button>
            </form>
            <?php if (is_array($flash) && count($flash['output'] ?? array()) > 0 && $activeTab === 'status'): ?>
                <details>
                    <summary>Diagnostic details</summary>
                    <pre class="shb-output"><?php echo e(implode("\n", $flash['output'])); ?></pre>
                </details>
            <?php endif; ?>
        </div>
    </section>

    <section class="shb-panel" data-panel="settings"<?php echo $activeTab !== 'settings' ? ' hidden' : ''; ?>>
        <?php if (isset($webhookGuidance) && $webhookGuidance !== ''): ?><div class="shb-callout"><strong>Webhook HTTPS setup</strong><p><?php echo e($webhookGuidance); ?></p><p>Private listener: http://&lt;loxberry-ip&gt;:<?php echo e($settings['HTTP_PORT'] ?? '8080'); ?>/webhooks/omlet/door-state</p></div><?php endif; ?>
        <form method="post">
            <input type="hidden" name="csrf_token" value="<?php echo e($csrfToken); ?>">
            <input type="hidden" name="action" value="save-settings">
            <?php foreach (group_fields($fieldSchema) as $group => $fields): ?>
                <?php $advanced = in_array($group, array('MQTT', 'Advanced', 'Logging'), true); ?>
                <?php if ($advanced): ?><details class="shb-advanced"><summary><?php echo e($group); ?></summary><?php else: ?><div class="shb-section"><h2 class="shb-section-title"><?php echo e($group); ?></h2><?php endif; ?>
                <?php foreach ($fields as $key => $field): ?>
                    <?php $error = $flash['errors'][$key] ?? ''; $inputId = 'field-' . strtolower(str_replace('_', '-', $key)); ?>
                    <div class="shb-form-row">
                        <label class="shb-label" for="<?php echo e($inputId); ?>"><?php echo e($field['label']); ?></label>
                        <div class="shb-control">
                            <?php if (($field['type'] ?? '') === 'toggle'): ?>
                                <input type="hidden" name="<?php echo e($key); ?>" value="false">
                                <label class="shb-toggle"><input id="<?php echo e($inputId); ?>" type="checkbox" name="<?php echo e($key); ?>" value="true"<?php echo ($settings[$key] ?? '') === 'true' ? ' checked' : ''; ?>><span>Enabled</span></label>
                            <?php elseif (($field['type'] ?? '') === 'select'): ?>
                                <select id="<?php echo e($inputId); ?>" name="<?php echo e($key); ?>">
                                    <?php foreach ($field['options'] as $value => $label): ?><option value="<?php echo e($value); ?>"<?php echo ($settings[$key] ?? '') === (string) $value ? ' selected' : ''; ?>><?php echo e($label); ?></option><?php endforeach; ?>
                                </select>
                            <?php else: ?>
                                <input id="<?php echo e($inputId); ?>" name="<?php echo e($key); ?>" type="<?php echo ($field['sensitive'] ?? false) ? 'password' : (($field['type'] ?? '') === 'number' ? 'number' : (($field['type'] ?? '') === 'url' ? 'url' : 'text')); ?>" value="<?php echo ($field['sensitive'] ?? false) ? '' : e($settings[$key] ?? ''); ?>"<?php echo isset($field['min']) ? ' min="' . (int) $field['min'] . '"' : ''; ?><?php echo isset($field['max']) ? ' max="' . (int) $field['max'] . '"' : ''; ?><?php echo ($field['required'] ?? false) && !($field['sensitive'] ?? false) ? ' required' : ''; ?><?php echo $error !== '' ? ' aria-invalid="true" aria-describedby="error-' . e($inputId) . '"' : ''; ?> autocomplete="<?php echo ($field['sensitive'] ?? false) ? 'new-password' : 'off'; ?>" placeholder="<?php echo e(($field['sensitive'] ?? false) ? 'Leave blank to keep the existing value' : ($field['placeholder'] ?? '')); ?>">
                            <?php endif; ?>
                            <p class="shb-help"><?php echo e($field['help']); ?></p>
                            <?php if ($error !== ''): ?><p class="shb-error" id="error-<?php echo e($inputId); ?>"><?php echo e($error); ?></p><?php endif; ?>
                        </div>
                        <button class="shb-help-button" type="button" title="<?php echo e($field['help']); ?>" aria-label="Help for <?php echo e($field['label']); ?>">?</button>
                    </div>
                <?php endforeach; ?>
                <?php if ($advanced): ?></details><?php else: ?></div><?php endif; ?>
            <?php endforeach; ?>
            <div class="shb-form-actions"><button class="shb-button shb-button--primary" type="submit">Save settings</button></div>
        </form>
    </section>

    <section class="shb-panel" data-panel="log"<?php echo $activeTab !== 'log' ? ' hidden' : ''; ?>>
        <div class="shb-log-meta">
            <div><h2 class="shb-section-title">Bridge log</h2><p>Last file update: <?php echo e($lastLogUpdate); ?></p></div>
            <form method="post"><input type="hidden" name="csrf_token" value="<?php echo e($csrfToken); ?>"><button class="shb-button shb-button--primary" name="action" value="log-tail">Refresh log</button></form>
        </div>
        <?php $logOutput = is_array($flash) && $activeTab === 'log' ? ($flash['output'] ?? array()) : read_log_tail($logFile); ?>
        <pre class="shb-output"><?php echo e(implode("\n", redact_output($logOutput, $fieldSchema))); ?></pre>
    </section>
</main>

<script>
(function () {
    var tabs = document.querySelectorAll('[data-tab]');
    var panels = document.querySelectorAll('[data-panel]');
    tabs.forEach(function (tab) {
        tab.addEventListener('click', function (event) {
            if (!window.history || !window.history.replaceState) return;
            event.preventDefault();
            var target = tab.getAttribute('data-tab');
            tabs.forEach(function (item) {
                var active = item === tab;
                item.classList.toggle('is-active', active);
                item.setAttribute('aria-current', active ? 'page' : 'false');
            });
            panels.forEach(function (panel) { panel.hidden = panel.getAttribute('data-panel') !== target; });
            window.history.replaceState({}, '', '?tab=' + encodeURIComponent(target));
        });
    });
}());
</script>
<?php
if ($loxberryUi) {
    LBWeb::lbfooter();
} else {
    echo '</body></html>';
}

function status_card_value($card, $settings) {
    if (isset($card['setting'])) {
        $value = $settings[$card['setting']] ?? '';
        if (($card['kind'] ?? '') === 'toggle') {
            return $value === 'true' ? 'Enabled' : 'Disabled';
        }
        if (($card['kind'] ?? '') === 'configured') {
            return $value !== '' ? 'Configured' : 'Setup required';
        }
    }
    return $card['value'] ?? 'Awaiting telemetry';
}

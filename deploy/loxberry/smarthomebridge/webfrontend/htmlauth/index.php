<?php
$allowed = array('start', 'stop', 'restart', 'status', 'dump-config');
$command = $_POST['command'] ?? 'status';
if (!in_array($command, $allowed, true)) {
    http_response_code(400);
    exit('Invalid command');
}

$script = getenv('LBPBIN') . '/bridge_ctl.sh';
$output = array();
$exitCode = 0;
exec(escapeshellcmd($script) . ' ' . escapeshellarg($command), $output, $exitCode);
?>
<!doctype html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <title>SmartHomeBridge</title>
</head>
<body>
    <h1>SmartHomeBridge</h1>
    <form method="post">
        <button name="command" value="status">Status</button>
        <button name="command" value="start">Start</button>
        <button name="command" value="stop">Stop</button>
        <button name="command" value="restart">Restart</button>
        <button name="command" value="dump-config">Config Check</button>
    </form>
    <pre><?php echo htmlspecialchars(implode("\n", $output), ENT_QUOTES, 'UTF-8'); ?></pre>
    <?php if ($exitCode !== 0): ?>
        <p>Command exited with code <?php echo (int) $exitCode; ?></p>
    <?php endif; ?>
</body>
</html>

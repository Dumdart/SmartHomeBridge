#include <Arduino.h>
#include <WebServer.h>
#include <WiFi.h>
#include <esp_camera.h>
#include <cstdarg>

#if __has_include("secrets.h")
#include "secrets.h"
#endif

#ifndef WIFI_SSID
#define WIFI_SSID ""
#endif

#ifndef WIFI_PASSWORD
#define WIFI_PASSWORD ""
#endif

#ifndef CAMERA_HOSTNAME
#define CAMERA_HOSTNAME "chicken-barn-esp32cam"
#endif

#ifndef CAMERA_FRAME_SIZE
#define CAMERA_FRAME_SIZE FRAMESIZE_VGA
#endif

#ifndef CAMERA_JPEG_QUALITY
#define CAMERA_JPEG_QUALITY 12
#endif

constexpr uint32_t serial_baud = 115200;
constexpr int8_t serial_rx_pin = 3;
constexpr int8_t serial_tx_pin = 1;
constexpr uint32_t wifi_connect_timeout_ms = 30000;
constexpr uint32_t serial_heartbeat_interval_ms = 5000;
constexpr uint16_t http_port = 80;

WebServer server(http_port);

bool camera_ready = false;
uint32_t failed_capture_count = 0;
uint32_t last_serial_heartbeat_ms = 0;

void serial_println(const char *message) {
  Serial.println(message);
  Serial.flush();
}

void serial_printf(const char *format, ...) {
  char buffer[192];
  va_list args;
  va_start(args, format);
  vsnprintf(buffer, sizeof(buffer), format, args);
  va_end(args);

  Serial.print(buffer);
  Serial.flush();
}

camera_config_t camera_config() {
  camera_config_t config;
  config.ledc_channel = LEDC_CHANNEL_0;
  config.ledc_timer = LEDC_TIMER_0;
  config.pin_d0 = 5;
  config.pin_d1 = 18;
  config.pin_d2 = 19;
  config.pin_d3 = 21;
  config.pin_d4 = 36;
  config.pin_d5 = 39;
  config.pin_d6 = 34;
  config.pin_d7 = 35;
  config.pin_xclk = 0;
  config.pin_pclk = 22;
  config.pin_vsync = 25;
  config.pin_href = 23;
  config.pin_sccb_sda = 26;
  config.pin_sccb_scl = 27;
  config.pin_pwdn = 32;
  config.pin_reset = -1;
  config.xclk_freq_hz = 20000000;
  config.pixel_format = PIXFORMAT_JPEG;
  config.frame_size = CAMERA_FRAME_SIZE;
  config.jpeg_quality = CAMERA_JPEG_QUALITY;
  config.fb_count = psramFound() ? 2 : 1;
  config.fb_location = psramFound() ? CAMERA_FB_IN_PSRAM : CAMERA_FB_IN_DRAM;
  config.grab_mode = CAMERA_GRAB_LATEST;

  return config;
}

void send_text(int status_code, const String &body) {
  server.send(status_code, "text/plain; charset=utf-8", body);
}

void handle_root() {
  send_text(200, "ESP32-CAM chicken barn camera. Use GET /jpg for the latest JPEG frame.\n");
}

void handle_health() {
  const String ip = WiFi.localIP().toString();
  const String payload =
      String("{\"status\":\"ok\",\"camera_ready\":") + (camera_ready ? "true" : "false") +
      ",\"wifi_connected\":" + (WiFi.isConnected() ? "true" : "false") +
      ",\"ip\":\"" + ip +
      "\",\"failed_capture_count\":" + String(failed_capture_count) + "}";

  server.send(camera_ready && WiFi.isConnected() ? 200 : 503, "application/json", payload);
}

void handle_jpg() {
  if (!camera_ready) {
    send_text(503, "camera not ready\n");
    return;
  }

  camera_fb_t *frame = esp_camera_fb_get();
  if (frame == nullptr) {
    failed_capture_count++;
    send_text(503, "camera capture failed\n");
    return;
  }

  server.sendHeader("Cache-Control", "no-store");
  server.setContentLength(frame->len);
  server.send(200, "image/jpeg", "");

  WiFiClient client = server.client();
  client.write(frame->buf, frame->len);
  esp_camera_fb_return(frame);
}

void handle_not_found() {
  send_text(404, "not found\n");
}

bool has_wifi_credentials() {
  return strlen(WIFI_SSID) > 0;
}

const char *wifi_status_text(wl_status_t status) {
  switch (status) {
    case WL_IDLE_STATUS:
      return "idle";
    case WL_NO_SSID_AVAIL:
      return "ssid_not_available";
    case WL_SCAN_COMPLETED:
      return "scan_completed";
    case WL_CONNECTED:
      return "connected";
    case WL_CONNECT_FAILED:
      return "connect_failed";
    case WL_CONNECTION_LOST:
      return "connection_lost";
    case WL_DISCONNECTED:
      return "disconnected";
    default:
      return "unknown";
  }
}

void connect_wifi() {
  if (!has_wifi_credentials()) {
    serial_println("Missing Wi-Fi credentials. Define WIFI_SSID and WIFI_PASSWORD in include/secrets.h.");
    return;
  }

  WiFi.mode(WIFI_STA);
  WiFi.setHostname(CAMERA_HOSTNAME);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

  serial_println("Connecting to configured Wi-Fi.");
  const uint32_t started_ms = millis();
  uint32_t attempt_count = 0;
  while (WiFi.status() != WL_CONNECTED && millis() - started_ms < wifi_connect_timeout_ms) {
    delay(500);
    attempt_count++;
    const uint32_t elapsed_ms = millis() - started_ms;
    const wl_status_t current_status = WiFi.status();
    serial_printf(
        "Wi-Fi attempt %lu: elapsed_ms=%lu status=%s\n",
        static_cast<unsigned long>(attempt_count),
        static_cast<unsigned long>(elapsed_ms),
        wifi_status_text(current_status));
  }

  if (WiFi.status() != WL_CONNECTED) {
    serial_printf("Wi-Fi connection failed. final_status=%s\n", wifi_status_text(WiFi.status()));
    return;
  }

  serial_printf(
      "Wi-Fi connected. ip=%s rssi_dbm=%ld Camera API: http://%s/jpg\n",
      WiFi.localIP().toString().c_str(),
      static_cast<long>(WiFi.RSSI()),
      WiFi.localIP().toString().c_str());
}

void configure_routes() {
  server.on("/", HTTP_GET, handle_root);
  server.on("/health", HTTP_GET, handle_health);
  server.on("/jpg", HTTP_GET, handle_jpg);
  server.onNotFound(handle_not_found);
  server.begin();
  serial_printf("HTTP server started on port %u.\n", http_port);
}

void print_serial_heartbeat() {
  const uint32_t now = millis();
  if (now - last_serial_heartbeat_ms < serial_heartbeat_interval_ms) {
    return;
  }

  last_serial_heartbeat_ms = now;
  serial_printf(
      "ESP32-CAM heartbeat: uptime_ms=%lu camera_ready=%s wifi_status=%s ip=%s failed_capture_count=%lu\n",
      static_cast<unsigned long>(now),
      camera_ready ? "true" : "false",
      wifi_status_text(WiFi.status()),
      WiFi.localIP().toString().c_str(),
      static_cast<unsigned long>(failed_capture_count));
}

void setup() {
  Serial.begin(serial_baud, SERIAL_8N1, serial_rx_pin, serial_tx_pin);
  Serial.setDebugOutput(true);
  delay(1500);
  serial_println("");
  serial_println("Serial ready at 115200 baud on UART0 RX=3 TX=1.");
  serial_println("Booting ESP32-CAM chicken barn camera.");

  camera_config_t config = camera_config();
  esp_err_t camera_status = esp_camera_init(&config);
  if (camera_status != ESP_OK) {
    serial_printf("Camera init failed: 0x%x\n", camera_status);
  } else {
    camera_ready = true;
    serial_println("Camera initialized.");
  }

  connect_wifi();
  configure_routes();
}

void loop() {
  server.handleClient();
  print_serial_heartbeat();
}

# ESP32-CAM Chicken Barn Camera

This PlatformIO firmware exposes a simple JPEG snapshot API for image inference.

## Configure Wi-Fi

Copy `include/secrets.example.h` to `include/secrets.h` and set the local Wi-Fi values
and camera bearer token.
`include/secrets.h` is ignored by Git and must not be committed.

## Build and upload

```powershell
pio run -e esp32cam
pio run -e esp32cam -t upload
pio device monitor -e esp32cam
```

## API

- `GET /jpg` returns the latest camera frame as `image/jpeg`.
- `GET /health` returns Wi-Fi, camera, IP address, and failed capture status as JSON.
- `GET /` returns a short text description.

`/jpg` and `/health` require an `Authorization: Bearer <CAMERA_AUTH_TOKEN>` header.
The firmware returns `503` when `CAMERA_AUTH_TOKEN` is not configured.

After the device connects, the serial monitor prints the camera URL, for example:

```text
Camera API: http://192.168.1.42/jpg
```

Use that `/jpg` URL as the image source for the chicken threat inference process.

# Web Nanny

Web Nanny is a lightweight browser-based baby monitor with WebRTC audio streaming and cry detection.

## Features

- Real-time audio streaming using WebRTC
- One sender and one listener
- Cry detection on the listener side
- Local HTTPS/WSS support
- Optional bearer auth for signaling and web pages
- Reconnect-friendly session handling with keep-alive support
- Docker support for Raspberry Pi / NAS deployment

## What's new (recent)

- Automatic TLS certificate generation at startup when TLS is enabled and no cert files are present (no host-mounted certs required for Docker). (commit: Add automatic TLS certificate generation and simplify Docker onboarding)
- Improved wake-lock and playback resilience to better support screen-off sender/listener behavior (commit: Improve wake-lock and playback resilience for screen-off transmission)
- Health check and metrics endpoints plus startup validation. (commit: Add health check and metrics endpoints with startup validation)
- Session-management, optional bearer auth, and reconnect-friendly behavior. (commit: Enhance WebSocket functionality with session management, authentication, and environment variable configuration)

## Local setup

### Requirements

- Python 3.11+
- Docker (optional, recommended for Raspberry Pi)
- Modern browser with WebRTC support

### Run locally with Python

1. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # or venv\Scripts\activate on Windows
   pip install -r requirements.txt
   ```

2. Configure optional environment variables for the local process:
   ```bash
   export PORT=8001
   export TLS_ENABLED=true
   export TLS_CERTFILE=cert.pem
   export TLS_KEYFILE=key.pem
   export AUTH_ENABLED=false
   export AUTH_TOKEN=your-secret-token
   export RECONNECT_GRACE_SECONDS=30
   export CLEANUP_INTERVAL_SECONDS=60
   ```
   On Windows PowerShell use `setx` or `$env:PORT = 8001` for the current session.

3. Generate self-signed certificates if you want local HTTPS/WSS:
   ```bash
   openssl req -x509 -newkey rsa:4096 -keyout key.pem -out cert.pem -days 365 -nodes \
     -subj "/C=PL/ST=Warsaw/L=Warsaw/O=WebNanny/CN=localhost"
   ```

4. Start the server:
   ```bash
   python main.py
   ```

5. Open in browser:
   - `https://<host>:8001/sender`
   - `https://<host>:8001/listener`

### Run with Docker

1. Create a `.env` file from `.env.example` and update values as needed:
   ```bash
   cp .env.example .env
   ```
   On Windows PowerShell:
   ```powershell
   Copy-Item .env.example .env
   ```

2. TLS and certificates in Docker

- If `TLS_ENABLED=true` and no certificate files are present, the app will auto-generate a self-signed `cert.pem` and `key.pem` at container startup (the container image includes the runtime dependency to generate certs).
- You do not need to mount host certificate files into the container for basic testing.
- To use custom certs, put your `cert.pem` and `key.pem` in the project root before running Docker and set `TLS_CERTFILE` / `TLS_KEYFILE` in `.env`.

3. Build the image:
   ```bash
   docker build -t web_nanny .
   ```

4. Start the container:
   ```bash
   docker-compose up -d
   ```

5. Open in browser:
   - `https://<host>:8001/sender`
   - `https://<host>:8001/listener`

## Usage Workflow

1. Access the homepage at `https://<host>:8001`.
2. Select your preferred language (Polish or English).
3. Choose your role: Sender (to broadcast audio) or Listener (to receive and monitor audio with cry detection).
4. Follow the on-screen instructions to start/stop audio streaming.

## Notes

- Do not commit `cert.pem`, `key.pem` or other secret files.
- This project is intended for trusted local networks.
- For production, use valid TLS certificates and add authentication.

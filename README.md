# Web Nanny

Web Nanny is a lightweight browser-based baby monitor with WebRTC audio streaming and cry detection.

## Features

- Real-time audio streaming using WebRTC
- One sender and one listener
- Cry detection on the listener side
- Local HTTPS/WSS support
- Docker support for Raspberry Pi / NAS deployment

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

2. Generate self-signed certificates:
   ```bash
   openssl req -x509 -newkey rsa:4096 -keyout key.pem -out cert.pem -days 365 -nodes \
     -subj "/C=PL/ST=Warsaw/L=Warsaw/O=WebNanny/CN=localhost"
   ```

3. Start the server:
   ```bash
   python main.py
   ```

4. Open in browser:
   - `https://<host>:2137/sender`
   - `https://<host>:2137/listener`

### Run with Docker

1. Build the image:
   ```bash
   docker build -t web_nanny .
   ```

2. Start the container:
   ```bash
   docker-compose up -d
   ```

3. Open in browser:
   - `https://<raspi-ip>:2137/sender`
   - `https://<raspi-ip>:2137/listener`

## Notes

- Do not commit `cert.pem`, `key.pem` or other secret files.
- This project is intended for trusted local networks.
- For production, use valid TLS certificates and add authentication.

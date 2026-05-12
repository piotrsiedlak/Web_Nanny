FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY main.py ./
COPY templates ./templates
COPY cert.pem ./cert.pem
COPY key.pem ./key.pem

EXPOSE 2137

CMD ["python", "main.py"]

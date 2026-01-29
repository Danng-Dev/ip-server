# 🌐 IP Address Service

A simple Docker-hostable Flask application that exposes IP address information via HTTP endpoints. Perfect for container debugging, network diagnostics, and service discovery.

![Python](https://img.shields.io/badge/Python-3.11-blue)
![Flask](https://img.shields.io/badge/Flask-2.3-green)
![Docker](https://img.shields.io/badge/Docker-Ready-blue)
![License](https://img.shields.io/badge/License-MIT-yellow)

## ✨ Features

- 🔍 **IP Discovery** - Multiple methods to detect container/host IP addresses
- 📊 **JSON & Plain Text** - Multiple output formats
- 🐳 **Docker Ready** - Pre-configured Dockerfile and docker-compose
- 🏥 **Health Checks** - Built-in health check endpoint
- 📋 **Request Info** - Inspect incoming request details
- 📈 **System Metrics** - CPU, memory, and disk usage
- 🔧 **Configurable** - Environment variable configuration
- 📝 **Logging** - Structured logging with configurable levels

## 🚀 Quick Start

### Using Docker Compose

~~~bash
git clone <your-repo>
cd ip-app
docker-compose up -d

curl http://localhost:5252
~~~

### Using Docker

~~~bash
docker build -t ip-app .
docker run -p 5252:5252 ip-app
~~~

### Local Development

~~~bash
pip install -r requirements.txt
python app.py
~~~

## 📡 API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Returns IP addresses (plain text, like `hostname -I`) |
| `/json` | GET | Returns IP addresses and hostname as JSON |
| `/health` | GET | Health check endpoint |
| `/request-info` | GET | Information about the incoming request |
| `/metrics` | GET | System metrics (CPU, memory, disk) |
| `/config` | GET | Current configuration settings |

## 📖 Usage Examples

### Get IP Addresses

~~~bash
# Plain text
curl http://localhost:5252/
# Output: 172.20.0.2

# JSON format
curl http://localhost:5252/json
# Output: {"hostname":"abc123","ip_addresses":["172.20.0.2"]}
~~~

### Health Check

~~~bash
curl http://localhost:5252/health
# Output: {"status":"healthy","timestamp":"2024-01-15T10:30:00"}
~~~

### Request Information

~~~bash
curl http://localhost:5252/request-info
~~~

**Output:**
~~~json
{
  "remote_addr": "172.20.0.1",
  "user_agent": "curl/7.68.0",
  "method": "GET",
  "headers": {
    "Host": "localhost:5252",
    "User-Agent": "curl/7.68.0",
    "Accept": "*/*"
  }
}
~~~

### System Metrics

~~~bash
curl http://localhost:5252/metrics
~~~

**Output:**
~~~json
{
  "cpu_percent": 2.5,
  "memory_percent": 15.3,
  "memory_used_mb": 156.2,
  "memory_total_mb": 1024.0,
  "disk_percent": 45.2,
  "disk_free_gb": 15.3,
  "uptime_seconds": 3600
}
~~~

## ⚙️ Configuration

Configure via environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `PORT` | `5252` | HTTP server port |
| `LOG_LEVEL` | `INFO` | Logging level (DEBUG, INFO, WARNING, ERROR) |
| `APP_NAME` | `ip-service` | Application name in logs |
| `SHOW_LOCALHOST_IPS` | `false` | Include localhost (127.x.x.x) IPs |
| `CORS_ENABLED` | `true` | Enable CORS headers |

### Example with Custom Config

~~~bash
docker run -p 8080:8080 \
  -e PORT=8080 \
  -e LOG_LEVEL=DEBUG \
  -e APP_NAME=my-ip-service \
  ip-app
~~~

## 🐳 Docker Compose Example

~~~yaml
version: '3.8'

services:
  ip-app:
    build: .
    ports:
      - "5252:5252"
    environment:
      - PORT=5252
      - LOG_LEVEL=INFO
      - SHOW_LOCALHOST_IPS=false
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:5252/health"]
      interval: 30s
      timeout: 10s
      retries: 3
~~~

## 🔧 Development

### Project Structure

~~~
ip-app/
├── app.py              # Main application
├── requirements.txt    # Python dependencies
├── Dockerfile          # Docker configuration
├── docker-compose.yml  # Docker Compose setup
└── README.md          # This file
~~~

### Running Tests

~~~bash
pip install pytest
pytest
~~~

### Building Locally

~~~bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run app
python app.py
~~~

## 🌟 Use Cases

- **Container Debugging** - Quickly check container IP assignments
- **Load Balancer Testing** - Verify which backend serves the request
- **Service Discovery** - Simple IP discovery in microservices
- **Network Diagnostics** - Troubleshoot network configuration
- **K8s Debugging** - Check pod IPs and networking

## 📝 Example Output

~~~bash
$ curl -s http://localhost:5252/json | jq .
{
  "hostname": "ip-app-7d9f4b8c5-xv2p4",
  "ip_addresses": [
    "10.244.1.15",
    "10.244.1.16"
  ],
  "timestamp": "2024-01-15T10:30:00",
  "version": "1.0.0"
}
~~~

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- Built with [Flask](https://flask.palletsprojects.com/)
- Inspired by the need for simple IP discovery in containerized environments

---

**Made with ❤️ for the DevOps community by DanngDev**

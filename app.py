"""
IP Address Service - A simple Flask app for IP discovery in containers
"""

from flask import Flask, jsonify, request, Response
from flask_cors import CORS
import socket
import os
import subprocess
import logging
import sys
from datetime import datetime
from functools import wraps

# Try to import psutil for metrics
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

app = Flask(__name__)

# Configuration
PORT = int(os.environ.get('PORT', 5252))
LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO').upper()
APP_NAME = os.environ.get('APP_NAME', 'ip-service')
SHOW_LOCALHOST_IPS = os.environ.get('SHOW_LOCALHOST_IPS', 'false').lower() == 'true'
CORS_ENABLED = os.environ.get('CORS_ENABLED', 'true').lower() == 'true'
VERSION = '1.0.0'

# Enable CORS if configured
if CORS_ENABLED:
    CORS(app)

# Setup logging
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(APP_NAME)

# Track startup time for uptime calculation
START_TIME = datetime.now()


def log_request(f):
    """Decorator to log incoming requests"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        logger.info(f"{request.method} {request.path} - {request.remote_addr}")
        return f(*args, **kwargs)
    return decorated_function


def get_ip_addresses():
    """Get all IP addresses similar to hostname -I"""
    ip_addresses = []
    
    # Method 1: Try to get from socket
    try:
        hostname = socket.gethostname()
        ips = socket.getaddrinfo(hostname, None)
        for ip in ips:
            ip_addr = ip[4][0]
            # Filter for IPv4 addresses
            is_localhost = ip_addr.startswith('127.')
            is_ipv6 = ':' in ip_addr
            
            if SHOW_LOCALHOST_IPS or (not is_localhost and not is_ipv6):
                if ip_addr not in ip_addresses:
                    ip_addresses.append(ip_addr)
    except Exception as e:
        logger.debug(f"Socket method failed: {e}")
    
    # Method 2: Use socket to get primary IP
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0)
        try:
            s.connect(('10.254.254.254', 1))
            primary_ip = s.getsockname()[0]
            if primary_ip not in ip_addresses:
                if SHOW_LOCALHOST_IPS or not primary_ip.startswith('127.'):
                    ip_addresses.insert(0, primary_ip)
        except Exception as e:
            logger.debug(f"Primary IP detection failed: {e}")
        finally:
            s.close()
    except Exception as e:
        logger.debug(f"Socket creation failed: {e}")
    
    # Method 3: Use hostname command (works in Linux containers)
    try:
        result = subprocess.run(['hostname', '-I'], capture_output=True, text=True)
        if result.returncode == 0:
            ips = result.stdout.strip().split()
            for ip in ips:
                if ip not in ip_addresses:
                    if SHOW_LOCALHOST_IPS or not ip.startswith('127.'):
                        ip_addresses.append(ip)
    except Exception as e:
        logger.debug(f"Hostname command failed: {e}")
    
    return ip_addresses


def get_system_metrics():
    """Get system metrics if psutil is available"""
    metrics = {
        'uptime_seconds': int((datetime.now() - START_TIME).total_seconds()),
        'psutil_available': PSUTIL_AVAILABLE
    }
    
    if PSUTIL_AVAILABLE:
        try:
            # CPU metrics
            metrics['cpu_percent'] = psutil.cpu_percent(interval=0.1)
            metrics['cpu_count'] = psutil.cpu_count()
            
            # Memory metrics
            memory = psutil.virtual_memory()
            metrics['memory_percent'] = memory.percent
            metrics['memory_used_mb'] = round(memory.used / (1024 * 1024), 2)
            metrics['memory_total_mb'] = round(memory.total / (1024 * 1024), 2)
            metrics['memory_available_mb'] = round(memory.available / (1024 * 1024), 2)
            
            # Disk metrics
            disk = psutil.disk_usage('/')
            metrics['disk_percent'] = disk.percent
            metrics['disk_used_gb'] = round(disk.used / (1024 ** 3), 2)
            metrics['disk_free_gb'] = round(disk.free / (1024 ** 3), 2)
            metrics['disk_total_gb'] = round(disk.total / (1024 ** 3), 2)
            
            # Network metrics
            net_io = psutil.net_io_counters()
            metrics['network_bytes_sent'] = net_io.bytes_sent
            metrics['network_bytes_recv'] = net_io.bytes_recv
            
        except Exception as e:
            logger.error(f"Error getting system metrics: {e}")
            metrics['error'] = str(e)
    
    return metrics


@app.route('/')
@log_request
def index():
    """Return IP addresses like hostname -I"""
    ips = get_ip_addresses()
    ip_string = ' '.join(ips) if ips else 'No IP addresses found'
    return Response(ip_string + '\n', mimetype='text/plain')


@app.route('/json')
@log_request
def json_endpoint():
    """Return IP addresses as JSON"""
    ips = get_ip_addresses()
    return jsonify({
        'hostname': socket.gethostname(),
        'ip_addresses': ips,
        'timestamp': datetime.now().isoformat(),
        'version': VERSION
    })


@app.route('/health')
@log_request
def health():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'app_name': APP_NAME,
        'version': VERSION
    })


@app.route('/request-info')
@log_request
def request_info():
    """Return information about the incoming request"""
    headers = dict(request.headers)
    
    return jsonify({
        'remote_addr': request.remote_addr,
        'remote_port': request.environ.get('REMOTE_PORT'),
        'user_agent': request.user_agent.string,
        'method': request.method,
        'path': request.path,
        'url': request.url,
        'scheme': request.scheme,
        'is_secure': request.is_secure,
        'content_type': request.content_type,
        'content_length': request.content_length,
        'headers': headers,
        'timestamp': datetime.now().isoformat()
    })


@app.route('/metrics')
@log_request
def metrics():
    """Return system metrics"""
    return jsonify({
        'timestamp': datetime.now().isoformat(),
        'metrics': get_system_metrics()
    })


@app.route('/config')
@log_request
def config():
    """Return current configuration (safe values only)"""
    return jsonify({
        'app_name': APP_NAME,
        'version': VERSION,
        'port': PORT,
        'log_level': LOG_LEVEL,
        'cors_enabled': CORS_ENABLED,
        'show_localhost_ips': SHOW_LOCALHOST_IPS,
        'python_version': sys.version,
        'hostname': socket.gethostname()
    })


@app.route('/all')
@log_request
def all_info():
    """Return all information in one endpoint"""
    return jsonify({
        'hostname': socket.gethostname(),
        'ip_addresses': get_ip_addresses(),
        'request': {
            'remote_addr': request.remote_addr,
            'user_agent': request.user_agent.string,
            'method': request.method
        },
        'metrics': get_system_metrics(),
        'config': {
            'app_name': APP_NAME,
            'version': VERSION,
            'port': PORT
        },
        'timestamp': datetime.now().isoformat(),
        'version': VERSION
    })


@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors"""
    logger.warning(f"404 error: {request.path}")
    return jsonify({
        'error': 'Not found',
        'path': request.path,
        'timestamp': datetime.now().isoformat()
    }), 404


@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    logger.error(f"500 error: {str(error)}")
    return jsonify({
        'error': 'Internal server error',
        'timestamp': datetime.now().isoformat()
    }), 500


if __name__ == '__main__':
    logger.info(f"Starting {APP_NAME} v{VERSION} on port {PORT}")
    logger.info(f"Log level: {LOG_LEVEL}")
    logger.info(f"CORS enabled: {CORS_ENABLED}")
    
    if not PSUTIL_AVAILABLE:
        logger.warning("psutil not installed - system metrics will be limited")
        logger.info("Install psutil for full metrics: pip install psutil")
    
    app.run(host='0.0.0.0', port=PORT, debug=False)

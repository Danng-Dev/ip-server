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
    
    # Method 1: Use hostname -I (BEST method - gets all interface IPs like 'hostname -I')
    try:
        result = subprocess.run(['hostname', '-I'], capture_output=True, text=True)
        if result.returncode == 0 and result.stdout.strip():
            ips = result.stdout.strip().split()
            logger.debug(f"hostname -I output: {ips}")
            for ip in ips:
                # Filter localhost IPs unless configured to show them
                is_localhost = ip.startswith('127.')
                is_ipv6 = ':' in ip
                
                if SHOW_LOCALHOST_IPS or (not is_localhost and not is_ipv6):
                    if ip not in ip_addresses:
                        ip_addresses.append(ip)
            logger.debug(f"IPs from hostname -I: {ip_addresses}")
            # If we got IPs this way, return them immediately (most reliable)
            if ip_addresses:
                return ip_addresses
    except Exception as e:
        logger.debug(f"Hostname -I command failed: {e}")
    
    # Method 2: Try using 'ip addr' command
    try:
        result = subprocess.run(['ip', '-4', 'addr', 'show'], capture_output=True, text=True)
        if result.returncode == 0:
            import re
            # Extract IP addresses from 'ip addr' output
            ip_pattern = re.compile(r'inet\s+(\d+\.\d+\.\d+\.\d+)')
            found_ips = ip_pattern.findall(result.stdout)
            logger.debug(f"ip addr output IPs: {found_ips}")
            for ip in found_ips:
                if SHOW_LOCALHOST_IPS or not ip.startswith('127.'):
                    if ip not in ip_addresses:
                        ip_addresses.append(ip)
    except Exception as e:
        logger.debug(f"ip addr command failed: {e}")
    
    # Method 3: Use psutil if available (very reliable)
    if PSUTIL_AVAILABLE:
        try:
            import psutil
            interfaces = psutil.net_if_addrs()
            for interface_name, addresses in interfaces.items():
                for addr in addresses:
                    if addr.family == socket.AF_INET:  # IPv4 only
                        ip = addr.address
                        if SHOW_LOCALHOST_IPS or not ip.startswith('127.'):
                            if ip not in ip_addresses:
                                ip_addresses.append(ip)
            logger.debug(f"IPs from psutil: {ip_addresses}")
        except Exception as e:
            logger.debug(f"psutil method failed: {e}")
    
    # Method 4: Fallback to socket.getaddrinfo (hostname resolution)
    if not ip_addresses:
        try:
            hostname = socket.gethostname()
            ips = socket.getaddrinfo(hostname, None)
            for ip in ips:
                ip_addr = ip[4][0]
                is_localhost = ip_addr.startswith('127.')
                is_ipv6 = ':' in ip_addr
                
                if SHOW_LOCALHOST_IPS or (not is_localhost and not is_ipv6):
                    if ip_addr not in ip_addresses:
                        ip_addresses.append(ip_addr)
        except Exception as e:
            logger.debug(f"Socket getaddrinfo failed: {e}")
    
    # Method 5: Last resort - try to get default route IP
    if not ip_addresses:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.settimeout(0)
            try:
                s.connect(('10.254.254.254', 1))
                primary_ip = s.getsockname()[0]
                if SHOW_LOCALHOST_IPS or not primary_ip.startswith('127.'):
                    if primary_ip not in ip_addresses:
                        ip_addresses.append(primary_ip)
            except Exception:
                pass
            finally:
                s.close()
        except Exception as e:
            logger.debug(f"Default route IP detection failed: {e}")
    
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


def get_network_interfaces():
    """Get detailed network interface information"""
    interfaces = {}
    
    # Method 1: Use psutil for detailed interface info
    if PSUTIL_AVAILABLE:
        try:
            import psutil
            iface_addrs = psutil.net_if_addrs()
            iface_stats = psutil.net_if_stats()
            
            for iface_name, addrs in iface_addrs.items():
                iface_info = {
                    'name': iface_name,
                    'is_up': iface_stats.get(iface_name, {}).isup if iface_name in iface_stats else None,
                    'addresses': []
                }
                
                for addr in addrs:
                    addr_info = {
                        'address': addr.address,
                        'family': str(addr.family),
                        'is_ipv4': addr.family == socket.AF_INET,
                        'is_ipv6': addr.family == socket.AF_INET6,
                        'is_localhost': addr.address.startswith('127.') or addr.address == '::1'
                    }
                    if hasattr(addr, 'netmask'):
                        addr_info['netmask'] = addr.netmask
                    if hasattr(addr, 'broadcast'):
                        addr_info['broadcast'] = addr.broadcast
                        
                    iface_info['addresses'].append(addr_info)
                
                interfaces[iface_name] = iface_info
        except Exception as e:
            logger.debug(f"psutil interface detection failed: {e}")
    
    # Method 2: Parse /proc/net/dev for Linux
    if not interfaces and os.path.exists('/proc/net/dev'):
        try:
            with open('/proc/net/dev', 'r') as f:
                for line in f:
                    if ':' in line and not line.strip().startswith('Inter-'):
                        iface_name = line.split(':')[0].strip()
                        if iface_name != 'lo':
                            interfaces[iface_name] = {'name': iface_name, 'is_up': True, 'addresses': []}
        except Exception as e:
            logger.debug(f"/proc/net/dev parsing failed: {e}")
    
    return interfaces


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
        'count': len(ips),
        'timestamp': datetime.now().isoformat(),
        'version': VERSION
    })


@app.route('/interfaces')
@log_request
def interfaces_endpoint():
    """Return detailed network interface information"""
    interfaces = get_network_interfaces()
    ips = get_ip_addresses()
    
    # Also get raw hostname -I output for comparison
    hostname_i_output = None
    try:
        result = subprocess.run(['hostname', '-I'], capture_output=True, text=True)
        if result.returncode == 0:
            hostname_i_output = result.stdout.strip()
    except:
        pass
    
    return jsonify({
        'hostname': socket.gethostname(),
        'ip_addresses': ips,
        'ip_count': len(ips),
        'hostname_i_raw': hostname_i_output,
        'interfaces': interfaces,
        'show_localhost_ips_config': SHOW_LOCALHOST_IPS,
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

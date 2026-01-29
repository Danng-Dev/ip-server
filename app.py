from flask import Flask, jsonify
import socket
import os
import requests

app = Flask(__name__)

def get_ip_addresses():
    """Get all IP addresses similar to hostname -I"""
    ip_addresses = []
    
    # Method 1: Try to get from socket
    try:
        hostname = socket.gethostname()
        ips = socket.getaddrinfo(hostname, None)
        for ip in ips:
            ip_addr = ip[4][0]
            # Filter for IPv4 addresses (not localhost)
            if ip_addr not in ip_addresses and not ip_addr.startswith('127.') and ':' not in ip_addr:
                ip_addresses.append(ip_addr)
    except:
        pass
    
    # Method 2: Use socket to get primary IP
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0)
        try:
            s.connect(('10.254.254.254', 1))  # Doesn't need to be reachable
            primary_ip = s.getsockname()[0]
            if primary_ip not in ip_addresses and not primary_ip.startswith('127.'):
                ip_addresses.insert(0, primary_ip)
        except Exception:
            pass
        finally:
            s.close()
    except:
        pass
    
    # Method 3: Get all network interfaces
    try:
        import netifaces
        for interface in netifaces.interfaces():
            addrs = netifaces.ifaddresses(interface)
            if netifaces.AF_INET in addrs:
                for addr_info in addrs[netifaces.AF_INET]:
                    ip = addr_info.get('addr')
                    if ip and not ip.startswith('127.') and ip not in ip_addresses:
                        ip_addresses.append(ip)
    except ImportError:
        pass
    
    # Method 4: Use ip command (works in Linux containers)
    try:
        import subprocess
        result = subprocess.run(['hostname', '-I'], capture_output=True, text=True)
        if result.returncode == 0:
            ips = result.stdout.strip().split()
            for ip in ips:
                if ip not in ip_addresses:
                    ip_addresses.append(ip)
    except:
        pass
    
    return ip_addresses

@app.route('/')
def index():
    """Return IP addresses like hostname -I"""
    ips = get_ip_addresses()
    
    # Format as plain text like hostname -I
    ip_string = ' '.join(ips) if ips else 'No IP addresses found'
    
    return ip_string + '\n'

@app.route('/json')
def json_endpoint():
    """Return IP addresses as JSON"""
    ips = get_ip_addresses()
    return jsonify({
        'hostname': socket.gethostname(),
        'ip_addresses': ips
    })

@app.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({'status': 'healthy'})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5252))
    app.run(host='0.0.0.0', port=port, debug=False)

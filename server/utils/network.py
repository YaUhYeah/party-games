"""Network utility functions."""
import socket
import subprocess
import platform
import json
from typing import Optional

def get_local_ip() -> str:
    """Get the local IP address of the machine.
    
    Returns the first non-localhost IPv4 address found.
    Falls back to localhost if no suitable address is found.
    """
    # First try: Connect to external server
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        if not ip.startswith('127.'):
            return ip
    except:
        pass

    # Second try: Use platform-specific commands
    system = platform.system().lower()
    
    if system == 'windows':
        try:
            # Use ipconfig
            output = subprocess.check_output('ipconfig', shell=True).decode()
            for line in output.split('\n'):
                if 'IPv4 Address' in line:
                    ip = line.split(':')[-1].strip()
                    if not ip.startswith('127.'):
                        return ip
        except:
            pass
    else:
        try:
            # Use ip addr (Linux/Unix)
            output = subprocess.check_output(['ip', 'addr']).decode()
            for line in output.split('\n'):
                if 'inet ' in line:
                    ip = line.split()[1].split('/')[0]
                    if not ip.startswith('127.'):
                        return ip
        except:
            pass

    # Third try: Use socket hostname
    try:
        hostname = socket.gethostname()
        ip = socket.gethostbyname(hostname)
        if not ip.startswith('127.'):
            return ip
    except:
        pass

    return "localhost"

def get_public_ip() -> Optional[str]:
    """Get the public IP address of the machine.
    
    Returns None if unable to get public IP or if requests module is not installed.
    """
    try:
        # Attempt to import requests only when needed
        import requests
        response = requests.get('https://api.ipify.org?format=json', timeout=5)
        return response.json()['ip']
    except (ImportError, Exception):
        return None
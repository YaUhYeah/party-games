"""Network utility functions."""
import socket
import netifaces

def get_local_ip() -> str:
    """Get the local IP address of the machine.
    
    Returns the first non-localhost IPv4 address found.
    Falls back to localhost if no suitable address is found.
    """
    try:
        # Try getting IP by connecting to external server
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        # Fallback: check all network interfaces
        try:
            for interface in netifaces.interfaces():
                addrs = netifaces.ifaddresses(interface)
                if netifaces.AF_INET in addrs:
                    for addr in addrs[netifaces.AF_INET]:
                        ip = addr['addr']
                        # Skip localhost and docker interfaces
                        if not ip.startswith('127.') and not ip.startswith('172.'):
                            return ip
        except:
            pass
        return "localhost"

def get_public_ip() -> str:
    """Get the public IP address of the machine.
    
    Returns None if unable to get public IP.
    """
    try:
        import requests
        response = requests.get('https://api.ipify.org?format=json', timeout=5)
        return response.json()['ip']
    except:
        return None
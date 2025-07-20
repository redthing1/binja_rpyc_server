"""
The service name
"""

SERVICE_NAME: str = "Binja-RPyC"

"""
Service description
"""
SERVICE_DESCRIPTION: str = "Use RPyC to control Binary Ninja headlessly"

"""
Change to True to enable debug messages
"""
DEBUG: bool = False

"""
The IPv4 host address to listen on
"""
DEFAULT_HOST_IP: str = "0.0.0.0"

"""
The TCP port to listen on
"""
DEFAULT_HOST_PORT: int = 18812

SETTING_AUTOSTART: str = "serviceStartOnLoad"
SETTING_RPYC_HOST: str = "serviceRpycListenHost"
SETTING_RPYC_PORT: str = "serviceRpycListenPort"
SETTING_RPYC_TIMEOUT: str = "serviceRpycTimeout"

"""
Default timeout in seconds for synchronous RPyC requests
"""
DEFAULT_TIMEOUT: int = 3600

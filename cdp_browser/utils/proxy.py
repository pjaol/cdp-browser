"""
Proxy utility module for CDP Browser.
Contains functions for proxy configuration.
"""
import logging
import os
from typing import Dict, Optional, Tuple, Union

logger = logging.getLogger(__name__)


class ProxyConfig:
    """
    Proxy configuration for CDP Browser.
    """

    def __init__(
        self,
        host: str,
        port: int,
        username: Optional[str] = None,
        password: Optional[str] = None,
        protocol: str = "http",
    ):
        """
        Initialize a ProxyConfig instance.

        Args:
            host: Proxy host
            port: Proxy port
            username: Proxy username (optional)
            password: Proxy password (optional)
            protocol: Proxy protocol (http, https, socks4, socks5)
        """
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.protocol = protocol.lower()
        
        # Validate protocol
        if self.protocol not in ["http", "https", "socks4", "socks5"]:
            raise ValueError(
                "Protocol must be one of: http, https, socks4, socks5"
            )

    @property
    def url(self) -> str:
        """
        Get proxy URL.

        Returns:
            Proxy URL
        """
        if self.username and self.password:
            return f"{self.protocol}://{self.username}:{self.password}@{self.host}:{self.port}"
        else:
            return f"{self.protocol}://{self.host}:{self.port}"

    @property
    def chrome_arg(self) -> str:
        """
        Get Chrome proxy argument.

        Returns:
            Chrome proxy argument
        """
        return f"--proxy-server={self.host}:{self.port}"

    @classmethod
    def from_url(cls, url: str) -> "ProxyConfig":
        """
        Create a ProxyConfig from a URL.

        Args:
            url: Proxy URL (e.g., http://user:pass@host:port)

        Returns:
            ProxyConfig instance
        """
        # Parse protocol
        if "://" in url:
            protocol, url = url.split("://", 1)
        else:
            protocol = "http"
        
        # Parse auth
        if "@" in url:
            auth, url = url.split("@", 1)
            if ":" in auth:
                username, password = auth.split(":", 1)
            else:
                username, password = auth, None
        else:
            username, password = None, None
        
        # Parse host and port
        if ":" in url:
            host, port = url.split(":", 1)
            port = int(port)
        else:
            host = url
            port = 80 if protocol == "http" else 443
        
        return cls(host, port, username, password, protocol)

    @classmethod
    def from_env(cls, env_var: str = "PROXY_SERVER") -> Optional["ProxyConfig"]:
        """
        Create a ProxyConfig from an environment variable.

        Args:
            env_var: Environment variable name

        Returns:
            ProxyConfig instance or None if not set
        """
        proxy_url = os.environ.get(env_var)
        if not proxy_url:
            return None
        
        return cls.from_url(proxy_url) 
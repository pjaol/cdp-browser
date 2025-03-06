"""
Tests for CDP connection.
"""
import asyncio
import os
import pytest

from cdp_browser.core.connection import CDPConnection
from cdp_browser.core.exceptions import CDPConnectionError


@pytest.mark.asyncio
async def test_connection_invalid_url():
    """Test connection with invalid URL."""
    connection = CDPConnection("ws://localhost:12345")
    
    with pytest.raises(CDPConnectionError):
        await connection.connect()


@pytest.mark.asyncio
async def test_send_command_not_connected():
    """Test sending command when not connected."""
    connection = CDPConnection("ws://localhost:9222")
    
    with pytest.raises(CDPConnectionError):
        await connection.send_command("Browser.getVersion")


@pytest.mark.skipif(
    not os.environ.get("CHROME_AVAILABLE"),
    reason="Chrome not available",
)
@pytest.mark.asyncio
async def test_connection_valid():
    """Test connection with valid URL."""
    connection = CDPConnection("ws://localhost:9222/devtools/browser/about:blank")
    
    try:
        await connection.connect()
        assert connection.connected
    except CDPConnectionError:
        pytest.skip("Chrome not available")
    finally:
        await connection.disconnect()


@pytest.mark.skipif(
    not os.environ.get("CHROME_AVAILABLE"),
    reason="Chrome not available",
)
@pytest.mark.asyncio
async def test_send_command():
    """Test sending command."""
    connection = CDPConnection("ws://localhost:9222/devtools/browser/about:blank")
    
    try:
        await connection.connect()
        result = await connection.send_command("Browser.getVersion")
        assert "Browser" in result
    except CDPConnectionError:
        pytest.skip("Chrome not available")
    finally:
        await connection.disconnect() 
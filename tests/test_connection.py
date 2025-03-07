"""
Tests for CDP connection.
"""
import asyncio
import os
import pytest
import aiohttp

from cdp_browser.core.connection import CDPConnection
from cdp_browser.core.exceptions import CDPConnectionError


async def get_browser_ws_url() -> str:
    """Get the browser WebSocket URL."""
    async with aiohttp.ClientSession() as session:
        async with session.get("http://localhost:9223/json/version") as response:
            if response.status != 200:
                raise CDPConnectionError(f"Failed to get browser WebSocket URL: {response.status}")
            data = await response.json()
            return data.get("webSocketDebuggerUrl")


@pytest.mark.asyncio
async def test_connection_invalid_url():
    """Test connection with invalid URL."""
    connection = CDPConnection("ws://localhost:12345")
    
    with pytest.raises(CDPConnectionError):
        await connection.connect()


@pytest.mark.asyncio
async def test_send_command_not_connected():
    """Test sending command when not connected."""
    connection = CDPConnection("ws://localhost:9223")
    
    with pytest.raises(CDPConnectionError):
        await connection.send_command("Browser.getVersion")


@pytest.mark.skipif(
    not os.environ.get("CHROME_AVAILABLE"),
    reason="Chrome not available",
)
@pytest.mark.asyncio
async def test_connection_valid():
    """Test connection with valid URL."""
    try:
        ws_url = await get_browser_ws_url()
        connection = CDPConnection(ws_url)
        
        await connection.connect()
        assert connection.connected
    except CDPConnectionError:
        pytest.skip("Chrome not available")
    finally:
        if 'connection' in locals():
            await connection.disconnect()


@pytest.mark.skipif(
    not os.environ.get("CHROME_AVAILABLE"),
    reason="Chrome not available",
)
@pytest.mark.asyncio
async def test_send_command():
    """Test sending command."""
    try:
        ws_url = await get_browser_ws_url()
        connection = CDPConnection(ws_url)
        
        await connection.connect()
        result = await connection.send_command("Browser.getVersion")
        assert "product" in result
        assert "Chrome" in result["product"]
        assert "protocolVersion" in result
    except CDPConnectionError:
        pytest.skip("Chrome not available")
    finally:
        if 'connection' in locals():
            await connection.disconnect() 
"""Tests for the Cloudflare Turnstile patch."""

import pytest
import logging
from unittest.mock import MagicMock, patch
import asyncio

from cdp_browser.browser.stealth.patches.cloudflare_turnstile import CloudflareTurnstilePatch


@pytest.mark.asyncio
async def test_turnstile_patch_initialization():
    """Test that the Cloudflare Turnstile patch initializes correctly."""
    turnstile_patch = CloudflareTurnstilePatch()
    assert turnstile_patch.NAME == "cloudflare_turnstile"
    assert not turnstile_patch.turnstile_detected
    assert turnstile_patch.challenge_params is None
    assert not turnstile_patch.callback_registered


@pytest.mark.asyncio
async def test_turnstile_detection_script_injection():
    """Test that the detection script is injected correctly."""
    # Create mock page object
    mock_page = MagicMock()
    # Configure mock to return an awaitable for async functions
    mock_page.evaluateOnNewDocument = MagicMock(return_value=asyncio.Future())
    mock_page.evaluateOnNewDocument.return_value.set_result(None)
    
    # Create the patch
    turnstile_patch = CloudflareTurnstilePatch()
    
    # Apply the patch
    await turnstile_patch._inject_detection_script(mock_page)
    
    # Verify that evaluateOnNewDocument was called once
    mock_page.evaluateOnNewDocument.assert_called_once()
    
    # Check that the script content includes key detection elements
    script_content = mock_page.evaluateOnNewDocument.call_args[0][0]
    assert "_cdp_turnstile" in script_content
    assert "interceptTurnstile" in script_content
    assert "checkForTurnstilePage" in script_content


@pytest.mark.asyncio
async def test_turnstile_message_handler_setup():
    """Test that the message handler is set up correctly."""
    # Create mock page object
    mock_page = MagicMock()
    mock_page.on = MagicMock()
    
    # Create the patch
    turnstile_patch = CloudflareTurnstilePatch()
    
    # Set up the message handler
    await turnstile_patch._setup_message_handler(mock_page)
    
    # Verify that page.on was called with "console"
    mock_page.on.assert_called_once()
    assert mock_page.on.call_args[0][0] == "console"


@pytest.mark.asyncio
async def test_apply_executes_all_setup_steps():
    """Test that the apply method executes all the required setup steps."""
    # Create mock objects
    mock_browser = MagicMock()
    mock_page = MagicMock()
    
    # Create patch with mocked methods
    turnstile_patch = CloudflareTurnstilePatch()
    
    # Create futures for mock async methods
    inject_future = asyncio.Future()
    inject_future.set_result(None)
    setup_future = asyncio.Future()
    setup_future.set_result(None)
    
    # Mock the methods to return the futures
    turnstile_patch._inject_detection_script = MagicMock(return_value=inject_future)
    turnstile_patch._setup_message_handler = MagicMock(return_value=setup_future)
    
    # Apply the patch
    result = await turnstile_patch.apply(mock_browser, mock_page)
    
    # Verify the result and method calls
    assert result is True
    turnstile_patch._inject_detection_script.assert_called_once_with(mock_page)
    turnstile_patch._setup_message_handler.assert_called_once_with(mock_page)


@pytest.mark.asyncio
async def test_solution_handler_registration():
    """Test that the solution handler is registered correctly."""
    # Create mock page object
    mock_page = MagicMock()
    
    # Configure mock to return an awaitable for async functions
    mock_page.evaluate = MagicMock(return_value=asyncio.Future())
    mock_page.evaluate.return_value.set_result(None)
    
    # Create the patch
    turnstile_patch = CloudflareTurnstilePatch()
    
    # Register the solution handler
    await turnstile_patch._register_solution_handler(mock_page)
    
    # Verify that evaluate was called once
    mock_page.evaluate.assert_called_once()
    
    # Check that the script content includes key solution elements
    script_content = mock_page.evaluate.call_args[0][0]
    assert "_cdp_apply_turnstile_solution" in script_content
    assert "solved" in script_content


@pytest.mark.asyncio
async def test_apply_solution():
    """Test applying a solution token."""
    # Create mock page object
    mock_page = MagicMock()
    
    # Configure mock to return an awaitable for async functions
    mock_page.evaluate = MagicMock(return_value=asyncio.Future())
    mock_page.evaluate.return_value.set_result(True)
    
    # Create the patch
    turnstile_patch = CloudflareTurnstilePatch()
    turnstile_patch.turnstile_detected = True
    
    # Apply a solution token
    result = await turnstile_patch.apply_solution(mock_page, "test_token")
    
    # Verify the result and evaluate call
    assert result is True
    mock_page.evaluate.assert_called_once()
    
    # Test case where no Turnstile is detected
    turnstile_patch.turnstile_detected = False
    result = await turnstile_patch.apply_solution(mock_page, "test_token")
    assert result is False


@pytest.mark.asyncio
async def test_is_detected():
    """Test checking if Turnstile is detected."""
    # Create mock page object
    mock_page = MagicMock()
    
    # Configure mock to return an awaitable for async functions
    mock_page.evaluate = MagicMock(return_value=asyncio.Future())
    mock_page.evaluate.return_value.set_result({"detected": True, "type": "standalone"})
    
    # Create the patch
    turnstile_patch = CloudflareTurnstilePatch()
    
    # Check if Turnstile is detected
    result = await turnstile_patch.is_detected(mock_page)
    
    # Verify the result
    assert result["detected"] is True
    assert result["type"] == "standalone"


def test_register_function():
    """Test the register function."""
    from cdp_browser.browser.stealth.patches.cloudflare_turnstile import register
    
    patch = register()
    assert isinstance(patch, CloudflareTurnstilePatch) 
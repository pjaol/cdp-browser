import asyncio
import websockets
import json
import requests
import time

CHROME_DEBUG_PORT = 9223
SAUCEDEMO_URL = "https://www.saucedemo.com/"
USERNAME = "standard_user"
PASSWORD = "secret_sauce"

async def send_command(websocket, command_id, method, params=None, session_id=None):
    """Helper function to send a command to Chrome CDP and return the response."""
    payload = {"id": command_id, "method": method}
    
    if session_id:
        payload["sessionId"] = session_id  # Include session ID for target-specific commands

    if params:
        payload["params"] = params

    await websocket.send(json.dumps(payload))
    response = await websocket.recv()
    return json.loads(response)

async def get_websocket_debugger_url():
    """Fetches the WebSocket URL from Chrome DevTools."""
    response = requests.get(f"http://localhost:{CHROME_DEBUG_PORT}/json/version")
    return response.json()["webSocketDebuggerUrl"]

async def open_new_tab(websocket):
    """Opens a new tab, attaches to it, and returns the target and session IDs."""
    print("Creating a new tab...")
    response = await send_command(websocket, 1, "Target.createTarget", {"url": "about:blank"})
    
    if "result" not in response:
        print(f"❌ Error creating target: {response}")
        return None, None
    
    target_id = response["result"]["targetId"]
    print(f"New Tab Target ID: {target_id}")

    print("Attaching to the tab...")
    response = await send_command(websocket, 2, "Target.attachToTarget", {"targetId": target_id, "flatten": True})

    if "params" not in response or "sessionId" not in response["params"]:
        print(f"❌ Failed to attach to target. Response: {response}")
        return None, None
    
    session_id = response["params"]["sessionId"]
    print(f"✅ Attached to session: {session_id}")

    return target_id, session_id

async def enable_page_domain(websocket, session_id):
    """Enables the 'Page' domain so we can use Page.navigate."""
    print("Enabling 'Page' domain...")
    response = await send_command(websocket, 3, "Page.enable", session_id=session_id)
    print(f"✅ 'Page' domain enabled: {response}")

async def navigate_to_url(websocket, session_id):
    """Navigates the browser to the target URL."""
    print(f"Navigating to {SAUCEDEMO_URL}...")
    await enable_page_domain(websocket, session_id)
    response = await send_command(websocket, 4, "Page.navigate", {"url": SAUCEDEMO_URL}, session_id=session_id)

    if "error" in response:
        print(f"❌ Navigation failed: {response}")
    else:
        print("✅ Navigation successful.")

async def wait_for_page_load(websocket):
    """Waits for the page to load by listening for 'Page.loadEventFired' event."""
    print("Waiting for page to load...")
    while True:
        response = await websocket.recv()
        data = json.loads(response)
        if data.get("method") == "Page.loadEventFired":
            print("✅ Page has fully loaded.")
            break

async def type_text(websocket, session_id, selector, text):
    """Simulates typing text character by character using Input.dispatchKeyEvent."""
    print(f"Typing into {selector}...")

    # Click the input field to focus
    await send_command(websocket, 6, "Runtime.evaluate", {"expression": f"document.querySelector('{selector}').focus();"}, session_id=session_id)

    await asyncio.sleep(0.3)  # Add a slight delay to prevent missing characters

    # Type each character
    for char in text:
        await send_command(websocket, 7, "Input.dispatchKeyEvent", {"type": "keyDown", "text": char}, session_id=session_id)
        await send_command(websocket, 8, "Input.dispatchKeyEvent", {"type": "keyUp", "text": char}, session_id=session_id)
        await asyncio.sleep(0.05)  # Mimic human typing

async def login_to_saucedemo(websocket, session_id):
    """Injects JavaScript to log into SauceDemo."""
    print("Typing username and password...")
    await type_text(websocket, session_id, "#user-name", USERNAME)
    await type_text(websocket, session_id, "#password", PASSWORD)

    # Click login button
    print("Clicking login button...")
    await send_command(websocket, 9, "Runtime.evaluate", {"expression": "document.querySelector('#login-button').click();"}, session_id=session_id)

async def wait_for_login_success(websocket, session_id, timeout=10):
    """Waits for the login to be successful by detecting a navigation event."""
    print("Waiting for login to complete...")
    start_time = time.time()

    while True:
        if time.time() - start_time > timeout:
            print("❌ Login timeout! Check if login was successful manually.")
            break

        response = await websocket.recv()
        data = json.loads(response)

        # Debugging: Print received events
        print(data)

        # Detect both standard and JavaScript-based navigation
        if data.get("method") in ["Page.frameNavigated", "Page.navigatedWithinDocument"]:
            url = data.get("params", {}).get("url", "")
            print(f"🔄 Detected navigation to {url}")

            if "inventory.html" in url:  # SauceDemo redirects here after login
                print("✅ Login successful!")
                return  

        await asyncio.sleep(0.1)  # Avoid excessive CPU usage

async def main():
    """Main function to perform the full login sequence."""
    ws_url = await get_websocket_debugger_url()

    async with websockets.connect(ws_url) as websocket:
        target_id, session_id = await open_new_tab(websocket)

        if not session_id:
            print("❌ Exiting: Could not attach to target.")
            return

        await navigate_to_url(websocket, session_id)
        await wait_for_page_load(websocket)
        await login_to_saucedemo(websocket, session_id)
        await wait_for_login_success(websocket, session_id)

# Run the script
asyncio.run(main())

Below is a refined plan and set of requirements to help “Cursor AI” build a Docker-based solution for ARM64 Chrome using direct CDP (Chrome DevTools Protocol) calls—**without relying on Selenium**, Puppeteer, or other drivers that aren’t fully compatible with ARM64. We’ll maintain the sprint-based approach, enabling small, testable deliverables.

---

## 1. Architecture and Requirements (No Selenium)

1. **Docker Image (ARM64)**  
   - **Base Image**: `browserless/chrome:latest` for `linux/arm64`.  
   - Must install Python (3.9+) and Poetry for dependencies.  
   - Provide a way to run Chrome in either **headless** mode or behind an **X virtual frame buffer** (e.g., Xvfb) if required.  
   - Must enable remote debugging (e.g., `--remote-debugging-port=36355`) so we can connect via the Chrome DevTools Protocol (CDP).  
   - **Proxy Support**: Provide a mechanism (environment variable or command-line) for `--proxy-server=HOST:PORT`.  
   - Keep the container minimal and build for ARM64, ensuring any OS-level dependencies (like `xvfb`, `libx11`, etc.) are included only if necessary.

2. **CDP Python Library (No Selenium)**  
   Since we can’t rely on Selenium or Puppeteer, we have two paths:
   1. **Use an existing Python library** that talks to Chrome’s DevTools Protocol (e.g., [pychrome](https://github.com/fate0/pychrome), [python-cdp](https://github.com/HyperionGray/python-cdp), [cdpy](https://github.com/mafredri/cdp), etc.).  
   2. **Build a minimal, custom client**:  
      - Use `websockets` or `aiohttp` to connect to the `ws://` endpoint.  
      - Send/receive JSON commands and events in the DevTools Protocol format.  
      - Provide a high-level API (e.g., `Browser`, `Page`, etc.) that wraps these raw commands.  

   For maintainability, it’s often easier to start with an existing library like `pychrome`—but you can also craft your own if you want a minimal footprint and complete control.

3. **Stealth / Bot Evasion**  
   - Eliminate typical headless signals by adjusting Chrome flags, user agent, etc.  
   - If building a custom client, you can inject JavaScript to hide or reassign certain values (`navigator.webdriver`, etc.).  
   - Avoid known detection heuristics (like missing plugins, MIME types, etc.).  
   - Since we’re not using Selenium or Puppeteer, we won’t rely on “undetected-chromedriver,” but we can replicate some stealth patches (e.g., by hooking `Page.addScriptToEvaluateOnNewDocument`).

4. **Testing & Verification**  
   - We need a **test harness** that:  
     1. Builds and spins up the Docker container.  
     2. Connects via the DevTools WebSocket.  
     3. Performs typical actions (navigate, fill forms, etc.).  
   - Confirm that environment variables like `HEADLESS=true` or `PROXY_SERVER=HOST:PORT` work as intended.  
   - Confirm stealth features (harder to automate, but we can do smoke tests that check certain JS properties).

5. **Project Structure & GitHub Flow**  
   - Organize the repository with the following typical layout:
     ```
     .
     ├── docker
     │   ├── Dockerfile
     │   ├── entrypoint.sh
     ├── cdp_browser
     │   ├── cdp_client  # Python modules for direct CDP usage
     │   │   ├── __init__.py
     │   │   ├── browser.py
     │   │   ├── page.py
     │   │   └── ...
     │   └── main.py     # example or CLI
     ├── tests
     │   ├── test_browser.py
     │   └── ...
     ├── pyproject.toml   # Poetry config
     └── README.md
     ```
   - **GitHub Flow**:  
     - Create feature branches per sprint or feature (e.g., `feature/xvfb-support`, `feature/cdp-forms`).  
     - Keep PRs small, tested, and documented.  
     - Each sprint merges to main with a versioned release.

---

## 2. Proposed Sprint Plan

### Sprint 1: Docker + Minimal CDP Connection
**Goal**: A container that runs ARM64 Chrome and a minimal Python script to connect over DevTools Protocol.

1. **Dockerfile & Entrypoint**  
   - Base on `browserless/chrome:latest` for `linux/arm64`.  
   - Install Python 3.9+ and Poetry.  
   - Copy `entrypoint.sh` that checks `HEADLESS` env var.  
     - If `HEADLESS=true`, launch Chrome with `--headless=new`.  
     - If `HEADLESS=false`, either skip headless or run `Xvfb` then launch Chrome.  
   - Expose port `36355` for remote debugging.  

2. **CDP Client Setup**  
   - In `cdp_client/__init__.py`, create a minimal `connect()` function that:  
     - Reads a `DEVTOOLS_WS_URL` or constructs `ws://127.0.0.1:36355/devtools/browser/<id>`.  
     - Establishes a WebSocket connection using `websockets` or `aiohttp`.  
     - Optionally calls a `Browser.getVersion` method to confirm success.  

3. **Basic Test**  
   - Write a Pytest that spins up the container locally (docker run), then attempts to connect from the host to confirm we can retrieve a Chrome version.  
   - If that works, the test passes.  
   - Merge changes as Sprint 1 deliverable.

### Sprint 2: Page Navigation, Form Filling, Proxy
**Goal**: Implement a more complete set of CDP commands, add proxy support, and do some basic interactions.

1. **Proxy Support**  
   - In the `entrypoint.sh`, if `PROXY_SERVER` is set, pass `--proxy-server=$PROXY_SERVER` to Chrome.  
   - Add a test that uses a local mock proxy server to verify traffic routes properly.

2. **Page Navigation**  
   - Add a `Page` or `Tab` module inside `cdp_client/`.  
   - Implement commands for:  
     - `Target.createTarget` (to open a new tab).  
     - `Page.navigate(url)`.  
     - Possibly `Runtime.evaluate(script)` to run JS.  
   - Provide a high-level convenience method, e.g.:  
     ```python
     page = browser.new_tab()
     page.navigate("https://example.com")
     ```
3. **Form Filling**  
   - We can implement using CDP’s `Input.dispatchMouseEvent` and `Input.dispatchKeyEvent`, or rely on “DOM methods” by injecting JS. For example:
     ```python
     page.evaluate_js("""
       document.querySelector('#myInput').value = 'test';
       document.querySelector('#myForm').submit();
     """)
     ```
   - Test it against a known local or public test page.

4. **Tests**  
   - Expand integration tests: navigate to a form, fill it, submit, confirm result.  
   - Confirm `proxy` usage (requests appear in proxy logs).

### Sprint 3: Stealth & Extended Features
**Goal**: Add stealth features (bot evasion), more advanced interactions, and finalize documentation.

1. **Stealth / Bot Evasion**  
   - In Chrome flags, disable obvious headless signals (some come disabled by default in `browserless/chrome`).  
   - Patch `navigator.webdriver`.  
   - Possibly inject scripts on page load using `Page.addScriptToEvaluateOnNewDocument` to mask headless.  
   - Add or refine user-agent string.  
   - Test with known detection sites (like “Am I Headless?” or “Bot Detection Demo”).

2. **Advanced Interactions**  
   - Handling alerts, confirmations (`Page.handleJavaScriptDialog`).  
   - Taking screenshots (`Page.captureScreenshot`).  
   - Intercepting network requests (`Network.*` commands) if needed.

3. **Documentation & Finalizing**  
   - Thorough docstrings for `cdp_client`.  
   - Top-level `README.md` with usage instructions.  
   - Example code in `examples/` or `main.py`.  
   - CI pipeline (GitHub Actions) to run Docker build & tests on each push.

---

## 3. Sample `pyproject.toml` (Poetry)

Below is an **example** `pyproject.toml` snippet for the Python side:

```toml
[tool.poetry]
name = "cdp-py-client"
version = "0.1.0"
description = "Lightweight Python client for Chrome DevTools Protocol on ARM64"
authors = ["Your Name <you@example.com>"]
license = "MIT"

[tool.poetry.dependencies]
python = "^3.9"
websocket-client = "^1.5.1"  # or websockets, if you prefer
pychrome = "^0.2.3"          # optional, if we want an existing library

[tool.poetry.dev-dependencies]
pytest = "^7.0"
pytest-cov = "^4.0"

[build-system]
requires = ["poetry>=1.1"]
build-backend = "poetry.core.masonry.api"
```

If you opt for a fully custom approach, skip `pychrome` and write your own WebSocket logic with `websockets` or `aiohttp`.

---

## 4. Summary and Next Steps

- **Sprint 1**: Basic Docker (ARM64) + minimal CDP connectivity.  
- **Sprint 2**: Page/tab management, navigation, form filling, proxy.  
- **Sprint 3**: Stealth improvements, more advanced interactions, finalize tests & docs.

By following these sprints, the “Cursor AI” team can deliver smaller, fully testable increments—eventually arriving at a lightweight, ARM64-compatible Docker container that runs Chrome headless (or via Xvfb) and communicates via DevTools Protocol **without Selenium**.
Thanks for the details! I'll research how to interact with Google Chrome using the CDP protocol via raw WebSockets, including working examples of browser, tab, page, navigation, and session handling. The research will cover:

- WebSocket connections and CDP payloads
- Differences in CDP implementation across Chrome, Chromium, Edge, Firefox, Safari, and Tor
- Common browser bot detection techniques and CDP-based evasion strategies
- Running Chrome in Docker, especially on ARM64, and overcoming issues like lack of drivers and dbus system
- Alternatives to browserless images to avoid lock-in and licensing issues
- Using proxies with CDP-based automation
- Techniques to verify CDP payloads against specific browser versions

I'll gather technical insights, examples, and best practices to help your engineers implement a robust solution. I'll update you when the research is ready.

# Chrome DevTools Protocol (CDP) via WebSockets for Browser Automation

## 1. Establishing a CDP WebSocket Connection and Sending Commands 
**Launching Chrome for CDP:** To use the Chrome DevTools Protocol, start Chrome/Chromium with the Remote Debugging port open. For example: 

```bash
chrome --remote-debugging-port=9222 --headless --no-sandbox --disable-gpu
``` 

When Chrome launches with this flag, it outputs a **WebSocket URL** for CDP (e.g. `ws://127.0.0.1:9222/devtools/browser/<id>`) ([GitHub - aslushnikov/getting-started-with-cdp: Getting Started With Chrome DevTools Protocol](https://github.com/aslushnikov/getting-started-with-cdp#:~:text=When%20Chromium%20is%20started%20with,output%20looks%20something%20like%20this)) ([GitHub - aslushnikov/getting-started-with-cdp: Getting Started With Chrome DevTools Protocol](https://github.com/aslushnikov/getting-started-with-cdp#:~:text=Clients%20can%20create%20a%20WebSocket,params)). You can also retrieve active targets and their WebSocket endpoints by visiting the JSON API (e.g. `http://localhost:9222/json/list`). Once you have a WebSocket URL, connect a client to it to start sending protocol messages ([GitHub - aslushnikov/getting-started-with-cdp: Getting Started With Chrome DevTools Protocol](https://github.com/aslushnikov/getting-started-with-cdp#:~:text=Clients%20can%20create%20a%20WebSocket,params)). Each message is a JSON object following a JSON-RPC style: it must include a unique `"id"`, a `"method"` (like `"Page.navigate"`), and optional `"params"` ([GitHub - aslushnikov/getting-started-with-cdp: Getting Started With Chrome DevTools Protocol](https://github.com/aslushnikov/getting-started-with-cdp#:~:text=Clients%20can%20create%20a%20WebSocket,params)) ([GitHub - aslushnikov/getting-started-with-cdp: Getting Started With Chrome DevTools Protocol](https://github.com/aslushnikov/getting-started-with-cdp#:~:text=A%20few%20things%20to%20notice%3A)). The browser will send back a response with the same `"id"`, or if an event occurs (asynchronous notification), it will send a message with no `"id"` field (indicating a **CDP event**) ([GitHub - aslushnikov/getting-started-with-cdp: Getting Started With Chrome DevTools Protocol](https://github.com/aslushnikov/getting-started-with-cdp#:~:text=A%20few%20things%20to%20notice%3A)). 

**CDP Commands and Events:** After connecting, you can send commands to control the browser or pages. For example, to list or monitor targets (tabs, pages, etc.), you can enable target discovery: 

```json
{ "id": 1, "method": "Target.setDiscoverTargets", "params": { "discover": true } }
``` 

Sending this over the WebSocket will prompt Chrome to emit **Target events** for each existing target. For instance, you’ll receive messages like `{"method":"Target.targetCreated","params":{...}}` for the browser context and any open page, followed by a response `{"id":1,"result":{}}` acknowledging the command ([GitHub - aslushnikov/getting-started-with-cdp: Getting Started With Chrome DevTools Protocol](https://github.com/aslushnikov/getting-started-with-cdp#:~:text=connected%21%20Sending%20Target.setDiscoverTargets%20%7B%22method%22%3A%22Target.targetCreated%22%2C%22params%22%3A%7B%22targetInfo%22%3A%7B%22targetId%22%3A%2238555cf%20e,result)). In general: 

- Every command message needs a unique `id`, and the response will carry the same `id` ([GitHub - aslushnikov/getting-started-with-cdp: Getting Started With Chrome DevTools Protocol](https://github.com/aslushnikov/getting-started-with-cdp#:~:text=A%20few%20things%20to%20notice%3A)).  
- Any message without an `id` is an **event** pushed from the browser (e.g. page load events, network events) ([GitHub - aslushnikov/getting-started-with-cdp: Getting Started With Chrome DevTools Protocol](https://github.com/aslushnikov/getting-started-with-cdp#:~:text=1,Target.setDiscoverTargets)).  
- Order matters: some commands cause a flood of events before their final result (as seen with `Target.setDiscoverTargets`) ([GitHub - aslushnikov/getting-started-with-cdp: Getting Started With Chrome DevTools Protocol](https://github.com/aslushnikov/getting-started-with-cdp#:~:text=1,Target.setDiscoverTargets)).  

**Attaching to Pages and Navigating:** Chrome’s CDP is organized into **domains** (Page, Runtime, Network, etc.) that apply to different “targets.” By default, connecting to the WebSocket URL for the **browser** creates a “browser session” (for top-level browser commands). To control a specific page/tab, you must either connect directly to that page’s WebSocket endpoint or attach to it via the **Target domain** ([GitHub - aslushnikov/getting-started-with-cdp: Getting Started With Chrome DevTools Protocol](https://github.com/aslushnikov/getting-started-with-cdp#:~:text=Some%20commands%20set%20state%20which,sessions%20connected%20to%20pages%20do)) ([GitHub - aslushnikov/getting-started-with-cdp: Getting Started With Chrome DevTools Protocol](https://github.com/aslushnikov/getting-started-with-cdp#:~:text=When%20a%20client%20connects%20over,a%20new%20page%20session%20created)). Using the browser-level connection, you can call `Target.attachToTarget` with a targetId to get a session for that page ([GitHub - aslushnikov/getting-started-with-cdp: Getting Started With Chrome DevTools Protocol](https://github.com/aslushnikov/getting-started-with-cdp#:~:text=Chrome%20DevTools%20protocol%20has%20APIs,be%20fetched%2Ftracked%20using%20Target%20domain)) ([GitHub - aslushnikov/getting-started-with-cdp: Getting Started With Chrome DevTools Protocol](https://github.com/aslushnikov/getting-started-with-cdp#:~:text=const%20sessionId%20%3D%20,result.sessionId)). This returns a `sessionId` which you include in subsequent commands to direct them at that page ([GitHub - aslushnikov/getting-started-with-cdp: Getting Started With Chrome DevTools Protocol](https://github.com/aslushnikov/getting-started-with-cdp#:~:text=inside%20the%20session%2C%20but%20different,send%20it%20to%20the%20page)) ([GitHub - aslushnikov/getting-started-with-cdp: Getting Started With Chrome DevTools Protocol](https://github.com/aslushnikov/getting-started-with-cdp#:~:text=non,send%20it%20to%20the%20page)). For example, after getting a `sessionId` for a target, you can navigate that tab to a URL: 

```json
{ "id": 2, "sessionId": "<session-id>", "method": "Page.navigate", "params": { "url": "https://example.com" } }
``` 

This would load the page and return a response when navigation completes ([GitHub - aslushnikov/getting-started-with-cdp: Getting Started With Chrome DevTools Protocol](https://github.com/aslushnikov/getting-started-with-cdp#:~:text=%2F%2F%20Navigate%20the%20page%20using,)). (If you connect directly to a page’s own WebSocket (e.g. `.../devtools/page/<id>`), you can send `Page.navigate` without needing a sessionId, since that connection is already scoped to the page.) 

**Executing JavaScript & Other Actions:** You can interact further by enabling domains and sending commands: e.g. use `Runtime.evaluate` to run JavaScript in the page context, or `DOM.*` commands to manipulate the DOM. For instance, to get the page title you might call: 

```json
{ "id": 3, "sessionId": "<session-id>", "method": "Runtime.evaluate", "params": { "expression": "document.title" } }
``` 

This returns the result of the evaluation. Many domains must be **enabled** before use. For example, to receive console logs or network events, you send `"Runtime.enable"` or `"Network.enable"` first. Some domains also support **listening for events**: after `Network.enable`, the browser will send `Network.requestWillBeSent`, `Network.responseReceived`, etc., events automatically. 

**Network Interception Example:** CDP allows low-level network request interception and modification. For example, you can intercept script requests as follows:

1. Enable the Network domain and then set up interception patterns: 

   ```json
   { "id": 4, "sessionId": "<session-id>", "method": "Network.enable", "params": {} }
   ``` 

   ```json
   { "id": 5, "sessionId": "<session-id>", "method": "Network.setRequestInterception", 
       "params": { "patterns": [ { "urlPattern": "*", "resourceType": "Script", "interceptionStage": "HeadersReceived" } ] } }
   ``` 

   This tells Chrome to pause on all script resource requests ([Using Chrome Devtools Protocol with Puppeteer ](https://jarrodoverson.com/post/using-chrome-devtools-protocol-with-puppeteer-737a1300bac0/#:~:text=await%20client)). (Note: many CDP methods are **experimental**, so calling `Network.enable` is a good practice to ensure events fire ([Using Chrome Devtools Protocol with Puppeteer ](https://jarrodoverson.com/post/using-chrome-devtools-protocol-with-puppeteer-737a1300bac0/#:~:text=Many%20CDP%20domains%20require%20that,experimental%20and%20subject%20to%20change)).)

2. Listen for the `Network.requestIntercepted` events. Each will contain an `interceptionId`. Using that ID, you can decide to continue, fulfill, or abort the request. For instance, to simply continue all intercepted requests without modification: 

   ```json
   { "id": 6, "sessionId": "<session-id>", "method": "Network.continueInterceptedRequest", 
       "params": { "interceptionId": "<the-interception-id>" } }
   ``` 

   If you wanted to modify the response, you could first call `Network.getResponseBodyForInterception` to get the response data, then provide a custom response with `Network.fulfillRequest` (constructing the raw HTTP response as base64) ([Using Chrome Devtools Protocol with Puppeteer ](https://jarrodoverson.com/post/using-chrome-devtools-protocol-with-puppeteer-737a1300bac0/#:~:text=Retrieving%20the%20body%20of%20a,response)) ([Using Chrome Devtools Protocol with Puppeteer ](https://jarrodoverson.com/post/using-chrome-devtools-protocol-with-puppeteer-737a1300bac0/#:~:text=Delivering%20a%20modified%20response)). This level of control (intercepting network, modifying DOM, etc.) highlights the power of CDP for browser automation.

**Session and Target Management:** With CDP you can open or close tabs and even manage multiple browser contexts. For example, `Target.createTarget` opens a new tab (target) in the browser. If connected at the browser level, you’ll get a `Target.targetCreated` event for the new tab. You could then attach to it as described. Each CDP session (browser-level or page-level) maintains its own state. Certain commands (like enabling domains) are session-scoped ([GitHub - aslushnikov/getting-started-with-cdp: Getting Started With Chrome DevTools Protocol](https://github.com/aslushnikov/getting-started-with-cdp#:~:text=Some%20commands%20set%20state%20which,sessions%20connected%20to%20pages%20do)), so they don’t affect other sessions. It’s important to include the correct `sessionId` if you have multiple targets; otherwise, your command might default to the top-level session (browser context) which doesn’t support page-specific methods ([GitHub - aslushnikov/getting-started-with-cdp: Getting Started With Chrome DevTools Protocol](https://github.com/aslushnikov/getting-started-with-cdp#:~:text=Some%20commands%20set%20state%20which,sessions%20connected%20to%20pages%20do)). 

**Browser vs. Page Context:** Note that some CDP domains are only available in certain contexts. For example, the `"Page"` domain exists for page targets but not for the browser target ([GitHub - aslushnikov/getting-started-with-cdp: Getting Started With Chrome DevTools Protocol](https://github.com/aslushnikov/getting-started-with-cdp#:~:text=Some%20commands%20set%20state%20which,sessions%20connected%20to%20pages%20do)). Conversely, the `"Browser"` domain (for controlling browser-wide settings) is only usable on the browser session. CDP also distinguishes **stable vs. experimental** APIs – experimental commands/events (marked in protocol docs) can change or be removed in future Chrome versions ([GitHub - aslushnikov/getting-started-with-cdp: Getting Started With Chrome DevTools Protocol](https://github.com/aslushnikov/getting-started-with-cdp#:~:text=Stable%20vs%20Experimental%20methods)). It’s best to use stable commands when possible, or be ready to adjust your payloads if you rely on experimental ones (the Chrome team maintains up-to-date clients like Puppeteer to handle protocol changes ([GitHub - aslushnikov/getting-started-with-cdp: Getting Started With Chrome DevTools Protocol](https://github.com/aslushnikov/getting-started-with-cdp#:~:text=The%20Chrome%20DevTools%20Protocol%20has,APIs%20and%20changes%2Fremoves%20them%20regularly))).

**Cross-Browser CDP Differences:** Chrome and Chromium share the same CDP interface (Chromium is the open-source core of Chrome, so their command payloads are identical). Microsoft Edge (Chromium-based, v79+): also uses the **same CDP**; you can launch Edge with `--remote-debugging-port` and use the same methods (only the reported browser name/version differs). Other browsers require different approaches: 

- **Firefox:** Firefox implemented a **subset of CDP** to support tools like Puppeteer ([Remote Protocols — Firefox Source Docs  documentation](https://firefox-source-docs.mozilla.org/remote/index.html#:~:text=Remote%20Protocol%20)). You can launch Firefox with `--remote-debugging-port` to get a WebSocket, but not all Chrome commands will work – only the commands from domains Firefox chose to support. (Firefox’s team is now focusing on the WebDriver BiDi protocol as a cross-browser standard, and their CDP support is considered experimental or being deprecated.) In practice, automation on Firefox is often done via **Marionette** or WebDriver, not raw CDP, because CDP coverage is limited. For example, Firefox might support basic Page navigation and Runtime eval through CDP, but not the full Network interception that Chrome offers. Always check Firefox’s documentation for what portion of CDP is implemented if you attempt this ([Remote Protocols — Firefox Source Docs  documentation](https://firefox-source-docs.mozilla.org/remote/index.html#:~:text=Remote%20Protocol%20)). 

- **Safari:** Safari does **not use CDP**. Safari’s Web Inspector uses a WebKit Remote Debugging Protocol, which is entirely different in terms of commands and structure. While it also uses WebSockets, the commands (domains/methods) are specific to WebKit. You cannot directly use Chrome CDP payloads on Safari. (Projects like **ios-webkit-debug-proxy** act as a bridge, translating Chrome CDP calls to Safari’s protocol ([How Playwright Communicates With Browsers – 93 DAYS](https://93days.me/how-playwright-communicates-with-browsers/#:~:text=Protocol%20for%20WebKit%20%28Safari%29,test%20script%20and%20the)) ([Debug iOS 6+7 Mobile Safari using the Chrome DevTools](https://stackoverflow.com/questions/11361822/debug-ios-67-mobile-safari-using-the-chrome-devtools#:~:text=making%20it%20incompatible%20with%20Chrome)), but this is an adaptation layer.) In short, automation on Safari means using Apple’s WebDriver (or WebKit’s protocol) rather than CDP. 

- **Tor Browser:** Tor Browser is based on Firefox ESR, and similarly does not natively expose Chrome’s CDP. If remote debugging is enabled on Tor (not typical for end-users, but possible for testing), it would use Firefox’s remote protocol under the hood. Additionally, Tor’s focus on privacy means automation is discouraged — even if you did enable the remote agent, Tor shares Firefox’s limitations (only the subset of CDP Firefox supports, if any). **Important:** Many CDP techniques (like altering fingerprints) defeat Tor’s anti-fingerprinting measures, so using CDP on Tor may make the browser behave *less* like a Tor browser from websites’ perspective. 

When automating, you should **verify that the CDP commands you send are supported by your browser version**. Each Chrome release comes with a specific CDP version. You can retrieve the protocol definition for your exact Chrome version by navigating to `chrome://version` (to get the version number) and then checking the CDP documentation for that version, or by calling the endpoint `http://localhost:9222/json/protocol`. If you send an unknown or unsupported command, the browser will respond with an error. Using stable commands and checking Chrome’s release notes/protocol docs is a best practice. In general, Chrome’s stable commands remain backward-compatible for a long time, but experimental ones (or ones only in Canary) might not exist in older versions ([GitHub - aslushnikov/getting-started-with-cdp: Getting Started With Chrome DevTools Protocol](https://github.com/aslushnikov/getting-started-with-cdp#:~:text=Stable%20vs%20Experimental%20methods)). Always tailor your JSON payloads to the target browser’s capabilities. 

## 2. Bot Detection Evasion via CDP 
Automating browsers means dealing with anti-bot **fingerprinting** checks. Websites use scripts and analysis to detect “non-human” browser traits. **Common detection methods** include: 

- **Navigator/WebDriver Flags:** E.g. checking `navigator.webdriver`. By W3C spec, a browser controlled by automation should have `navigator.webdriver=true`. Many sites simply look for this flag as an indicator of Selenium/automation. Chrome in *headless* mode used to set this true by default. Modern Chromiums have an option to start without this flag. For example, launching Chrome with `--disable-blink-features=AutomationControlled` causes `navigator.webdriver` to be `false`/undefined, making automation less obvious ([java - Selenium webdriver: Modifying navigator.webdriver flag to prevent selenium detection - Stack Overflow](https://stackoverflow.com/questions/53039551/selenium-webdriver-modifying-navigator-webdriver-flag-to-prevent-selenium-detec#:~:text=Preventing%20Detection%20)) ([java - Selenium webdriver: Modifying navigator.webdriver flag to prevent selenium detection - Stack Overflow](https://stackoverflow.com/questions/53039551/selenium-webdriver-modifying-navigator-webdriver-flag-to-prevent-selenium-detec#:~:text=driver.execute_cdp_cmd%28,)). You can also explicitly override it via CDP. Using the CDP command `Page.addScriptToEvaluateOnNewDocument`, you can inject a script before any page script runs. For instance, you can define `navigator.webdriver` to return `undefined` (the normal value in a real browser) so that checks for it will fail ([java - Selenium webdriver: Modifying navigator.webdriver flag to prevent selenium detection - Stack Overflow](https://stackoverflow.com/questions/53039551/selenium-webdriver-modifying-navigator-webdriver-flag-to-prevent-selenium-detec#:~:text=driver.execute_cdp_cmd%28,)). In Python Selenium this is done as: 

  ```python
  driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
      "source": "Object.defineProperty(navigator, 'webdriver', { get: () => undefined })"
  })
  ``` 

  This script runs at page load, ensuring that `navigator.webdriver` is not present when site scripts check it ([java - Selenium webdriver: Modifying navigator.webdriver flag to prevent selenium detection - Stack Overflow](https://stackoverflow.com/questions/53039551/selenium-webdriver-modifying-navigator-webdriver-flag-to-prevent-selenium-detec#:~:text=driver.execute_cdp_cmd%28,)). (Note: It’s important to set it to `undefined` – not `false` – because in a real browser the property doesn’t exist at all ([java - Selenium webdriver: Modifying navigator.webdriver flag to prevent selenium detection - Stack Overflow](https://stackoverflow.com/questions/53039551/selenium-webdriver-modifying-navigator-webdriver-flag-to-prevent-selenium-detec#:~:text=by%20the%20way%2C%20you%20want,is%20a%20dead%20giveaway)).) Chrome’s CDP makes such modification easy; **no other browser** currently lets you inject script at document start in this way ([java - Selenium webdriver: Modifying navigator.webdriver flag to prevent selenium detection - Stack Overflow](https://stackoverflow.com/questions/53039551/selenium-webdriver-modifying-navigator-webdriver-flag-to-prevent-selenium-detec#:~:text=Since%20this%20question%20is%20related,is%20close%20with%20Remote%20Protocol)), so this is a Chromium-only evasion technique. Firefox’s automation (Marionette) doesn’t support an equivalent hook, so `navigator.webdriver` will remain `true` if using Firefox’s WebDriver ([java - Selenium webdriver: Modifying navigator.webdriver flag to prevent selenium detection - Stack Overflow](https://stackoverflow.com/questions/53039551/selenium-webdriver-modifying-navigator-webdriver-flag-to-prevent-selenium-detec#:~:text=Since%20this%20question%20is%20related,is%20close%20with%20Remote%20Protocol)). 

- **Headless Browser Signals:** Many detection scripts look for clues of headless Chrome. For example, older headless Chrome had the `userAgent` containing “HeadlessChrome”. Newer versions hide this, but you can also override the user agent via CDP. Using `Network.setUserAgentOverride` you can set a custom UA string ([java - Selenium webdriver: Modifying navigator.webdriver flag to prevent selenium detection - Stack Overflow](https://stackoverflow.com/questions/53039551/selenium-webdriver-modifying-navigator-webdriver-flag-to-prevent-selenium-detec#:~:text=%2A%20Rotating%20the%20user,command%20as%20follows)). Often automation will mimic a common browser UA (without "Headless" and matching the Chrome version). Other JavaScript-visible clues include the presence of `chrome` runtime object (in Chrome, an object `window.chrome` is normally defined; in pure Chromium or headless it might be missing or have different properties), the number of plugins (`navigator.plugins.length` might be 0 in headless vs >0 in real Chrome), or default languages (`navigator.languages`). These can be tweaked with CDP: e.g. you can inject scripts to spoof plugin data or override `Navigator.languages`. Puppeteer’s “stealth” plugins actually do a lot of this via `Page.addScriptToEvaluateOnNewDocument` under the hood – for example, inserting dummy plugins so that `navigator.plugins` isn’t empty, and fixing `navigator.permissions.query` to not reveal headless mode. Using CDP directly, you can mimic those approaches by injection. 

- **Canvas & WebGL Fingerprinting:** Sites may draw hidden canvases or use WebGL to get a fingerprint of the rendering engine. Headless or virtual environments sometimes produce a consistent but **distinct** image or signature (e.g. missing certain graphics driver optimizations or using software rendering). For example, Cloudflare’s bot detection draws a canvas and inspects the pixels; a headless browser’s output often has subtle differences, or uses a software GL renderer (like Google SwiftShader) with a known signature ([How to Bypass Cloudflare With Selenium (2025 Guide) - ZenRows](https://www.zenrows.com/blog/selenium-cloudflare-bypass#:~:text=Canvas%20Fingerprinting)). Through CDP, you can attempt to evade these checks. One approach is to intercept the canvas or WebGL calls in the page context (again via script injection) – e.g., patch `HTMLCanvasElement.prototype.toDataURL` or the WebGL context’s `getParameter` method to return consistent values. This is complex but feasible: you could use `Page.addScriptToEvaluateOnNewDocument` to inject a script that overrides these methods before the site’s scripts run. For instance, you might override WebGL’s `RENDERER` and `VENDOR` strings to mimic a common GPU (so instead of `"Google Inc. (LLVM)" you return `"Intel Inc."` or similar). There are open-source projects that do this (like puppeteer-extra-plugin-stealth and others), which essentially apply a series of CDP-driven patches to make headless Chrome mimic a regular Chrome. Keep in mind that any such **fingerprint modifications** should be applied **early** (at document start) to be effective.

- **Other Fingerprinting Vectors:** Anti-bot scripts can check many things: system color depth, audio context oscillator output, timezone, font rendering, etc. Many of these can be adjusted via CDP or browser launch parameters. For example, you can control geolocation and timezone via the `Emulation.setTimezoneOverride` and `Emulation.setGeolocationOverride` commands, or set the `navigator.platform` using `Page.addScriptToEvaluateOnNewDocument`. If a site uses the **Battery API or Network Information API** to detect automation (some headless versions might not implement these fully), you could also polyfill or spoof them in the page. The key is to research what fingerprinting technique is in play and use CDP to adjust the browser’s exposed state to match a normal user environment.

- **Detection Variations by Browser:** Bot detection scripts often target Chrome (the most common for automation). Chromium-based browsers (Chrome, new Edge, Brave, etc.) share these fingerprint traits. Edge, for example, will also have `navigator.webdriver=true` if automated via Selenium, and can be fixed in the same way. Firefox has its own fingerprint; fewer sites specifically target Firefox automation, but some signals (like the **`webdriver` flag and certain property definitions) still apply. Safari’s automation (via safaridriver) runs a full browser instance, so it’s less commonly flagged by typical “headless Chrome” checks, but it has other limitations (and fewer tools to modify fingerprints on the fly). **Tor Browser** aims to make all users look identical (the **“Tor Browser fingerprint”**). If you automate Tor and change things like the user agent or canvas behavior, you break that uniformity – making you stand out *more*. In other words, using CDP on Tor (via its Firefox debug protocol, if enabled) to alter fingerprints isn’t advisable; the whole point of Tor’s design is that *every* Tor user **shares the same fingerprint**, so it’s best not to deviate. Bot detection on Tor is more likely to flag any deviation from the expected Tor Browser profile rather than the standard automation markers of Chrome.

**Techniques for Evasion:** In practice, to evade bot detection you’ll combine browser launch flags and CDP commands: e.g. launch with `--disable-blink-features=AutomationControlled` and perhaps `--disable-web-security` (to avoid certain restrictions), then use CDP to override userAgent, navigator properties, and inject stealth scripts. Always test your automation against known detection scripts (like the open-source **Incolumitas bot test** ([Bot / Headless Chrome Detection Tests](https://bot.incolumitas.com/#:~:text=Bot%20%2F%20Headless%20Chrome%20Detection,Canvas%20Fingerprint%20WebGL)) or **CreepJS** score) to see if it’s detectable. Adjust the CDP tweaks accordingly. Keep in mind that advanced systems also use out-of-band detection like TLS fingerprinting (the pattern of the TLS handshake) ([How to Bypass Cloudflare With Selenium (2025 Guide) - ZenRows](https://www.zenrows.com/blog/selenium-cloudflare-bypass#:~:text=TLS%20Fingerprinting)) or traffic analysis, which you cannot easily spoof via CDP alone because those happen at the network level. For those, you might need a proxy solution (discussed next) or custom network stack. But for the majority of front-end detections (JS and rendering based), CDP gives you the hooks to modify the browser’s reported behavior to appear more human-like ([Puppeteer Fingerprinting: Explained & Bypassed - ZenRows](https://www.zenrows.com/blog/puppeteer-fingerprint#:~:text=Missing%20or%20inconsistent%20fingerprint%20parameters,settings%2C%20and%20adding%20stealth%20plugins)). 

## 3. Running Chrome in Docker (ARM64 & x86_64) 
Containerizing Chrome is common for consistent environments in automation. Here are considerations for running Chrome in Docker on both x86_64 and ARM64 architectures:

- **Using Official/Custom Builds:** Google Chrome for Linux is officially built for x86_64. On x86_64, you can often use the latest Chrome or Chromium package in a Debian/Ubuntu-based image. For example, you might base on `ubuntu:20.04` and install the Chrome .deb, or use a pre-made image (like Selenium’s standalone-chrome or the Puppeteer image). On **ARM64** (e.g. Apple M1, Raspberry Pi), there is no official Google Chrome binary. You rely on **Chromium builds** for ARM. Many Linux distros lag in Chromium versions for ARM64 ([Justin Ribeiro](https://justinribeiro.com/chronicle/2021/12/21/arm64-m1-silicon-chromium-build-added-to-chrome-headless-docker-container/#:~:text=This%20isn%E2%80%99t%20without%20issues,Yikes)) – for instance, Debian’s arm64 Chromium might be several versions behind latest Chrome ([Justin Ribeiro](https://justinribeiro.com/chronicle/2021/12/21/arm64-m1-silicon-chromium-build-added-to-chrome-headless-docker-container/#:~:text=This%20isn%E2%80%99t%20without%20issues,Yikes)). You can use these (or community builds) but be aware you might not have the newest features. Another option is to cross-compile or use a project that provides an ARM64 headless build. For example, the **Browserless.io** Docker image and others have started offering multi-arch support (sometimes by including an official Chrome for x86 and using QEMU emulation on ARM, or by using Chromium for ARM). There are also projects like `alpine-chrome` and `chromedp/docker-headless-shell` that ship a minimal Chromium; check their documentation for ARM64 support.

- **Docker Flags and Dependencies:** Chrome inside a container often needs additional flags because it’s not running with a normal desktop environment. Common flags include `--no-sandbox` (needed if running as root in container), `--disable-dev-shm-usage` (to avoid `/dev/shm` issues), `--disable-gpu` (since GPU drivers may not be available), and of course `--headless` if you don’t need a visible UI. In Docker, you typically run headless. If you need a UI (for debugging), you’d have to set up Xvfb or a VNC, which is beyond standard CDP usage. Also, Chrome may attempt to use the **DBus** system bus (for example, for device discovery, sandbox, or printing). On some minimal images, you’ll see errors like *“Failed to connect to the bus: No such file or directory”* ([Headless chromium in ubuntu docker container - Stack Overflow](https://stackoverflow.com/questions/66512149/headless-chromium-in-ubuntu-docker-container#:~:text=outputs)) ([Headless chromium in ubuntu docker container - Stack Overflow](https://stackoverflow.com/questions/66512149/headless-chromium-in-ubuntu-docker-container#:~:text=,No%20such%20file%20or%20directory)). The browser can still run headless despite the error, but to silence it you might need to include a DBus service. One solution on Alpine-based images is to install and run `dbus` (and related init) inside the container ([Headless chromium in ubuntu docker container - Stack Overflow](https://stackoverflow.com/questions/66512149/headless-chromium-in-ubuntu-docker-container#:~:text=Otherwise%20you%20can%20try%20adding%2Frunning,dbus)). For instance, adding: 

  ```Dockerfile
  RUN apk add dbus && mkdir -p /run/dbus \ 
      && dbus-daemon --system --fork
  ``` 

  in your Dockerfile can start a minimal dbus. This is often not strictly required for operation, but some Chrome features expect it. If you see **`/var/run/dbus/...: Connection refused`** errors, this is the remedy ([Headless chromium in ubuntu docker container - Stack Overflow](https://stackoverflow.com/questions/66512149/headless-chromium-in-ubuntu-docker-container#:~:text=Not%20working%20for%20me%20%3A,to%20socket%20%2Frun%2Fdbus%2Fsystem_bus_socket%3A%20Connection%20refused)) ([Headless chromium in ubuntu docker container - Stack Overflow](https://stackoverflow.com/questions/66512149/headless-chromium-in-ubuntu-docker-container#:~:text=If%20you%20are%20running%20on,Image%3A%20enter%20image%20description%20here)).

- **ARM64 Specific Issues:** On ARM/M1 hosts, if you cannot get a native Chrome/Chromium, one workaround is to run the x86_64 Chrome in emulation. Docker Desktop for Mac allows running Intel containers via Rosetta. Enabling “Use Rosetta for x86/amd64 emulation on Apple Silicon” lets you pull an x86 Chrome image and run it transparently on ARM ([Headless chromium in ubuntu docker container - Stack Overflow](https://stackoverflow.com/questions/66512149/headless-chromium-in-ubuntu-docker-container#:~:text=Add%20a%20comment%20%C2%A0)). The downside is performance loss due to emulation. Native ARM64 Chromium in Docker, as mentioned, may be older. Some projects (like Justin Ribeiro’s headless Chromium containers) specifically provide an ARM64 tag, but caution that it might be behind on security patches ([Justin Ribeiro](https://justinribeiro.com/chronicle/2021/12/21/arm64-m1-silicon-chromium-build-added-to-chrome-headless-docker-container/#:~:text=This%20isn%E2%80%99t%20without%20issues,Yikes)) ([Justin Ribeiro](https://justinribeiro.com/chronicle/2021/12/21/arm64-m1-silicon-chromium-build-added-to-chrome-headless-docker-container/#:~:text=So%2C%20while%20this%20build%20will,problems%2C%20file%20bugs%20on%20the)). Always weigh the need for newest Chrome features vs. the convenience of running on ARM. If using an older Chromium, verify that the CDP commands you need are supported (e.g., very old versions might not have newer CDP domains or might require different parameters).

- **Avoiding Licensing Issues:** The **Chrome** binary is proprietary, while **Chromium** is open-source. Some Docker images bundle official Chrome – in theory, you should ensure you have permission (Google’s license typically allows personal use but not unrestricted redistribution). To be safe, many opt for Chromium in Docker to avoid any licensing grey area. If you require official Chrome (for features like Widevine DRM or latest V8), you might accept the license and install it during build (e.g. download the .deb in Dockerfile). If not, using Chromium (or a project like **Playwright** that provides Chromium) might be easier legally. Images like **browserless** have either licensing arrangements or use Chromium; if you want full control, you can build your own image using the open-source Chromium from Google’s Linux repos or even the Chrome Dev/Beta channels (Google provides standalone downloads that you could curl in a Dockerfile with license acceptance).

- **Proxies and Networking in Docker:** If your automation needs to go through a proxy (for development, scraping from behind corporate network, or IP rotation), you must configure Chrome to use it. Simply setting environment variables in Docker (like `http_proxy`) won’t affect Chrome, since Chrome doesn’t automatically use env vars – it needs explicit proxy settings. The most straightforward way is to launch Chrome with the `--proxy-server` flag. For example, `--proxy-server="http://myproxy:3128"` will route Chrome’s traffic through an HTTP proxy. You can specify different proxies for different protocols using a semicolon-separated list, e.g. `--proxy-server="http=proxy1:8080;https=proxy2:8080"` ([Proxy support in Chrome](https://chromium.googlesource.com/chromium/src/+/HEAD/net/docs/proxy.md#:~:text=If%20instead%20we%20wanted%20to,This%20now%20expands%20to)) ([Proxy support in Chrome](https://chromium.googlesource.com/chromium/src/+/HEAD/net/docs/proxy.md#:~:text=,as%20SOCKSv4%20rather%20than%20HTTP)). If you omit the scheme, Chrome assumes a format (it might default to HTTP or SOCKS depending on context; it’s safer to include the scheme as shown to be explicit ([Proxy support in Chrome](https://chromium.googlesource.com/chromium/src/+/HEAD/net/docs/proxy.md#:~:text=The%20command%20line%20above%20uses,format%2C%20with%20some%20additional%20features))). Chrome’s proxy flag applies to web requests made by pages – it will proxy `http://` and `https://` URL fetches, and even WebSocket connections follow the “other proxies” rules (generally they use the same proxy as HTTPS if configured) ([Proxy support in Chrome](https://chromium.googlesource.com/chromium/src/+/HEAD/net/docs/proxy.md#:~:text=Mapping%20WebSockets%20URLs%20to%20a,proxy)). 

  In Docker, ensure that the container can reach the proxy address (network settings, DNS, etc., should be configured). If your proxy requires authentication, Chrome will respond to a 407 Proxy Auth by attempting to use the system’s credentials service or prompt – which isn’t accessible in headless mode. Since CDP doesn’t have a direct command to set proxy auth, you may need to embed credentials in the proxy URL (e.g. `--proxy-server="http://user:pass@proxy:3128"`) or handle the authentication at the network level. Alternatively, use a tool like **mitmproxy** or a custom script as an intermediary if complex proxy logic is needed. 

- **Compatibility with Docker Networking:** For local development behind a proxy, you might also set `--proxy-bypass-list` to exclude certain domains (like internal resources) from the proxy ([Proxy support in Chrome](https://chromium.googlesource.com/chromium/src/+/HEAD/net/docs/proxy.md#:~:text=There%20are%20a%20lot%20of,discussed%20in%20other%20sections)) ([Proxy support in Chrome](https://chromium.googlesource.com/chromium/src/+/HEAD/net/docs/proxy.md#:~:text=%2A%20proxies%20for%20HTTPS%20,%60http%3A%2F%2Ffoo%3A8080)). This can be important if your container needs to access both internal and external addresses. Also, remember that DNS resolution might happen outside the proxy by default. In Chrome, DNS for proxied requests is usually done by the proxy server (especially for SOCKS proxies, Chrome will let the proxy do DNS) ([Proxy support in Chrome](https://chromium.googlesource.com/chromium/src/+/HEAD/net/docs/proxy.md#:~:text=and%20allows%20for%20name%20resolution,be%20deferred%20to%20the%20proxy)) ([Proxy support in Chrome](https://chromium.googlesource.com/chromium/src/+/HEAD/net/docs/proxy.md#:~:text=In%20Chrome%20when%20a%20proxy%27s,always%20use%20proxy%20side%20resolution)). But for HTTP proxies, DNS is typically done by the proxy as well (since you send the hostname to the proxy). In Docker, ensure the container’s DNS is correctly set (via Docker `--dns` option or default to host DNS) so that even direct DNS queries (for non-proxied URLs or the proxy hostname itself) can resolve.

- **Running Headless vs Headful in Docker:** Headless mode is recommended in containers (no GUI needed). Chrome’s headless mode in recent versions behaves very much like regular Chrome, minus the visible UI, and it *now supports* nearly all APIs (earlier headless had some feature gaps which are mostly closed). If you do need to run full Chrome (headful) in Docker (for example, to debug with VNC), you’ll need an X11 server or xvfb in the container, which adds complexity (and you’d still use CDP to control it). In most cases, using `--headless` is simpler and using CDP/WebSockets to control it is the same as with a visible browser.

**Troubleshooting Docker Issues:** If Chrome fails to launch in Docker, check the error logs. A common issue is sandboxing – if you see errors about needing `--no-sandbox`, it means Chrome doesn’t want to run as root without the flag. Using a non-root user in the container can avoid needing `--no-sandbox`, but many opt to just add the flag for simplicity. Another issue is /dev/shm (shared memory) being too small by default; using `--disable-dev-shm-usage` makes Chrome use regular memory instead ([Headless chromium in ubuntu docker container - Stack Overflow](https://stackoverflow.com/questions/66512149/headless-chromium-in-ubuntu-docker-container#:~:text=To%20have%20real%20headless%20chromium,to%20your%20line%20as%20follows)). On ARM, if you get illegal instruction errors, it could mean you’re accidentally running the wrong binary (e.g., trying to run x86 Chrome on ARM without emulation). In that case, verify your image architecture or enable the emulator as mentioned.

## 4. CDP Payload Validation & Proxy Configuration in Automation 
**Constructing Valid CDP Payloads:** When sending raw JSON over WebSockets, it’s crucial to match the exact structure expected by the browser’s CDP implementation. Chrome publishes a protocol definition (a JSON schema of all commands, types, events) for each version. Tools and libraries (like Selenium’s DevTools interface or Puppeteer’s internal driver) are built around these schemas. If you are crafting raw payloads, follow these best practices:

- **Use the Browser’s Protocol Version:** You can query the running browser for its protocol version and supported domains. For instance, sending the command `Browser.getVersion` will return fields including `"protocolVersion"` and the Chrome product version. This can hint if you’re in sync (e.g., protocolVersion "1.3" is a generic marker, but the Chrome version “112.0.x” tells you which JSON protocol spec to refer to). Alternatively, browse the official **Chrome DevTools Protocol** documentation for the specific Chrome version or the “tip-of-tree” if you’re on Canary ([GitHub - aslushnikov/getting-started-with-cdp: Getting Started With Chrome DevTools Protocol](https://github.com/aslushnikov/getting-started-with-cdp#:~:text=Stable%20vs%20Experimental%20methods)). The documentation (on the Chrome DevTools GitHub pages) lists each domain’s commands and parameters. Verify your JSON keys and parameter types against that. An incorrect field (e.g., a typo in method name or wrong type) usually yields an error response from Chrome – it won’t crash, but it won’t do what you expect either.

- **Browser Differences:** As noted, not all browsers implement all CDP domains. So, if you intend your automation to work across browsers, you may need conditionals. For example, **Chromium-based** browsers all support the `Network.setUserAgentOverride` command, but **Firefox’s CDP** (if enabled) might not. Likewise, `Page.addScriptToEvaluateOnNewDocument` is Chrome-only. If you connect to a browser that doesn’t support a method, you’ll typically get an error like `{"id":…,"error":{"code": -32601, "message": "Method not found"}}`. Design your automation to handle or ignore such responses gracefully. In cross-browser frameworks, a common strategy is to use **capabilities detection**: e.g., ask `Browser.getVersion` or a dummy command to infer “is this Chrome or Firefox?” and then branch logic. In the future, the WebDriver BiDi protocol aims to standardize this across browsers, but until then raw CDP will be mostly Chrome/Chromium-centric ([Deprecating CDP Support in Firefox: Embracing the Future with WebDriver ...](https://fxdx.dev/deprecating-cdp-support-in-firefox-embracing-the-future-with-webdriver-bidi/#:~:text=Deprecating%20CDP%20Support%20in%20Firefox%3A,the%20introduction%20of%20the)) ([Deprecation of experimental CDP support in Firefox - Google Groups](https://groups.google.com/a/chromium.org/g/chromium-dev/c/YtjFJHE8tFw#:~:text=I%20would%20like%20to%20inform,Key%20Points)).

- **Validating Responses:** When you send a command, you can verify it succeeded by examining the response message. A successful response from CDP will have a matching `"id"` and a `"result"` object (even if empty). If something went wrong, you’ll get an `"error"` object instead of `"result"`. For example, if you send a `Network.getResponseBody` too early (before enabling Network), Chrome might respond with an error indicating the domain is not enabled. Use these errors for troubleshooting – they often tell you that you need to call an `"enable"` method or that a given parameter is invalid. During development, it’s useful to run a **Protocol monitor** (Chrome’s DevTools has a Protocol Monitor panel you can enable, which shows you all CDP messages when you use the DevTools UI ([Protocol monitor: View and send CDP requests - Chrome DevTools](https://developer.chrome.com/docs/devtools/protocol-monitor#:~:text=DevTools%20developer,Check%20the))). You can also use a logging proxy for CDP (like `chromedp-proxy`) to see the wire traffic ([GitHub - chromedp/chromedp-proxy: chromedp-proxy is a logging proxy for ...](https://github.com/chromedp/chromedp-proxy#:~:text=GitHub%20,localhost%20to%20a%20remote%20endpoint)). This helps in learning the correct sequences and payloads. Some engineers use DevTools itself to figure out the protocol: for example, using the Chrome DevTools UI to perform an action (like toggling a setting) and watching in the Protocol Monitor to see which CDP commands were sent.

- **Working with Proxies via CDP:** As mentioned, the primary way to use a network proxy is to launch the browser with the appropriate command-line flags (since CDP does not have a direct “set proxy” command at runtime for Chromium). Ensure your automation script passes `--proxy-server` (and `--proxy-bypass-list` or `--proxy-pac-url` if needed) when launching Chrome. If you are controlling an already-running browser via CDP and need to set a proxy, you’re out of luck – Chrome won’t let you change proxy settings on the fly via CDP. In such cases, you’d have to restart the browser with different settings or use a lower-level network trick. One advanced workaround is to intercept requests via `Fetch.enable` (a CDP domain) and manually re-route them through a proxy server socket within your automation logic, but this is complex and essentially re-implements proxying. It’s far easier to start the browser pointed at the proxy. 

  Different browsers handle proxies differently: **Chromium** supports the flags as described. **Firefox** (in WebDriver) would use a WebDriver capability or preference (not CDP) – you can set `network.proxy.*` preferences in the Firefox profile for HTTP/SSL/SOCKS proxies. **Edge** uses the same flags as Chrome (since it’s Chromium under the hood). **Safari** uses system proxy settings (since there’s no headless mode, it uses whatever macOS is set to, unless you use safaridriver which doesn’t expose a proxy capability directly). So, for cross-browser automation, you often configure proxies outside of CDP (via WebDriver desired capabilities or environment). In Chrome’s case, do it at launch. 

- **Validating Proxy Setup:** To ensure your proxy is actually in use, you can perform a simple test in automation: navigate to a URL that returns your IP (like `https://api.ipify.org?format=json`) and check if the IP seen is the proxy’s IP. Or inspect the Chrome logs – if misconfigured, Chrome might log a proxy connection error. Also note that certain local addresses (like `localhost` or `127.0.0.1`) may bypass the proxy by default. If you *want* even local traffic to go through proxy (for example, if your proxy handles all routes), use `--proxy-bypass-list="<-loopback>"` to not bypass localhost ([Configuring a SOCKS proxy server in Chrome - The Chromium Projects](https://www.chromium.org/developers/design-documents/network-stack/socks-proxy/#:~:text=NOTE%3A%20proxying%20of%20ftp%3A%2F%2F%20URLs,not%20disabled%20in%20Chrome)). Conversely, if you want to bypass proxy for specific domains, list them (e.g., `--proxy-bypass-list="*.mycompany.internal"`).

**Testing and Best Practices:** Always test your raw CDP automation against the real browser manually first. It can be helpful to start Chrome with `--remote-debugging-port=9222` and then use a tool (even a simple `wscat` or Python websocket client) to send a few known-good commands (like `Page.navigate` and `Runtime.evaluate`). This will build confidence that your JSON is formatted correctly. Pay attention to case sensitivity in method names and enum values. If possible, refer to the official **protocol definitions** for your browser: Chrome’s are on the Chromium GitHub ([Chrome DevTools Protocol - GitHub Pages](https://chromedevtools.github.io/devtools-protocol/#:~:text=Chrome%20DevTools%20Protocol%20,of%20commands%20it%20supports)) (or the `devtools-protocol` NPM package contains the latest schema). By validating your payloads against these definitions (you could even code-generate classes from the JSON schema), you avoid mistakes. 

Finally, when implementing an automation solution with raw CDP, it’s wise to incorporate some **retry and timeout logic**. WebSocket connections can drop (e.g., if Chrome crashes or closes), so handle reconnects. Also, if a command is sent (like `Page.navigate`), you might want to wait for an event (like `Page.loadEventFired`) or at least the response before sending the next command, to avoid overwhelming the browser. Using the `id`/response correlation, you can implement a simple promise-like system (as shown in the example SEND function in the Puppeteer repo) ([GitHub - aslushnikov/getting-started-with-cdp: Getting Started With Chrome DevTools Protocol](https://github.com/aslushnikov/getting-started-with-cdp#:~:text=File%3A%20)) – i.e., send the JSON and wait until you get a message with the same `id` back. This ensures the command executed successfully. Maintaining sessionId routing is also important if you have multiple tabs. 

By following these practices – establishing the WebSocket connection properly, sending well-formed JSON commands, accounting for differences in browser support, evading detection through clever CDP injections, and configuring the environment (Docker, proxy, etc.) – you can build a robust automation solution that leverages CDP to its fullest capabilities.

**Sources:**

1. Alexey Shpilman, *Getting Started with CDP* – Example of connecting via WebSocket, target discovery, and sessions ([GitHub - aslushnikov/getting-started-with-cdp: Getting Started With Chrome DevTools Protocol](https://github.com/aslushnikov/getting-started-with-cdp#:~:text=When%20Chromium%20is%20started%20with,output%20looks%20something%20like%20this)) ([GitHub - aslushnikov/getting-started-with-cdp: Getting Started With Chrome DevTools Protocol](https://github.com/aslushnikov/getting-started-with-cdp#:~:text=connected%21%20Sending%20Target.setDiscoverTargets%20%7B%22method%22%3A%22Target.targetCreated%22%2C%22params%22%3A%7B%22targetInfo%22%3A%7B%22targetId%22%3A%2238555cf%20e,result)).  
2. Chrome DevTools Protocol Official Docs – Description of protocol structure and domains ([GitHub - aslushnikov/getting-started-with-cdp: Getting Started With Chrome DevTools Protocol](https://github.com/aslushnikov/getting-started-with-cdp#:~:text=Clients%20can%20create%20a%20WebSocket,params)) ([GitHub - aslushnikov/getting-started-with-cdp: Getting Started With Chrome DevTools Protocol](https://github.com/aslushnikov/getting-started-with-cdp#:~:text=A%20few%20things%20to%20notice%3A)).  
3. Puppeteer GitHub (CDP Sessions) – Using Target.attachToTarget and Page.navigate with sessionId ([GitHub - aslushnikov/getting-started-with-cdp: Getting Started With Chrome DevTools Protocol](https://github.com/aslushnikov/getting-started-with-cdp#:~:text=%2F%2F%20Navigate%20the%20page%20using,)) ([GitHub - aslushnikov/getting-started-with-cdp: Getting Started With Chrome DevTools Protocol](https://github.com/aslushnikov/getting-started-with-cdp#:~:text=inside%20the%20session%2C%20but%20different,send%20it%20to%20the%20page)).  
4. Jarrod Overson, *Using CDP with Puppeteer* – Network interception via `Network.setRequestInterception` and `Network.continueInterceptedRequest` ([Using Chrome Devtools Protocol with Puppeteer ](https://jarrodoverson.com/post/using-chrome-devtools-protocol-with-puppeteer-737a1300bac0/#:~:text=await%20client)) ([Using Chrome Devtools Protocol with Puppeteer ](https://jarrodoverson.com/post/using-chrome-devtools-protocol-with-puppeteer-737a1300bac0/#:~:text=After%20setting%20our%20interception%20we,continueInterceptedRequest)).  
5. Stack Overflow – *Modifying navigator.webdriver to prevent detection* – Example using `Page.addScriptToEvaluateOnNewDocument` ([java - Selenium webdriver: Modifying navigator.webdriver flag to prevent selenium detection - Stack Overflow](https://stackoverflow.com/questions/53039551/selenium-webdriver-modifying-navigator-webdriver-flag-to-prevent-selenium-detec#:~:text=driver.execute_cdp_cmd%28,)) ([java - Selenium webdriver: Modifying navigator.webdriver flag to prevent selenium detection - Stack Overflow](https://stackoverflow.com/questions/53039551/selenium-webdriver-modifying-navigator-webdriver-flag-to-prevent-selenium-detec#:~:text=Since%20this%20question%20is%20related,is%20close%20with%20Remote%20Protocol)).  
6. ZenRows Blog – *Puppeteer Fingerprinting & Cloudflare* – Common anti-bot fingerprint methods (navigator.webdriver, HeadlessChrome UA, canvas fingerprint) ([Puppeteer Fingerprinting: Explained & Bypassed - ZenRows](https://www.zenrows.com/blog/puppeteer-fingerprint#:~:text=Missing%20or%20inconsistent%20fingerprint%20parameters,settings%2C%20and%20adding%20stealth%20plugins)) ([How to Bypass Cloudflare With Selenium (2025 Guide) - ZenRows](https://www.zenrows.com/blog/selenium-cloudflare-bypass#:~:text=Canvas%20Fingerprinting)).  
7. Stack Overflow – *Headless Chrome in Docker* – Required flags (`--remote-debugging-port`, etc.) and solving dbus issues on ARM ([Headless chromium in ubuntu docker container - Stack Overflow](https://stackoverflow.com/questions/66512149/headless-chromium-in-ubuntu-docker-container#:~:text=To%20have%20real%20headless%20chromium,to%20your%20line%20as%20follows)) ([Headless chromium in ubuntu docker container - Stack Overflow](https://stackoverflow.com/questions/66512149/headless-chromium-in-ubuntu-docker-container#:~:text=If%20you%20are%20running%20on,Image%3A%20enter%20image%20description%20here)).  
8. Chromium Proxy Settings Documentation – Usage of `--proxy-server` with schemes and behavior for WebSocket URLs ([Proxy support in Chrome](https://chromium.googlesource.com/chromium/src/+/HEAD/net/docs/proxy.md#:~:text=,This%20now%20expands%20to)) ([Proxy support in Chrome](https://chromium.googlesource.com/chromium/src/+/HEAD/net/docs/proxy.md#:~:text=,as%20SOCKSv4%20rather%20than%20HTTP)).


# Examples
Sure! Below are step-by-step examples of how to interact with Chrome DevTools Protocol (CDP) via **raw WebSockets** in Python using the `websockets` library. Each section contains:

1. **Connecting to Chrome via CDP WebSocket**
2. **Opening a new tab**
3. **Navigating to a URL**
4. **Waiting for the page to finish loading**
5. **Capturing the rendered DOM**
6. **Extracting full page HTML including dynamically rendered JavaScript content**
7. **Capturing a screenshot of the page (optional)**
8. **Closing the tab**

---

### 🚀 **1. Connecting to Chrome DevTools WebSocket**
First, **start Chrome with Remote Debugging enabled**:

```sh
chrome --remote-debugging-port=9222 --headless --disable-gpu --disable-extensions --disable-software-rasterizer
```
> You can also use `chromium` instead of `chrome` if needed.

Now, retrieve the WebSocket URL dynamically.

```python
import requests

def get_websocket_debugger_url():
    response = requests.get("http://localhost:9222/json/version")
    data = response.json()
    return data["webSocketDebuggerUrl"]

ws_url = get_websocket_debugger_url()
print(f"WebSocket URL: {ws_url}")
```
---

### 📌 **2. Opening a New Tab**
To open a new tab, we need to use `Target.createTarget`. This creates a new blank tab.

#### **CDP Payload:**
```json
{
  "id": 1,
  "method": "Target.createTarget",
  "params": {
    "url": "about:blank"
  }
}
```

#### **Python WebSocket Implementation**
```python
import asyncio
import websockets
import json

async def open_new_tab(ws_url):
    async with websockets.connect(ws_url) as websocket:
        payload = {
            "id": 1,
            "method": "Target.createTarget",
            "params": {"url": "about:blank"}
        }
        await websocket.send(json.dumps(payload))

        response = await websocket.recv()
        response_data = json.loads(response)
        target_id = response_data["result"]["targetId"]

        print(f"New tab created with Target ID: {target_id}")
        return target_id

target_id = asyncio.run(open_new_tab(ws_url))
```

---

### 🌍 **3. Navigating to a URL**
Now, we need to **attach to the newly created tab** and **navigate to a webpage**.

#### **CDP Payload:**
```json
{
  "id": 2,
  "method": "Target.attachToTarget",
  "params": {
    "targetId": "<target_id>",
    "flatten": True
  }
}
```

```json
{
  "id": 3,
  "method": "Page.navigate",
  "params": {
    "url": "https://example.com"
  }
}
```

#### **Python WebSocket Implementation**
```python
async def navigate_to_url(ws_url, target_id):
    async with websockets.connect(ws_url) as websocket:
        # Attach to the tab
        attach_payload = {
            "id": 2,
            "method": "Target.attachToTarget",
            "params": {"targetId": target_id, "flatten": True}
        }
        await websocket.send(json.dumps(attach_payload))
        attach_response = await websocket.recv()
        session_id = json.loads(attach_response)["result"]["sessionId"]

        # Navigate to the URL
        navigate_payload = {
            "id": 3,
            "sessionId": session_id,
            "method": "Page.navigate",
            "params": {"url": "https://example.com"}
        }
        await websocket.send(json.dumps(navigate_payload))

        print(f"Navigated to https://example.com in tab {target_id}")

        return session_id

session_id = asyncio.run(navigate_to_url(ws_url, target_id))
```

---

### ⏳ **4. Waiting for the Page to Finish Loading**
We listen for the **Page.loadEventFired** event to confirm the page has fully loaded.

#### **Python WebSocket Implementation**
```python
async def wait_for_page_load(ws_url, session_id):
    async with websockets.connect(ws_url) as websocket:
        while True:
            response = await websocket.recv()
            data = json.loads(response)
            if data.get("method") == "Page.loadEventFired":
                print("Page load completed.")
                break

asyncio.run(wait_for_page_load(ws_url, session_id))
```

---

### 📰 **5. Extracting the Rendered DOM**
Since many websites use React/JavaScript, we need to wait until the JavaScript executes before extracting the final HTML.

#### **CDP Payload:**
```json
{
  "id": 4,
  "method": "Runtime.evaluate",
  "params": {
    "expression": "document.documentElement.outerHTML"
  }
}
```

#### **Python WebSocket Implementation**
```python
async def get_page_html(ws_url, session_id):
    async with websockets.connect(ws_url) as websocket:
        payload = {
            "id": 4,
            "sessionId": session_id,
            "method": "Runtime.evaluate",
            "params": {
                "expression": "document.documentElement.outerHTML"
            }
        }
        await websocket.send(json.dumps(payload))
        response = await websocket.recv()
        html_content = json.loads(response)["result"]["result"]["value"]

        print(f"Extracted HTML:\n{html_content[:500]}")  # Printing first 500 chars
        return html_content

html_content = asyncio.run(get_page_html(ws_url, session_id))
```

---

### 📸 **6. Capturing a Screenshot**
We can capture a full-page screenshot in **base64** format and save it as an image.

#### **CDP Payload:**
```json
{
  "id": 5,
  "method": "Page.captureScreenshot",
  "params": {
    "format": "png",
    "fromSurface": True
  }
}
```

#### **Python WebSocket Implementation**
```python
import base64

async def capture_screenshot(ws_url, session_id):
    async with websockets.connect(ws_url) as websocket:
        payload = {
            "id": 5,
            "sessionId": session_id,
            "method": "Page.captureScreenshot",
            "params": {"format": "png", "fromSurface": True}
        }
        await websocket.send(json.dumps(payload))
        response = await websocket.recv()
        screenshot_data = json.loads(response)["result"]["data"]

        # Save the image
        with open("screenshot.png", "wb") as f:
            f.write(base64.b64decode(screenshot_data))

        print("Screenshot saved as screenshot.png")

asyncio.run(capture_screenshot(ws_url, session_id))
```

---

### 🔄 **7. Closing the Tab**
Once we're done, we should close the tab using `Target.closeTarget`.

#### **CDP Payload:**
```json
{
  "id": 6,
  "method": "Target.closeTarget",
  "params": {
    "targetId": "<target_id>"
  }
}
```

#### **Python WebSocket Implementation**
```python
async def close_tab(ws_url, target_id):
    async with websockets.connect(ws_url) as websocket:
        payload = {
            "id": 6,
            "method": "Target.closeTarget",
            "params": {"targetId": target_id}
        }
        await websocket.send(json.dumps(payload))
        response = await websocket.recv()
        print("Tab closed.")

asyncio.run(close_tab(ws_url, target_id))
```

---

### ✅ **Final Notes**
- This approach **bypasses Selenium and Puppeteer**, which often trigger bot detection.
- By extracting HTML **after JavaScript execution**, this method captures **fully rendered** pages.
- **Running inside Docker**: Ensure Chrome runs with `--remote-debugging-port=9222` and `--disable-gpu` to avoid rendering issues.
- **Proxy Support**: Use `--proxy-server="http://proxy_ip:port"` when launching Chrome if needed.

This implementation provides a **full CDP-based browser automation pipeline** with minimal detection risk. 🚀 Let me know if you need additional refinements!



# Testing CDP with CLI tools

Absolutely! Below are the equivalent **cURL** and **wscat** (WebSocket) commands to interact with Chrome's CDP. This allows for easy manual testing and verification.

---

## 🔧 **Step 1: Start Chrome with Remote Debugging**
Run Chrome with the `--remote-debugging-port` flag:
```sh
chrome --remote-debugging-port=9222 --headless --disable-gpu --disable-extensions --disable-software-rasterizer
```
or for Chromium:
```sh
chromium --remote-debugging-port=9222 --headless --disable-gpu
```

---

## 🌎 **Step 2: Get WebSocket Debugger URL**
To retrieve the WebSocket URL, use:
```sh
curl -s http://localhost:9222/json/version | jq -r '.webSocketDebuggerUrl'
```
> If `jq` is not installed, you can simply use:
```sh
curl -s http://localhost:9222/json/version
```
This will return:
```json
{
  "webSocketDebuggerUrl": "ws://localhost:9222/devtools/browser/xxxxx"
}
```
Copy the WebSocket URL for use with `wscat`.

---

## 🆕 **Step 3: Open a New Tab**
Use:
```sh
curl -X POST http://localhost:9222/json/new
```
This returns:
```json
{
  "id": "TARGET_ID",
  "title": "",
  "url": "about:blank",
  "webSocketDebuggerUrl": "ws://localhost:9222/devtools/page/xxxxxxxx"
}
```
Copy the **WebSocketDebuggerUrl** for the next steps.

---

## 🛠️ **Step 4: Connect to the WebSocket Using `wscat`**
Install `wscat` if you don’t have it:
```sh
npm install -g wscat
```
Now, connect:
```sh
wscat -c ws://localhost:9222/devtools/page/xxxxxxxx
```

---

## 📡 **Step 5: Navigate to a URL**
Once connected via `wscat`, send this JSON payload to navigate:
```json
{ "id": 1, "method": "Page.navigate", "params": { "url": "https://example.com" } }
```
Expected response:
```json
{ "id": 1, "result": { "frameId": "xxxx" } }
```

---

## ⏳ **Step 6: Wait for the Page to Load**
Listen for the `Page.loadEventFired` event:
```json
{ "method": "Page.loadEventFired", "params": { "timestamp": 123456.789 } }
```

---

## 📰 **Step 7: Extract Rendered HTML**
Send:
```json
{ "id": 2, "method": "Runtime.evaluate", "params": { "expression": "document.documentElement.outerHTML" } }
```
This returns:
```json
{
  "id": 2,
  "result": {
    "result": {
      "type": "string",
      "value": "<html>...</html>"
    }
  }
}
```

---

## 📸 **Step 8: Capture Screenshot**
Send:
```json
{ "id": 3, "method": "Page.captureScreenshot", "params": { "format": "png", "fromSurface": true } }
```
Response:
```json
{
  "id": 3,
  "result": {
    "data": "iVBORw0KGgoAAAANS..."
  }
}
```
Save the base64 string as an image:
```sh
echo "iVBORw0KGgoAAAANS..." | base64 -d > screenshot.png
```

---

## 🔄 **Step 9: Close the Tab**
Send:
```json
{ "id": 4, "method": "Target.closeTarget", "params": { "targetId": "xxxxxxxx" } }
```
Response:
```json
{ "id": 4, "result": { "success": true } }
```

---

## 🏆 **Final Thoughts**
- You can **manually test all CDP commands** with `wscat` before coding.
- Using `curl`, you can **automate** simple actions.
- For **automation**, WebSockets in Python provide full control.

This method provides **quick validation** without writing code! 🚀 Let me know if you need further refinements.
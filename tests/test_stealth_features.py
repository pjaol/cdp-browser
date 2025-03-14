"""
Comprehensive tests for stealth features.

This module contains tests for each stealth feature listed in the status table.
Tests are marked with appropriate xfail markers based on current implementation status.
"""

import pytest
from pytest_asyncio import fixture
import asyncio
from cdp_browser.browser.stealth import StealthBrowser
from cdp_browser.browser.stealth.profile import StealthProfile
import logging
import json
import os
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@fixture(scope="function")
async def stealth_browser():
    """Create a stealth browser instance with maximum protection."""
    profile = StealthProfile(
        level="maximum",
        user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        window_size={"width": 1920, "height": 1080},
        languages=["en-US", "en"]
    )
    
    async with StealthBrowser(profile=profile) as browser:
        yield browser

@pytest.mark.asyncio
async def test_webdriver_property(stealth_browser):
    """Test WebDriver property emulation."""
    page = await stealth_browser.create_page()
    try:
        # Test that webdriver property exists but is set to false (like in real Chrome)
        result = await page.evaluate("""
            () => {
                // Safely get property descriptor
                const getDescriptor = () => {
                    try {
                        return Object.getOwnPropertyDescriptor(navigator, 'webdriver');
                    } catch (e) {
                        return null;
                    }
                };
                
                const descriptor = getDescriptor();
                
                const results = {
                    // Property should exist but be false
                    directAccess: navigator.webdriver === false,
                    propertyExists: 'webdriver' in navigator,
                    
                    // Property should be properly defined
                    hasOwnProperty: navigator.hasOwnProperty('webdriver'),
                    
                    // Descriptor details (if available)
                    descriptorExists: descriptor !== null,
                    descriptorConfigurable: descriptor ? descriptor.configurable : 'N/A',
                    descriptorEnumerable: descriptor ? descriptor.enumerable : 'N/A',
                    
                    // Edge case checks
                    notUndefined: navigator.webdriver !== undefined,
                    notNull: navigator.webdriver !== null,
                    
                    // Make sure other automation indicators are not present
                    noSelenium: !('selenium' in navigator),
                    noCDP: !('cdp' in navigator),
                    noDriver: !('driver' in navigator)
                };
                return results;
            }
        """)
        
        # Log detailed results
        logger.info(f"WebDriver property test results:")
        for key, value in result.items():
            logger.info(f"{key}: {value}")
        
        # Check critical assertions
        assert result['directAccess'], "navigator.webdriver should be false"
        assert result['propertyExists'], "webdriver property should exist in navigator"
        assert result['notUndefined'], "webdriver should not be undefined"
        assert result['notNull'], "webdriver should not be null"
        assert result['noSelenium'], "selenium property should not exist"
        assert result['noCDP'], "cdp property should not exist"
        assert result['noDriver'], "driver property should not exist"
        
        # Log descriptor information (informative, not critical)
        if not result['descriptorExists']:
            logger.warning("Property descriptor for webdriver could not be obtained")
        
        logger.info("WebDriver property correctly emulated")
    finally:
        await page.close()

@pytest.mark.asyncio
async def test_chrome_runtime(stealth_browser):
    """Test Chrome runtime emulation."""
    page = await stealth_browser.create_page()
    try:
        result = await page.evaluate("""
            () => {
                const results = {
                    chromeExists: typeof window.chrome === 'object',
                    runtimeExists: typeof window.chrome?.runtime === 'object',
                    runtimeMethods: {
                        getURL: typeof chrome?.runtime?.getURL === 'function',
                        connect: typeof chrome?.runtime?.connect === 'function',
                        sendMessage: typeof chrome?.runtime?.sendMessage === 'function'
                    },
                    appExists: typeof window.chrome?.app === 'object',
                    csiExists: typeof window.chrome?.csi === 'function',
                    loadTimesExists: typeof window.chrome?.loadTimes === 'function'
                };
                return results;
            }
        """)
        
        logger.info(f"Chrome runtime emulation results: {json.dumps(result, indent=2)}")
        assert result["chromeExists"], "Chrome object not found"
        assert result["runtimeExists"], "Chrome runtime not found"
        assert all(result["runtimeMethods"].values()), "Missing runtime methods"
        assert result["appExists"], "Chrome app not found"
        assert result["csiExists"], "Chrome csi not found"
        assert result["loadTimesExists"], "Chrome loadTimes not found"
    finally:
        await page.close()

@pytest.mark.asyncio
async def test_user_agent_spoofing(stealth_browser):
    """Test user agent consistency across different methods."""
    page = await stealth_browser.create_page()
    try:
        result = await page.evaluate("""
            () => {
                const results = {
                    navigatorUA: navigator.userAgent,
                    uaData: navigator.userAgentData ? {
                        platform: navigator.userAgentData.platform,
                        mobile: navigator.userAgentData.mobile,
                        brands: navigator.userAgentData.brands
                    } : null,
                    appVersion: navigator.appVersion,
                    platform: navigator.platform,
                    vendor: navigator.vendor
                };
                return results;
            }
        """)
        
        logger.info(f"User agent spoofing results: {json.dumps(result, indent=2)}")
        expected_ua = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
        assert result["navigatorUA"] == expected_ua, "Incorrect user agent"
        assert result["vendor"] == "Google Inc.", "Incorrect vendor"
        assert "Mac" in result["platform"], "Incorrect platform"
    finally:
        await page.close()

@pytest.mark.asyncio
async def test_window_size(stealth_browser):
    """Test window size consistency."""
    page = await stealth_browser.create_page()
    try:
        result = await page.evaluate("""
            () => {
                return {
                    innerWidth: window.innerWidth,
                    innerHeight: window.innerHeight,
                    outerWidth: window.outerWidth,
                    outerHeight: window.outerHeight,
                    devicePixelRatio: window.devicePixelRatio
                };
            }
        """)
        
        logger.info(f"Window size results: {json.dumps(result, indent=2)}")
        assert result["innerWidth"] == 1920, "Incorrect window width"
        assert result["innerHeight"] == 1080, "Incorrect window height"
        assert result["devicePixelRatio"] > 0, "Invalid devicePixelRatio"
    finally:
        await page.close()

@pytest.mark.asyncio
async def test_languages(stealth_browser):
    """Test language preferences consistency."""
    page = await stealth_browser.create_page()
    try:
        result = await page.evaluate("""
            () => {
                return {
                    languages: navigator.languages,
                    language: navigator.language,
                    browserLanguage: navigator.browserLanguage,
                    userLanguage: navigator.userLanguage
                };
            }
        """)
        
        logger.info(f"Language preferences results: {json.dumps(result, indent=2)}")
        assert result["languages"][0] == "en-US", "Incorrect primary language"
        assert result["language"] == "en-US", "Incorrect navigator.language"
    finally:
        await page.close()

@pytest.mark.asyncio
async def test_plugins(stealth_browser):
    """Test plugins emulation."""
    page = await stealth_browser.create_page()
    try:
        # Add more detailed debug info
        debug_info = await page.evaluate("""
            () => {
                const debug = {
                    pluginsObj: Object.prototype.toString.call(navigator.plugins),
                    pluginsLength: navigator.plugins ? navigator.plugins.length : 'undefined',
                    pluginsKeys: Object.keys(navigator.plugins || {}),
                    pluginsPropertyNames: Object.getOwnPropertyNames(navigator.plugins || {}),
                    isPluginsIterable: typeof navigator.plugins?.[Symbol.iterator] === 'function',
                    mimeTypesObj: Object.prototype.toString.call(navigator.mimeTypes),
                    mimeTypesLength: navigator.mimeTypes ? navigator.mimeTypes.length : 'undefined',
                    mimeTypesKeys: Object.keys(navigator.mimeTypes || {}),
                    mimeTypesPropertyNames: Object.getOwnPropertyNames(navigator.mimeTypes || {}),
                    isMimeTypesIterable: typeof navigator.mimeTypes?.[Symbol.iterator] === 'function',
                    hasPluginsBasic: typeof navigator.plugins === 'object' && navigator.plugins !== null,
                    chromeExists: typeof window.chrome === 'object',
                    runtimeExists: typeof window.chrome?.runtime === 'object'
                };
                
                return debug;
            }
        """)
        
        print(f"Plugins debug info: {json.dumps(debug_info, indent=2)}")
        logger.info(f"Plugins debug info: {json.dumps(debug_info, indent=2)}")
        
        # Check if any stealth patches have been applied
        stealth_check = await page.evaluate("""
            () => {
                return {
                    webdriver: navigator.webdriver,
                    hasChrome: !!window.chrome,
                    hasRuntime: !!(window.chrome && window.chrome.runtime),
                    vendor: navigator.vendor,
                    languages: navigator.languages,
                    userAgent: navigator.userAgent
                };
            }
        """)
        
        print(f"Stealth check: {json.dumps(stealth_check, indent=2)}")
        logger.info(f"Stealth check: {json.dumps(stealth_check, indent=2)}")
        
        # List all plugins directly
        plugins_list = await page.evaluate("""
            () => {
                const directPlugins = [];
                if (navigator.plugins) {
                    for (let i = 0; i < navigator.plugins.length; i++) {
                        const p = navigator.plugins[i];
                        if (p) {
                            directPlugins.push({
                                index: i,
                                name: p.name || 'undefined',
                                filename: p.filename || 'undefined',
                                description: p.description || 'undefined',
                                length: p.length || 0
                            });
                        } else {
                            directPlugins.push({index: i, name: 'null plugin'});
                        }
                    }
                }
                return directPlugins;
            }
        """)
        
        print(f"Direct plugins list: {json.dumps(plugins_list, indent=2)}")
        logger.info(f"Direct plugins list: {json.dumps(plugins_list, indent=2)}")
        
        result = await page.evaluate("""
            () => {
                // Helper function to safely convert to array
                const safeArrayFrom = (collection) => {
                    // Check if the collection exists and has length
                    if (!collection || typeof collection.length !== 'number') {
                        return [];
                    }
                    
                    // Manual conversion if Array.from doesn't work
                    const result = [];
                    for (let i = 0; i < collection.length; i++) {
                        if (collection[i]) {
                            result.push(collection[i]);
                        }
                    }
                    return result;
                };
                
                const plugins = safeArrayFrom(navigator.plugins).map(p => ({
                    name: p.name,
                    filename: p.filename,
                    description: p.description,
                    length: p.length
                }));

                const mimeTypes = safeArrayFrom(navigator.mimeTypes).map(mt => ({
                    type: mt.type,
                    description: mt.description,
                    suffixes: mt.suffixes
                }));

                return { plugins, mimeTypes };
            }
        """)

        print(f"Plugins emulation results: {json.dumps(result, indent=2)}")
        logger.info(f"Plugins emulation results: {json.dumps(result, indent=2)}")

        # Check for standard Chrome plugins
        plugin_names = [p["name"] for p in result["plugins"]]
        assert "Chrome PDF Plugin" in plugin_names, "Missing Chrome PDF Plugin"
        assert "Chrome PDF Viewer" in plugin_names, "Missing Chrome PDF Viewer"
        assert "Native Client" in plugin_names, "Missing Native Client"
        
        # Check for standard mime types
        mime_types = [mt["type"] for mt in result["mimeTypes"]]
        assert "application/pdf" in mime_types, "Missing PDF mime type"
        assert "application/x-nacl" in mime_types, "Missing Native Client mime type"
    finally:
        await page.close()

@pytest.mark.asyncio
@pytest.mark.xfail(reason="Worker user agent consistency still needs improvement")
async def test_worker_user_agent(stealth_browser):
    """Test Web Worker user agent consistency."""
    page = await stealth_browser.create_page()
    try:
        result = await page.evaluate("""
            () => new Promise((resolve) => {
                const mainUA = navigator.userAgent;
                const worker = new Worker(URL.createObjectURL(new Blob([`
                    self.postMessage(navigator.userAgent);
                `], { type: 'application/javascript' })));
                
                worker.onmessage = (e) => {
                    worker.terminate();
                    resolve({
                        mainUA,
                        workerUA: e.data,
                        matches: mainUA === e.data
                    });
                };
            })
        """)
        
        logger.info(f"Worker user agent results: {json.dumps(result, indent=2)}")
        assert result["matches"], "Worker user agent doesn't match main thread"
    finally:
        await page.close()

@pytest.mark.asyncio
async def test_function_prototypes(stealth_browser):
    """Test function prototype integrity."""
    page = await stealth_browser.create_page()
    try:
        result = await page.evaluate("""
            () => {
                const results = {
                    toString: Function.prototype.toString.toString().includes('[native code]'),
                    getOwnPropertyDescriptor: Object.getOwnPropertyDescriptor.toString().includes('[native code]'),
                    defineProperty: Object.defineProperty.toString().includes('[native code]'),
                    chrome: window.chrome ? chrome.runtime.connect.toString().includes('[native code]') : false
                };
                return results;
            }
        """)
        
        logger.info(f"Function prototype results: {json.dumps(result, indent=2)}")
        assert all(result.values()), "One or more function prototypes are not native-like"
    finally:
        await page.close()

@pytest.mark.asyncio
@pytest.mark.xfail(reason="iframe handling still needs improvement")
async def test_iframe_handling(stealth_browser):
    """Test iframe stealth consistency."""
    page = await stealth_browser.create_page()
    try:
        result = await page.evaluate("""
            () => new Promise((resolve) => {
                const iframe = document.createElement('iframe');
                document.body.appendChild(iframe);
                
                // Wait for iframe to load
                iframe.onload = () => {
                    const results = {
                        mainUA: navigator.userAgent,
                        iframeUA: iframe.contentWindow.navigator.userAgent,
                        mainWebdriver: navigator.webdriver,
                        iframeWebdriver: iframe.contentWindow.navigator.webdriver,
                        mainChrome: typeof window.chrome === 'object',
                        iframeChrome: typeof iframe.contentWindow.chrome === 'object'
                    };
                    document.body.removeChild(iframe);
                    resolve(results);
                };
                
                iframe.src = 'about:blank';
            })
        """)
        
        logger.info(f"iframe handling results: {json.dumps(result, indent=2)}")
        assert result["mainUA"] == result["iframeUA"], "User agent mismatch in iframe"
        assert result["mainWebdriver"] == result["iframeWebdriver"], "Webdriver property mismatch in iframe"
        assert result["mainChrome"] == result["iframeChrome"], "Chrome object mismatch in iframe"
    finally:
        await page.close()

@pytest.mark.asyncio
@pytest.mark.xfail(reason="JavaScript challenge response not fully implemented")
async def test_javascript_challenge(stealth_browser):
    """Test JavaScript challenge response capabilities."""
    page = await stealth_browser.create_page()
    try:
        result = await page.evaluate("""
            () => {
                // Simulate common challenge checks
                const results = {
                    functionLength: Function.toString.length === 0,
                    objectKeys: Object.keys(navigator).length > 0,
                    proxyDetection: (() => {
                        try {
                            const proxy = new Proxy({}, {});
                            return true;
                        } catch (e) {
                            return false;
                        }
                    })(),
                    errorStack: (() => {
                        try {
                            throw new Error('test');
                        } catch (e) {
                            return e.stack.includes('at');
                        }
                    })()
                };
                return results;
            }
        """)
        
        logger.info(f"JavaScript challenge results: {json.dumps(result, indent=2)}")
        assert all(result.values()), "One or more JavaScript challenge checks failed"
    finally:
        await page.close()

@pytest.mark.asyncio
@pytest.mark.xfail(reason="Mouse/keyboard behavior not implemented yet")
async def test_mouse_keyboard_behavior(stealth_browser):
    """Test human-like mouse and keyboard behavior."""
    page = await stealth_browser.create_page()
    try:
        # Navigate to a test page
        await page.navigate("about:blank")
        await page.evaluate("""
            () => {
                document.body.innerHTML = `
                    <input type="text" id="test-input">
                    <button id="test-button">Click Me</button>
                `;
            }
        """)
        
        # Test mouse movement
        await page.mouse_move(100, 100)  # Should implement natural movement
        await page.click("#test-button")
        
        # Test keyboard input
        await page.type("#test-input", "test typing")
        
        result = await page.evaluate("""
            () => {
                const events = [];
                const input = document.getElementById('test-input');
                const button = document.getElementById('test-button');
                
                ['mousemove', 'mousedown', 'mouseup', 'click'].forEach(event => {
                    button.addEventListener(event, () => events.push(event));
                });
                
                ['keydown', 'keyup', 'keypress'].forEach(event => {
                    input.addEventListener(event, () => events.push(event));
                });
                
                return events;
            }
        """)
        
        logger.info(f"Mouse/keyboard behavior results: {json.dumps(result, indent=2)}")
        assert len(result) > 0, "No mouse/keyboard events recorded"
    finally:
        await page.close()

@pytest.mark.asyncio
@pytest.mark.xfail(reason="Cloudflare Turnstile bypass not implemented")
async def test_cloudflare_turnstile(stealth_browser):
    """Test Cloudflare Turnstile handling."""
    page = await stealth_browser.create_page()
    try:
        await page.navigate("https://nowsecure.nl")  # Known Cloudflare protected site
        
        # Check for Turnstile challenge
        result = await page.evaluate("""
            () => {
                return {
                    hasTurnstile: document.querySelector('iframe[src*="challenges.cloudflare.com"]') !== null,
                    hasChallenge: document.querySelector('#challenge-form') !== null,
                    pageTitle: document.title
                };
            }
        """)
        
        logger.info(f"Cloudflare Turnstile results: {json.dumps(result, indent=2)}")
        assert not result["hasTurnstile"], "Turnstile challenge detected"
        assert not result["hasChallenge"], "Cloudflare challenge detected"
    finally:
        await page.close()

@pytest.mark.asyncio
@pytest.mark.xfail(reason="Browser fingerprinting protection partially implemented")
async def test_browser_fingerprinting(stealth_browser):
    """Test browser fingerprinting protection."""
    page = await stealth_browser.create_page()
    try:
        result = await page.evaluate("""
            () => {
                const canvas = document.createElement('canvas');
                const ctx = canvas.getContext('2d');
                ctx.textBaseline = "top";
                ctx.font = "14px 'Arial'";
                ctx.fillStyle = "#f60";
                ctx.fillRect(125,1,62,20);
                ctx.fillStyle = "#069";
                ctx.fillText("Hello, world!", 2, 15);
                
                const webgl = document.createElement('canvas').getContext('webgl');
                
                return {
                    canvasFingerprint: canvas.toDataURL(),
                    webglVendor: webgl.getParameter(webgl.VENDOR),
                    webglRenderer: webgl.getParameter(webgl.RENDERER),
                    fonts: document.fonts.check("12px NonExistentFont"),
                    audioContext: (() => {
                        try {
                            const audioContext = new (window.AudioContext || window.webkitAudioContext)();
                            const oscillator = audioContext.createOscillator();
                            const analyser = audioContext.createAnalyser();
                            const gain = audioContext.createGain();
                            const scriptProcessor = audioContext.createScriptProcessor(4096, 1, 1);
                            return true;
                        } catch (e) {
                            return false;
                        }
                    })()
                };
            }
        """)
        
        logger.info(f"Browser fingerprinting results: {json.dumps(result, indent=2)}")
        
        # Store the first fingerprint
        first_fingerprint = result["canvasFingerprint"]
        
        # Get a second fingerprint
        result2 = await page.evaluate("""
            () => {
                const canvas = document.createElement('canvas');
                const ctx = canvas.getContext('2d');
                ctx.textBaseline = "top";
                ctx.font = "14px 'Arial'";
                ctx.fillStyle = "#f60";
                ctx.fillRect(125,1,62,20);
                ctx.fillStyle = "#069";
                ctx.fillText("Hello, world!", 2, 15);
                return canvas.toDataURL();
            }
        """)
        
        # Fingerprints should be different due to our protection
        assert first_fingerprint != result2, "Canvas fingerprints are identical"
    finally:
        await page.close()

@pytest.mark.asyncio
@pytest.mark.xfail(reason="TLS fingerprinting not implemented yet")
async def test_tls_fingerprinting(stealth_browser):
    """Test TLS fingerprinting protection."""
    page = await stealth_browser.create_page()
    try:
        # Navigate to a TLS checking service
        await page.navigate("https://www.howsmyssl.com/a/check")
        
        result = await page.evaluate("""
            () => {
                return document.body.textContent;
            }
        """)
        
        tls_info = json.loads(result)
        logger.info(f"TLS fingerprinting results: {json.dumps(tls_info, indent=2)}")
        
        # Check for expected TLS configuration
        assert tls_info["tls_version"] == "TLS 1.3", "Unexpected TLS version"
        assert not tls_info["given_cipher_suites"].includes("TLS_AES_128_CCM"), "Unexpected cipher suite"
    finally:
        await page.close()

@pytest.mark.asyncio
@pytest.mark.xfail(reason="Audio/Canvas fingerprinting protection partially implemented")
async def test_audio_canvas_fingerprinting(stealth_browser):
    """Test audio and canvas fingerprinting protection."""
    page = await stealth_browser.create_page()
    try:
        result = await page.evaluate("""
            () => {
                // Test canvas fingerprinting
                const getCanvasFingerprint = () => {
                    const canvas = document.createElement('canvas');
                    const ctx = canvas.getContext('2d');
                    ctx.textBaseline = "top";
                    ctx.font = "14px 'Arial'";
                    ctx.fillStyle = "#f60";
                    ctx.fillRect(125,1,62,20);
                    ctx.fillStyle = "#069";
                    ctx.fillText("Hello, world!", 2, 15);
                    return canvas.toDataURL();
                };
                
                // Test audio fingerprinting
                const getAudioFingerprint = () => new Promise((resolve) => {
                    const audioContext = new (window.AudioContext || window.webkitAudioContext)();
                    const oscillator = audioContext.createOscillator();
                    const analyser = audioContext.createAnalyser();
                    const gain = audioContext.createGain();
                    const scriptProcessor = audioContext.createScriptProcessor(4096, 1, 1);
                    
                    gain.gain.value = 0; // Prevent sound
                    oscillator.type = "triangle";
                    oscillator.connect(analyser);
                    analyser.connect(scriptProcessor);
                    scriptProcessor.connect(gain);
                    gain.connect(audioContext.destination);
                    oscillator.start(0);
                    
                    const fingerprint = [];
                    scriptProcessor.onaudioprocess = (e) => {
                        const inputData = e.inputBuffer.getChannelData(0);
                        fingerprint.push(...inputData.slice(0, 10));
                        
                        if (fingerprint.length >= 10) {
                            oscillator.stop();
                            audioContext.close();
                            resolve(fingerprint);
                        }
                    };
                });
                
                return Promise.all([
                    Promise.resolve(getCanvasFingerprint()),
                    getAudioFingerprint()
                ]).then(([canvasFingerprint, audioFingerprint]) => ({
                    canvasFingerprint,
                    audioFingerprint: audioFingerprint.slice(0, 10)
                }));
            }
        """)
        
        logger.info("Audio/Canvas fingerprinting results:")
        logger.info(f"Canvas fingerprint length: {len(result['canvasFingerprint'])}")
        logger.info(f"Audio fingerprint first 10 values: {result['audioFingerprint']}")
        
        # Get a second set of fingerprints
        result2 = await page.evaluate("""
            () => {
                const canvas = document.createElement('canvas');
                const ctx = canvas.getContext('2d');
                ctx.textBaseline = "top";
                ctx.font = "14px 'Arial'";
                ctx.fillStyle = "#f60";
                ctx.fillRect(125,1,62,20);
                ctx.fillStyle = "#069";
                ctx.fillText("Hello, world!", 2, 15);
                return canvas.toDataURL();
            }
        """)
        
        # Fingerprints should be different due to our protection
        assert result["canvasFingerprint"] != result2, "Canvas fingerprints are identical"
    finally:
        await page.close() 
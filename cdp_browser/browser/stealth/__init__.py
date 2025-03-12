"""
StealthBrowser implementation for anti-detection.
"""
from typing import Optional, Dict, Any
import logging
import asyncio

from ..browser import Browser
from ..page import Page
from .profile import StealthProfile

logger = logging.getLogger(__name__)

class StealthBrowser(Browser):
    """A browser with anti-detection capabilities."""
    
    def __init__(self, profile: Optional[StealthProfile] = None, host: str = "localhost", port: int = 9223):
        """
        Initialize the stealth browser with optional profile.
        
        Args:
            profile: Optional StealthProfile for stealth settings
            host: Chrome DevTools host (default: localhost)
            port: Chrome DevTools port (default: 9223)
        """
        super().__init__(host=host, port=port)
        self.profile = profile or StealthProfile()
    
    async def create_page(self) -> Page:
        """Create a new page with stealth patches applied."""
        logger.debug("Creating new page using parent class...")
        page = await super().create_page()
        
        try:
            # Enable required domains one at a time
            logger.debug("Enabling required domains...")
            await page.send_command("Network.enable")
            await page.send_command("Page.enable")
            await page.send_command("Runtime.enable")
            
            # Apply stealth patches
            logger.debug("Applying stealth patches...")
            await self._apply_stealth_patches(page)
            
            logger.debug("Successfully created stealth page")
            return page
            
        except Exception as e:
            logger.error(f"Error setting up stealth page: {e}")
            try:
                await page.close()
            except Exception as close_error:
                logger.error(f"Error closing page after setup failure: {close_error}")
            raise RuntimeError(f"Failed to setup stealth page: {e}")
    
    async def _apply_stealth_patches(self, page: Page) -> None:
        """Apply all stealth patches to a page."""
        try:
            logger.debug("Applying stealth patches...")
            
            # First, apply core Chrome runtime patches
            await page.send_command("Page.addScriptToEvaluateOnNewDocument", {
                "source": """
                    // Core Chrome runtime setup
                    (() => {
                        const originalFunction = window.Function;
                        const originalToString = Function.prototype.toString;
                        
                        // Helper to make functions look native
                        const makeNativeFunction = (fn, name = '') => {
                            const wrapped = originalFunction('return ' + fn)();
                            Object.defineProperty(wrapped, 'name', { value: name });
                            Object.defineProperty(wrapped, 'toString', {
                                value: () => `function ${name || fn.name || ''}() { [native code] }`,
                                configurable: true,
                                writable: true
                            });
                            return wrapped;
                        };

                        // Create runtime object first
                        const runtime = {};

                        // Set up prototype chain
                        Object.setPrototypeOf(runtime, EventTarget.prototype);

                        // Define runtime methods
                        const runtimeMethods = {
                            getURL: function getURL(path) { return 'chrome-extension://' + this.id + '/' + path; },
                            reload: function reload() {},
                            requestUpdateCheck: function requestUpdateCheck(callback) {
                                const result = { status: 'no_update' };
                                if (callback) callback(result);
                                return Promise.resolve(result);
                            },
                            getPlatformInfo: function getPlatformInfo(callback) {
                                const info = { os: 'mac', arch: 'x86-64', nacl_arch: 'x86-64' };
                                if (callback) callback(info);
                                return Promise.resolve(info);
                            },
                            connect: function connect() { return {}; },
                            sendMessage: function sendMessage() {},
                            getManifest: function getManifest() { return {}; }
                        };

                        // Add methods to runtime object
                        for (const [name, fn] of Object.entries(runtimeMethods)) {
                            Object.defineProperty(runtime, name, {
                                value: makeNativeFunction(fn, name),
                                writable: false,
                                enumerable: true,
                                configurable: true
                            });
                        }

                        // Add event handling methods
                        const eventMethods = ['addEventListener', 'removeEventListener', 'dispatchEvent'];
                        eventMethods.forEach(method => {
                            Object.defineProperty(runtime, method, {
                                value: EventTarget.prototype[method],
                                writable: false,
                                enumerable: false,
                                configurable: true
                            });
                        });

                        // Define runtime properties
                        Object.defineProperties(runtime, {
                            id: {
                                value: 'chrome-extension',
                                writable: false,
                                enumerable: true,
                                configurable: false
                            },
                            lastError: {
                                value: undefined,
                                writable: true,
                                enumerable: true,
                                configurable: true
                            },
                            OnInstalledReason: {
                                value: { CHROME_UPDATE: 'chrome_update', INSTALL: 'install', UPDATE: 'update' },
                                writable: false,
                                enumerable: true,
                                configurable: false
                            },
                            OnRestartRequiredReason: {
                                value: { APP_UPDATE: 'app_update', OS_UPDATE: 'os_update', PERIODIC: 'periodic' },
                                writable: false,
                                enumerable: true,
                                configurable: false
                            },
                            PlatformArch: {
                                value: { ARM: 'arm', ARM64: 'arm64', X86_32: 'x86-32', X86_64: 'x86-64' },
                                writable: false,
                                enumerable: true,
                                configurable: false
                            },
                            PlatformOs: {
                                value: { ANDROID: 'android', CROS: 'cros', LINUX: 'linux', MAC: 'mac', WIN: 'win' },
                                writable: false,
                                enumerable: true,
                                configurable: false
                            }
                        });

                        // Make runtime properties look native
                        Object.defineProperty(runtime, Symbol.toStringTag, { value: 'ChromeRuntimeObject' });

                        // Setup window.chrome with proper prototypes
                        const chrome = {
                            app: {
                                InstallState: { DISABLED: 'disabled', INSTALLED: 'installed', NOT_INSTALLED: 'not_installed' },
                                RunningState: { CANNOT_RUN: 'cannot_run', READY_TO_RUN: 'ready_to_run', RUNNING: 'running' },
                                getDetails: makeNativeFunction(function getDetails() { return {}; }, 'getDetails'),
                                getIsInstalled: makeNativeFunction(function getIsInstalled() { return false; }, 'getIsInstalled'),
                                installState: makeNativeFunction(function installState() { return 'not_installed'; }, 'installState'),
                                isInstalled: false,
                                window: {
                                    get current() { return null; },
                                    create: makeNativeFunction(function create() { return {}; }, 'create'),
                                    getAll: makeNativeFunction(function getAll() { return []; }, 'getAll')
                                }
                            },
                            runtime: runtime,
                            csi: makeNativeFunction(function csi() {
                                return {
                                    startE: Date.now(),
                                    onloadT: Date.now(),
                                    pageT: Date.now(),
                                    tran: 15
                                };
                            }, 'csi'),
                            loadTimes: makeNativeFunction(function loadTimes() {
                                return {
                                    commitLoadTime: Date.now() / 1000,
                                    connectionInfo: "h2",
                                    finishDocumentLoadTime: Date.now() / 1000,
                                    finishLoadTime: Date.now() / 1000,
                                    firstPaintAfterLoadTime: Date.now() / 1000,
                                    firstPaintTime: Date.now() / 1000,
                                    navigationType: "Other",
                                    npnNegotiatedProtocol: "h2",
                                    requestTime: Date.now() / 1000,
                                    startLoadTime: Date.now() / 1000,
                                    wasAlternateProtocolAvailable: false,
                                    wasFetchedViaSpdy: true,
                                    wasNpnNegotiated: true
                                };
                            }, 'loadTimes')
                        };
                        
                        // Make chrome properties look native
                        Object.defineProperty(chrome, Symbol.toStringTag, { value: 'Chrome' });
                        
                        // Ensure chrome is properly initialized with non-configurable runtime
                        Object.defineProperty(window, 'chrome', {
                            value: chrome,
                            configurable: false,
                            enumerable: true,
                            writable: false
                        });

                        // Ensure webdriver is completely removed
                        try {
                            Object.defineProperty(Object.getPrototypeOf(navigator), 'webdriver', {
                                get: () => undefined,
                                configurable: true,
                                enumerable: true
                            });
                        } catch (e) {
                            // If we can't modify the prototype, try direct property
                            Object.defineProperty(navigator, 'webdriver', {
                                get: () => undefined,
                                configurable: true,
                                enumerable: true
                            });
                        }
                        
                        // Additional cleanup for webdriver
                        if (navigator.webdriver === undefined) {
                            delete navigator.webdriver;
                        }
                    })();
                """
            })
            
            # Apply navigator patches
            await page.send_command("Page.addScriptToEvaluateOnNewDocument", {
                "source": """
                    (() => {
                        // Navigator properties
                        const navigatorProps = {
                            vendor: 'Google Inc.',
                            vendorSub: '',
                            productSub: '20030107',
                            hardwareConcurrency: 8,
                            deviceMemory: 8,
                            webdriver: undefined
                        };
                        
                        // Override navigator properties
                        for (const [key, value] of Object.entries(navigatorProps)) {
                            Object.defineProperty(navigator, key, {
                                get: () => value,
                                configurable: true,
                                enumerable: true
                            });
                        }
                        
                        // Hide automation
                        delete Object.getPrototypeOf(navigator).webdriver;
                        
                        // Additional cleanup to ensure webdriver is completely removed
                        Object.defineProperty(navigator, 'webdriver', {
                            get: () => undefined,
                            configurable: true,
                            enumerable: true
                        });
                    })();
                """
            })
            
            # Apply plugins and mimetypes
            await page.send_command("Page.addScriptToEvaluateOnNewDocument", {
                "source": """
                    (() => {
                        // Create plugin factory
                        const createPlugin = (name, description, filename, mimeTypes) => {
                            const plugin = { name, description, filename };
                            Object.defineProperty(plugin, 'length', { value: mimeTypes.length });
                            Object.defineProperty(plugin, 'item', { value: (index) => plugin[index] });
                            Object.defineProperty(plugin, 'namedItem', { value: (name) => plugin[name] });
                            
                            mimeTypes.forEach((mt, i) => {
                                const mimeType = {
                                    type: mt.type,
                                    suffixes: mt.suffixes,
                                    description: mt.description,
                                    enabledPlugin: plugin
                                };
                                plugin[i] = mimeType;
                                plugin[mt.type] = mimeType;
                            });
                            
                            return plugin;
                        };
                        
                        // Create default plugins
                        const defaultPlugins = [
                            createPlugin(
                                'Chrome PDF Plugin',
                                'Portable Document Format',
                                'internal-pdf-viewer',
                                [{ type: 'application/x-google-chrome-pdf', suffixes: 'pdf', description: 'Portable Document Format' }]
                            ),
                            createPlugin(
                                'Chrome PDF Viewer',
                                '',
                                'mhjfbmdgcfjbbpaeojofohoefgiehjai',
                                [{ type: 'application/pdf', suffixes: 'pdf', description: '' }]
                            ),
                            createPlugin(
                                'Native Client',
                                '',
                                'internal-nacl-plugin',
                                [
                                    { type: 'application/x-nacl', suffixes: '', description: 'Native Client Executable' },
                                    { type: 'application/x-pnacl', suffixes: '', description: 'Portable Native Client Executable' }
                                ]
                            )
                        ];
                        
                        // Create plugins array
                        const plugins = {
                            length: defaultPlugins.length,
                            item: function(index) { return this[index]; },
                            namedItem: function(name) { return this[name]; },
                            refresh: function() {}
                        };
                        
                        // Add plugins to array
                        defaultPlugins.forEach((plugin, i) => {
                            plugins[i] = plugin;
                            plugins[plugin.name] = plugin;
                        });
                        
                        // Override navigator.plugins and mimeTypes
                        Object.defineProperty(navigator, 'plugins', {
                            get: () => plugins,
                            enumerable: true,
                            configurable: true
                        });
                        
                        // Create mimeTypes array
                        const mimeTypes = {
                            length: 0,
                            item: function(index) { return this[index]; },
                            namedItem: function(name) { return this[name]; }
                        };
                        
                        Object.defineProperty(navigator, 'mimeTypes', {
                            get: () => mimeTypes,
                            enumerable: true,
                            configurable: true
                        });
                    })();
                """
            })
            
            # Apply user agent if specified
            if self.profile.user_agent:
                await page.send_command("Network.setUserAgentOverride", {
                    "userAgent": self.profile.user_agent,
                    "platform": "MacIntel",
                    "acceptLanguage": "en-US,en;q=0.9",
                    "userAgentMetadata": {
                        "brands": [
                            {"brand": "Chrome", "version": "121"},
                            {"brand": "Chromium", "version": "121"},
                            {"brand": "Not=A?Brand", "version": "24"}
                        ],
                        "fullVersion": "121.0.6167.85",
                        "platform": "macOS",
                        "platformVersion": "13.0.0",
                        "architecture": "x86",
                        "model": "",
                        "mobile": False,
                        "bitness": "64",
                        "wow64": False
                    }
                })
            
            # Apply viewport settings
            await page.send_command("Emulation.setDeviceMetricsOverride", {
                "width": self.profile.window_size["width"],
                "height": self.profile.window_size["height"],
                "deviceScaleFactor": 1,
                "mobile": False
            })
            
            # Wait for patches to settle
            await asyncio.sleep(0.1)
            
            logger.debug("Successfully applied all stealth patches")
            
        except Exception as e:
            logger.error(f"Failed to apply stealth patches: {e}")
            raise RuntimeError(f"Failed to apply stealth patches: {e}")
    
    def get_profile(self) -> StealthProfile:
        """Get the current stealth profile."""
        return self.profile
    
    def update_profile(self, profile: StealthProfile) -> None:
        """
        Update the stealth profile.
        Note: Changes will only take effect after a browser restart.
        
        Args:
            profile: New StealthProfile instance
        """
        self.profile = profile
    
    async def _apply_page_patch(self, page: Page, patch: Dict[str, Any]) -> None:
        """Apply a patch to a specific page."""
        patch_type = patch["type"]
        
        if patch_type == "webdriver":
            await page.evaluate("""
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
            """)
        elif patch_type == "user_agent":
            if patch.get("value"):
                await page.send_command("Network.setUserAgentOverride", {
                    "userAgent": patch["value"]
                })
        elif patch_type == "viewport":
            size = patch.get("size", {})
            await page.send_command("Emulation.setDeviceMetricsOverride", {
                "width": size.get("width", 1920),
                "height": size.get("height", 1080),
                "deviceScaleFactor": 1,
                "mobile": False
            })
        # Add more page-specific patches as needed 
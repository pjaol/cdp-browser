"""
Chrome runtime patches.

These patches emulate the Chrome browser runtime properties and behavior,
preventing detection through missing or inconsistent Chrome-specific features.
"""

from . import register_patch

# Basic Chrome runtime patch
register_patch(
    name="chrome_runtime_basic",
    description="Basic Chrome runtime emulation",
    priority=40,
    script="""
    (() => {
        // Create a basic chrome object if it doesn't exist
        if (!window.chrome) {
            window.chrome = {
                runtime: {},
                app: {},
                loadTimes: function() {},
                csi: function() {}
            };
        }
    })();
    """
)

# Advanced Chrome runtime patch
register_patch(
    name="chrome_runtime_advanced",
    description="Advanced Chrome runtime emulation with full API support",
    priority=41,
    script="""
    (() => {
        // Helper to make functions look native
        const makeNativeFunction = (fn, name = '') => {
            const originalFunction = window.Function;
            const wrapped = originalFunction('return ' + fn)();
            Object.defineProperty(wrapped, 'name', { value: name });
            Object.defineProperty(wrapped, 'toString', {
                value: function() { return `function ${name || fn.name || ''}() { [native code] }` },
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
    })();
    """
)

# Chrome permissions API patch
register_patch(
    name="chrome_permissions",
    description="Chrome permissions API emulation",
    priority=42,
    script="""
    (() => {
        // Helper to make functions look native
        const makeNativeFunction = (fn, name = '') => {
            const originalFunction = window.Function;
            const wrapped = originalFunction('return ' + fn)();
            Object.defineProperty(wrapped, 'name', { value: name });
            Object.defineProperty(wrapped, 'toString', {
                value: function() { return `function ${name || fn.name || ''}() { [native code] }` },
                configurable: true,
                writable: true
            });
            return wrapped;
        };
        
        // Patch navigator.permissions if it exists
        if (navigator.permissions) {
            try {
                // Store the original query method
                const originalQuery = navigator.permissions.query;
                
                // Override the query method to handle special cases
                navigator.permissions.query = makeNativeFunction(function(parameters) {
                    // Special case for notifications permission
                    if (parameters.name === 'notifications') {
                        return Promise.resolve({ state: Notification.permission });
                    }
                    
                    // Special case for clipboard-write permission (commonly used in fingerprinting)
                    if (parameters.name === 'clipboard-write') {
                        return Promise.resolve({ state: 'granted' });
                    }
                    
                    // Special case for clipboard-read permission
                    if (parameters.name === 'clipboard-read') {
                        return Promise.resolve({ state: 'prompt' });
                    }
                    
                    // Handle other permissions normally
                    return originalQuery.call(this, parameters);
                }, 'query');
            } catch (e) {
                // Ignore errors
            }
        } else {
            // If permissions API doesn't exist, create a minimal implementation
            try {
                navigator.permissions = {
                    query: makeNativeFunction(function(parameters) {
                        // Default response for common permissions
                        const states = {
                            'notifications': 'prompt',
                            'clipboard-write': 'prompt',
                            'clipboard-read': 'prompt',
                            'camera': 'prompt',
                            'microphone': 'prompt',
                            'geolocation': 'prompt'
                        };
                        
                        // Create a permission status object
                        const status = {
                            state: states[parameters.name] || 'prompt',
                            onchange: null
                        };
                        
                        // Make it look like a real PermissionStatus
                        Object.defineProperty(status, Symbol.toStringTag, { value: 'PermissionStatus' });
                        
                        return Promise.resolve(status);
                    }, 'query')
                };
            } catch (e) {
                // Ignore errors
            }
        }
    })();
    """
) 
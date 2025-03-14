"""
Chrome runtime patches.

These patches emulate the Chrome browser runtime properties and behavior,
preventing detection through missing or inconsistent Chrome-specific features.
"""

from . import register_patch

# Helper functions patch
register_patch(
    name="chrome_helpers",
    description="Helper functions for Chrome emulation",
    priority=39,  # Run before other Chrome patches
    script="""
    (() => {
        // Helper to make functions look native
        const makeNativeFunction = (fn, name = '') => {
            const wrapped = function() {
                return fn.apply(this, arguments);
            };
            Object.defineProperty(wrapped, 'name', { value: name });
            Object.defineProperty(wrapped, 'toString', {
                value: () => `function ${name}() { [native code] }`,
                configurable: true
            });
            return wrapped;
        };
        
        // Make it globally available
        Object.defineProperty(window, 'makeNativeFunction', {
            value: makeNativeFunction,
            configurable: false,
            enumerable: false,
            writable: false
        });
    })();
    """
)

# Basic Chrome runtime patch - no dependencies
register_patch(
    name="chrome_runtime_basic",
    description="Basic Chrome runtime emulation",
    priority=40,
    script="""
    (() => {
        // Create a basic chrome object if it doesn't exist
        if (!window.chrome) {
            const chrome = {
                runtime: {},
                app: {},
                loadTimes: function() {},
                csi: function() {}
            };
            
            // Make chrome object non-configurable
            Object.defineProperty(window, 'chrome', {
                value: chrome,
                configurable: false,
                enumerable: true,
                writable: false
            });
            
            // Add toString tag
            Object.defineProperty(chrome, Symbol.toStringTag, { value: 'Chrome' });
            
            // Make functions look native
            const makeNativeFunction = (fn, name = '') => {
                const wrapped = function() {
                    return fn.apply(this, arguments);
                };
                Object.defineProperty(wrapped, 'name', { value: name });
                Object.defineProperty(wrapped, 'toString', {
                    value: () => `function ${name}() { [native code] }`,
                    configurable: true
                });
                return wrapped;
            };
            
            // Apply native function wrapper
            chrome.loadTimes = makeNativeFunction(chrome.loadTimes, 'loadTimes');
            chrome.csi = makeNativeFunction(chrome.csi, 'csi');
        }
    })();
    """
)

# Advanced Chrome runtime patch
register_patch(
    name="chrome_runtime_advanced",
    description="Advanced Chrome runtime emulation with full API support",
    priority=41,
    dependencies=["chrome_runtime_basic"],
    script="""
    (() => {
        if (!window.chrome) return;  // Ensure basic patch ran first
        
        // Helper to make functions look native
        const makeNativeFunction = (fn, name = '') => {
            const wrapped = function() {
                return fn.apply(this, arguments);
            };
            Object.defineProperty(wrapped, 'name', { value: name });
            Object.defineProperty(wrapped, 'toString', {
                value: () => `function ${name}() { [native code] }`,
                configurable: true
            });
            return wrapped;
        };
        
        // Create runtime object with proper prototype
        const runtime = Object.create(EventTarget.prototype);
        
        // Define runtime methods
        const runtimeMethods = {
            getURL: function(path) { return 'chrome-extension://' + this.id + '/' + path; },
            reload: function() {},
            requestUpdateCheck: function(callback) {
                const result = { status: 'no_update' };
                if (callback) callback(result);
                return Promise.resolve(result);
            },
            getPlatformInfo: function(callback) {
                const info = { os: 'mac', arch: 'x86-64', nacl_arch: 'x86-64' };
                if (callback) callback(info);
                return Promise.resolve(info);
            },
            connect: function() { return {}; },
            sendMessage: function() {},
            getManifest: function() { return {}; }
        };
        
        // Add methods to runtime object
        for (const [name, fn] of Object.entries(runtimeMethods)) {
            runtime[name] = makeNativeFunction(fn, name);
        }
        
        // Define runtime properties
        const runtimeProps = {
            id: { value: 'chrome-extension', configurable: false },
            lastError: { value: undefined, configurable: true },
            OnInstalledReason: { 
                value: Object.freeze({ CHROME_UPDATE: 'chrome_update', INSTALL: 'install', UPDATE: 'update' }),
                configurable: false 
            },
            OnRestartRequiredReason: { 
                value: Object.freeze({ APP_UPDATE: 'app_update', OS_UPDATE: 'os_update', PERIODIC: 'periodic' }),
                configurable: false 
            },
            PlatformArch: { 
                value: Object.freeze({ ARM: 'arm', ARM64: 'arm64', X86_32: 'x86-32', X86_64: 'x86-64' }),
                configurable: false 
            },
            PlatformOs: { 
                value: Object.freeze({ ANDROID: 'android', CROS: 'cros', LINUX: 'linux', MAC: 'mac', WIN: 'win' }),
                configurable: false 
            }
        };
        
        // Add properties to runtime object
        Object.defineProperties(runtime, runtimeProps);
        
        // Create app object
        const app = {
            InstallState: Object.freeze({ DISABLED: 'disabled', INSTALLED: 'installed', NOT_INSTALLED: 'not_installed' }),
            RunningState: Object.freeze({ CANNOT_RUN: 'cannot_run', READY_TO_RUN: 'ready_to_run', RUNNING: 'running' }),
            getDetails: makeNativeFunction(function() { return {}; }, 'getDetails'),
            getIsInstalled: makeNativeFunction(function() { return false; }, 'getIsInstalled'),
            installState: makeNativeFunction(function() { return 'not_installed'; }, 'installState'),
            isInstalled: false,
            window: {
                get current() { return null; },
                create: makeNativeFunction(function() { return {}; }, 'create'),
                getAll: makeNativeFunction(function() { return []; }, 'getAll')
            }
        };
        
        // Update chrome object properties
        Object.defineProperties(window.chrome, {
            runtime: { value: runtime, configurable: false, enumerable: true, writable: false },
            app: { value: app, configurable: false, enumerable: true, writable: false },
            csi: {
                value: makeNativeFunction(function() {
                    return {
                        startE: Date.now(),
                        onloadT: Date.now(),
                        pageT: Date.now(),
                        tran: 15
                    };
                }, 'csi'),
                configurable: false,
                enumerable: true,
                writable: false
            },
            loadTimes: {
                value: makeNativeFunction(function() {
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
                }, 'loadTimes'),
                configurable: false,
                enumerable: true,
                writable: false
            }
        });
    })();
    """
)

# Chrome permissions API patch
register_patch(
    name="chrome_permissions",
    description="Chrome permissions API emulation",
    priority=42,
    dependencies=["chrome_runtime_basic", "chrome_runtime_advanced"],
    script="""
    (() => {
        if (!window.chrome) return;  // Ensure previous patches ran
        
        // Helper to make functions look native
        const makeNativeFunction = (fn, name = '') => {
            const wrapped = function() {
                return fn.apply(this, arguments);
            };
            Object.defineProperty(wrapped, 'name', { value: name });
            Object.defineProperty(wrapped, 'toString', {
                value: () => `function ${name}() { [native code] }`,
                configurable: true
            });
            return wrapped;
        };
        
        // Add permissions API
        Object.defineProperty(window.chrome, 'permissions', {
            value: {
                getAll: makeNativeFunction(function(callback) {
                    const permissions = { permissions: [], origins: [] };
                    if (callback) callback(permissions);
                    return Promise.resolve(permissions);
                }, 'getAll'),
                contains: makeNativeFunction(function(permissions, callback) {
                    const result = false;
                    if (callback) callback(result);
                    return Promise.resolve(result);
                }, 'contains'),
                request: makeNativeFunction(function(permissions, callback) {
                    const result = false;
                    if (callback) callback(result);
                    return Promise.resolve(result);
                }, 'request'),
                remove: makeNativeFunction(function(permissions, callback) {
                    const result = false;
                    if (callback) callback(result);
                    return Promise.resolve(result);
                }, 'remove')
            },
            configurable: false,
            enumerable: true,
            writable: false
        });
    })();
    """
) 
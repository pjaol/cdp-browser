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
        // Simple helper to make functions look native
        window.makeNativeFunction = function(fn, name) {
            const wrapped = function() {
                return fn.apply(this, arguments);
            };
            
            wrapped.toString = function() {
                return "function " + (name || fn.name || "") + "() { [native code] }";
            };
            
            return wrapped;
        };
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
            
            // Simple helper to make functions look native if makeNativeFunction isn't available yet
            const makeNative = (fn, name = '') => {
                const wrapped = function() {
                    return fn.apply(this, arguments);
                };
                
                wrapped.toString = function() {
                    return "function " + (name || fn.name || "") + "() { [native code] }";
                };
                
                return wrapped;
            };
            
            // Apply native function wrapper
            chrome.loadTimes = makeNative(chrome.loadTimes, 'loadTimes');
            chrome.csi = makeNative(chrome.csi, 'csi');
        }
    })();
    """
)

# Advanced Chrome runtime patch
register_patch(
    name="chrome_runtime_advanced",
    description="Advanced Chrome runtime emulation with full API support",
    priority=41,
    dependencies=["chrome_runtime_basic", "chrome_helpers"],
    script="""
    (() => {
        if (!window.chrome) return;  // Ensure basic patch ran first
        if (!window.makeNativeFunction) return; // Ensure chrome_helpers ran first
        
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
            runtime[name] = window.makeNativeFunction(fn, name);
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
            getDetails: window.makeNativeFunction(function() { return {}; }, 'getDetails'),
            getIsInstalled: window.makeNativeFunction(function() { return false; }, 'getIsInstalled'),
            installState: window.makeNativeFunction(function() { return 'not_installed'; }, 'installState'),
            isInstalled: false,
            window: {
                get current() { return null; },
                create: window.makeNativeFunction(function() { return {}; }, 'create'),
                getAll: window.makeNativeFunction(function() { return []; }, 'getAll')
            }
        };
        
        // Update chrome object properties
        Object.defineProperties(window.chrome, {
            runtime: { value: runtime, configurable: false, enumerable: true, writable: false },
            app: { value: app, configurable: false, enumerable: true, writable: false },
            csi: {
                value: window.makeNativeFunction(function() {
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
                value: window.makeNativeFunction(function() {
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
        try {
            if (!window.chrome) return;  // Ensure previous patches ran
            
            // Create permissions API methods
            const permissionsAPI = {
                getAll: function(callback) {
                    const permissions = { permissions: [], origins: [] };
                    if (callback) callback(permissions);
                    return Promise.resolve(permissions);
                },
                contains: function(permissions, callback) {
                    const result = false;
                    if (callback) callback(result);
                    return Promise.resolve(result);
                },
                request: function(permissions, callback) {
                    const result = false;
                    if (callback) callback(result);
                    return Promise.resolve(result);
                },
                remove: function(permissions, callback) {
                    const result = false;
                    if (callback) callback(result);
                    return Promise.resolve(result);
                }
            };
            
            // Use window.makeNativeFunction if it's defined from chrome_helpers patch
            const makeNativeFunc = window.makeNativeFunction || function(fn, name) {
                const wrapped = function() {
                    return fn.apply(this, arguments);
                };
                
                wrapped.toString = function() {
                    return "function " + (name || fn.name || "") + "() { [native code] }";
                };
                
                return wrapped;
            };
            
            // Wrap each method with makeNative
            const wrappedPermissions = {};
            for (const [key, fn] of Object.entries(permissionsAPI)) {
                wrappedPermissions[key] = makeNativeFunc(fn, key);
            }
            
            // Add to chrome object - using safer direct property assignment
            if (window.chrome && !window.chrome.permissions) {
                window.chrome.permissions = wrappedPermissions;
                
                // Make it look more native with non-configurable property after assignment
                if (Object.defineProperty) {
                    try {
                        Object.defineProperty(window.chrome, 'permissions', {
                            value: wrappedPermissions,
                            configurable: false,
                            enumerable: true,
                            writable: false
                        });
                    } catch (defineError) {
                        console.error("Error making permissions non-configurable:", defineError);
                        // Property already exists, so we're fine continuing
                    }
                }
            }
        } catch (e) {
            console.error("Error in chrome_permissions patch:", e);
            // Don't throw to avoid breaking the page
        }
    })();
    """
)

# Function prototypes patch
register_patch(
    name="function_prototypes",
    description="Make function prototypes appear native",
    priority=30,  # Run before all other patches
    script="""
    (() => {
        // Create a debugging function to help identify issues
        const debug = (msg) => {
            // Uncomment for debugging
            // console.debug('function_prototypes patch: ' + msg);
        };
        
        try {
            debug('Storing original toString');
            // Store original toString
            const originalToString = Function.prototype.toString;
            
            debug('Creating toString override');
            // Create simple toString override
            Function.prototype.toString = function() {
                // For native functions, return native code string
                const fnName = this.name || "";
                debug('toString called for: ' + fnName);
                
                // Special cases for specific functions
                if (this === Function.prototype.toString || 
                    this === Object.getOwnPropertyDescriptor || 
                    this === Object.defineProperty ||
                    fnName.startsWith("get") || 
                    fnName.startsWith("set") || 
                    fnName === "toString" || 
                    fnName === "valueOf" || 
                    fnName === "constructor" || 
                    fnName === "hasOwnProperty") {
                    debug('Returning native string for: ' + fnName);
                    return `function ${fnName}() { [native code] }`;
                }
                
                // For all other functions, use the original toString
                debug('Using original toString for: ' + fnName);
                return originalToString.call(this);
            };
            
            debug('Setting toString property');
            // Make toString look native
            Object.defineProperty(Function.prototype.toString, "toString", {
                value: function() { return "function toString() { [native code] }"; },
                writable: false,
                configurable: true,
                enumerable: false
            });
            
            debug('Function prototype patch completed successfully');
        } catch (e) {
            // Log any errors but don't throw
            console.error('Error in function_prototypes patch:', e);
        }
    })();
    """
) 
"""
User agent patches.

These patches ensure consistent user agent reporting across different methods
of checking, preventing detection through user agent inconsistencies.
"""

from . import register_patch

# Basic user agent patch
register_patch(
    name="user_agent_basic",
    description="Basic user agent consistency",
    priority=20,
    script="""
    (() => {
        // Only override properties that can't be set via CDP
        const navigatorProps = {
            vendor: 'Google Inc.',
            languages: ['en-US', 'en'],
            platform: 'MacIntel'  // Match the platform to the user agent string
        };
        
        // Apply navigator property overrides
        for (const [key, value] of Object.entries(navigatorProps)) {
            try {
                Object.defineProperty(navigator, key, {
                    get: () => value,
                    configurable: true,
                    enumerable: true
                });
            } catch (e) {
                // Ignore errors
            }
        }
    })();
    """
)

# Advanced user agent patch
register_patch(
    name="user_agent_advanced",
    description="Advanced user agent consistency with browser-specific values",
    priority=21,
    script="""
    (() => {
        // Store original methods first at the top level before any modifications
        const originalFunction = window.Function;
        const originalObjectDefineProperty = Object.defineProperty;
        const originalObjectGetOwnPropertyDescriptor = Object.getOwnPropertyDescriptor;
        const originalToString = Function.prototype.toString;

        // Helper to make a function look native without using the functions we're about to modify
        const utilMakeNativeFunction = (fn, name = '') => {
            // Create a new function with the same body
            const functionBody = fn.toString().replace(/^[^{]*{/, '').replace(/}[^}]*$/, '');
            const wrapped = originalFunction('return (function ' + name + '() {' + functionBody + '})')();
            
            // Make the function look native
            originalObjectDefineProperty(wrapped, 'name', {
                value: name,
                configurable: true,
                enumerable: false,
                writable: false
            });
            
            // Make toString look native
            originalObjectDefineProperty(wrapped, 'toString', {
                value: function() {
                    return `function ${name || fn.name || ''}() { [native code] }`;
                },
                configurable: true,
                enumerable: false,
                writable: true
            });
            
            // Make toString.toString look native
            originalObjectDefineProperty(wrapped.toString, 'toString', {
                value: function() {
                    return `function toString() { [native code] }`;
                },
                configurable: true,
                enumerable: false,
                writable: true
            });
            
            // Set length property
            originalObjectDefineProperty(wrapped, 'length', {
                value: fn.length,
                configurable: true,
                enumerable: false,
                writable: false
            });
            
            // Ensure prototype chain is correct
            Object.setPrototypeOf(wrapped, Function.prototype);
            
            return wrapped;
        };

        // Native-looking getOwnPropertyDescriptor
        const nativeGetOwnPropertyDescriptor = function getOwnPropertyDescriptor(obj, prop) {
            // Handle special cases first
            if (obj === Object && (prop === 'getOwnPropertyDescriptor' || prop === 'defineProperty')) {
                // Make Object methods appear native
                return {
                    value: obj[prop],
                    writable: true,
                    enumerable: false,
                    configurable: true
                };
            }
            
            // Check for wrapped functions with toString
            if (obj && typeof obj === 'function' && prop === 'toString' && 
                obj.toString && obj.toString.toString && 
                obj.toString.toString() === 'function toString() { [native code] }') {
                return {
                    value: obj.toString,
                    writable: true,
                    enumerable: false,
                    configurable: true
                };
            }
            
            // Handle webdriver property on navigator
            if (obj === navigator && prop === 'webdriver') {
                return undefined;
            }
            
            // For all other cases, defer to the original method
            return originalObjectGetOwnPropertyDescriptor.apply(this, arguments);
        };

        // Native-looking defineProperty
        const nativeDefineProperty = function defineProperty(obj, prop, descriptor) {
            // Special case for wrapped functions
            if (obj && typeof obj === 'function' && prop === 'toString' &&
                obj.toString && obj.toString.toString && 
                obj.toString.toString() === 'function toString() { [native code] }') {
                // Preserve the native-looking toString
                return obj;
            }
            
            // For all other cases, defer to the original method
            return originalObjectDefineProperty.apply(this, arguments);
        };

        // Create wrapper functions that appear native
        const wrappedGetOwnPropertyDescriptor = utilMakeNativeFunction(nativeGetOwnPropertyDescriptor, 'getOwnPropertyDescriptor');
        const wrappedDefineProperty = utilMakeNativeFunction(nativeDefineProperty, 'defineProperty');

        // Install our wrapped functions
        originalObjectDefineProperty(Object, 'getOwnPropertyDescriptor', {
            value: wrappedGetOwnPropertyDescriptor,
            writable: true,
            enumerable: false,
            configurable: true
        });

        originalObjectDefineProperty(Object, 'defineProperty', {
            value: wrappedDefineProperty,
            writable: true,
            enumerable: false,
            configurable: true
        });

        // Create a helper for general use
        const makeNativeFunction = (fn, name = '') => {
            // Create a new function with the same body
            const functionBody = fn.toString().replace(/^[^{]*{/, '').replace(/}[^}]*$/, '');
            const wrapped = Function('return (function ' + name + '() {' + functionBody + '})')();
            
            // Make the function look native
            Object.defineProperty(wrapped, 'name', {
                value: name,
                configurable: true,
                enumerable: false,
                writable: false
            });
            
            // Make toString look native
            Object.defineProperty(wrapped, 'toString', {
                value: function() {
                    return `function ${name || fn.name || ''}() { [native code] }`;
                },
                configurable: true,
                enumerable: false,
                writable: true
            });
            
            // Make toString.toString look native
            Object.defineProperty(wrapped.toString, 'toString', {
                value: function() {
                    return `function toString() { [native code] }`;
                },
                configurable: true,
                enumerable: false,
                writable: true
            });
            
            // Set length property
            Object.defineProperty(wrapped, 'length', {
                value: fn.length,
                configurable: true,
                enumerable: false,
                writable: false
            });
            
            // Ensure prototype chain is correct
            Object.setPrototypeOf(wrapped, Function.prototype);
            
            return wrapped;
        };
        
        // Override navigator.userAgentData if available
        if ('userAgentData' in navigator) {
            try {
                const brands = [
                    { brand: "Chrome", version: "121" },
                    { brand: "Chromium", version: "121" },
                    { brand: "Not=A?Brand", version: "24" }
                ];
                
                const platform = 'macOS';
                
                // Create a fake userAgentData object
                const uaData = {
                    brands: brands,
                    mobile: false,
                    platform: platform,
                    getHighEntropyValues: makeNativeFunction(function getHighEntropyValues(hints) {
                        return Promise.resolve({
                            brands: brands,
                            mobile: false,
                            platform: platform,
                            architecture: 'x86',
                            bitness: '64',
                            model: '',
                            platformVersion: '10.15.7',
                            uaFullVersion: '121.0.0.0',
                            fullVersionList: brands,
                            wow64: false
                        });
                    }, 'getHighEntropyValues'),
                    toJSON: makeNativeFunction(function toJSON() {
                        return {
                            brands: this.brands,
                            mobile: this.mobile,
                            platform: this.platform
                        };
                    }, 'toJSON')
                };
                
                // Override userAgentData
                Object.defineProperty(navigator, 'userAgentData', {
                    get: () => uaData,
                    configurable: true,
                    enumerable: true
                });
            } catch (e) {
                // Ignore errors
            }
        }
        
        // Override navigator.connection if available
        if ('connection' in navigator) {
            try {
                const connection = {
                    downlink: 10,
                    effectiveType: '4g',
                    rtt: 50,
                    saveData: false,
                    type: 'wifi',
                    onchange: null
                };
                
                Object.defineProperty(navigator, 'connection', {
                    get: () => connection,
                    configurable: true,
                    enumerable: true
                });
            } catch (e) {
                // Ignore errors
            }
        }
        
        // Override navigator.plugins and mimeTypes to match the user agent
        try {
            // Create consistent mimeTypes and plugins based on the browser
            const createPlugins = () => {
                const plugins = [
                    {
                        name: 'Chrome PDF Plugin',
                        filename: 'internal-pdf-viewer',
                        description: 'Portable Document Format',
                        length: 1,
                        item: makeNativeFunction(function(index) { return this[index]; }, 'item'),
                        namedItem: makeNativeFunction(function(name) { return this[name]; }, 'namedItem'),
                        0: {
                            type: 'application/x-google-chrome-pdf',
                            suffixes: 'pdf',
                            description: 'Portable Document Format'
                        }
                    },
                    {
                        name: 'Chrome PDF Viewer',
                        filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai',
                        description: '',
                        length: 1,
                        item: makeNativeFunction(function(index) { return this[index]; }, 'item'),
                        namedItem: makeNativeFunction(function(name) { return this[name]; }, 'namedItem'),
                        0: {
                            type: 'application/pdf',
                            suffixes: 'pdf',
                            description: ''
                        }
                    },
                    {
                        name: 'Native Client',
                        filename: 'internal-nacl-plugin',
                        description: '',
                        length: 2,
                        item: makeNativeFunction(function(index) { return this[index]; }, 'item'),
                        namedItem: makeNativeFunction(function(name) { return this[name]; }, 'namedItem'),
                        0: {
                            type: 'application/x-nacl',
                            suffixes: '',
                            description: 'Native Client Executable'
                        },
                        1: {
                            type: 'application/x-pnacl',
                            suffixes: '',
                            description: 'Portable Native Client Executable'
                        }
                    }
                ];
                
                return plugins;
            };
            
            const plugins = createPlugins();
            
            // Create a plugins array with the correct properties
            const pluginsArray = {
                length: plugins.length,
                item: makeNativeFunction(function(index) { return this[index]; }, 'item'),
                namedItem: makeNativeFunction(function(name) { 
                    for (let i = 0; i < this.length; i++) {
                        if (this[i].name === name) {
                            return this[i];
                        }
                    }
                    return null;
                }, 'namedItem'),
                refresh: makeNativeFunction(function() {}, 'refresh')
            };
            
            // Add plugins to the array
            for (let i = 0; i < plugins.length; i++) {
                pluginsArray[i] = plugins[i];
                pluginsArray[plugins[i].name] = plugins[i];
            }
            
            // Create a mimeTypes array
            const mimeTypesArray = {
                length: 0,
                item: makeNativeFunction(function(index) { return this[index]; }, 'item'),
                namedItem: makeNativeFunction(function(name) { return this[name]; }, 'namedItem')
            };
            
            // Add mimeTypes from plugins
            let mimeTypeIndex = 0;
            for (let i = 0; i < plugins.length; i++) {
                const plugin = plugins[i];
                for (let j = 0; j < plugin.length; j++) {
                    const mimeType = plugin[j];
                    mimeTypesArray[mimeTypeIndex] = mimeType;
                    mimeTypesArray[mimeType.type] = mimeType;
                    mimeTypeIndex++;
                }
            }
            
            // Set the length property
            Object.defineProperty(mimeTypesArray, 'length', {
                value: mimeTypeIndex,
                writable: false,
                enumerable: true,
                configurable: true
            });
            
            // Override navigator.plugins and mimeTypes
            Object.defineProperty(navigator, 'plugins', {
                get: () => pluginsArray,
                configurable: true,
                enumerable: true
            });
            
            Object.defineProperty(navigator, 'mimeTypes', {
                get: () => mimeTypesArray,
                configurable: true,
                enumerable: true
            });
        } catch (e) {
            // Ignore errors
        }
    })();
    """
) 
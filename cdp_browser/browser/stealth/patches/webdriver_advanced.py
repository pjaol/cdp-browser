"""
WebDriver property spoofing patches.

These patches help hide the WebDriver property which is commonly used
to detect automated browsers.
"""

from . import register_patch

# Advanced WebDriver patch - multiple layers of protection
register_patch(
    name="webdriver_advanced",
    description="Advanced WebDriver property spoofing with multiple layers",
    priority=11,
    script="""
    (() => {
        // Helper to make functions look native
        const makeNativeFunction = (fn, name = '') => {
            // Store original functions
            const originalFunction = window.Function;
            const originalObjectDefineProperty = Object.defineProperty;
            const originalObjectGetOwnPropertyDescriptor = Object.getOwnPropertyDescriptor;
            const originalToString = Function.prototype.toString;
            
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
            const toStringDescriptor = originalObjectGetOwnPropertyDescriptor(Function.prototype, 'toString');
            originalObjectDefineProperty(wrapped, 'toString', {
                ...toStringDescriptor,
                value: function toString() {
                    return `function ${name || fn.name || ''}() { [native code] }`;
                }
            });
            
            // Make toString.toString look native
            originalObjectDefineProperty(wrapped.toString, 'toString', {
                ...toStringDescriptor,
                value: function toString() {
                    return `function toString() { [native code] }`;
                }
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
        
        // Multiple layers of WebDriver property removal
        
        // Layer 1: Delete from prototype
        try {
            const navigatorProto = Object.getPrototypeOf(navigator);
            if (navigatorProto && 'webdriver' in navigatorProto) {
                delete navigatorProto.webdriver;
            }
        } catch (e) {
            // Ignore errors
        }
        
        // Layer 2: Define property on navigator that returns undefined
        try {
            Object.defineProperty(navigator, 'webdriver', {
                get: makeNativeFunction(function() { return undefined; }, ''),
                configurable: true,
                enumerable: true
            });
        } catch (e) {
            // Fallback if defineProperty fails
            try {
                navigator.webdriver = undefined;
            } catch (e2) {
                // Ignore errors
            }
        }
        
        // Layer 3: Monitor property access attempts
        try {
            // Store original functions
            const originalGetOwnPropertyDescriptor = Object.getOwnPropertyDescriptor;
            const originalDefineProperty = Object.defineProperty;
            
            // Override Object.getOwnPropertyDescriptor
            const wrappedGetOwnPropertyDescriptor = makeNativeFunction(function getOwnPropertyDescriptor(obj, prop) {
                if (obj === navigator && prop === 'webdriver') {
                    return undefined;
                }
                return originalGetOwnPropertyDescriptor.apply(this, arguments);
            }, 'getOwnPropertyDescriptor');
            
            // Override Object.defineProperty
            const wrappedDefineProperty = makeNativeFunction(function defineProperty(obj, prop, descriptor) {
                if (obj === navigator && prop === 'webdriver') {
                    return undefined;
                }
                return originalDefineProperty.apply(this, arguments);
            }, 'defineProperty');
            
            // Apply the overrides
            Object.defineProperty(Object, 'getOwnPropertyDescriptor', {
                value: wrappedGetOwnPropertyDescriptor,
                configurable: true,
                enumerable: false,
                writable: true
            });
            
            Object.defineProperty(Object, 'defineProperty', {
                value: wrappedDefineProperty,
                configurable: true,
                enumerable: false,
                writable: true
            });
        } catch (e) {
            // Ignore errors
        }
        
        // Layer 4: Trap property access with Proxy if supported
        try {
            if (typeof Proxy !== 'undefined') {
                // Create a proxy for navigator to intercept webdriver access
                const navigatorProxy = new Proxy(navigator, {
                    get: function(target, prop) {
                        if (prop === 'webdriver') {
                            return undefined;
                        }
                        return target[prop];
                    },
                    has: function(target, prop) {
                        if (prop === 'webdriver') {
                            return false;
                        }
                        return prop in target;
                    }
                });
                
                // Try to replace navigator with proxy in specific contexts
                // This is experimental and may not work in all browsers
                try {
                    // For specific detection scripts that use a local navigator reference
                    const originalGetOwnPropertyDescriptors = Object.getOwnPropertyDescriptors;
                    Object.getOwnPropertyDescriptors = makeNativeFunction(function getOwnPropertyDescriptors(obj) {
                        const descriptors = originalGetOwnPropertyDescriptors.apply(this, arguments);
                        if (obj === navigator && descriptors.webdriver) {
                            delete descriptors.webdriver;
                        }
                        return descriptors;
                    }, 'getOwnPropertyDescriptors');
                } catch (e) {
                    // Ignore errors
                }
            }
        } catch (e) {
            // Ignore errors
        }
        
        // Layer 5: Override property detection in Object.keys and other methods
        try {
            const originalObjectKeys = Object.keys;
            Object.keys = makeNativeFunction(function keys(obj) {
                const keys = originalObjectKeys.apply(this, arguments);
                if (obj === navigator) {
                    return keys.filter(key => key !== 'webdriver');
                }
                return keys;
            }, 'keys');
            
            const originalObjectValues = Object.values;
            Object.values = makeNativeFunction(function values(obj) {
                const values = originalObjectValues.apply(this, arguments);
                if (obj === navigator && 'webdriver' in obj) {
                    const index = originalObjectKeys(obj).indexOf('webdriver');
                    if (index !== -1) {
                        values.splice(index, 1);
                    }
                }
                return values;
            }, 'values');
        } catch (e) {
            // Ignore errors
        }
    })();
    """
) 
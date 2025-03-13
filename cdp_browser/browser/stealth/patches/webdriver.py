"""
WebDriver property spoofing patches.

These patches help hide the WebDriver property which is commonly used
to detect automated browsers.
"""

from . import register_patch

# Basic WebDriver patch - simple property removal
register_patch(
    name="webdriver_basic",
    description="Basic WebDriver property removal",
    priority=10,  # Run early
    script="""
    (() => {
        // Simple property removal
        Object.defineProperty(navigator, 'webdriver', {
            get: () => undefined,
            configurable: true,
            enumerable: true
        });
        
        // Delete from prototype if possible
        try {
            delete Object.getPrototypeOf(navigator).webdriver;
        } catch (e) {
            // Ignore errors
        }
    })();
    """
)

# Advanced WebDriver patch - multiple layers of protection
register_patch(
    name="webdriver_advanced",
    description="Advanced WebDriver property spoofing with multiple layers",
    priority=11,
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
        
        // Layer 2: Define property on navigator that returns false
        try {
            Object.defineProperty(navigator, 'webdriver', {
                get: makeNativeFunction(function() { return false; }, ''),
                configurable: true,
                enumerable: true
            });
        } catch (e) {
            // Fallback if defineProperty fails
            try {
                navigator.webdriver = false;
            } catch (e2) {
                // Ignore errors
            }
        }
        
        // Layer 3: Monitor property access attempts
        try {
            const originalDefineProperty = Object.defineProperty;
            Object.defineProperty = function(obj, prop, descriptor) {
                // Block attempts to redefine navigator.webdriver
                if (obj === navigator && prop === 'webdriver') {
                    return obj;
                }
                return originalDefineProperty.call(this, obj, prop, descriptor);
            };
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
                            return false;
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
                    Object.getOwnPropertyDescriptors = function(obj) {
                        const descriptors = originalGetOwnPropertyDescriptors.apply(this, arguments);
                        if (obj === navigator && descriptors.webdriver) {
                            descriptors.webdriver.value = false;
                        }
                        return descriptors;
                    };
                } catch (e) {
                    // Ignore errors
                }
            }
        } catch (e) {
            // Ignore errors
        }
        
        // Layer 5: Override property access detection methods
        try {
            const originalGetOwnPropertyDescriptor = Object.getOwnPropertyDescriptor;
            Object.getOwnPropertyDescriptor = function(obj, prop) {
                if (obj === navigator && prop === 'webdriver') {
                    return {
                        value: false,
                        configurable: true,
                        enumerable: false,
                        writable: true
                    };
                }
                return originalGetOwnPropertyDescriptor.apply(this, arguments);
            };
        } catch (e) {
            // Ignore errors
        }
        
        // Layer 6: Override property detection in Object.keys and other methods
        try {
            const originalObjectKeys = Object.keys;
            Object.keys = function(obj) {
                const keys = originalObjectKeys.apply(this, arguments);
                if (obj === navigator) {
                    return keys.filter(key => key !== 'webdriver');
                }
                return keys;
            };
            
            const originalObjectValues = Object.values;
            Object.values = function(obj) {
                const values = originalObjectValues.apply(this, arguments);
                if (obj === navigator && 'webdriver' in obj) {
                    const index = originalObjectKeys(obj).indexOf('webdriver');
                    if (index !== -1) {
                        values.splice(index, 1);
                    }
                }
                return values;
            };
        } catch (e) {
            // Ignore errors
        }
    })();
    """
)

# Experimental WebDriver patch - most aggressive approach
register_patch(
    name="experimental_webdriver_extreme",
    description="Experimental aggressive WebDriver property protection",
    priority=12,
    script="""
    (() => {
        // This is an experimental patch that uses more aggressive techniques
        // It may cause compatibility issues with some websites
        
        // Create a clean iframe to get a fresh navigator object
        try {
            const iframe = document.createElement('iframe');
            iframe.style.display = 'none';
            document.body.appendChild(iframe);
            
            // Get clean navigator from iframe
            const cleanNavigator = iframe.contentWindow.navigator;
            
            // Copy all properties from clean navigator to current navigator
            for (const prop in cleanNavigator) {
                if (prop !== 'webdriver') {
                    try {
                        // Skip properties that can't be redefined
                        const descriptor = Object.getOwnPropertyDescriptor(cleanNavigator, prop);
                        if (descriptor && descriptor.configurable) {
                            Object.defineProperty(navigator, prop, descriptor);
                        }
                    } catch (e) {
                        // Ignore errors
                    }
                }
            }
            
            // Remove the iframe
            document.body.removeChild(iframe);
        } catch (e) {
            // Ignore errors
        }
        
        // Override the entire navigator object if possible
        try {
            // This is extremely aggressive and may break things
            const navigatorProps = {};
            for (const prop in navigator) {
                if (prop !== 'webdriver') {
                    navigatorProps[prop] = navigator[prop];
                }
            }
            
            // Add false webdriver property
            navigatorProps.webdriver = false;
            
            // Try to redefine navigator (may not work in all browsers)
            Object.defineProperty(window, 'navigator', {
                value: navigatorProps,
                configurable: false,
                enumerable: true,
                writable: false
            });
        } catch (e) {
            // Ignore errors
        }
    })();
    """
) 
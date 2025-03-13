"""
iframe handling patches.

These patches ensure that iframes have the same stealth properties as the main frame,
preventing detection through iframe inconsistencies.
"""

from . import register_patch

# Basic iframe handling patch
register_patch(
    name="iframe_basic",
    description="Basic iframe handling to ensure consistent navigator properties",
    priority=80,  # Run after other patches
    script="""
    (() => {
        // Store important navigator properties
        const navigatorProps = {
            userAgent: navigator.userAgent,
            appVersion: navigator.appVersion,
            platform: navigator.platform,
            vendor: navigator.vendor,
            webdriver: false
        };
        
        // Override iframe creation
        const originalCreateElement = document.createElement;
        
        document.createElement = function(tagName) {
            const element = originalCreateElement.apply(this, arguments);
            
            // If this is an iframe, patch it after it's added to the document
            if (tagName.toLowerCase() === 'iframe') {
                // Use a mutation observer to detect when the iframe is added to the DOM
                const observer = new MutationObserver((mutations, obs) => {
                    try {
                        // Check if the iframe has been added to the DOM
                        if (element.contentWindow) {
                            // Apply patches to the iframe
                            try {
                                // Access the iframe's navigator
                                const iframeNavigator = element.contentWindow.navigator;
                                
                                // Override navigator properties
                                for (const [key, value] of Object.entries(navigatorProps)) {
                                    try {
                                        Object.defineProperty(iframeNavigator, key, {
                                            get: () => value,
                                            configurable: true,
                                            enumerable: true
                                        });
                                    } catch (e) {
                                        // Ignore errors
                                    }
                                }
                                
                                // Ensure webdriver is completely removed
                                try {
                                    delete Object.getPrototypeOf(iframeNavigator).webdriver;
                                } catch (e) {
                                    // Ignore errors
                                }
                            } catch (e) {
                                // Ignore cross-origin errors
                            }
                            
                            // Disconnect the observer once we've patched the iframe
                            obs.disconnect();
                        }
                    } catch (e) {
                        // Ignore errors and disconnect
                        obs.disconnect();
                    }
                });
                
                // Start observing the document for changes
                observer.observe(document, { childList: true, subtree: true });
            }
            
            return element;
        };
    })();
    """
)

# Advanced iframe handling patch
register_patch(
    name="iframe_advanced",
    description="Advanced iframe handling with comprehensive property matching",
    priority=81,
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
        
        // Store important navigator properties
        const navigatorProps = {
            userAgent: navigator.userAgent,
            appVersion: navigator.appVersion,
            platform: navigator.platform,
            vendor: navigator.vendor,
            language: navigator.language,
            languages: navigator.languages,
            deviceMemory: navigator.deviceMemory,
            hardwareConcurrency: navigator.hardwareConcurrency,
            appName: navigator.appName,
            appCodeName: navigator.appCodeName,
            cookieEnabled: navigator.cookieEnabled,
            doNotTrack: navigator.doNotTrack,
            maxTouchPoints: navigator.maxTouchPoints,
            webdriver: false
        };
        
        // Store important window properties
        const windowProps = {
            chrome: window.chrome,
            devicePixelRatio: window.devicePixelRatio,
            innerHeight: window.innerHeight,
            innerWidth: window.innerWidth,
            outerHeight: window.outerHeight,
            outerWidth: window.outerWidth,
            screenX: window.screenX,
            screenY: window.screenY,
            screenLeft: window.screenLeft,
            screenTop: window.screenTop
        };
        
        // Create a script to inject into iframes
        const createIframeScript = () => {
            // Convert navigator properties to a string representation for injection
            const navigatorPropsStr = JSON.stringify(navigatorProps, (key, value) => {
                if (Array.isArray(value)) {
                    return `__ARRAY__${JSON.stringify(value)}`;
                }
                if (value === undefined) {
                    return '__UNDEFINED__';
                }
                return value;
            });
            
            // Create the script content
            return `
                (() => {
                    try {
                        // Parse navigator properties
                        const navigatorProps = JSON.parse('${navigatorPropsStr.replace(/'/g, "\\'")}', (key, value) => {
                            if (typeof value === 'string' && value.startsWith('__ARRAY__')) {
                                return JSON.parse(value.substring(9));
                            }
                            if (value === '__UNDEFINED__') {
                                return undefined;
                            }
                            return value;
                        });
                        
                        // Apply navigator properties
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
                        
                        // Ensure webdriver is completely removed
                        try {
                            const navigatorProto = Object.getPrototypeOf(navigator);
                            if (navigatorProto && 'webdriver' in navigatorProto) {
                                delete navigatorProto.webdriver;
                            }
                            
                            // Define property on navigator that returns false
                            Object.defineProperty(navigator, 'webdriver', {
                                get: () => false,
                                configurable: true,
                                enumerable: true
                            });
                        } catch (e) {
                            // Ignore errors
                        }
                        
                        // Setup chrome object if needed
                        if (!window.chrome) {
                            window.chrome = {
                                runtime: {},
                                app: {},
                                loadTimes: function() {},
                                csi: function() {}
                            };
                        }
                        
                        // Override property access detection methods
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
                        
                        // Apply the same patches to any nested iframes
                        document.createElement = (function(originalCreateElement) {
                            return function(tagName) {
                                const element = originalCreateElement.apply(this, arguments);
                                
                                if (tagName.toLowerCase() === 'iframe') {
                                    // Use a mutation observer to detect when the iframe is added to the DOM
                                    const observer = new MutationObserver((mutations, obs) => {
                                        try {
                                            // Check if the iframe has been added to the DOM
                                            if (element.contentWindow) {
                                                // Apply the same script to the nested iframe
                                                const script = element.contentWindow.document.createElement('script');
                                                script.textContent = document.currentScript.textContent;
                                                element.contentWindow.document.head.appendChild(script);
                                                
                                                // Disconnect the observer once we've patched the iframe
                                                obs.disconnect();
                                            }
                                        } catch (e) {
                                            // Ignore cross-origin errors and disconnect
                                            obs.disconnect();
                                        }
                                    });
                                    
                                    // Start observing the document for changes
                                    observer.observe(document, { childList: true, subtree: true });
                                }
                                
                                return element;
                            };
                        })(document.createElement);
                    } catch (e) {
                        // Ignore errors
                    }
                })();
            `;
        };
        
        // Override iframe creation
        const originalCreateElement = document.createElement;
        
        document.createElement = function(tagName) {
            const element = originalCreateElement.apply(this, arguments);
            
            // If this is an iframe, patch it after it's added to the document
            if (tagName.toLowerCase() === 'iframe') {
                // Use a mutation observer to detect when the iframe is added to the DOM
                const observer = new MutationObserver((mutations, obs) => {
                    try {
                        // Check if the iframe has been added to the DOM
                        if (element.contentWindow && element.contentDocument) {
                            // Apply patches to the iframe
                            try {
                                // Create a script element to inject our patches
                                const script = element.contentDocument.createElement('script');
                                script.textContent = createIframeScript();
                                
                                // Add the script to the iframe
                                if (element.contentDocument.head) {
                                    element.contentDocument.head.appendChild(script);
                                } else if (element.contentDocument.documentElement) {
                                    // If head doesn't exist yet, create it
                                    const head = element.contentDocument.createElement('head');
                                    head.appendChild(script);
                                    element.contentDocument.documentElement.appendChild(head);
                                }
                                
                                // Also try to patch directly
                                try {
                                    // Access the iframe's navigator
                                    const iframeNavigator = element.contentWindow.navigator;
                                    
                                    // Override navigator properties
                                    for (const [key, value] of Object.entries(navigatorProps)) {
                                        try {
                                            Object.defineProperty(iframeNavigator, key, {
                                                get: () => value,
                                                configurable: true,
                                                enumerable: true
                                            });
                                        } catch (e) {
                                            // Ignore errors
                                        }
                                    }
                                    
                                    // Ensure webdriver is completely removed
                                    try {
                                        delete Object.getPrototypeOf(iframeNavigator).webdriver;
                                    } catch (e) {
                                        // Ignore errors
                                    }
                                } catch (e) {
                                    // Ignore cross-origin errors
                                }
                            } catch (e) {
                                // Ignore errors
                            }
                            
                            // Disconnect the observer once we've patched the iframe
                            obs.disconnect();
                        }
                    } catch (e) {
                        // Ignore errors and disconnect
                        obs.disconnect();
                    }
                });
                
                // Start observing the document for changes
                observer.observe(document, { childList: true, subtree: true });
                
                // Also handle onload event as a backup
                element.addEventListener('load', function() {
                    try {
                        if (element.contentDocument) {
                            // Create a script element to inject our patches
                            const script = element.contentDocument.createElement('script');
                            script.textContent = createIframeScript();
                            
                            // Add the script to the iframe
                            if (element.contentDocument.head) {
                                element.contentDocument.head.appendChild(script);
                            }
                        }
                    } catch (e) {
                        // Ignore cross-origin errors
                    }
                });
            }
            
            return element;
        };
        
        // Also patch existing iframes
        try {
            const iframes = document.querySelectorAll('iframe');
            for (const iframe of iframes) {
                try {
                    if (iframe.contentWindow && iframe.contentDocument) {
                        // Create a script element to inject our patches
                        const script = iframe.contentDocument.createElement('script');
                        script.textContent = createIframeScript();
                        
                        // Add the script to the iframe
                        if (iframe.contentDocument.head) {
                            iframe.contentDocument.head.appendChild(script);
                        }
                    }
                } catch (e) {
                    // Ignore cross-origin errors
                }
            }
        } catch (e) {
            // Ignore errors
        }
    })();
    """
) 
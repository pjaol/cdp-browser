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
        // Store the current user agent
        const userAgent = navigator.userAgent;
        
        // Override navigator properties
        const navigatorProps = {
            userAgent: userAgent,
            appVersion: userAgent.replace('Mozilla/', ''),
            platform: 'MacIntel',
            vendor: 'Google Inc.'
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
        
        // Parse user agent to extract components
        const parseUserAgent = (ua) => {
            const result = {
                browser: 'Chrome',
                browserVersion: '121.0.0.0',
                engine: 'WebKit',
                engineVersion: '537.36',
                os: 'Mac OS X',
                osVersion: '10_15_7',
                device: '',
                isWindows: false,
                isMac: true,
                isLinux: false,
                isAndroid: false,
                isIOS: false
            };
            
            // Extract browser and version
            const chromeMatch = ua.match(/Chrome\\/([\\d.]+)/);
            if (chromeMatch) {
                result.browserVersion = chromeMatch[1];
            }
            
            // Extract engine version
            const webkitMatch = ua.match(/AppleWebKit\\/([\\d.]+)/);
            if (webkitMatch) {
                result.engineVersion = webkitMatch[1];
            }
            
            // Extract OS and version
            if (ua.includes('Windows')) {
                result.os = 'Windows';
                result.isWindows = true;
                result.isMac = false;
                
                const windowsMatch = ua.match(/Windows NT ([\\d.]+)/);
                if (windowsMatch) {
                    result.osVersion = windowsMatch[1];
                    // Map Windows NT version to Windows version
                    const windowsVersions = {
                        '10.0': '10',
                        '6.3': '8.1',
                        '6.2': '8',
                        '6.1': '7',
                        '6.0': 'Vista',
                        '5.2': 'XP',
                        '5.1': 'XP'
                    };
                    result.osVersionName = windowsVersions[result.osVersion] || '';
                }
            } else if (ua.includes('Mac OS X')) {
                result.os = 'Mac OS X';
                result.isMac = true;
                
                const macMatch = ua.match(/Mac OS X ([\\d_]+)/);
                if (macMatch) {
                    result.osVersion = macMatch[1];
                }
            } else if (ua.includes('Linux')) {
                result.os = 'Linux';
                result.isLinux = true;
                result.isMac = false;
            } else if (ua.includes('Android')) {
                result.os = 'Android';
                result.isAndroid = true;
                result.isMac = false;
                
                const androidMatch = ua.match(/Android ([\\d.]+)/);
                if (androidMatch) {
                    result.osVersion = androidMatch[1];
                }
            } else if (ua.includes('iPhone') || ua.includes('iPad') || ua.includes('iPod')) {
                result.os = 'iOS';
                result.isIOS = true;
                result.isMac = false;
                
                const iosMatch = ua.match(/OS ([\\d_]+)/);
                if (iosMatch) {
                    result.osVersion = iosMatch[1];
                }
            }
            
            return result;
        };
        
        // Get the current user agent
        const userAgent = navigator.userAgent;
        const parsedUA = parseUserAgent(userAgent);
        
        // Create consistent navigator properties
        const navigatorProps = {
            userAgent: userAgent,
            appVersion: userAgent.replace('Mozilla/', ''),
            platform: parsedUA.isMac ? 'MacIntel' : 
                      parsedUA.isWindows ? 'Win32' : 
                      parsedUA.isLinux ? 'Linux x86_64' : 
                      parsedUA.isAndroid ? 'Linux armv8l' : 
                      parsedUA.isIOS ? 'iPhone' : 'MacIntel',
            vendor: 'Google Inc.',
            appName: 'Netscape',
            appCodeName: 'Mozilla'
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
        
        // Override navigator.userAgentData if available
        if ('userAgentData' in navigator) {
            try {
                const brands = [
                    { brand: "Chrome", version: parsedUA.browserVersion.split('.')[0] },
                    { brand: "Chromium", version: parsedUA.browserVersion.split('.')[0] },
                    { brand: "Not=A?Brand", version: "24" }
                ];
                
                const mobile = parsedUA.isAndroid || parsedUA.isIOS;
                
                const platform = parsedUA.isMac ? 'macOS' : 
                                parsedUA.isWindows ? 'Windows' : 
                                parsedUA.isLinux ? 'Linux' : 
                                parsedUA.isAndroid ? 'Android' : 
                                parsedUA.isIOS ? 'iOS' : 'macOS';
                
                // Create a fake userAgentData object
                const uaData = {
                    brands: brands,
                    mobile: mobile,
                    platform: platform,
                    getHighEntropyValues: makeNativeFunction(function getHighEntropyValues(hints) {
                        return Promise.resolve({
                            brands: brands,
                            mobile: mobile,
                            platform: platform,
                            architecture: parsedUA.isMac || parsedUA.isWindows ? 'x86' : 'arm',
                            bitness: '64',
                            model: '',
                            platformVersion: parsedUA.osVersion.replace(/_/g, '.'),
                            uaFullVersion: parsedUA.browserVersion,
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
        
        // Override navigator.languages
        try {
            Object.defineProperty(navigator, 'languages', {
                get: () => ['en-US', 'en'],
                configurable: true,
                enumerable: true
            });
        } catch (e) {
            // Ignore errors
        }
        
        // Override navigator.mimeTypes and plugins to match the user agent
        try {
            // Create consistent mimeTypes and plugins based on the browser
            const createPlugins = () => {
                const plugins = [];
                
                // Add Chrome PDF Plugin
                plugins.push({
                    name: 'Chrome PDF Plugin',
                    filename: 'internal-pdf-viewer',
                    description: 'Portable Document Format',
                    length: 1,
                    item: function(index) { return this[index]; },
                    namedItem: function(name) { return this[name]; },
                    0: {
                        type: 'application/x-google-chrome-pdf',
                        suffixes: 'pdf',
                        description: 'Portable Document Format'
                    }
                });
                
                // Add Chrome PDF Viewer
                plugins.push({
                    name: 'Chrome PDF Viewer',
                    filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai',
                    description: '',
                    length: 1,
                    item: function(index) { return this[index]; },
                    namedItem: function(name) { return this[name]; },
                    0: {
                        type: 'application/pdf',
                        suffixes: 'pdf',
                        description: ''
                    }
                });
                
                // Add Native Client
                plugins.push({
                    name: 'Native Client',
                    filename: 'internal-nacl-plugin',
                    description: '',
                    length: 2,
                    item: function(index) { return this[index]; },
                    namedItem: function(name) { return this[name]; },
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
                });
                
                return plugins;
            };
            
            const plugins = createPlugins();
            
            // Create a plugins array with the correct properties
            const pluginsArray = {
                length: plugins.length,
                item: function(index) { return this[index]; },
                namedItem: function(name) { 
                    for (let i = 0; i < this.length; i++) {
                        if (this[i].name === name) {
                            return this[i];
                        }
                    }
                    return null;
                },
                refresh: function() {}
            };
            
            // Add plugins to the array
            for (let i = 0; i < plugins.length; i++) {
                pluginsArray[i] = plugins[i];
                pluginsArray[plugins[i].name] = plugins[i];
            }
            
            // Create a mimeTypes array
            const mimeTypesArray = {
                length: 0,
                item: function(index) { return this[index]; },
                namedItem: function(name) { return this[name]; }
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
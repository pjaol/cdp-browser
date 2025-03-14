"""
Worker-related stealth patches.

These patches ensure that Web Workers have the same user agent and properties
as the main thread, preventing detection through worker inconsistencies.
"""

from . import register_patch

# Basic Worker patch - simple user agent consistency
register_patch(
    name="worker_basic",
    description="Basic Worker user agent consistency",
    priority=30,  # Run after user agent is set
    script="""
    (() => {
        // Store the current user agent
        const mainUserAgent = navigator.userAgent;
        
        // Override Worker constructor to patch user agent
        const originalWorker = window.Worker;
        
        // Create a patched Worker constructor
        function PatchedWorker(url, options) {
            // Create the worker normally
            const worker = new originalWorker(url, options);
            
            // Inject user agent consistency script
            const blob = new Blob([`
                // Override worker navigator properties
                Object.defineProperty(navigator, 'userAgent', {
                    get: function() { return "${mainUserAgent}"; },
                    configurable: true
                });
            `], { type: 'application/javascript' });
            
            // Create URL for the blob
            const blobUrl = URL.createObjectURL(blob);
            
            // Import the script into the worker
            worker.postMessage({
                type: '__stealth_worker_init__',
                blobUrl: blobUrl
            });
            
            return worker;
        }
        
        // Make the patched Worker look like the original
        PatchedWorker.prototype = originalWorker.prototype;
        PatchedWorker.toString = function() { return 'function Worker() { [native code] }'; };
        
        // Replace the Worker constructor
        window.Worker = PatchedWorker;
    })();
    """
)

# Advanced Worker patch - comprehensive worker protection
register_patch(
    name="worker_advanced",
    description="Advanced Worker protection with comprehensive property matching",
    priority=31,
    script="""
    (() => {
        // Helper to make functions look native
        const makeNativeFunction = (fn, name = '') => {
            return function() {
                return fn.apply(this, arguments);
            };
        };
        
        // Store important navigator properties
        const navigatorProps = {
            userAgent: navigator.userAgent,
            appVersion: navigator.appVersion,
            platform: navigator.platform,
            vendor: navigator.vendor,
            language: navigator.language,
            deviceMemory: navigator.deviceMemory,
            hardwareConcurrency: navigator.hardwareConcurrency,
            appName: navigator.appName,
            appCodeName: navigator.appCodeName,
            cookieEnabled: navigator.cookieEnabled,
            doNotTrack: navigator.doNotTrack,
            maxTouchPoints: navigator.maxTouchPoints,
            webdriver: undefined
        };
        
        // Create a script to inject into workers
        const workerPatchScript = `
            // Override worker navigator properties
            const props = ${JSON.stringify(navigatorProps)};
            Object.keys(props).forEach(key => {
                Object.defineProperty(navigator, key, {
                    get: function() { return props[key]; },
                    configurable: true
                });
            });
            
            // Override worker detection methods
            self.isSecureContext = window.isSecureContext;
            
            // Add message handler to receive additional patches
            self.addEventListener('message', function(e) {
                if (e.data && e.data.type === '__stealth_worker_init__') {
                    // Import additional stealth scripts
                    if (e.data.blobUrl) {
                        importScripts(e.data.blobUrl);
                    }
                }
            });
        `;
        
        // Override Worker constructor
        const originalWorker = window.Worker;
        
        function PatchedWorker(url, options) {
            // Create a blob with our patch script
            const blob = new Blob([workerPatchScript], { type: 'application/javascript' });
            const blobUrl = URL.createObjectURL(blob);
            
            // Create the worker with patched scripts
            const worker = new originalWorker(url, options);
            
            // Apply patches
            worker.postMessage({
                type: '__stealth_worker_init__',
                blobUrl: blobUrl
            });
            
            // Return the patched worker
            return worker;
        }
        
        // Make the patched Worker look like the original
        PatchedWorker.prototype = originalWorker.prototype;
        PatchedWorker.toString = makeNativeFunction(function Worker() {}, 'Worker');
        
        // Replace the Worker constructor
        try {
            Object.defineProperty(window, 'Worker', {
                value: PatchedWorker,
                configurable: false,
                enumerable: true,
                writable: false
            });
        } catch (e) {
            // Fallback if defineProperty fails
            window.Worker = PatchedWorker;
        }
        
        // Also patch SharedWorker if available
        if (typeof SharedWorker !== 'undefined') {
            const originalSharedWorker = window.SharedWorker;
            
            function PatchedSharedWorker(url, options) {
                // Create a blob with our patch script
                const blob = new Blob([workerPatchScript], { type: 'application/javascript' });
                const blobUrl = URL.createObjectURL(blob);
                
                // Create the worker with patched scripts
                const worker = new originalSharedWorker(url, options);
                
                // Apply patches
                worker.port.postMessage({
                    type: '__stealth_worker_init__',
                    blobUrl: blobUrl
                });
                
                // Return the patched worker
                return worker;
            }
            
            // Make the patched SharedWorker look like the original
            PatchedSharedWorker.prototype = originalSharedWorker.prototype;
            PatchedSharedWorker.toString = makeNativeFunction(function SharedWorker() {}, 'SharedWorker');
            
            // Replace the SharedWorker constructor
            try {
                Object.defineProperty(window, 'SharedWorker', {
                    value: PatchedSharedWorker,
                    configurable: false,
                    enumerable: true,
                    writable: false
                });
            } catch (e) {
                // Fallback if defineProperty fails
                window.SharedWorker = PatchedSharedWorker;
            }
        }
        
        // Clean up URL.createObjectURL to prevent memory leaks
        const originalCreateObjectURL = URL.createObjectURL;
        URL.createObjectURL = function() {
            const url = originalCreateObjectURL.apply(this, arguments);
            if (arguments[0] instanceof Blob && arguments[0].type === 'application/javascript') {
                setTimeout(() => {
                    try {
                        URL.revokeObjectURL(url);
                    } catch (e) {
                        // Ignore revocation errors
                    }
                }, 1000);
            }
            return url;
        };
    })();
    """
) 
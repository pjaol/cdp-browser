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
            languages: JSON.stringify(navigator.languages),
            deviceMemory: navigator.deviceMemory,
            hardwareConcurrency: navigator.hardwareConcurrency,
            appName: navigator.appName,
            appCodeName: navigator.appCodeName,
            cookieEnabled: navigator.cookieEnabled,
            doNotTrack: navigator.doNotTrack,
            maxTouchPoints: navigator.maxTouchPoints,
            webdriver: false
        };
        
        // Create a script to inject into workers
        const workerPatchScript = `
            // Override worker navigator properties
            ${Object.entries(navigatorProps).map(([key, value]) => {
                if (typeof value === 'string' && value.startsWith('[') && value.endsWith(']')) {
                    // Handle arrays like languages
                    return `
                        Object.defineProperty(navigator, '${key}', {
                            get: function() { return JSON.parse('${value}'); },
                            configurable: true
                        });
                    `;
                } else if (typeof value === 'string') {
                    // Handle string values
                    return `
                        Object.defineProperty(navigator, '${key}', {
                            get: function() { return "${value.replace(/"/g, '\\"')}"; },
                            configurable: true
                        });
                    `;
                } else {
                    // Handle other values
                    return `
                        Object.defineProperty(navigator, '${key}', {
                            get: function() { return ${value}; },
                            configurable: true
                        });
                    `;
                }
            }).join('\n')}
            
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
            
            // Prepend our script to the worker
            const originalScripts = Array.isArray(url) ? url : [url];
            const patchedScripts = [blobUrl, ...originalScripts];
            
            // Create the worker with patched scripts
            const worker = new originalWorker(patchedScripts, options);
            
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
                
                // Prepend our script to the worker
                const originalScripts = Array.isArray(url) ? url : [url];
                const patchedScripts = [blobUrl, ...originalScripts];
                
                // Create the worker with patched scripts
                const worker = new originalSharedWorker(patchedScripts, options);
                
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
        
        // Monitor for dynamic worker creation
        // This catches workers created via Blob URLs
        const originalCreateObjectURL = URL.createObjectURL;
        URL.createObjectURL = function(blob) {
            if (blob instanceof Blob && blob.type === 'application/javascript') {
                // Try to detect if this is for a worker
                try {
                    // Convert blob to text to check content
                    const reader = new FileReader();
                    reader.readAsText(blob);
                    reader.onload = function() {
                        const content = reader.result;
                        // If it looks like worker code, create a new blob with our patches
                        if (content.includes('self.') || content.includes('addEventListener') || 
                            content.includes('postMessage')) {
                            const newBlob = new Blob([workerPatchScript, content], { type: 'application/javascript' });
                            // Replace the original blob with our patched version
                            blob = newBlob;
                        }
                    };
                } catch (e) {
                    // Ignore errors
                }
            }
            return originalCreateObjectURL.apply(this, arguments);
        };
    })();
    """
) 
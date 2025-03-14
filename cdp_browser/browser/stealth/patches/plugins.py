"""
Plugins patches.

These patches emulate browser plugins and mimeTypes to make the browser
appear more like a regular Chrome browser.
"""

from . import register_patch

# Basic plugins patch
register_patch(
    name="plugins_basic",
    description="Basic plugins and mimeTypes emulation",
    priority=70,
    script="""
    (() => {
        try {
            console.log("Starting plugins_basic patch");
            
            // Create plugin factory with robust error handling
            const createPlugin = (name, description, filename, mimeTypes) => {
                const plugin = { name, description, filename };
                
                // Add length property
                plugin.length = mimeTypes.length;
                
                // Add methods
                plugin.item = function(index) { return this[index]; };
                plugin.namedItem = function(name) { return this[name]; };
                
                // Add mime types to plugin
                mimeTypes.forEach((mt, i) => {
                    const mimeType = {
                        type: mt.type,
                        suffixes: mt.suffixes,
                        description: mt.description,
                        enabledPlugin: plugin
                    };
                    plugin[i] = mimeType;
                    plugin[mt.type] = mimeType;
                });
                
                return plugin;
            };
            
            // Create default plugins
            const defaultPlugins = [
                createPlugin(
                    'Chrome PDF Plugin',
                    'Portable Document Format',
                    'internal-pdf-viewer',
                    [{ type: 'application/x-google-chrome-pdf', suffixes: 'pdf', description: 'Portable Document Format' }]
                ),
                createPlugin(
                    'Chrome PDF Viewer',
                    '',
                    'mhjfbmdgcfjbbpaeojofohoefgiehjai',
                    [{ type: 'application/pdf', suffixes: 'pdf', description: '' }]
                ),
                createPlugin(
                    'Native Client',
                    '',
                    'internal-nacl-plugin',
                    [
                        { type: 'application/x-nacl', suffixes: '', description: 'Native Client Executable' },
                        { type: 'application/x-pnacl', suffixes: '', description: 'Portable Native Client Executable' }
                    ]
                )
            ];
            
            // Create plugins array that's properly iterable
            const plugins = {};
            
            // Add length property
            plugins.length = defaultPlugins.length;
            
            // Add methods
            plugins.item = function(index) { return this[index]; };
            plugins.namedItem = function(name) { return this[name]; };
            plugins.refresh = function() {};
            
            // Add Symbol.iterator to make Array.from work
            plugins[Symbol.iterator] = function* () {
                for (let i = 0; i < this.length; i++) {
                    yield this[i];
                }
            };
            
            // Add plugins to array
            defaultPlugins.forEach((plugin, i) => {
                plugins[i] = plugin;
                plugins[plugin.name] = plugin;
            });
            
            // Override navigator.plugins using direct assignment
            navigator.__defineGetter__('plugins', function() {
                return plugins;
            });
            
            // Create mimeTypes array that's properly iterable
            const mimeTypes = {};
            
            // Add the necessary methods
            mimeTypes.item = function(index) { return this[index]; };
            mimeTypes.namedItem = function(name) { return this[name]; };
            
            // Add Symbol.iterator to make Array.from work
            mimeTypes[Symbol.iterator] = function* () {
                for (let i = 0; i < this.length; i++) {
                    yield this[i];
                }
            };
            
            // Add mimeTypes from plugins
            let mimeTypeIndex = 0;
            for (let i = 0; i < defaultPlugins.length; i++) {
                const plugin = defaultPlugins[i];
                for (let j = 0; j < plugin.length; j++) {
                    const mimeType = plugin[j];
                    mimeTypes[mimeTypeIndex] = mimeType;
                    mimeTypes[mimeType.type] = mimeType;
                    mimeTypeIndex++;
                }
            }
            
            // Set the length property
            mimeTypes.length = mimeTypeIndex;
            
            // Override navigator.mimeTypes using direct assignment
            navigator.__defineGetter__('mimeTypes', function() {
                return mimeTypes;
            });
            
            console.log("Successfully completed plugins_basic patch");
            
        } catch (e) {
            console.error("Error in plugins_basic patch:", e);
            // Don't throw to avoid breaking the page
        }
    })();
    """
)

# Advanced plugins patch
register_patch(
    name="plugins_advanced",
    description="Advanced plugins and mimeTypes emulation with proper prototypes",
    priority=71,
    dependencies=["plugins_basic"],
    script="""
    (() => {
        try {
            console.log("Starting plugins_advanced patch");
            
            // Helper to make functions look native
            const makeNativeFunction = (fn, name = '') => {
                try {
                    // Use a safer approach without eval
                    const wrapped = function() {
                        return fn.apply(this, arguments);
                    };
                    
                    Object.defineProperty(wrapped, 'name', { value: name });
                    Object.defineProperty(wrapped, 'toString', {
                        value: function() {
                            return "function " + name + "() { [native code] }";
                        },
                        writable: false,
                        configurable: true
                    });
                    
                    return wrapped;
                } catch (e) {
                    console.error("Error creating native function:", e);
                    return fn; // Fallback to original function
                }
            };
            
            // Verify plugins exist before continuing
            if (navigator.plugins) {
                console.log(`Found plugins: length=${navigator.plugins.length}`);
                
                // Make plugins look more native
                try {
                    if (navigator.plugins.item) {
                        navigator.plugins.item = makeNativeFunction(navigator.plugins.item, 'item');
                    }
                    
                    if (navigator.plugins.namedItem) {
                        navigator.plugins.namedItem = makeNativeFunction(navigator.plugins.namedItem, 'namedItem');
                    }
                    
                    if (navigator.plugins.refresh) {
                        navigator.plugins.refresh = makeNativeFunction(navigator.plugins.refresh, 'refresh');
                    }
                } catch (e) {
                    console.error("Error making plugins methods native:", e);
                }
                
                // Make mimeTypes look more native
                try {
                    if (navigator.mimeTypes && navigator.mimeTypes.item) {
                        navigator.mimeTypes.item = makeNativeFunction(navigator.mimeTypes.item, 'item');
                    }
                    
                    if (navigator.mimeTypes && navigator.mimeTypes.namedItem) {
                        navigator.mimeTypes.namedItem = makeNativeFunction(navigator.mimeTypes.namedItem, 'namedItem');
                    }
                } catch (e) {
                    console.error("Error making mimeTypes methods native:", e);
                }
                
                // Make individual plugins look more native
                for (let i = 0; i < navigator.plugins.length; i++) {
                    try {
                        const plugin = navigator.plugins[i];
                        if (plugin && plugin.item) {
                            plugin.item = makeNativeFunction(plugin.item, 'item');
                        }
                        if (plugin && plugin.namedItem) {
                            plugin.namedItem = makeNativeFunction(plugin.namedItem, 'namedItem');
                        }
                    } catch (e) {
                        console.error(`Error making plugin ${i} methods native:`, e);
                    }
                }
            } else {
                console.log("No plugins found to enhance");
            }
            
            console.log("Successfully completed plugins_advanced patch");
            
        } catch (e) {
            console.error("Error in plugins_advanced patch:", e);
            // Don't throw to avoid breaking the page
        }
    })();
    """
) 
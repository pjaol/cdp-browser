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
        // Create plugin factory
        const createPlugin = (name, description, filename, mimeTypes) => {
            const plugin = { name, description, filename };
            Object.defineProperty(plugin, 'length', { value: mimeTypes.length });
            Object.defineProperty(plugin, 'item', { value: (index) => plugin[index] });
            Object.defineProperty(plugin, 'namedItem', { value: (name) => plugin[name] });
            
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
        
        // Create plugins array
        const plugins = {
            length: defaultPlugins.length,
            item: function(index) { return this[index]; },
            namedItem: function(name) { return this[name]; },
            refresh: function() {}
        };
        
        // Add plugins to array
        defaultPlugins.forEach((plugin, i) => {
            plugins[i] = plugin;
            plugins[plugin.name] = plugin;
        });
        
        // Override navigator.plugins and mimeTypes
        Object.defineProperty(navigator, 'plugins', {
            get: () => plugins,
            enumerable: true,
            configurable: true
        });
        
        // Create mimeTypes array
        const mimeTypes = {
            length: 0,
            item: function(index) { return this[index]; },
            namedItem: function(name) { return this[name]; }
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
        Object.defineProperty(mimeTypes, 'length', {
            value: mimeTypeIndex,
            writable: false,
            enumerable: true,
            configurable: true
        });
        
        Object.defineProperty(navigator, 'mimeTypes', {
            get: () => mimeTypes,
            enumerable: true,
            configurable: true
        });
    })();
    """
)

# Advanced plugins patch
register_patch(
    name="plugins_advanced",
    description="Advanced plugins and mimeTypes emulation with proper prototypes",
    priority=71,
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
        
        // Create plugin factory with proper prototypes
        const createPlugin = (name, description, filename, mimeTypes) => {
            // Create base plugin object
            const plugin = Object.create(Object.prototype);
            
            // Define core properties
            Object.defineProperties(plugin, {
                name: { value: name, enumerable: true, configurable: true },
                description: { value: description, enumerable: true, configurable: true },
                filename: { value: filename, enumerable: true, configurable: true },
                length: { value: mimeTypes.length, enumerable: true, configurable: true }
            });
            
            // Define methods
            plugin.item = makeNativeFunction(function item(index) { 
                return this[index] || null; 
            }, 'item');
            
            plugin.namedItem = makeNativeFunction(function namedItem(name) { 
                return this[name] || null; 
            }, 'namedItem');
            
            // Add mimeTypes to the plugin
            mimeTypes.forEach((mt, i) => {
                // Create mimeType object
                const mimeType = Object.create(Object.prototype);
                
                // Define mimeType properties
                Object.defineProperties(mimeType, {
                    type: { value: mt.type, enumerable: true, configurable: true },
                    suffixes: { value: mt.suffixes, enumerable: true, configurable: true },
                    description: { value: mt.description, enumerable: true, configurable: true }
                });
                
                // Set circular reference
                Object.defineProperty(mimeType, 'enabledPlugin', { 
                    value: plugin,
                    enumerable: true, 
                    configurable: true 
                });
                
                // Make it look like a real MimeType
                Object.defineProperty(mimeType, Symbol.toStringTag, { value: 'MimeType' });
                
                // Add to plugin by index and type
                plugin[i] = mimeType;
                plugin[mt.type] = mimeType;
            });
            
            // Make it look like a real Plugin
            Object.defineProperty(plugin, Symbol.toStringTag, { value: 'Plugin' });
            
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
        
        // Create PluginArray with proper prototype
        const createPluginArray = (plugins) => {
            // Create base object
            const pluginArray = Object.create(Object.prototype);
            
            // Define length property
            Object.defineProperty(pluginArray, 'length', {
                value: plugins.length,
                enumerable: true,
                configurable: true
            });
            
            // Define methods
            pluginArray.item = makeNativeFunction(function item(index) {
                return this[index] || null;
            }, 'item');
            
            pluginArray.namedItem = makeNativeFunction(function namedItem(name) {
                return this[name] || null;
            }, 'namedItem');
            
            pluginArray.refresh = makeNativeFunction(function refresh() {
                // This method doesn't actually do anything in modern browsers
            }, 'refresh');
            
            // Add plugins to array
            plugins.forEach((plugin, i) => {
                pluginArray[i] = plugin;
                pluginArray[plugin.name] = plugin;
            });
            
            // Make it look like a real PluginArray
            Object.defineProperty(pluginArray, Symbol.toStringTag, { value: 'PluginArray' });
            
            return pluginArray;
        };
        
        // Create MimeTypeArray with proper prototype
        const createMimeTypeArray = (plugins) => {
            // Create base object
            const mimeTypeArray = Object.create(Object.prototype);
            
            // Define methods
            mimeTypeArray.item = makeNativeFunction(function item(index) {
                return this[index] || null;
            }, 'item');
            
            mimeTypeArray.namedItem = makeNativeFunction(function namedItem(name) {
                return this[name] || null;
            }, 'namedItem');
            
            // Add mimeTypes from plugins
            let mimeTypeIndex = 0;
            for (let i = 0; i < plugins.length; i++) {
                const plugin = plugins[i];
                for (let j = 0; j < plugin.length; j++) {
                    const mimeType = plugin[j];
                    mimeTypeArray[mimeTypeIndex] = mimeType;
                    mimeTypeArray[mimeType.type] = mimeType;
                    mimeTypeIndex++;
                }
            }
            
            // Set the length property
            Object.defineProperty(mimeTypeArray, 'length', {
                value: mimeTypeIndex,
                enumerable: true,
                configurable: true
            });
            
            // Make it look like a real MimeTypeArray
            Object.defineProperty(mimeTypeArray, Symbol.toStringTag, { value: 'MimeTypeArray' });
            
            return mimeTypeArray;
        };
        
        // Create the plugin and mimeType arrays
        const pluginArray = createPluginArray(defaultPlugins);
        const mimeTypeArray = createMimeTypeArray(defaultPlugins);
        
        // Override navigator.plugins and mimeTypes
        Object.defineProperty(navigator, 'plugins', {
            get: () => pluginArray,
            enumerable: true,
            configurable: true
        });
        
        Object.defineProperty(navigator, 'mimeTypes', {
            get: () => mimeTypeArray,
            enumerable: true,
            configurable: true
        });
    })();
    """
) 
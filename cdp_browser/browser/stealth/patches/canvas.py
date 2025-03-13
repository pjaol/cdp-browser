"""
Canvas fingerprinting protection patches.

These patches help prevent canvas fingerprinting by adding subtle noise
to canvas operations or providing consistent fingerprints.
"""

from . import register_patch

# Basic canvas fingerprinting protection
register_patch(
    name="canvas_basic",
    description="Basic canvas fingerprinting protection with subtle noise",
    priority=50,
    script="""
    (() => {
        // Get original canvas methods
        const getContext = HTMLCanvasElement.prototype.getContext;
        const toDataURL = HTMLCanvasElement.prototype.toDataURL;
        const toBlob = HTMLCanvasElement.prototype.toBlob;
        
        // Add subtle noise to canvas data
        const addNoise = (canvas) => {
            try {
                // Only add noise if the canvas is being used for fingerprinting
                // (small canvas or hidden canvas)
                if (canvas.width <= 500 && canvas.height <= 200) {
                    const ctx = getContext.call(canvas, '2d');
                    
                    // Get image data
                    const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height);
                    const data = imageData.data;
                    
                    // Add very subtle noise to random pixels
                    // This is designed to be almost invisible but change the fingerprint
                    for (let i = 0; i < data.length; i += 4) {
                        // Only modify 5% of pixels with minimal changes
                        if (Math.random() < 0.05) {
                            // Add very small noise (-1, 0, or +1)
                            data[i] = Math.max(0, Math.min(255, data[i] + (Math.random() > 0.5 ? 1 : -1)));
                            data[i+1] = Math.max(0, Math.min(255, data[i+1] + (Math.random() > 0.5 ? 1 : -1)));
                            data[i+2] = Math.max(0, Math.min(255, data[i+2] + (Math.random() > 0.5 ? 1 : -1)));
                        }
                    }
                    
                    // Put the modified image data back
                    ctx.putImageData(imageData, 0, 0);
                }
            } catch (e) {
                // Ignore errors
            }
        };
        
        // Override toDataURL
        HTMLCanvasElement.prototype.toDataURL = function() {
            addNoise(this);
            return toDataURL.apply(this, arguments);
        };
        
        // Override toBlob
        HTMLCanvasElement.prototype.toBlob = function() {
            addNoise(this);
            return toBlob.apply(this, arguments);
        };
        
        // Monitor getContext to detect canvas fingerprinting
        HTMLCanvasElement.prototype.getContext = function() {
            const context = getContext.apply(this, arguments);
            
            // Only modify 2d context
            if (arguments[0] === '2d' && context) {
                // Store original methods
                const originalFillText = context.fillText;
                const originalStrokeText = context.strokeText;
                
                // Override fillText to detect text rendering fingerprinting
                context.fillText = function() {
                    // Check if this is likely a fingerprinting attempt
                    // (common fingerprinting strings)
                    const text = arguments[0] || '';
                    if (
                        text.includes('Cwm fjordbank') || 
                        text.includes('Sphinx of black quartz') ||
                        text.includes('abcdefghijklmnopqrstuvwxyz') ||
                        text.includes('mmmmmmmmmmlli')
                    ) {
                        // Apply very subtle modification to the position
                        if (arguments[1] !== undefined && arguments[2] !== undefined) {
                            // Add ±0.1px to the position
                            arguments[1] += (Math.random() * 0.2) - 0.1;
                            arguments[2] += (Math.random() * 0.2) - 0.1;
                        }
                    }
                    
                    return originalFillText.apply(this, arguments);
                };
                
                // Override strokeText similarly
                context.strokeText = function() {
                    const text = arguments[0] || '';
                    if (
                        text.includes('Cwm fjordbank') || 
                        text.includes('Sphinx of black quartz') ||
                        text.includes('abcdefghijklmnopqrstuvwxyz') ||
                        text.includes('mmmmmmmmmmlli')
                    ) {
                        if (arguments[1] !== undefined && arguments[2] !== undefined) {
                            arguments[1] += (Math.random() * 0.2) - 0.1;
                            arguments[2] += (Math.random() * 0.2) - 0.1;
                        }
                    }
                    
                    return originalStrokeText.apply(this, arguments);
                };
            }
            
            return context;
        };
    })();
    """
)

# Advanced canvas fingerprinting protection
register_patch(
    name="canvas_advanced",
    description="Advanced canvas fingerprinting protection with consistent fingerprints",
    priority=51,
    script="""
    (() => {
        // Generate a consistent but unique fingerprint modifier
        // This will be the same for a given browser session
        const generateFingerprint = () => {
            // Create a stable fingerprint based on user agent
            // This ensures the same user gets the same fingerprint
            let fingerprint = 0;
            const userAgent = navigator.userAgent;
            
            for (let i = 0; i < userAgent.length; i++) {
                fingerprint = ((fingerprint << 5) - fingerprint) + userAgent.charCodeAt(i);
                fingerprint = fingerprint & fingerprint; // Convert to 32bit integer
            }
            
            // Create a seeded random number generator
            const seededRandom = () => {
                let seed = fingerprint;
                return function() {
                    seed = (seed * 9301 + 49297) % 233280;
                    return seed / 233280;
                };
            };
            
            return {
                random: seededRandom(),
                value: fingerprint
            };
        };
        
        const fingerprint = generateFingerprint();
        
        // Store original methods
        const getContext = HTMLCanvasElement.prototype.getContext;
        const toDataURL = HTMLCanvasElement.prototype.toDataURL;
        const toBlob = HTMLCanvasElement.prototype.toBlob;
        
        // Add consistent noise to canvas data
        const addConsistentNoise = (canvas) => {
            try {
                // Only add noise if the canvas is being used for fingerprinting
                // (small canvas or hidden canvas)
                if (canvas.width <= 500 && canvas.height <= 200) {
                    const ctx = getContext.call(canvas, '2d');
                    
                    // Get image data
                    const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height);
                    const data = imageData.data;
                    
                    // Add consistent noise based on our fingerprint
                    for (let i = 0; i < data.length; i += 4) {
                        // Use our seeded random to ensure consistency
                        if (fingerprint.random() < 0.05) {
                            // Add very small noise (-1, 0, or +1)
                            const mod = fingerprint.random() > 0.5 ? 1 : -1;
                            data[i] = Math.max(0, Math.min(255, data[i] + mod));
                            data[i+1] = Math.max(0, Math.min(255, data[i+1] + mod));
                            data[i+2] = Math.max(0, Math.min(255, data[i+2] + mod));
                        }
                    }
                    
                    // Put the modified image data back
                    ctx.putImageData(imageData, 0, 0);
                }
            } catch (e) {
                // Ignore errors
            }
        };
        
        // Override toDataURL
        HTMLCanvasElement.prototype.toDataURL = function() {
            addConsistentNoise(this);
            return toDataURL.apply(this, arguments);
        };
        
        // Override toBlob
        HTMLCanvasElement.prototype.toBlob = function(callback) {
            addConsistentNoise(this);
            return toBlob.apply(this, arguments);
        };
        
        // Monitor getContext to detect canvas fingerprinting
        HTMLCanvasElement.prototype.getContext = function() {
            const context = getContext.apply(this, arguments);
            
            // Only modify 2d context
            if (arguments[0] === '2d' && context) {
                // Store original methods
                const originalFillText = context.fillText;
                const originalStrokeText = context.strokeText;
                const originalMeasureText = context.measureText;
                
                // Override fillText to detect text rendering fingerprinting
                context.fillText = function() {
                    // Check if this is likely a fingerprinting attempt
                    const text = arguments[0] || '';
                    if (
                        text.includes('Cwm fjordbank') || 
                        text.includes('Sphinx of black quartz') ||
                        text.includes('abcdefghijklmnopqrstuvwxyz') ||
                        text.includes('mmmmmmmmmmlli') ||
                        text.length > 10
                    ) {
                        // Apply consistent modification to the position
                        if (arguments[1] !== undefined && arguments[2] !== undefined) {
                            // Add a consistent offset based on our fingerprint
                            const offsetX = (fingerprint.random() * 0.2) - 0.1;
                            const offsetY = (fingerprint.random() * 0.2) - 0.1;
                            arguments[1] += offsetX;
                            arguments[2] += offsetY;
                        }
                    }
                    
                    return originalFillText.apply(this, arguments);
                };
                
                // Override strokeText similarly
                context.strokeText = function() {
                    const text = arguments[0] || '';
                    if (
                        text.includes('Cwm fjordbank') || 
                        text.includes('Sphinx of black quartz') ||
                        text.includes('abcdefghijklmnopqrstuvwxyz') ||
                        text.includes('mmmmmmmmmmlli') ||
                        text.length > 10
                    ) {
                        if (arguments[1] !== undefined && arguments[2] !== undefined) {
                            const offsetX = (fingerprint.random() * 0.2) - 0.1;
                            const offsetY = (fingerprint.random() * 0.2) - 0.1;
                            arguments[1] += offsetX;
                            arguments[2] += offsetY;
                        }
                    }
                    
                    return originalStrokeText.apply(this, arguments);
                };
                
                // Override measureText to ensure consistent text metrics
                context.measureText = function(text) {
                    const metrics = originalMeasureText.apply(this, arguments);
                    
                    // Check if this is likely a fingerprinting attempt
                    if (
                        text.includes('Cwm fjordbank') || 
                        text.includes('Sphinx of black quartz') ||
                        text.includes('abcdefghijklmnopqrstuvwxyz') ||
                        text.includes('mmmmmmmmmmlli') ||
                        text.length > 10
                    ) {
                        // Add a tiny consistent modification to the width
                        const widthMod = (fingerprint.random() * 0.02) - 0.01;
                        metrics.width += widthMod;
                        
                        // If advanced TextMetrics properties are available, modify them too
                        if (metrics.actualBoundingBoxAscent !== undefined) {
                            const smallMod = (fingerprint.random() * 0.02) - 0.01;
                            metrics.actualBoundingBoxAscent += smallMod;
                        }
                        
                        if (metrics.actualBoundingBoxDescent !== undefined) {
                            const smallMod = (fingerprint.random() * 0.02) - 0.01;
                            metrics.actualBoundingBoxDescent += smallMod;
                        }
                    }
                    
                    return metrics;
                };
            }
            
            return context;
        };
        
        // Also protect OffscreenCanvas if available
        if (typeof OffscreenCanvas !== 'undefined') {
            const offscreenGetContext = OffscreenCanvas.prototype.getContext;
            const offscreenToDataURL = OffscreenCanvas.prototype.convertToBlob;
            
            // Override convertToBlob (equivalent to toBlob for OffscreenCanvas)
            if (offscreenToDataURL) {
                OffscreenCanvas.prototype.convertToBlob = function() {
                    addConsistentNoise(this);
                    return offscreenToDataURL.apply(this, arguments);
                };
            }
            
            // Monitor getContext for OffscreenCanvas
            OffscreenCanvas.prototype.getContext = function() {
                const context = offscreenGetContext.apply(this, arguments);
                
                // Only modify 2d context
                if (arguments[0] === '2d' && context) {
                    // Apply the same modifications as for regular canvas
                    const originalFillText = context.fillText;
                    const originalStrokeText = context.strokeText;
                    
                    if (originalFillText) {
                        context.fillText = function() {
                            const text = arguments[0] || '';
                            if (
                                text.includes('Cwm fjordbank') || 
                                text.includes('Sphinx of black quartz') ||
                                text.includes('abcdefghijklmnopqrstuvwxyz') ||
                                text.includes('mmmmmmmmmmlli')
                            ) {
                                if (arguments[1] !== undefined && arguments[2] !== undefined) {
                                    const offsetX = (fingerprint.random() * 0.2) - 0.1;
                                    const offsetY = (fingerprint.random() * 0.2) - 0.1;
                                    arguments[1] += offsetX;
                                    arguments[2] += offsetY;
                                }
                            }
                            
                            return originalFillText.apply(this, arguments);
                        };
                    }
                    
                    if (originalStrokeText) {
                        context.strokeText = function() {
                            const text = arguments[0] || '';
                            if (
                                text.includes('Cwm fjordbank') || 
                                text.includes('Sphinx of black quartz') ||
                                text.includes('abcdefghijklmnopqrstuvwxyz') ||
                                text.includes('mmmmmmmmmmlli')
                            ) {
                                if (arguments[1] !== undefined && arguments[2] !== undefined) {
                                    const offsetX = (fingerprint.random() * 0.2) - 0.1;
                                    const offsetY = (fingerprint.random() * 0.2) - 0.1;
                                    arguments[1] += offsetX;
                                    arguments[2] += offsetY;
                                }
                            }
                            
                            return originalStrokeText.apply(this, arguments);
                        };
                    }
                }
                
                return context;
            };
        }
    })();
    """
) 
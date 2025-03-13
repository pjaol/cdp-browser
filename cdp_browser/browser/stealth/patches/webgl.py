"""
WebGL fingerprinting protection patches.

These patches help prevent WebGL fingerprinting by normalizing WebGL parameters
and adding subtle variations to WebGL rendering.
"""

from . import register_patch

# Basic WebGL fingerprinting protection
register_patch(
    name="webgl_basic",
    description="Basic WebGL fingerprinting protection with parameter normalization",
    priority=60,
    script="""
    (() => {
        // Store original methods
        const getParameter = WebGLRenderingContext.prototype.getParameter;
        const getExtension = WebGLRenderingContext.prototype.getExtension;
        const getShaderPrecisionFormat = WebGLRenderingContext.prototype.getShaderPrecisionFormat;
        
        // Common WebGL fingerprinting parameters
        const VENDOR = 0x1F00;
        const RENDERER = 0x1F01;
        const VERSION = 0x1F02;
        const SHADING_LANGUAGE_VERSION = 0x8B8C;
        const UNMASKED_VENDOR_WEBGL = 0x9245;
        const UNMASKED_RENDERER_WEBGL = 0x9246;
        
        // Override getParameter to normalize fingerprinting parameters
        WebGLRenderingContext.prototype.getParameter = function(parameter) {
            // Normalize common fingerprinting parameters
            switch (parameter) {
                case VENDOR:
                    return "WebKit";
                case RENDERER:
                    return "WebKit WebGL";
                case UNMASKED_VENDOR_WEBGL:
                    return "Google Inc.";
                case UNMASKED_RENDERER_WEBGL:
                    return "ANGLE (Apple, Apple M1 Pro, OpenGL 4.1)";
                default:
                    return getParameter.apply(this, arguments);
            }
        };
        
        // Also apply to WebGL2RenderingContext if available
        if (typeof WebGL2RenderingContext !== 'undefined') {
            WebGL2RenderingContext.prototype.getParameter = WebGLRenderingContext.prototype.getParameter;
        }
    })();
    """
)

# Advanced WebGL fingerprinting protection
register_patch(
    name="webgl_advanced",
    description="Advanced WebGL fingerprinting protection with consistent variations",
    priority=61,
    script="""
    (() => {
        // Generate a consistent but unique fingerprint modifier
        // This will be the same for a given browser session
        const generateFingerprint = () => {
            // Create a stable fingerprint based on user agent
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
        const getParameter = WebGLRenderingContext.prototype.getParameter;
        const getExtension = WebGLRenderingContext.prototype.getExtension;
        const getShaderPrecisionFormat = WebGLRenderingContext.prototype.getShaderPrecisionFormat;
        const getSupportedExtensions = WebGLRenderingContext.prototype.getSupportedExtensions;
        const readPixels = WebGLRenderingContext.prototype.readPixels;
        
        // Common WebGL fingerprinting parameters
        const VENDOR = 0x1F00;
        const RENDERER = 0x1F01;
        const VERSION = 0x1F02;
        const SHADING_LANGUAGE_VERSION = 0x8B8C;
        const UNMASKED_VENDOR_WEBGL = 0x9245;
        const UNMASKED_RENDERER_WEBGL = 0x9246;
        const ALIASED_LINE_WIDTH_RANGE = 0x846E;
        const ALIASED_POINT_SIZE_RANGE = 0x846D;
        const MAX_VIEWPORT_DIMS = 0x0D3A;
        
        // Define consistent WebGL parameters
        const webglParams = {
            [VENDOR]: "WebKit",
            [RENDERER]: "WebKit WebGL",
            [VERSION]: "WebGL 1.0 (OpenGL ES 2.0 Chromium)",
            [SHADING_LANGUAGE_VERSION]: "WebGL GLSL ES 1.0 (OpenGL ES GLSL ES 1.0 Chromium)",
            [UNMASKED_VENDOR_WEBGL]: "Google Inc.",
            [UNMASKED_RENDERER_WEBGL]: "ANGLE (Apple, Apple M1 Pro, OpenGL 4.1)"
        };
        
        // Override getParameter to provide consistent fingerprinting parameters
        WebGLRenderingContext.prototype.getParameter = function(parameter) {
            // Check if this is a fingerprinting parameter
            if (parameter in webglParams) {
                return webglParams[parameter];
            }
            
            // For numeric array parameters, add subtle consistent variations
            const result = getParameter.apply(this, arguments);
            
            if (result instanceof Float32Array) {
                // Clone the result to avoid modifying the original
                const newResult = new Float32Array(result);
                
                // Add subtle consistent variations
                for (let i = 0; i < newResult.length; i++) {
                    // Add very small noise (±0.01% of the value)
                    const noise = (fingerprint.random() * 0.0002) - 0.0001;
                    newResult[i] = newResult[i] * (1 + noise);
                }
                
                return newResult;
            }
            
            if (result instanceof Int32Array) {
                // Clone the result to avoid modifying the original
                const newResult = new Int32Array(result);
                
                // For certain parameters, add subtle consistent variations
                if (parameter === MAX_VIEWPORT_DIMS) {
                    // Add very small noise (±1 pixel)
                    const noise0 = Math.floor(fingerprint.random() * 3) - 1;
                    const noise1 = Math.floor(fingerprint.random() * 3) - 1;
                    newResult[0] += noise0;
                    newResult[1] += noise1;
                }
                
                return newResult;
            }
            
            return result;
        };
        
        // Override getShaderPrecisionFormat to provide consistent precision values
        WebGLRenderingContext.prototype.getShaderPrecisionFormat = function() {
            const result = getShaderPrecisionFormat.apply(this, arguments);
            
            if (result) {
                // Clone the result
                const newResult = {
                    precision: result.precision,
                    rangeMin: result.rangeMin,
                    rangeMax: result.rangeMax
                };
                
                // Add subtle consistent variations
                const precisionNoise = Math.floor(fingerprint.random() * 3) - 1;
                newResult.precision += precisionNoise;
                
                return newResult;
            }
            
            return result;
        };
        
        // Override readPixels to add subtle noise to pixel data
        WebGLRenderingContext.prototype.readPixels = function(x, y, width, height, format, type, pixels) {
            // Call the original method
            readPixels.apply(this, arguments);
            
            // Only modify small readbacks that might be used for fingerprinting
            if (width * height <= 256) {
                try {
                    // Add subtle consistent noise to the pixel data
                    for (let i = 0; i < pixels.length; i++) {
                        if (fingerprint.random() < 0.05) {
                            // Add very small noise (-1, 0, or +1)
                            const mod = fingerprint.random() > 0.5 ? 1 : -1;
                            
                            // For Uint8Array or similar
                            if (pixels instanceof Uint8Array || pixels instanceof Uint8ClampedArray) {
                                pixels[i] = Math.max(0, Math.min(255, pixels[i] + mod));
                            }
                            // For Float32Array
                            else if (pixels instanceof Float32Array) {
                                pixels[i] += mod * 0.01;
                            }
                        }
                    }
                } catch (e) {
                    // Ignore errors
                }
            }
        };
        
        // Override getSupportedExtensions to provide a consistent set of extensions
        WebGLRenderingContext.prototype.getSupportedExtensions = function() {
            const extensions = getSupportedExtensions.apply(this, arguments);
            
            // Return a stable set of extensions
            return [
                "ANGLE_instanced_arrays",
                "EXT_blend_minmax",
                "EXT_color_buffer_half_float",
                "EXT_disjoint_timer_query",
                "EXT_float_blend",
                "EXT_frag_depth",
                "EXT_shader_texture_lod",
                "EXT_texture_compression_bptc",
                "EXT_texture_compression_rgtc",
                "EXT_texture_filter_anisotropic",
                "WEBKIT_EXT_texture_filter_anisotropic",
                "EXT_sRGB",
                "KHR_parallel_shader_compile",
                "OES_element_index_uint",
                "OES_fbo_render_mipmap",
                "OES_standard_derivatives",
                "OES_texture_float",
                "OES_texture_float_linear",
                "OES_texture_half_float",
                "OES_texture_half_float_linear",
                "OES_vertex_array_object",
                "WEBGL_color_buffer_float",
                "WEBGL_compressed_texture_s3tc",
                "WEBKIT_WEBGL_compressed_texture_s3tc",
                "WEBGL_compressed_texture_s3tc_srgb",
                "WEBGL_debug_renderer_info",
                "WEBGL_debug_shaders",
                "WEBGL_depth_texture",
                "WEBKIT_WEBGL_depth_texture",
                "WEBGL_draw_buffers",
                "WEBGL_lose_context",
                "WEBKIT_WEBGL_lose_context",
                "WEBGL_multi_draw"
            ];
        };
        
        // Also apply to WebGL2RenderingContext if available
        if (typeof WebGL2RenderingContext !== 'undefined') {
            WebGL2RenderingContext.prototype.getParameter = WebGLRenderingContext.prototype.getParameter;
            WebGL2RenderingContext.prototype.getShaderPrecisionFormat = WebGLRenderingContext.prototype.getShaderPrecisionFormat;
            WebGL2RenderingContext.prototype.readPixels = WebGLRenderingContext.prototype.readPixels;
            WebGL2RenderingContext.prototype.getSupportedExtensions = WebGLRenderingContext.prototype.getSupportedExtensions;
        }
        
        // Block access to WEBGL_debug_renderer_info extension which reveals GPU info
        const originalGetExtension = WebGLRenderingContext.prototype.getExtension;
        WebGLRenderingContext.prototype.getExtension = function(name) {
            if (name === 'WEBGL_debug_renderer_info') {
                // Return a fake extension with the expected constants
                return {
                    UNMASKED_VENDOR_WEBGL: UNMASKED_VENDOR_WEBGL,
                    UNMASKED_RENDERER_WEBGL: UNMASKED_RENDERER_WEBGL
                };
            }
            return originalGetExtension.apply(this, arguments);
        };
        
        if (typeof WebGL2RenderingContext !== 'undefined') {
            WebGL2RenderingContext.prototype.getExtension = WebGLRenderingContext.prototype.getExtension;
        }
    })();
    """
) 
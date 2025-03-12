"""
Stealth patches for CDP browser to avoid bot detection.
These patches are applied at the browser and page level to make automation less detectable.
"""

import json
from typing import Dict, Any

class StealthPatches:
    @staticmethod
    def get_webdriver_patch() -> Dict[str, Any]:
        """
        Patch to hide navigator.webdriver flag.
        """
        return {
            "source": """
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
            """
        }
    
    @staticmethod
    def get_chrome_runtime_patch() -> Dict[str, Any]:
        """
        Patch to ensure window.chrome exists and has expected properties.
        """
        return {
            "source": """
                window.chrome = {
                    app: {
                        isInstalled: false,
                        InstallState: {
                            DISABLED: 'disabled',
                            INSTALLED: 'installed',
                            NOT_INSTALLED: 'not_installed'
                        },
                        RunningState: {
                            CANNOT_RUN: 'cannot_run',
                            READY_TO_RUN: 'ready_to_run',
                            RUNNING: 'running'
                        }
                    },
                    runtime: {
                        OnInstalledReason: {
                            CHROME_UPDATE: 'chrome_update',
                            INSTALL: 'install',
                            SHARED_MODULE_UPDATE: 'shared_module_update',
                            UPDATE: 'update'
                        },
                        OnRestartRequiredReason: {
                            APP_UPDATE: 'app_update',
                            OS_UPDATE: 'os_update',
                            PERIODIC: 'periodic'
                        },
                        PlatformArch: {
                            ARM: 'arm',
                            ARM64: 'arm64',
                            MIPS: 'mips',
                            MIPS64: 'mips64',
                            X86_32: 'x86-32',
                            X86_64: 'x86-64'
                        },
                        PlatformNaclArch: {
                            ARM: 'arm',
                            MIPS: 'mips',
                            MIPS64: 'mips64',
                            X86_32: 'x86-32',
                            X86_64: 'x86-64'
                        },
                        PlatformOs: {
                            ANDROID: 'android',
                            CROS: 'cros',
                            LINUX: 'linux',
                            MAC: 'mac',
                            OPENBSD: 'openbsd',
                            WIN: 'win'
                        },
                        RequestUpdateCheckStatus: {
                            NO_UPDATE: 'no_update',
                            THROTTLED: 'throttled',
                            UPDATE_AVAILABLE: 'update_available'
                        }
                    }
                };
            """
        }
    
    @staticmethod
    def get_permissions_patch() -> Dict[str, Any]:
        """
        Patch navigator.permissions to prevent detection.
        """
        return {
            "source": """
                const originalQuery = window.navigator.permissions.query;
                window.navigator.permissions.query = (parameters) => (
                    parameters.name === 'notifications' ?
                        Promise.resolve({state: Notification.permission}) :
                        originalQuery(parameters)
                );
            """
        }
    
    @staticmethod
    def get_plugins_patch() -> Dict[str, Any]:
        """
        Add fake plugins to prevent detection of headless mode.
        """
        return {
            "source": """
                Object.defineProperty(navigator, 'plugins', {
                    get: () => {
                        const ChromePDFPlugin = () => ({
                            description: 'Portable Document Format',
                            filename: 'internal-pdf-viewer',
                            name: 'Chrome PDF Plugin',
                            mimeTypes: [{
                                type: 'application/x-google-chrome-pdf',
                                suffixes: 'pdf',
                                description: 'Portable Document Format'
                            }]
                        });

                        const plugins = [ChromePDFPlugin()];
                        plugins.__proto__ = Array.prototype;
                        
                        plugins.item = idx => plugins[idx];
                        plugins.namedItem = name => plugins.find(p => p.name === name);
                        
                        return plugins;
                    }
                });
            """
        }
    
    @staticmethod
    def get_languages_patch() -> Dict[str, Any]:
        """
        Patch navigator.languages to return common values.
        """
        return {
            "source": """
                Object.defineProperty(navigator, 'languages', {
                    get: () => ['en-US', 'en']
                });
            """
        }
    
    @staticmethod
    def get_webgl_vendor_patch() -> Dict[str, Any]:
        """
        Patch WebGL to return common vendor and renderer strings.
        """
        return {
            "source": """
                const getParameter = WebGLRenderingContext.prototype.getParameter;
                WebGLRenderingContext.prototype.getParameter = function(parameter) {
                    if (parameter === 37445) {
                        return 'Intel Inc.';
                    }
                    if (parameter === 37446) {
                        return 'Intel Iris OpenGL Engine';
                    }
                    return getParameter.apply(this, arguments);
                };
            """
        }
    
    @staticmethod
    def get_user_agent_info_patch() -> Dict[str, Any]:
        """
        Patch userAgentData to return consistent values.
        """
        return {
            "source": """
                if (navigator.userAgentData) {
                    Object.defineProperty(navigator, 'userAgentData', {
                        get: () => ({
                            brands: [
                                { brand: 'Chrome', version: '121' },
                                { brand: 'Chromium', version: '121' }
                            ],
                            mobile: false,
                            platform: 'macOS'
                        })
                    });
                }
            """
        }

    @classmethod
    def get_all_patches(cls) -> Dict[str, Any]:
        """
        Get all stealth patches combined.
        """
        patches = [
            cls.get_webdriver_patch(),
            cls.get_chrome_runtime_patch(),
            cls.get_permissions_patch(),
            cls.get_plugins_patch(),
            cls.get_languages_patch(),
            cls.get_webgl_vendor_patch(),
            cls.get_user_agent_info_patch()
        ]
        
        # Combine all patches into a single script
        combined_source = "".join(patch["source"] for patch in patches)
        return {"source": combined_source}

class StealthConfig:
    """Configuration for Chrome launch flags to enhance stealth."""
    
    @staticmethod
    def get_stealth_flags() -> list[str]:
        """
        Get Chrome flags that help avoid detection.
        """
        return [
            '--disable-blink-features=AutomationControlled',
            '--disable-features=IsolateOrigins,site-per-process',
            '--disable-site-isolation-trials',
            '--disable-features=BlockInsecurePrivateNetworkRequests',
            '--disable-features=AudioServiceOutOfProcess',
            '--disable-features=AudioServiceSandbox',
            '--disable-features=IsolateOrigins',
            '--disable-features=site-per-process',
            '--disable-features=GlobalMediaControls',
            '--allow-running-insecure-content',
            '--disable-web-security',
            '--disable-client-side-phishing-detection',
            '--disable-component-extensions-with-background-pages',
            '--disable-default-apps',
            '--disable-domain-reliability',
            '--disable-features=AudioServiceOutOfProcess',
            '--disable-features=LazyFrameLoading',
            '--disable-features=DestroyProfileOnBrowserClose',
            '--disable-features=MediaRouter',
            '--disable-features=OptimizationHints',
            '--disable-features=Translate',
            '--disable-hang-monitor',
            '--disable-ipc-flooding-protection',
            '--disable-popup-blocking',
            '--disable-prompt-on-repost',
            '--disable-renderer-backgrounding',
            '--disable-sync',
            '--force-color-profile=srgb',
            '--metrics-recording-only',
            '--no-first-run',
            '--password-store=basic',
            '--use-mock-keychain',
            '--no-service-autorun',
            '--no-experiments',
            '--no-default-browser-check',
            '--no-pings',
        ] 
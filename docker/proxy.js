/**
 * Simple reverse proxy for Chrome DevTools Protocol
 * This allows connections from any IP address to the Chrome instance
 */

const httpProxy = require('http-proxy');
const http = require('http');
const url = require('url');
const { exec } = require('child_process');

// Chrome DevTools WebSocket URL (internal)
const chromeWsUrl = 'ws://127.0.0.1:9222';
const chromeHttpUrl = 'http://127.0.0.1:9222';

// External port to listen on
const proxyPort = 9223;

// Create a proxy server
const proxy = httpProxy.createServer({
  target: chromeHttpUrl,
  ws: true
});

// Handle proxy errors
proxy.on('error', function(err, req, res) {
  console.error('Proxy error:', err);
  if (res && res.writeHead) {
    res.writeHead(500, { 'Content-Type': 'text/plain' });
    res.end('Proxy error: ' + err);
  }
});

// Create an HTTP server to handle initial requests
const server = http.createServer((req, res) => {
  // For regular HTTP requests, proxy to Chrome
  console.log(`Proxying HTTP request: ${req.url}`);
  
  // Special handling for browserless API endpoints
  if (req.url.startsWith('/screenshot') || req.url.startsWith('/content') || req.url.startsWith('/function')) {
    // For browserless API endpoints, we need to handle them manually
    // by executing Chrome commands via CDP
    
    // For now, just return a 501 Not Implemented
    res.writeHead(501, { 'Content-Type': 'text/plain' });
    res.end('Browserless API endpoints are not yet implemented in the proxy. Please use the CDP protocol directly.');
    return;
  }
  
  // For all other requests, proxy to Chrome
  proxy.web(req, res, { target: chromeHttpUrl });
});

// Handle WebSocket connections
server.on('upgrade', (req, socket, head) => {
  const parsedUrl = url.parse(req.url);
  console.log(`Proxying WebSocket connection: ${req.url}`);
  
  // Rewrite the URL to point to the correct browser instance
  if (req.url.includes('/devtools/browser/')) {
    // Get the current browser ID
    exec('curl http://localhost:9222/json/version', (error, stdout, stderr) => {
      if (error) {
        console.error(`Error getting browser ID: ${error}`);
        socket.end();
        return;
      }
      
      try {
        const versionInfo = JSON.parse(stdout);
        const wsUrl = versionInfo.webSocketDebuggerUrl;
        const browserId = wsUrl.split('/').pop();
        
        // Rewrite the URL with the correct browser ID
        req.url = `/devtools/browser/${browserId}`;
        console.log(`Rewritten WebSocket URL: ${req.url}`);
        
        // Proxy the WebSocket connection
        proxy.ws(req, socket, head);
      } catch (e) {
        console.error(`Error parsing browser ID: ${e}`);
        socket.end();
      }
    });
  } else {
    // For all other WebSocket connections, proxy as-is
    proxy.ws(req, socket, head);
  }
});

// Start the server
server.listen(proxyPort, '0.0.0.0', () => {
  console.log(`Reverse proxy running at http://0.0.0.0:${proxyPort}`);
  console.log(`Forwarding to ${chromeWsUrl}`);
}); 
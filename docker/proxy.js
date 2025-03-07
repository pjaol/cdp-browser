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
  
  // For all requests, proxy to Chrome
  proxy.web(req, res, { target: chromeHttpUrl });
});

// Handle WebSocket connections
server.on('upgrade', (req, socket, head) => {
  const parsedUrl = url.parse(req.url);
  console.log(`Proxying WebSocket connection: ${req.url}`);
  
  // For all WebSocket connections, proxy as-is
  proxy.ws(req, socket, head);
});

// Start the server
server.listen(proxyPort, '0.0.0.0', () => {
  console.log(`Reverse proxy running at http://0.0.0.0:${proxyPort}`);
  console.log(`Forwarding to ${chromeWsUrl}`);
}); 
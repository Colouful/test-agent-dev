const http = require('http')
const fs = require('fs')
const path = require('path')

const DIST = path.join(__dirname, 'frontend', 'dist')
const PORT = 3000

const MIME = {
  '.html': 'text/html; charset=utf-8',
  '.js':   'application/javascript',
  '.css':  'text/css',
  '.json': 'application/json',
  '.png':  'image/png',
  '.jpg':  'image/jpeg',
  '.svg':  'image/svg+xml',
  '.ico':  'image/x-icon',
  '.woff2': 'font/woff2',
  '.woff': 'font/woff',
  '.ttf':  'font/ttf',
}

http.createServer((req, res) => {
  let filePath = path.join(DIST, req.url === '/' ? '/index.html' : req.url)
  // Strip query strings
  filePath = filePath.split('?')[0]

  if (!fs.existsSync(filePath) || fs.statSync(filePath).isDirectory()) {
    // SPA fallback — return index.html for all unknown paths
    filePath = path.join(DIST, 'index.html')
  }

  const ext = path.extname(filePath)
  const contentType = MIME[ext] || 'application/octet-stream'

  // Cache static assets
  const headers = { 'Content-Type': contentType }
  if (ext !== '.html') headers['Cache-Control'] = 'max-age=31536000, immutable'

  fs.readFile(filePath, (err, data) => {
    if (err) { res.writeHead(500); res.end('Error'); return }
    res.writeHead(200, headers)
    res.end(data)
  })
}).listen(PORT, '0.0.0.0', () => {
  console.log(`Frontend serving on port ${PORT} from ${DIST}`)
})

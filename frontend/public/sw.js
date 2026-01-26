/**
 * Service Worker for PyBase
 *
 * Provides offline support and background sync capabilities:
 * - Caches static assets (JS, CSS, images)
 * - Caches API responses with network-first strategy
 * - Provides offline fallback
 * - Supports background sync for queued requests
 */

const CACHE_NAME = 'pybase-v1'
const STATIC_CACHE = 'pybase-static-v1'
const API_CACHE = 'pybase-api-v1'

// Static assets to cache on install
const STATIC_ASSETS = [
  '/',
  '/index.html',
  '/vite.svg',
]

// API routes to cache
const API_PATTERNS = [
  /\/api\/v1\/records/,
  /\/api\/v1\/tables/,
  /\/api\/v1\/fields/,
]

/**
 * Install event - cache static assets
 */
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(STATIC_CACHE).then((cache) => {
      return cache.addAll(STATIC_ASSETS)
    })
  )
  // Force activation
  self.skipWaiting()
})

/**
 * Activate event - clean up old caches
 */
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames
          .filter((name) => name !== STATIC_CACHE && name !== API_CACHE)
          .map((name) => caches.delete(name))
      )
    })
  )
  // Take control immediately
  self.clients.claim()
})

/**
 * Fetch event - handle requests with cache strategies
 */
self.addEventListener('fetch', (event) => {
  const { request } = event
  const url = new URL(request.url)

  // Skip non-GET requests
  if (request.method !== 'GET') {
    return
  }

  // Skip chrome extensions and other protocols
  if (!url.protocol.startsWith('http')) {
    return
  }

  // API requests - network first with cache fallback
  if (url.pathname.startsWith('/api/')) {
    event.respondWith(handleApiRequest(request))
    return
  }

  // Static assets - cache first with network fallback
  event.respondWith(handleStaticRequest(request))
})

/**
 * Handle API requests with network-first strategy
 * @param {Request} request
 * @returns {Promise<Response>}
 */
async function handleApiRequest(request) {
  const url = new URL(request.url)

  // Check if this is a cacheable API request
  const isCacheable = API_PATTERNS.some((pattern) => pattern.test(url.pathname))

  if (!isCacheable) {
    // Non-cacheable API - go to network only
    return fetch(request).catch((error) => {
      // Return offline error response
      return new Response(
        JSON.stringify({
          error: 'Network error',
          message: 'Unable to connect to server. Please check your connection.',
        }),
        {
          status: 503,
          headers: { 'Content-Type': 'application/json' },
        }
      )
    })
  }

  // Network first for cacheable APIs
  try {
    const response = await fetch(request)

    // Cache successful GET responses
    if (response.ok && response.status === 200) {
      const clone = response.clone()
      caches.open(API_CACHE).then((cache) => cache.put(request, clone))
    }

    return response
  } catch (error) {
    // Network failed - try cache
    const cachedResponse = await caches.match(request)

    if (cachedResponse) {
      return cachedResponse
    }

    // Return offline error response
    return new Response(
      JSON.stringify({
        error: 'Offline',
        message: 'No cached data available. Please connect to the internet.',
        cached: false,
      }),
      {
        status: 503,
        headers: { 'Content-Type': 'application/json' },
      }
    )
  }
}

/**
 * Handle static asset requests with cache-first strategy
 * @param {Request} request
 * @returns {Promise<Response>}
 */
async function handleStaticRequest(request) {
  // Try cache first
  const cachedResponse = await caches.match(request)

  if (cachedResponse) {
    // Update cache in background
    fetch(request).then((response) => {
      if (response.ok) {
        caches.open(STATIC_CACHE).then((cache) => cache.put(request, response))
      }
    })

    return cachedResponse
  }

  // Not in cache - fetch from network
  try {
    const response = await fetch(request)

    // Cache successful responses
    if (response.ok) {
      const clone = response.clone()
      caches.open(STATIC_CACHE).then((cache) => cache.put(request, clone))
    }

    return response
  } catch (error) {
    // Network failed - return offline page
    return new Response(
      '<html><body><h1>Offline</h1><p>You are currently offline. Please check your connection.</p></body></html>',
      {
        status: 503,
        headers: { 'Content-Type': 'text/html' },
      }
    )
  }
}

/**
 * Background sync for queued requests
 * Handles POST/PUT/DELETE requests that failed while offline
 */
self.addEventListener('sync', (event) => {
  if (event.tag === 'background-sync') {
    event.waitUntil(syncQueuedRequests())
  }
})

/**
 * Sync queued requests
 * @returns {Promise<void>}
 */
async function syncQueuedRequests() {
  try {
    // Get all queued requests from IndexedDB
    const queuedRequests = await getQueuedRequests()

    for (const request of queuedRequests) {
      try {
        // Retry the request
        await fetch(request.url, {
          method: request.method,
          headers: request.headers,
          body: request.body,
        })

        // Remove successfully synced request
        await removeQueuedRequest(request.id)
      } catch (error) {
        // Keep request in queue for next sync
      }
    }
  } catch (error) {
    // IndexedDB error - queue might not exist
  }
}

/**
 * Get queued requests from IndexedDB
 * @returns {Promise<Array>}
 */
function getQueuedRequests() {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open('PyBaseOfflineQueue', 1)

    request.onerror = () => reject(request.error)
    request.onsuccess = () => {
      const db = request.result
      const tx = db.transaction('requests', 'readonly')
      const store = tx.objectStore('requests')
      const getAll = store.getAll()

      getAll.onsuccess = () => resolve(getAll.result)
      getAll.onerror = () => reject(getAll.error)
    }

    request.onupgradeneeded = () => {
      // Create object store if it doesn't exist
      const db = request.result
      if (!db.objectStoreNames.contains('requests')) {
        db.createObjectStore('requests', { keyPath: 'id' })
      }
    }
  })
}

/**
 * Remove a queued request from IndexedDB
 * @param {string} id
 * @returns {Promise<void>}
 */
function removeQueuedRequest(id) {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open('PyBaseOfflineQueue', 1)

    request.onerror = () => reject(request.error)
    request.onsuccess = () => {
      const db = request.result
      const tx = db.transaction('requests', 'readwrite')
      const store = tx.objectStore('requests')
      const deleteReq = store.delete(id)

      deleteReq.onsuccess = () => resolve()
      deleteReq.onerror = () => reject(deleteReq.error)
    }
  })
}

/**
 * Message event - handle messages from client
 */
self.addEventListener('message', (event) => {
  const { data } = event

  if (data.type === 'SKIP_WAITING') {
    self.skipWaiting()
  }

  if (data.type === 'CACHE_CLEAR') {
    event.waitUntil(
      caches.keys().then((cacheNames) => {
        return Promise.all(
          cacheNames.map((name) => caches.delete(name))
        )
      })
    )
  }

  if (data.type === 'CACHE_API_RESPONSE') {
    event.waitUntil(
      caches.open(API_CACHE).then((cache) => {
        return cache.put(data.request, data.response)
      })
    )
  }
})

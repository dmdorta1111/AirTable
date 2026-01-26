/**
 * Service Worker registration utilities for PyBase
 *
 * Handles service worker registration, updates, and communication
 * for offline support and background sync capabilities.
 */

import { useState, useEffect, useCallback } from "react"

export type ServiceWorkerStatus =
  | "unsupported"
  | "registering"
  | "registered"
  | "updated"
  | "error"

export interface ServiceWorkerConfig {
  /** Service worker script path (default: /sw.js) */
  swPath?: string
  /** Called when service worker is successfully registered */
  onSuccess?: (registration: ServiceWorkerRegistration) => void
  /** Called when service worker update is found */
  onUpdate?: (registration: ServiceWorkerRegistration) => void
  /** Called on registration error */
  onError?: (error: Error) => void
}

/**
 * Check if service workers are supported in current browser
 * @returns true if service workers are supported
 */
export function isServiceWorkerSupported(): boolean {
  return (
    typeof navigator !== "undefined" &&
    "serviceWorker" in navigator &&
    typeof window !== "undefined" &&
    "caches" in window
  )
}

/**
 * Register the service worker
 * @param config - Registration configuration options
 * @returns Promise<ServiceWorkerRegistration | null>
 *
 * @example
 * ```ts
 * // Basic registration
 * const registration = await registerServiceWorker()
 *
 * // With event handlers
 * const registration = await registerServiceWorker({
 *   swPath: '/sw.js',
 *   onSuccess: (reg) => console.log('Registered!', reg),
 *   onUpdate: (reg) => {
 *     if (confirm('New version available. Update now?')) {
 *       reg.waiting?.postMessage({ type: 'SKIP_WAITING' })
 *     }
 *   },
 *   onError: (error) => console.error('SW error:', error)
 * })
 * ```
 */
export async function registerServiceWorker(
  config: ServiceWorkerConfig = {}
): Promise<ServiceWorkerRegistration | null> {
  if (!isServiceWorkerSupported()) {
    if (config.onError) {
      config.onError(
        new Error("Service workers are not supported in this browser")
      )
    }
    return null
  }

  const { swPath = "/sw.js", onSuccess, onUpdate, onError } = config

  try {
    const registration = await navigator.serviceWorker.register(swPath, {
      updateViaCache: "none",
    })

    if (onSuccess) {
      onSuccess(registration)
    }

    // Check for updates
    registration.addEventListener("updatefound", () => {
      const newWorker = registration.installing

      if (!newWorker) {
        return
      }

      newWorker.addEventListener("statechange", () => {
        if (newWorker.state === "installed" && navigator.serviceWorker.controller) {
          // New version available
          if (onUpdate) {
            onUpdate(registration)
          }
        }
      })
    })

    return registration
  } catch (error) {
    const swError =
      error instanceof Error ? error : new Error(String(error))
    if (onError) {
      onError(swError)
    }
    return null
  }
}

/**
 * Unregister the service worker
 * @returns Promise<boolean> true if unregistration was successful
 */
export async function unregisterServiceWorker(): Promise<boolean> {
  if (!isServiceWorkerSupported()) {
    return false
  }

  try {
    const registration = await navigator.serviceWorker.getRegistration()

    if (!registration) {
      return true
    }

    const result = await registration.unregister()
    return result
  } catch (error) {
    return false
  }
}

/**
 * Get current service worker registration
 * @returns Promise<ServiceWorkerRegistration | null>
 */
export async function getServiceWorkerRegistration(): Promise<ServiceWorkerRegistration | null> {
  if (!isServiceWorkerSupported()) {
    return null
  }

  try {
    const registration = await navigator.serviceWorker.getRegistration()
    return registration || null
  } catch (error) {
    return null
  }
}

/**
 * Get service worker status
 * @returns Promise<ServiceWorkerStatus>
 */
export async function getServiceWorkerStatus(): Promise<ServiceWorkerStatus> {
  if (!isServiceWorkerSupported()) {
    return "unsupported"
  }

  try {
    const registration = await navigator.serviceWorker.getRegistration()

    if (!registration) {
      return "registering"
    }

    if (registration.waiting) {
      return "updated"
    }

    if (navigator.serviceWorker.controller) {
      return "registered"
    }

    return "registering"
  } catch (error) {
    return "error"
  }
}

/**
 * Skip waiting for service worker update and activate immediately
 * @param registration - Service worker registration
 */
export function skipWaiting(registration: ServiceWorkerRegistration): void {
  if (registration.waiting) {
    registration.waiting.postMessage({ type: "SKIP_WAITING" })
  }
}

/**
 * Clear all service worker caches
 * @returns Promise<void>
 */
export async function clearServiceWorkerCaches(): Promise<void> {
  if (!isServiceWorkerSupported()) {
    return
  }

  try {
    const cacheNames = await caches.keys()
    await Promise.all(cacheNames.map((name) => caches.delete(name)))
  } catch (error) {
    // Cache clearing failed
  }
}

/**
 * Cache an API response manually
 * @param request - Request object or URL string
 * @param response - Response to cache
 */
export async function cacheApiResponse(
  request: RequestInfo | URL,
  response: Response
): Promise<void> {
  if (!isServiceWorkerSupported()) {
    return
  }

  try {
    const registration = await getServiceWorkerRegistration()

    if (registration?.active) {
      registration.active.postMessage({
        type: "CACHE_API_RESPONSE",
        request,
        response,
      })
    }
  } catch (error) {
    // Failed to send message to service worker
  }
}

/**
 * Check if app is currently offline
 * @returns true if offline
 */
export function isOffline(): boolean {
  return (
    typeof navigator !== "undefined" &&
    (navigator.onLine === false || !navigator.onLine)
  )
}

/**
 * Listen for online/offline events
 * @param onOnline - Callback when app goes online
 * @param onOffline - Callback when app goes offline
 * @returns Cleanup function
 */
export function listenNetworkStatus(
  onOnline?: () => void,
  onOffline?: () => void
): () => void {
  if (typeof window === "undefined") {
    return () => {}
  }

  const handleOnline = () => onOnline?.()
  const handleOffline = () => onOffline?.()

  window.addEventListener("online", handleOnline)
  window.addEventListener("offline", handleOffline)

  return () => {
    window.removeEventListener("online", handleOnline)
    window.removeEventListener("offline", handleOffline)
  }
}

/**
 * Queue a request for background sync
 * @param url - Request URL
 * @param options - Fetch options
 * @returns Promise<void>
 */
export async function queueRequestForSync(
  url: string,
  options: RequestInit = {}
): Promise<void> {
  if (!isServiceWorkerSupported()) {
    throw new Error("Service workers not supported")
  }

  const id = `request-${Date.now()}-${Math.random()}`

  return new Promise((resolve, reject) => {
    const request = indexedDB.open("PyBaseOfflineQueue", 1)

    request.onerror = () => reject(request.error)
    request.onsuccess = () => {
      const db = request.result
      const tx = db.transaction("requests", "readwrite")
      const store = tx.objectStore("requests")

      store.put({
        id,
        url,
        method: options.method || "GET",
        headers: options.headers || {},
        body: options.body,
        timestamp: Date.now(),
      })

      tx.oncomplete = () => {
        // Register sync event
        if (navigator.serviceWorker.controller) {
          navigator.serviceWorker.controller.postMessage({
            type: "SYNC_REQUEST",
          })
        }
        resolve()
      }

      tx.onerror = () => reject(tx.error)
    }

    request.onupgradeneeded = () => {
      const db = request.result
      if (!db.objectStoreNames.contains("requests")) {
        db.createObjectStore("requests", { keyPath: "id" })
      }
    }
  })
}

/**
 * React hook for service worker registration
 * @param config - Registration configuration
 * @returns Object with status and registration
 *
 * @example
 * ```tsx
 * function App() {
 *   const { status, registration, refresh } = useServiceWorker({
 *     onUpdate: (reg) => {
 *       setShowUpdateBanner(true)
 *       setRegistration(reg)
 *     }
 *   })
 *
 *   return (
 *     <div>
 *       {status === 'updated' && <UpdateBanner />}
 *     </div>
 *   )
 * }
 * ```
 */
export function useServiceWorker(
  config: ServiceWorkerConfig = {}
): {
  status: ServiceWorkerStatus
  registration: ServiceWorkerRegistration | null
  refresh: () => Promise<void>
} {
  const [status, setStatus] = useState<ServiceWorkerStatus>(() =>
    isServiceWorkerSupported() ? "registering" : "unsupported"
  )
  const [registration, setRegistration] = useState<ServiceWorkerRegistration | null>(null)

  const { swPath = "/sw.js", onSuccess, onUpdate, onError } = config

  useEffect(() => {
    if (!isServiceWorkerSupported()) {
      setStatus("unsupported")
      return
    }

    let mounted = true

    const register = async () => {
      try {
        const reg = await navigator.serviceWorker.register(swPath, {
          updateViaCache: "none",
        })

        if (!mounted) return

        setRegistration(reg)
        setStatus("registered")

        if (onSuccess) {
          onSuccess(reg)
        }

        // Listen for updates
        reg.addEventListener("updatefound", () => {
          const newWorker = reg.installing

          if (!newWorker) return

          newWorker.addEventListener("statechange", () => {
            if (newWorker.state === "installed" && navigator.serviceWorker.controller) {
              if (mounted) {
                setStatus("updated")
              }
              if (onUpdate) {
                onUpdate(reg)
              }
            }
          })
        })

        // Handle controller change (when skipWaiting is called)
        navigator.serviceWorker.addEventListener("controllerchange", () => {
          if (mounted) {
            // Optionally reload the page when the new service worker takes control
            // window.location.reload()
          }
        })
      } catch (error) {
        if (!mounted) return

        setStatus("error")
        const swError = error instanceof Error ? error : new Error(String(error))
        if (onError) {
          onError(swError)
        }
      }
    }

    register()

    return () => {
      mounted = false
    }
  }, [swPath, onSuccess, onUpdate, onError])

  const refresh = useCallback(async () => {
    if (!registration) return

    try {
      await registration.update()
    } catch (error) {
      // Update check failed
    }
  }, [registration])

  return { status, registration, refresh }
}

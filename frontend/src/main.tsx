import { StrictMode } from "react"
import { createRoot } from "react-dom/client"
import { QueryClientProvider } from "@tanstack/react-query"
import { RouterProvider } from "react-router-dom"
import { queryClient } from "@/lib/queryClient"
import { router } from "@/lib/router"
import { registerServiceWorker } from "@/utils/serviceWorkerRegistration"
import "./index.css"

// Register service worker for offline support
registerServiceWorker({
  swPath: "/sw.js",
  onSuccess: (registration) => {
    console.log("Service Worker registered successfully:", registration)
  },
  onUpdate: (registration) => {
    console.log("Service Worker update available:", registration)
    // Prompt user to refresh for new version
    if (window.confirm("A new version is available. Refresh to update?")) {
      registration.waiting?.postMessage({ type: "SKIP_WAITING" })
      window.location.reload()
    }
  },
  onError: (error) => {
    console.error("Service Worker registration failed:", error)
  },
})

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
    </QueryClientProvider>
  </StrictMode>,
)

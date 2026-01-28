import { useEffect, useState } from "react"
import { useNavigate, useSearchParams } from "react-router-dom"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { handleSAMLCallback, handleOIDCCallback } from "../api/ssoApi"
import { useAuthStore } from "../stores/authStore"

export default function SSOCallback() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const setAuth = useAuthStore((state) => state.setAuth)
  const [status, setStatus] = useState<"loading" | "success" | "error">("loading")
  const [error, setError] = useState("")

  useEffect(() => {
    const handleCallback = async () => {
      try {
        // Check if this is a SAML callback
        const samlResponse = searchParams.get("SAMLResponse")
        const relayState = searchParams.get("RelayState")

        if (samlResponse) {
          // SAML callback
          const response = await handleSAMLCallback({
            SAMLResponse: samlResponse,
            RelayState: relayState || undefined,
          })
          setAuth(response.user, response.access_token)
          setStatus("success")
          setTimeout(() => navigate("/dashboard", { replace: true }), 500)
          return
        }

        // Check if this is an OIDC callback
        const code = searchParams.get("code")
        const state = searchParams.get("state")
        const provider = searchParams.get("provider")

        if (code && state) {
          // OIDC callback
          const response = await handleOIDCCallback({
            code,
            state,
            provider: provider || undefined,
          })
          setAuth(response.user, response.access_token)
          setStatus("success")
          setTimeout(() => navigate("/dashboard", { replace: true }), 500)
          return
        }

        // No valid callback parameters
        setError("Invalid callback parameters")
        setStatus("error")
      } catch (err: any) {
        setError(err.response?.data?.detail || err.message || "Authentication failed")
        setStatus("error")
      }
    }

    handleCallback()
  }, [searchParams, setAuth, navigate])

  return (
    <div className="flex min-h-screen items-center justify-center bg-background">
      <Card className="w-full max-w-md">
        <CardHeader>
          <CardTitle>SSO Authentication</CardTitle>
          <CardDescription>
            {status === "loading" && "Processing your authentication..."}
            {status === "success" && "Authentication successful!"}
            {status === "error" && "Authentication failed"}
          </CardDescription>
        </CardHeader>
        <CardContent>
          {status === "loading" && (
            <div className="flex items-center justify-center">
              <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent"></div>
            </div>
          )}
          {status === "success" && (
            <div className="text-center text-sm text-muted-foreground">
              Redirecting you to the dashboard...
            </div>
          )}
          {status === "error" && (
            <div className="space-y-4">
              <div className="text-sm text-destructive">{error}</div>
              <button
                onClick={() => navigate("/login", { replace: true })}
                className="w-full rounded-md bg-primary px-4 py-2 text-sm text-primary-foreground hover:bg-primary/90"
              >
                Return to Login
              </button>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}

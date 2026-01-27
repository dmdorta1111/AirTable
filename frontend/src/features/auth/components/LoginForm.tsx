import { useState, useEffect } from "react"
import { useNavigate } from "react-router-dom"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Separator } from "@/components/ui/separator"
import { login } from "../api/authApi"
import { useAuthStore } from "../stores/authStore"
import {
  initiateSAMLLogin,
  initiateOIDCLogin,
  getAvailableProviders,
} from "../api/ssoApi"

interface SSOProvider {
  type: "saml" | "oidc"
  provider: string
  name: string
}

export default function LoginForm() {
  const navigate = useNavigate()
  const setAuth = useAuthStore((state) => state.setAuth)
  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState("")
  const [ssoProviders, setSSOProviders] = useState<SSOProvider[]>([])
  const [ssoLoading, setSSOLoading] = useState(false)
  const [showSSO, setShowSSO] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError("")
    setLoading(true)

    try {
      const response = await login({ email, password })
      setAuth(response.user, response.access_token)
      navigate("/dashboard")
    } catch (err: any) {
      setError(err.response?.data?.detail || "Login failed")
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    const fetchProviders = async () => {
      try {
        const providers = await getAvailableProviders()
        setSSOProviders(providers)
        setShowSSO(providers.length > 0)
      } catch {
        setShowSSO(false)
      }
    }
    fetchProviders()
  }, [])

  const handleSSOLogin = async (provider: SSOProvider) => {
    setSSOLoading(true)
    setError("")

    try {
      let loginUrl: string
      if (provider.type === "saml") {
        const response = await initiateSAMLLogin()
        loginUrl = response.login_url
      } else {
        const response = await initiateOIDCLogin(provider.provider)
        loginUrl = response.login_url
      }
      window.location.href = loginUrl
    } catch (err: any) {
      setError(err.response?.data?.detail || "SSO login failed")
      setSSOLoading(false)
    }
  }

  return (
    <Card className="w-full max-w-md">
      <CardHeader>
        <CardTitle>Login to PyBase</CardTitle>
        <CardDescription>Enter your credentials to access your workspace</CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="email">Email</Label>
            <Input
              id="email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              disabled={loading}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="password">Password</Label>
            <Input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              disabled={loading}
            />
          </div>
          {error && <div className="text-sm text-destructive">{error}</div>}
          <Button type="submit" className="w-full" disabled={loading || ssoLoading}>
            {loading ? "Logging in..." : "Login"}
          </Button>
        </form>

        {showSSO && ssoProviders.length > 0 && (
          <div className="mt-6">
            <div className="relative">
              <div className="absolute inset-0 flex items-center">
                <Separator />
              </div>
              <div className="relative flex justify-center text-xs uppercase">
                <span className="bg-background px-2 text-muted-foreground">Or continue with</span>
              </div>
            </div>
            <div className="mt-4 space-y-2">
              {ssoProviders.map((provider) => (
                <Button
                  key={`${provider.type}-${provider.provider}`}
                  type="button"
                  variant="outline"
                  className="w-full"
                  disabled={ssoLoading || loading}
                  onClick={() => handleSSOLogin(provider)}
                >
                  {ssoLoading ? "Connecting..." : `Sign in with ${provider.name}`}
                </Button>
              ))}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
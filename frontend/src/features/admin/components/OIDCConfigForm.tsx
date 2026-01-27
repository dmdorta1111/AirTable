import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Checkbox } from "@/components/ui/checkbox"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Separator } from "@/components/ui/separator"
import { updateOIDCConfig, type OIDCConfig } from "@/features/auth/api/ssoApi"

interface OIDCConfigFormProps {
  initialConfig: OIDCConfig
  onSave?: (config: OIDCConfig) => void
  onError?: (error: string) => void
}

export default function OIDCConfigForm({
  initialConfig,
  onSave,
  onError,
}: OIDCConfigFormProps) {
  const [config, setConfig] = useState<OIDCConfig>(initialConfig)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState("")
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({})

  const validateField = (name: string, value: any): string | null => {
    switch (name) {
      case "provider":
        if (!value || value.trim() === "") {
          return "Provider name is required"
        }
        if (!/^[a-z0-9_-]+$/i.test(value)) {
          return "Provider name must contain only letters, numbers, hyphens, and underscores"
        }
        break
      case "client_id":
        if (!value || value.trim() === "") {
          return "Client ID is required"
        }
        break
      case "client_secret":
        if (!value || value.trim() === "") {
          return "Client Secret is required"
        }
        break
      case "authorization_endpoint":
        if (!value || value.trim() === "") {
          return "Authorization Endpoint is required"
        }
        try {
          new URL(value)
        } catch {
          return "Must be a valid URL"
        }
        break
      case "token_endpoint":
        if (!value || value.trim() === "") {
          return "Token Endpoint is required"
        }
        try {
          new URL(value)
        } catch {
          return "Must be a valid URL"
        }
        break
      case "userinfo_endpoint":
        if (!value || value.trim() === "") {
          return "UserInfo Endpoint is required"
        }
        try {
          new URL(value)
        } catch {
          return "Must be a valid URL"
        }
        break
      case "jwks_uri":
        if (!value || value.trim() === "") {
          return "JWKS URI is required"
        }
        try {
          new URL(value)
        } catch {
          return "Must be a valid URL"
        }
        break
      case "scope":
        if (value && value.trim() !== "") {
          const scopes = value.split(" ").filter((s: string) => s.trim() !== "")
          if (scopes.length === 0) {
            return "Scope must contain at least one value"
          }
        }
        break
    }
    return null
  }

  const validateForm = (): boolean => {
    const errors: Record<string, string> = {}

    const providerError = validateField("provider", config.provider)
    if (providerError) errors.provider = providerError

    const clientIdError = validateField("client_id", config.client_id)
    if (clientIdError) errors.client_id = clientIdError

    const clientSecretError = validateField("client_secret", config.client_secret)
    if (clientSecretError) errors.client_secret = clientSecretError

    const authEndpointError = validateField(
      "authorization_endpoint",
      config.authorization_endpoint
    )
    if (authEndpointError) errors.authorization_endpoint = authEndpointError

    const tokenEndpointError = validateField("token_endpoint", config.token_endpoint)
    if (tokenEndpointError) errors.token_endpoint = tokenEndpointError

    const userInfoEndpointError = validateField(
      "userinfo_endpoint",
      config.userinfo_endpoint
    )
    if (userInfoEndpointError) errors.userinfo_endpoint = userInfoEndpointError

    const jwksUriError = validateField("jwks_uri", config.jwks_uri)
    if (jwksUriError) errors.jwks_uri = jwksUriError

    const scopeError = validateField("scope", config.scope || "")
    if (scopeError) errors.scope = scopeError

    setFieldErrors(errors)
    return Object.keys(errors).length === 0
  }

  const handleFieldChange = (name: keyof OIDCConfig, value: any) => {
    setConfig((prev) => ({ ...prev, [name]: value }))

    // Clear field error when user starts typing
    if (fieldErrors[name]) {
      setFieldErrors((prev) => {
        const newErrors = { ...prev }
        delete newErrors[name]
        return newErrors
      })
    }

    // Clear general error
    if (error) {
      setError("")
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError("")

    if (!validateForm()) {
      setError("Please fix the validation errors below")
      return
    }

    setSaving(true)

    try {
      const savedConfig = await updateOIDCConfig(config.provider, config)
      setConfig(savedConfig)
      onSave?.(savedConfig)
    } catch (err: any) {
      const errorMessage = err.response?.data?.detail || "Failed to save OIDC configuration"
      setError(errorMessage)
      onError?.(errorMessage)
    } finally {
      setSaving(false)
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>OIDC Configuration</CardTitle>
        <CardDescription>
          Configure OpenID Connect authentication for your Identity Provider
        </CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="space-y-6">
          {/* Enable OIDC */}
          <div className="flex items-center space-x-2">
            <Checkbox
              id="oidc-enabled"
              checked={config.enabled}
              onCheckedChange={(checked) => handleFieldChange("enabled", checked)}
            />
            <Label htmlFor="oidc-enabled">Enable OIDC authentication</Label>
          </div>

          <Separator />

          {/* Provider Settings */}
          <div className="space-y-4">
            <h3 className="text-sm font-medium">Provider Settings</h3>

            <div className="space-y-2">
              <Label htmlFor="provider">
                Provider Name
                <span className="text-destructive ml-1">*</span>
              </Label>
              <Input
                id="provider"
                value={config.provider}
                onChange={(e) => handleFieldChange("provider", e.target.value)}
                placeholder="google, azure, okta, auth0, etc."
                disabled={saving}
                className={fieldErrors.provider ? "border-destructive" : ""}
              />
              {fieldErrors.provider && (
                <p className="text-sm text-destructive">{fieldErrors.provider}</p>
              )}
              <p className="text-sm text-muted-foreground">
                A unique identifier for this provider (lowercase letters, numbers, hyphens, and
                underscores only)
              </p>
            </div>

            <div className="space-y-2">
              <Label htmlFor="client_id">
                Client ID
                <span className="text-destructive ml-1">*</span>
              </Label>
              <Input
                id="client_id"
                value={config.client_id}
                onChange={(e) => handleFieldChange("client_id", e.target.value)}
                placeholder="your-client-id"
                disabled={saving}
                className={fieldErrors.client_id ? "border-destructive" : ""}
              />
              {fieldErrors.client_id && (
                <p className="text-sm text-destructive">{fieldErrors.client_id}</p>
              )}
            </div>

            <div className="space-y-2">
              <Label htmlFor="client_secret">
                Client Secret
                <span className="text-destructive ml-1">*</span>
              </Label>
              <Input
                id="client_secret"
                type="password"
                value={config.client_secret}
                onChange={(e) => handleFieldChange("client_secret", e.target.value)}
                placeholder="your-client-secret"
                disabled={saving}
                className={fieldErrors.client_secret ? "border-destructive" : ""}
              />
              {fieldErrors.client_secret && (
                <p className="text-sm text-destructive">{fieldErrors.client_secret}</p>
              )}
              <p className="text-sm text-muted-foreground">
                Keep this secret. Store it securely in your IdP configuration
              </p>
            </div>
          </div>

          <Separator />

          {/* Endpoint Settings */}
          <div className="space-y-4">
            <h3 className="text-sm font-medium">Endpoint URLs</h3>

            <div className="space-y-2">
              <Label htmlFor="authorization_endpoint">
                Authorization Endpoint
                <span className="text-destructive ml-1">*</span>
              </Label>
              <Input
                id="authorization_endpoint"
                value={config.authorization_endpoint}
                onChange={(e) => handleFieldChange("authorization_endpoint", e.target.value)}
                placeholder="https://provider.com/oauth2/authorize"
                disabled={saving}
                className={fieldErrors.authorization_endpoint ? "border-destructive" : ""}
              />
              {fieldErrors.authorization_endpoint && (
                <p className="text-sm text-destructive">{fieldErrors.authorization_endpoint}</p>
              )}
            </div>

            <div className="space-y-2">
              <Label htmlFor="token_endpoint">
                Token Endpoint
                <span className="text-destructive ml-1">*</span>
              </Label>
              <Input
                id="token_endpoint"
                value={config.token_endpoint}
                onChange={(e) => handleFieldChange("token_endpoint", e.target.value)}
                placeholder="https://provider.com/oauth2/token"
                disabled={saving}
                className={fieldErrors.token_endpoint ? "border-destructive" : ""}
              />
              {fieldErrors.token_endpoint && (
                <p className="text-sm text-destructive">{fieldErrors.token_endpoint}</p>
              )}
            </div>

            <div className="space-y-2">
              <Label htmlFor="userinfo_endpoint">
                UserInfo Endpoint
                <span className="text-destructive ml-1">*</span>
              </Label>
              <Input
                id="userinfo_endpoint"
                value={config.userinfo_endpoint}
                onChange={(e) => handleFieldChange("userinfo_endpoint", e.target.value)}
                placeholder="https://provider.com/oauth2/userinfo"
                disabled={saving}
                className={fieldErrors.userinfo_endpoint ? "border-destructive" : ""}
              />
              {fieldErrors.userinfo_endpoint && (
                <p className="text-sm text-destructive">{fieldErrors.userinfo_endpoint}</p>
              )}
            </div>

            <div className="space-y-2">
              <Label htmlFor="jwks_uri">
                JWKS URI
                <span className="text-destructive ml-1">*</span>
              </Label>
              <Input
                id="jwks_uri"
                value={config.jwks_uri}
                onChange={(e) => handleFieldChange("jwks_uri", e.target.value)}
                placeholder="https://provider.com/.well-known/jwks.json"
                disabled={saving}
                className={fieldErrors.jwks_uri ? "border-destructive" : ""}
              />
              {fieldErrors.jwks_uri && (
                <p className="text-sm text-destructive">{fieldErrors.jwks_uri}</p>
              )}
            </div>

            <div className="space-y-2">
              <Label htmlFor="scope">Scope (Optional)</Label>
              <Input
                id="scope"
                value={config.scope || ""}
                onChange={(e) => handleFieldChange("scope", e.target.value)}
                placeholder="openid email profile"
                disabled={saving}
                className={fieldErrors.scope ? "border-destructive" : ""}
              />
              {fieldErrors.scope && <p className="text-sm text-destructive">{fieldErrors.scope}</p>}
              <p className="text-sm text-muted-foreground">
                Space-separated list of OAuth scopes. Default: "openid email profile"
              </p>
            </div>
          </div>

          <Separator />

          {/* Provisioning Settings */}
          <div className="space-y-4">
            <h3 className="text-sm font-medium">Provisioning Settings</h3>

            <div className="flex items-center space-x-2">
              <Checkbox
                id="oidc-jit"
                checked={config.jit_provisioning_enabled || false}
                onCheckedChange={(checked) =>
                  handleFieldChange("jit_provisioning_enabled", checked)
                }
                disabled={saving}
              />
              <div className="space-y-1">
                <Label htmlFor="oidc-jit">Enable JIT provisioning</Label>
                <p className="text-sm text-muted-foreground">
                  Automatically create user accounts on first SSO login
                </p>
              </div>
            </div>
          </div>

          {/* General Error */}
          {error && <div className="text-sm text-destructive">{error}</div>}

          {/* Submit Button */}
          <div className="flex justify-end">
            <Button type="submit" disabled={saving}>
              {saving ? "Saving..." : "Save OIDC Configuration"}
            </Button>
          </div>
        </form>
      </CardContent>
    </Card>
  )
}

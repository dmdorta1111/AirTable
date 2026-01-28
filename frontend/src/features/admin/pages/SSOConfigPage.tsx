import { useState, useEffect } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Checkbox } from "@/components/ui/checkbox"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Separator } from "@/components/ui/separator"
import {
  getSSOConfig,
  updateOIDCConfig,
  deleteOIDCConfig,
  updateSSOSettings,
  type SAMLConfig,
  type OIDCConfig,
} from "@/features/auth/api/ssoApi"
import SAMLConfigForm from "../components/SAMLConfigForm"

interface OIDCProviderConfig {
  provider: string
  config: OIDCConfig
}

export default function SSOConfigPage() {
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState("")
  const [success, setSuccess] = useState("")
  const [activeTab, setActiveTab] = useState<"saml" | "oidc" | "settings">("saml")

  // SAML state
  const [samlConfig, setSAMLConfig] = useState<SAMLConfig>({
    enabled: false,
    idp_entity_id: "",
    idp_sso_url: "",
    idp_x509_cert: "",
    sp_entity_id: "",
    assertion_consumer_service_url: "",
    name_id_format: "urn:oasis:names:tc:SAML:1.1:nameid-format:unspecified",
    attribute_mapping: {},
    role_mapping: {},
    jit_provisioning_enabled: false,
  })
  const [samlKey, setSamlKey] = useState(0)

  // OIDC state
  const [oidcProviders, setOidcProviders] = useState<OIDCProviderConfig[]>([])
  const [newOidcProvider, setNewOidcProvider] = useState<OIDCConfig>({
    enabled: false,
    provider: "",
    client_id: "",
    client_secret: "",
    authorization_endpoint: "",
    token_endpoint: "",
    userinfo_endpoint: "",
    jwks_uri: "",
    scope: "openid email profile",
    attribute_mapping: {},
    role_mapping: {},
    jit_provisioning_enabled: false,
  })

  // Settings state
  const [ssoOnlyMode, setSsoOnlyMode] = useState(false)
  const [adminRecoveryUser, setAdminRecoveryUser] = useState("")

  useEffect(() => {
    loadConfig()
  }, [])

  const loadConfig = async () => {
    try {
      setLoading(true)
      const config = await getSSOConfig()

      // Load SAML config
      if (config.saml) {
        setSAMLConfig(config.saml)
      }

      // Load OIDC configs
      if (config.oidc) {
        const providers = Object.entries(config.oidc).map(([provider, cfg]) => ({
          provider,
          config: cfg,
        }))
        setOidcProviders(providers)
      }

      // Load settings
      setSsoOnlyMode(config.sso_only_mode)
      setAdminRecoveryUser(config.admin_recovery_user || "")
    } catch (err: any) {
      setError(err.response?.data?.detail || "Failed to load SSO configuration")
    } finally {
      setLoading(false)
    }
  }

  const handleSAMLConfigSaved = (config: SAMLConfig) => {
    setSAMLConfig(config)
    setSuccess("SAML configuration saved successfully")
    setTimeout(() => setSuccess(""), 3000)
    setSamlKey((prev) => prev + 1)
  }

  const handleSAMLError = (error: string) => {
    setError(error)
  }

  const handleAddOIDCProvider = async () => {
    if (!newOidcProvider.provider) {
      setError("Provider name is required")
      return
    }

    setSaving(true)
    setError("")
    setSuccess("")

    try {
      await updateOIDCConfig(newOidcProvider.provider, newOidcProvider)
      setSuccess("OIDC provider added successfully")
      setNewOidcProvider({
        enabled: false,
        provider: "",
        client_id: "",
        client_secret: "",
        authorization_endpoint: "",
        token_endpoint: "",
        userinfo_endpoint: "",
        jwks_uri: "",
        scope: "openid email profile",
        attribute_mapping: {},
        role_mapping: {},
        jit_provisioning_enabled: false,
      })
      await loadConfig()
      setTimeout(() => setSuccess(""), 3000)
    } catch (err: any) {
      setError(err.response?.data?.detail || "Failed to add OIDC provider")
    } finally {
      setSaving(false)
    }
  }

  const handleDeleteOIDCProvider = async (provider: string) => {
    if (!confirm(`Are you sure you want to delete the ${provider} OIDC provider?`)) {
      return
    }

    setSaving(true)
    setError("")
    setSuccess("")

    try {
      await deleteOIDCConfig(provider)
      setSuccess("OIDC provider deleted successfully")
      await loadConfig()
      setTimeout(() => setSuccess(""), 3000)
    } catch (err: any) {
      setError(err.response?.data?.detail || "Failed to delete OIDC provider")
    } finally {
      setSaving(false)
    }
  }

  const handleSaveSettings = async () => {
    setSaving(true)
    setError("")
    setSuccess("")

    try {
      await updateSSOSettings({
        sso_only_mode: ssoOnlyMode,
        admin_recovery_user: adminRecoveryUser || undefined,
      })
      setSuccess("Settings saved successfully")
      setTimeout(() => setSuccess(""), 3000)
    } catch (err: any) {
      setError(err.response?.data?.detail || "Failed to save settings")
    } finally {
      setSaving(false)
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="text-muted-foreground">Loading SSO configuration...</div>
      </div>
    )
  }

  return (
    <div className="container max-w-6xl mx-auto py-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold">SSO Configuration</h1>
        <p className="text-muted-foreground mt-2">
          Configure Single Sign-On authentication using SAML or OIDC
        </p>
      </div>

      {error && (
        <div className="mb-4 p-4 text-sm text-destructive bg-destructive/10 rounded-md">
          {error}
        </div>
      )}

      {success && (
        <div className="mb-4 p-4 text-sm text-green-700 bg-green-50 dark:bg-green-900/20 rounded-md">
          {success}
        </div>
      )}

      {/* Tabs */}
      <div className="flex space-x-1 border-b mb-6">
        <button
          onClick={() => setActiveTab("saml")}
          className={`px-4 py-2 text-sm font-medium transition-colors ${
            activeTab === "saml"
              ? "border-b-2 border-primary text-foreground"
              : "text-muted-foreground hover:text-foreground"
          }`}
        >
          SAML
        </button>
        <button
          onClick={() => setActiveTab("oidc")}
          className={`px-4 py-2 text-sm font-medium transition-colors ${
            activeTab === "oidc"
              ? "border-b-2 border-primary text-foreground"
              : "text-muted-foreground hover:text-foreground"
          }`}
        >
          OIDC
        </button>
        <button
          onClick={() => setActiveTab("settings")}
          className={`px-4 py-2 text-sm font-medium transition-colors ${
            activeTab === "settings"
              ? "border-b-2 border-primary text-foreground"
              : "text-muted-foreground hover:text-foreground"
          }`}
        >
          Settings
        </button>
      </div>

      {/* SAML Configuration */}
      {activeTab === "saml" && (
        <SAMLConfigForm
          key={samlKey}
          initialConfig={samlConfig}
          onSave={handleSAMLConfigSaved}
          onError={handleSAMLError}
        />
      )}

      {/* OIDC Configuration */}
      {activeTab === "oidc" && (
        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Add OIDC Provider</CardTitle>
              <CardDescription>Configure a new OpenID Connect provider</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-1 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="oidc-provider">Provider Name</Label>
                  <Input
                    id="oidc-provider"
                    value={newOidcProvider.provider}
                    onChange={(e) =>
                      setNewOidcProvider({ ...newOidcProvider, provider: e.target.value })
                    }
                    placeholder="google, azure, okta, etc."
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="oidc-client-id">Client ID</Label>
                  <Input
                    id="oidc-client-id"
                    value={newOidcProvider.client_id}
                    onChange={(e) =>
                      setNewOidcProvider({ ...newOidcProvider, client_id: e.target.value })
                    }
                    placeholder="your-client-id"
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="oidc-client-secret">Client Secret</Label>
                  <Input
                    id="oidc-client-secret"
                    type="password"
                    value={newOidcProvider.client_secret}
                    onChange={(e) =>
                      setNewOidcProvider({ ...newOidcProvider, client_secret: e.target.value })
                    }
                    placeholder="your-client-secret"
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="oidc-auth-endpoint">Authorization Endpoint</Label>
                  <Input
                    id="oidc-auth-endpoint"
                    value={newOidcProvider.authorization_endpoint}
                    onChange={(e) =>
                      setNewOidcProvider({
                        ...newOidcProvider,
                        authorization_endpoint: e.target.value,
                      })
                    }
                    placeholder="https://provider.com/oauth2/authorize"
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="oidc-token-endpoint">Token Endpoint</Label>
                  <Input
                    id="oidc-token-endpoint"
                    value={newOidcProvider.token_endpoint}
                    onChange={(e) =>
                      setNewOidcProvider({
                        ...newOidcProvider,
                        token_endpoint: e.target.value,
                      })
                    }
                    placeholder="https://provider.com/oauth2/token"
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="oidc-userinfo-endpoint">UserInfo Endpoint</Label>
                  <Input
                    id="oidc-userinfo-endpoint"
                    value={newOidcProvider.userinfo_endpoint}
                    onChange={(e) =>
                      setNewOidcProvider({
                        ...newOidcProvider,
                        userinfo_endpoint: e.target.value,
                      })
                    }
                    placeholder="https://provider.com/oauth2/userinfo"
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="oidc-jwks-uri">JWKS URI</Label>
                  <Input
                    id="oidc-jwks-uri"
                    value={newOidcProvider.jwks_uri}
                    onChange={(e) =>
                      setNewOidcProvider({ ...newOidcProvider, jwks_uri: e.target.value })
                    }
                    placeholder="https://provider.com/.well-known/jwks.json"
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="oidc-scope">Scope (Optional)</Label>
                  <Input
                    id="oidc-scope"
                    value={newOidcProvider.scope || ""}
                    onChange={(e) =>
                      setNewOidcProvider({ ...newOidcProvider, scope: e.target.value })
                    }
                    placeholder="openid email profile"
                  />
                </div>

                <div className="flex items-center space-x-2">
                  <Checkbox
                    id="oidc-enabled"
                    checked={newOidcProvider.enabled}
                    onCheckedChange={(checked) =>
                      setNewOidcProvider({ ...newOidcProvider, enabled: checked as boolean })
                    }
                  />
                  <Label htmlFor="oidc-enabled">Enable this provider</Label>
                </div>

                <div className="flex items-center space-x-2">
                  <Checkbox
                    id="oidc-jit"
                    checked={newOidcProvider.jit_provisioning_enabled || false}
                    onCheckedChange={(checked) =>
                      setNewOidcProvider({
                        ...newOidcProvider,
                        jit_provisioning_enabled: checked as boolean,
                      })
                    }
                  />
                  <Label htmlFor="oidc-jit">Enable JIT provisioning</Label>
                </div>
              </div>

              <div className="flex justify-end">
                <Button onClick={handleAddOIDCProvider} disabled={saving}>
                  {saving ? "Adding..." : "Add Provider"}
                </Button>
              </div>
            </CardContent>
          </Card>

          {/* Existing OIDC Providers */}
          {oidcProviders.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle>Configured Providers</CardTitle>
                <CardDescription>Manage your existing OIDC providers</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {oidcProviders.map(({ provider, config }) => (
                    <div
                      key={provider}
                      className="flex items-center justify-between p-4 border rounded-lg"
                    >
                      <div>
                        <div className="font-medium">{provider}</div>
                        <div className="text-sm text-muted-foreground">
                          {config.enabled ? "Enabled" : "Disabled"}
                        </div>
                      </div>
                      <Button
                        variant="destructive"
                        size="sm"
                        onClick={() => handleDeleteOIDCProvider(provider)}
                        disabled={saving}
                      >
                        Delete
                      </Button>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}
        </div>
      )}

      {/* Settings */}
      {activeTab === "settings" && (
        <Card>
          <CardHeader>
            <CardTitle>SSO Settings</CardTitle>
            <CardDescription>Configure global SSO behavior</CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            <div className="flex items-center space-x-2">
              <Checkbox
                id="sso-only"
                checked={ssoOnlyMode}
                onCheckedChange={(checked) => setSsoOnlyMode(checked as boolean)}
              />
              <div className="space-y-1">
                <Label htmlFor="sso-only">SSO Only Mode</Label>
                <p className="text-sm text-muted-foreground">
                  When enabled, users can only log in via SSO. Password authentication will be
                  disabled.
                </p>
              </div>
            </div>

            <Separator />

            <div className="space-y-2">
              <Label htmlFor="admin-recovery">Admin Recovery User Email</Label>
              <Input
                id="admin-recovery"
                type="email"
                value={adminRecoveryUser}
                onChange={(e) => setAdminRecoveryUser(e.target.value)}
                placeholder="admin@example.com"
              />
              <p className="text-sm text-muted-foreground">
                Optional: Designated admin user who can access password login recovery in SSO-only
                mode
              </p>
            </div>

            <div className="flex justify-end">
              <Button onClick={handleSaveSettings} disabled={saving}>
                {saving ? "Saving..." : "Save Settings"}
              </Button>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}

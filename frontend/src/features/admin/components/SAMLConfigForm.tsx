import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import { Checkbox } from "@/components/ui/checkbox"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Separator } from "@/components/ui/separator"
import { updateSAMLConfig, type SAMLConfig } from "@/features/auth/api/ssoApi"

interface SAMLConfigFormProps {
  initialConfig: SAMLConfig
  onSave?: (config: SAMLConfig) => void
  onError?: (error: string) => void
}

export default function SAMLConfigForm({
  initialConfig,
  onSave,
  onError,
}: SAMLConfigFormProps) {
  const [config, setConfig] = useState<SAMLConfig>(initialConfig)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState("")
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({})

  const validateField = (name: string, value: any): string | null => {
    switch (name) {
      case "idp_entity_id":
        if (!value || value.trim() === "") {
          return "Identity Provider Entity ID is required"
        }
        try {
          new URL(value)
        } catch {
          return "Must be a valid URL"
        }
        break
      case "idp_sso_url":
        if (!value || value.trim() === "") {
          return "Identity Provider SSO URL is required"
        }
        try {
          new URL(value)
        } catch {
          return "Must be a valid URL"
        }
        break
      case "idp_x509_cert":
        if (!value || value.trim() === "") {
          return "Identity Provider X.509 Certificate is required"
        }
        if (!value.includes("BEGIN CERTIFICATE") || !value.includes("END CERTIFICATE")) {
          return "Must be a valid X.509 certificate in PEM format"
        }
        break
      case "sp_entity_id":
        if (value && value.trim() !== "") {
          try {
            new URL(value)
          } catch {
            return "Must be a valid URL"
          }
        }
        break
      case "assertion_consumer_service_url":
        if (value && value.trim() !== "") {
          try {
            new URL(value)
          } catch {
            return "Must be a valid URL"
          }
        }
        break
    }
    return null
  }

  const validateForm = (): boolean => {
    const errors: Record<string, string> = {}

    const entityIdError = validateField("idp_entity_id", config.idp_entity_id)
    if (entityIdError) errors.idp_entity_id = entityIdError

    const ssoUrlError = validateField("idp_sso_url", config.idp_sso_url)
    if (ssoUrlError) errors.idp_sso_url = ssoUrlError

    const certError = validateField("idp_x509_cert", config.idp_x509_cert)
    if (certError) errors.idp_x509_cert = certError

    const spEntityIdError = validateField("sp_entity_id", config.sp_entity_id || "")
    if (spEntityIdError) errors.sp_entity_id = spEntityIdError

    const acsUrlError = validateField(
      "assertion_consumer_service_url",
      config.assertion_consumer_service_url || ""
    )
    if (acsUrlError) errors.assertion_consumer_service_url = acsUrlError

    setFieldErrors(errors)
    return Object.keys(errors).length === 0
  }

  const handleFieldChange = (name: keyof SAMLConfig, value: any) => {
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
      const savedConfig = await updateSAMLConfig(config)
      setConfig(savedConfig)
      onSave?.(savedConfig)
    } catch (err: any) {
      const errorMessage = err.response?.data?.detail || "Failed to save SAML configuration"
      setError(errorMessage)
      onError?.(errorMessage)
    } finally {
      setSaving(false)
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>SAML Configuration</CardTitle>
        <CardDescription>
          Configure SAML 2.0 authentication for your Identity Provider
        </CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="space-y-6">
          {/* Enable SAML */}
          <div className="flex items-center space-x-2">
            <Checkbox
              id="saml-enabled"
              checked={config.enabled}
              onCheckedChange={(checked) => handleFieldChange("enabled", checked)}
            />
            <Label htmlFor="saml-enabled">Enable SAML authentication</Label>
          </div>

          <Separator />

          {/* Identity Provider Settings */}
          <div className="space-y-4">
            <h3 className="text-sm font-medium">Identity Provider Settings</h3>

            <div className="space-y-2">
              <Label htmlFor="idp_entity_id">
                Identity Provider Entity ID
                <span className="text-destructive ml-1">*</span>
              </Label>
              <Input
                id="idp_entity_id"
                value={config.idp_entity_id}
                onChange={(e) => handleFieldChange("idp_entity_id", e.target.value)}
                placeholder="https://idp.example.com/entityid"
                disabled={saving}
                className={fieldErrors.idp_entity_id ? "border-destructive" : ""}
              />
              {fieldErrors.idp_entity_id && (
                <p className="text-sm text-destructive">{fieldErrors.idp_entity_id}</p>
              )}
            </div>

            <div className="space-y-2">
              <Label htmlFor="idp_sso_url">
                Identity Provider SSO URL
                <span className="text-destructive ml-1">*</span>
              </Label>
              <Input
                id="idp_sso_url"
                value={config.idp_sso_url}
                onChange={(e) => handleFieldChange("idp_sso_url", e.target.value)}
                placeholder="https://idp.example.com/sso"
                disabled={saving}
                className={fieldErrors.idp_sso_url ? "border-destructive" : ""}
              />
              {fieldErrors.idp_sso_url && (
                <p className="text-sm text-destructive">{fieldErrors.idp_sso_url}</p>
              )}
            </div>

            <div className="space-y-2">
              <Label htmlFor="idp_x509_cert">
                Identity Provider X.509 Certificate
                <span className="text-destructive ml-1">*</span>
              </Label>
              <Textarea
                id="idp_x509_cert"
                value={config.idp_x509_cert}
                onChange={(e) => handleFieldChange("idp_x509_cert", e.target.value)}
                placeholder="-----BEGIN CERTIFICATE-----&#10;...&#10;-----END CERTIFICATE-----"
                className={`min-h-[120px] ${fieldErrors.idp_x509_cert ? "border-destructive" : ""}`}
                disabled={saving}
              />
              {fieldErrors.idp_x509_cert && (
                <p className="text-sm text-destructive">{fieldErrors.idp_x509_cert}</p>
              )}
            </div>
          </div>

          <Separator />

          {/* Service Provider Settings */}
          <div className="space-y-4">
            <h3 className="text-sm font-medium">Service Provider Settings (Optional)</h3>

            <div className="space-y-2">
              <Label htmlFor="sp_entity_id">Service Provider Entity ID</Label>
              <Input
                id="sp_entity_id"
                value={config.sp_entity_id || ""}
                onChange={(e) => handleFieldChange("sp_entity_id", e.target.value)}
                placeholder="https://yourapp.com/saml/metadata"
                disabled={saving}
                className={fieldErrors.sp_entity_id ? "border-destructive" : ""}
              />
              {fieldErrors.sp_entity_id && (
                <p className="text-sm text-destructive">{fieldErrors.sp_entity_id}</p>
              )}
              <p className="text-sm text-muted-foreground">
                Leave empty to use the default SP entity ID
              </p>
            </div>

            <div className="space-y-2">
              <Label htmlFor="assertion_consumer_service_url">Assertion Consumer Service URL</Label>
              <Input
                id="assertion_consumer_service_url"
                value={config.assertion_consumer_service_url || ""}
                onChange={(e) =>
                  handleFieldChange("assertion_consumer_service_url", e.target.value)
                }
                placeholder="https://yourapp.com/auth/callback"
                disabled={saving}
                className={fieldErrors.assertion_consumer_service_url ? "border-destructive" : ""}
              />
              {fieldErrors.assertion_consumer_service_url && (
                <p className="text-sm text-destructive">
                  {fieldErrors.assertion_consumer_service_url}
                </p>
              )}
              <p className="text-sm text-muted-foreground">
                Leave empty to use the default ACS URL
              </p>
            </div>

            <div className="space-y-2">
              <Label htmlFor="name_id_format">Name ID Format</Label>
              <Input
                id="name_id_format"
                value={config.name_id_format || ""}
                onChange={(e) => handleFieldChange("name_id_format", e.target.value)}
                placeholder="urn:oasis:names:tc:SAML:1.1:nameid-format:unspecified"
                disabled={saving}
              />
              <p className="text-sm text-muted-foreground">
                Default: urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress
              </p>
            </div>
          </div>

          <Separator />

          {/* Provisioning Settings */}
          <div className="space-y-4">
            <h3 className="text-sm font-medium">Provisioning Settings</h3>

            <div className="flex items-center space-x-2">
              <Checkbox
                id="saml-jit"
                checked={config.jit_provisioning_enabled || false}
                onCheckedChange={(checked) =>
                  handleFieldChange("jit_provisioning_enabled", checked)
                }
                disabled={saving}
              />
              <div className="space-y-1">
                <Label htmlFor="saml-jit">Enable JIT provisioning</Label>
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
              {saving ? "Saving..." : "Save SAML Configuration"}
            </Button>
          </div>
        </form>
      </CardContent>
    </Card>
  )
}

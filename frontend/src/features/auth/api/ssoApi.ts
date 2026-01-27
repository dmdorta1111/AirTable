import { get, post } from "@/lib/api"

/**
 * SSO Authentication API client functions
 * Handles SAML and OIDC authentication flows
 */

// SAML Authentication

export async function initiateSAMLLogin(): Promise<{ login_url: string }> {
  return post<{ login_url: string }>("/api/v1/saml/login")
}

export async function handleSAMLCallback(data: {
  SAMLResponse: string
  RelayState?: string
}): Promise<{ access_token: string; token_type: string; user: any }> {
  return post("/api/v1/saml/callback", data)
}

export async function getSAMLMetadata(): Promise<string> {
  // Returns XML metadata as text
  const response = await fetch("/api/v1/saml/metadata")
  if (!response.ok) {
    throw new Error(`Failed to fetch SAML metadata: ${response.statusText}`)
  }
  return response.text()
}

// OIDC Authentication

export async function initiateOIDCLogin(provider: string): Promise<{ login_url: string }> {
  return post<{ login_url: string }>(`/api/v1/oidc/login?provider=${provider}`)
}

export async function handleOIDCCallback(data: {
  code: string
  state: string
  provider?: string
}): Promise<{ access_token: string; token_type: string; user: any }> {
  return post("/api/v1/oidc/callback", data)
}

// SSO Configuration Management (Admin)

export interface SAMLConfig {
  enabled: boolean
  idp_entity_id: string
  idp_sso_url: string
  idp_x509_cert: string
  sp_entity_id?: string
  assertion_consumer_service_url?: string
  name_id_format?: string
  attribute_mapping?: Record<string, string>
  role_mapping?: Record<string, string>
  jit_provisioning_enabled?: boolean
}

export interface OIDCConfig {
  enabled: boolean
  provider: string
  client_id: string
  client_secret: string
  authorization_endpoint: string
  token_endpoint: string
  userinfo_endpoint: string
  jwks_uri: string
  scope?: string
  attribute_mapping?: Record<string, string>
  role_mapping?: Record<string, string>
  jit_provisioning_enabled?: boolean
}

export interface SSOConfig {
  saml?: SAMLConfig
  oidc?: Record<string, OIDCConfig>
  sso_only_mode: boolean
  admin_recovery_user?: string
}

export async function getSSOConfig(): Promise<SSOConfig> {
  return get<SSOConfig>("/api/v1/sso/config")
}

export async function updateSAMLConfig(config: SAMLConfig): Promise<SAMLConfig> {
  return post<SAMLConfig>("/api/v1/sso/config/saml", config)
}

export async function updateOIDCConfig(provider: string, config: OIDCConfig): Promise<OIDCConfig> {
  return post<OIDCConfig>(`/api/v1/sso/config/oidc/${provider}`, config)
}

export async function deleteOIDCConfig(provider: string): Promise<void> {
  return post(`/api/v1/sso/config/oidc/${provider}/delete`)
}

export async function updateSSOSettings(settings: {
  sso_only_mode: boolean
  admin_recovery_user?: string
}): Promise<void> {
  return post("/api/v1/sso/config/settings", settings)
}

// Helper function to check if SSO is enabled

export async function isSSOEnabled(): Promise<boolean> {
  try {
    const config = await getSSOConfig()
    return (
      (config.saml?.enabled ?? false) ||
      ((config.oidc && Object.values(config.oidc).some((c) => c.enabled)) ?? false)
    )
  } catch {
    return false
  }
}

// Helper function to get available SSO providers

export async function getAvailableProviders(): Promise<
  Array<{ type: "saml" | "oidc"; provider: string; name: string }>
> {
  try {
    const config = await getSSOConfig()
    const providers: Array<{ type: "saml" | "oidc"; provider: string; name: string }> = []

    if (config.saml?.enabled) {
      providers.push({
        type: "saml",
        provider: "saml",
        name: config.saml.sp_entity_id || "SAML",
      })
    }

    if (config.oidc) {
      Object.entries(config.oidc).forEach(([provider, cfg]) => {
        if (cfg.enabled) {
          providers.push({
            type: "oidc",
            provider,
            name: provider.charAt(0).toUpperCase() + provider.slice(1),
          })
        }
      })
    }

    return providers
  } catch {
    return []
  }
}

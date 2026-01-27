import { create } from "zustand"
import type { User } from "@/types"

export type SSOProvider = "saml" | "oidc" | null

interface AuthState {
  user: User | null
  token: string | null
  isAuthenticated: boolean
  ssoProvider: SSOProvider
  ssoProviderName: string | null
  isSSO: boolean
  setAuth: (user: User, token: string, ssoProvider?: SSOProvider, ssoProviderName?: string) => void
  logout: () => void
  clearSSO: () => void
}

const STORAGE_KEYS = {
  ACCESS_TOKEN: "access_token",
  USER: "user",
  SSO_PROVIDER: "sso_provider",
  SSO_PROVIDER_NAME: "sso_provider_name",
} as const

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  token: null,
  isAuthenticated: false,
  ssoProvider: null,
  ssoProviderName: null,
  isSSO: false,
  setAuth: (user: User, token: string, ssoProvider?: SSOProvider, ssoProviderName?: string) => {
    localStorage.setItem(STORAGE_KEYS.ACCESS_TOKEN, token)
    localStorage.setItem(STORAGE_KEYS.USER, JSON.stringify(user))

    // Store SSO-specific data if provided
    if (ssoProvider) {
      localStorage.setItem(STORAGE_KEYS.SSO_PROVIDER, ssoProvider)
      if (ssoProviderName) {
        localStorage.setItem(STORAGE_KEYS.SSO_PROVIDER_NAME, ssoProviderName)
      }
      set({
        user,
        token,
        isAuthenticated: true,
        ssoProvider,
        ssoProviderName: ssoProviderName || null,
        isSSO: true,
      })
    } else {
      // Clear SSO data if logging in via regular auth
      localStorage.removeItem(STORAGE_KEYS.SSO_PROVIDER)
      localStorage.removeItem(STORAGE_KEYS.SSO_PROVIDER_NAME)
      set({
        user,
        token,
        isAuthenticated: true,
        ssoProvider: null,
        ssoProviderName: null,
        isSSO: false,
      })
    }
  },
  logout: () => {
    localStorage.removeItem(STORAGE_KEYS.ACCESS_TOKEN)
    localStorage.removeItem(STORAGE_KEYS.USER)
    localStorage.removeItem(STORAGE_KEYS.SSO_PROVIDER)
    localStorage.removeItem(STORAGE_KEYS.SSO_PROVIDER_NAME)
    set({
      user: null,
      token: null,
      isAuthenticated: false,
      ssoProvider: null,
      ssoProviderName: null,
      isSSO: false,
    })
  },
  clearSSO: () => {
    localStorage.removeItem(STORAGE_KEYS.SSO_PROVIDER)
    localStorage.removeItem(STORAGE_KEYS.SSO_PROVIDER_NAME)
    set({
      ssoProvider: null,
      ssoProviderName: null,
      isSSO: false,
    })
  },
}))

// Initialize auth state from localStorage
const storedToken = localStorage.getItem(STORAGE_KEYS.ACCESS_TOKEN)
const storedUser = localStorage.getItem(STORAGE_KEYS.USER)
const storedSSOProvider = localStorage.getItem(STORAGE_KEYS.SSO_PROVIDER) as SSOProvider
const storedSSOProviderName = localStorage.getItem(STORAGE_KEYS.SSO_PROVIDER_NAME)

if (storedToken && storedUser) {
  useAuthStore.setState({
    token: storedToken,
    user: JSON.parse(storedUser),
    isAuthenticated: true,
    ssoProvider: storedSSOProvider || null,
    ssoProviderName: storedSSOProviderName || null,
    isSSO: !!storedSSOProvider,
  })
}
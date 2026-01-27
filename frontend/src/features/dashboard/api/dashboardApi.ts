import { post } from "@/lib/api"

export interface DashboardCreateFromTemplate {
  base_id: string
  template_id: string
  name: string
  description?: string
  is_personal?: boolean
}

export interface DashboardResponse {
  id: string
  base_id: string
  created_by_id: string | null
  name: string
  description: string | null
  is_default: boolean
  is_personal: boolean
  is_public: boolean
  is_locked: boolean
  is_shared: boolean
  color: string | null
  icon: string | null
  template_id: string | null
  share_token: string | null
  last_viewed_at: string | null
  layout_config: Record<string, unknown> | null
  settings: Record<string, unknown> | null
  global_filters: unknown[] | null
  created_at: string
  updated_at: string
  deleted_at: string | null
}

export async function createFromTemplate(
  data: DashboardCreateFromTemplate
): Promise<DashboardResponse> {
  return post<DashboardResponse>("/api/v1/dashboards/from-template", data)
}

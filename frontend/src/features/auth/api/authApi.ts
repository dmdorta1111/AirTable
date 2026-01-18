import type { LoginRequest, LoginResponse } from "@/types"
import { post } from "@/lib/api"

export async function login(data: LoginRequest): Promise<LoginResponse> {
  return post<LoginResponse>("/auth/login", data)
}

export async function register(data: {
  email: string
  password: string
  name?: string
}): Promise<LoginResponse> {
  return post<LoginResponse>("/auth/register", data)
}

export async function logout(): Promise<void> {
  await post("/auth/logout")
}
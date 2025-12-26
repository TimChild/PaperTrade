export interface HealthResponse {
  status: string
  version?: string
  timestamp?: string
}

export interface ApiError {
  message: string
  status?: number
}

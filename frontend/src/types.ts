export type CheckStatus = 'up' | 'down' | 'changed'

export interface Token {
  access_token: string
  token_type: string
  username: string
}

export interface Monitor {
  id: number
  name: string
  url: string
  interval_seconds: number
  expected_status: number
  keyword: string | null
  watch_content: boolean
  paused: boolean
  webhook_url: string | null
  last_status: CheckStatus | null
  last_checked_at: string | null
  uptime_ratio: number | null
  avg_latency_ms: number | null
  open_incidents: number
}

export interface MonitorInput {
  name: string
  url: string
  interval_seconds: number
  expected_status: number
  keyword: string | null
  watch_content: boolean
  webhook_url: string | null
}

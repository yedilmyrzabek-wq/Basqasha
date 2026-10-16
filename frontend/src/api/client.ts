import createClient from 'openapi-fetch'
import type { components, paths } from './schema'

/** Typed client generated from docs/api/openapi.yaml (`npm run gen:api`). Same origin; Vite proxies /api and /files. */
export const api = createClient<paths>({ baseUrl: window.location.origin })

export type Schemas = components['schemas']
export type StepKey = Schemas['StepKey']
export type StepState = Schemas['StepState']
export type StepStatus = StepState['status']
export type WaitReason = NonNullable<StepState['wait_reason']>
export type Project = Schemas['Project']
export type ProjectDetail = Schemas['ProjectDetail']
export type Angle = Schemas['angle']
export type Fact = Schemas['fact']
export type FactSource = Schemas['source']
export type FactRow = Schemas['FactRow']
export type Settings = Schemas['Settings']

/**
 * The spec's ProjectCreate uses `anyOf: [required source_url | required transcript]`,
 * which openapi-typescript collapses to `unknown`; this mirrors its properties.
 */
export interface ProjectCreate {
  source_url?: string
  transcript?: string
  title?: string
  language?: 'kk' | 'ru' | 'en'
  target_seconds?: number
  sponsored?: boolean
}

export class ApiError extends Error {
  status: number
  errors: string[]
  constructor(message: string, status: number, errors: string[] = []) {
    super(message)
    this.status = status
    this.errors = errors
  }
}

function describeError(error: unknown, response: Response): ApiError {
  if (response.status === 502 || response.status === 503 || response.status === 504) {
    return new ApiError('Бэкенд недоступен — запустите сервер (BACKEND_PORT)', response.status)
  }
  if (error && typeof error === 'object' && 'detail' in error) {
    const { detail, errors } = error as { detail: unknown; errors?: unknown }
    const list = Array.isArray(errors) ? errors.map(String) : []
    if (typeof detail === 'string') return new ApiError(detail, response.status, list)
    // FastAPI validation errors: detail = [{loc, msg}]
    if (Array.isArray(detail)) {
      const msgs = detail.map((d) =>
        d && typeof d === 'object' && 'msg' in d
          ? `${Array.isArray(d.loc) ? d.loc.slice(1).join('.') + ': ' : ''}${String(d.msg)}`
          : JSON.stringify(d),
      )
      return new ApiError(msgs.join('; '), response.status, msgs)
    }
  }
  return new ApiError(
    typeof error === 'string' && error ? error : `Ошибка ${response.status} ${response.statusText}`,
    response.status,
  )
}

/** Turns an openapi-fetch result into data or a thrown ApiError (for TanStack Query). */
export async function unwrap<T>(
  call: Promise<{ data?: T; error?: unknown; response: Response }>,
): Promise<T> {
  let res: { data?: T; error?: unknown; response: Response }
  try {
    res = await call
  } catch {
    throw new ApiError('Бэкенд недоступен — нет соединения', 0)
  }
  if (!res.response.ok) throw describeError(res.error, res.response)
  return res.data as T
}

export function errorText(e: unknown): string {
  if (!e) return ''
  return e instanceof Error ? e.message : String(e)
}

/** multipart/form-data serializer for upload endpoints. */
export function formData(body: Record<string, unknown>): FormData {
  const fd = new FormData()
  for (const [k, v] of Object.entries(body)) {
    if (v === undefined || v === null) continue
    fd.append(k, v instanceof Blob ? v : String(v))
  }
  return fd
}

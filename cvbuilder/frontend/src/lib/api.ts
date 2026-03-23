import axios from 'axios'

export const api = axios.create({
  baseURL: '/api',
  headers: { 'Content-Type': 'application/json' },
})

// ---- Token helpers ----

export function getToken(): string | null {
  return localStorage.getItem('cvbuilder_token')
}

export function setToken(token: string): void {
  localStorage.setItem('cvbuilder_token', token)
}

export function clearToken(): void {
  localStorage.removeItem('cvbuilder_token')
}

// Attach token to every request
api.interceptors.request.use((config) => {
  const token = getToken()
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// On 401, redirect to login
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401 && !error.config?.url?.includes('/auth/')) {
      clearToken()
      window.location.href = '/login'
    }
    return Promise.reject(error)
  },
)

// ---- Auth API ----

export interface UserOut {
  id: number
  email: string
  full_name: string | null
  is_active: boolean
  is_admin: boolean
  created_at: string | null
}

export interface Token {
  access_token: string
  token_type: string
}

export async function loginUser(email: string, password: string): Promise<Token> {
  const form = new URLSearchParams()
  form.append('username', email)
  form.append('password', password)
  const { data } = await api.post<Token>('/auth/login', form, {
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
  })
  return data
}

export async function registerUser(email: string, password: string, fullName?: string): Promise<UserOut> {
  const { data } = await api.post<UserOut>('/auth/register', {
    email,
    password,
    full_name: fullName || null,
  })
  return data
}

export async function getCurrentUser(): Promise<UserOut> {
  const { data } = await api.get<UserOut>('/auth/me')
  return data
}

// ---- Types ----

export interface Profile {
  id: number
  name: string | null
  email: string | null
  phone: string | null
  website: string | null
  orcid: string | null
  semantic_scholar_id: string | null
  linkedin: string | null
  addresses: Address[]
}

export interface Address {
  id: number
  type: 'home' | 'work'
  line_order: number
  text: string
}

export interface Education {
  id: number
  degree: string | null
  year: number | null
  subject: string | null
  school: string | null
  sort_order: number
}

export interface Experience {
  id: number
  title: string | null
  years_start: string | null
  years_end: string | null
  employer: string | null
  sort_order: number
}

export interface Consulting {
  id: number
  title: string | null
  years: string | null
  employer: string | null
  sort_order: number
}

export interface Membership {
  id: number
  org: string | null
  years: string | null
  sort_order: number
}

export interface Panel {
  id: number
  panel: string | null
  org: string | null
  role: string | null
  date: string | null
  panel_id: string | null
  type: 'advisory' | 'grant_review'
  sort_order: number
}

export interface Patent {
  id: number
  name: string | null
  number: string | null
  status: string | null
  sort_order: number
  authors: PatentAuthor[]
}

export interface PatentAuthor {
  id: number
  author_name: string
  author_order: number
}

export interface Symposium {
  id: number
  title: string | null
  meeting: string | null
  date: string | null
  role: string | null
  sort_order: number
}

export interface Class {
  id: number
  class_name: string | null
  year: number | null
  role: string | null
  school: string | null
  students: number | null
  lectures: number | null
  in_three_year: boolean | null
  sort_order: number
}

export interface Grant {
  id: number
  title: string | null
  agency: string | null
  amount: string | null
  years_start: string | null
  years_end: string | null
  role: string | null
  id_number: string | null
  status: string | null
  sort_order: number
}

export interface Award {
  id: number
  name: string | null
  year: string | null
  org: string | null
  date: string | null
  sort_order: number
}

export interface Press {
  id: number
  outlet: string | null
  title: string | null
  date: string | null
  url: string | null
  topic: string | null
  sort_order: number
}

export interface Trainee {
  id: number
  name: string | null
  degree: string | null
  years_start: string | null
  years_end: string | null
  type: string | null
  school: string | null
  thesis: string | null
  current_position: string | null
  trainee_type: 'advisee' | 'postdoc'
  sort_order: number
}

export interface WorkAuthor {
  id: number
  author_name: string
  author_order: number
  student: boolean
  corresponding: boolean
  cofirst: boolean
  cosenior: boolean
}

export interface Work {
  id: number
  work_type: string
  title: string | null
  year: number | null
  month: number | null
  day: number | null
  doi: string | null
  data: Record<string, unknown>
  authors: WorkAuthor[]
}

export interface TemplateSection {
  id: number
  section_key: string
  enabled: boolean
  section_order: number
  config: Record<string, string> | null
  depth: number
}

export interface CVTemplate {
  id: number
  name: string
  description: string | null
  is_system: boolean
  style: Record<string, string> | null
  sort_direction: string
  author: string | null
  author_contact: string | null
  guidance_url: string | null
  created_at: string
  updated_at: string
  sections: TemplateSection[]
}

export interface CVInstanceItem {
  id: number
  item_id: number
}

export interface CVInstanceSection {
  id: number
  section_key: string
  enabled: boolean | null
  section_order: number | null
  heading_override: string | null
  config_overrides: Record<string, unknown> | null
  depth: number
  curated: boolean
  items: CVInstanceItem[]
}

export interface CVInstance {
  id: number
  template_id: number
  name: string
  description: string | null
  style_overrides: Record<string, string> | null
  sort_direction_override: string | null
  created_at: string
  updated_at: string
  sections: CVInstanceSection[]
  template_name: string | null
}

export interface AvailableItem {
  id: number
  label: string
  selected: boolean
}

export interface ScholarlyOutputStats {
  total_works: number
  counts_by_type: Record<string, number>
  works_by_year: { year: number; count: number }[]
  first_author_count: number
  corresponding_author_count: number
  senior_author_count: number
  student_led_count: number
  h_index: number
  i10_index: number
  total_citations: number
  citations_by_year: { year: number; count: number }[]
}

export interface TraineeDetail {
  name: string
  degree: string
  advisor_type: string
  institution: string
  period: string
  current_position: string
  is_current: boolean
}

export interface MentorshipCategory {
  count: number
  current: number
  trainees: TraineeDetail[]
}

export interface RoleCount {
  role: string
  count: number
}

export interface TeachingStats {
  courses_total: number
  courses_three_year: number
  unique_courses: number
  by_role: RoleCount[]
  by_role_five_year: RoleCount[]
}

export interface MentorshipStats {
  total: number
  current: number
  postdoctoral: MentorshipCategory
  doctoral: MentorshipCategory
  masters: MentorshipCategory
  undergraduate: MentorshipCategory
  other: MentorshipCategory
}

export interface TeachingMentorshipStats {
  teaching: TeachingStats
  mentorship: MentorshipStats
  courses_total: number
  courses_three_year: number
  unique_courses: number
  trainees_total: number
  trainee_breakdown: { type: string; count: number }[]
  current_trainees: number
}

export interface GrantDetail {
  title: string
  agency: string
  role: string
  period: string
  amount: string
  id_number: string
}

export interface GrantCategoryStats {
  count: number
  total_amount: number
  total_amount_display: string
  by_role: { role: string; count: number }[]
  grants: GrantDetail[]
}

export interface FundingStats {
  grants_total: number
  total_funding_amount: string
  total_funding_raw: number
  active: GrantCategoryStats
  completed: GrantCategoryStats
}

export interface ServiceStats {
  committees: number
  advisory_panels: number
  grant_review_panels: number
  symposia: number
  editorial: number
  peer_review: number
  service_breakdown: { label: string; count: number }[]
}

export interface DashboardData {
  profile_complete: boolean
  scholarly_output: ScholarlyOutputStats
  teaching_mentorship: TeachingMentorshipStats
  funding: FundingStats
  service: ServiceStats
}

export interface DOILookupResponse {
  title: string | null
  year: string | null
  journal: string | null
  volume: string | null
  issue: string | null
  pages: string | null
  authors: string[]
  doi: string | null
}

export interface PublicationCandidate {
  title: string
  year: string | null
  journal: string | null
  volume: string | null
  issue: string | null
  pages: string | null
  doi: string | null
  authors: string[]
  source: string
  pmid: string | null
  pub_type: string
  match_warning: string | null
  preprint_doi: string | null
  published_doi: string | null
}

export interface SyncCheckResponse {
  candidates: PublicationCandidate[]
  searched: string[]
  errors: Record<string, string>
}

// ---- Section Definitions API ----

export interface SectionFieldDef {
  key: string
  label: string
  type: 'text' | 'date' | 'url' | 'multiline' | 'boolean'
}

export interface SectionDefinition {
  id: number
  section_key: string
  label: string
  layout: 'entry' | 'list'
  fields: SectionFieldDef[]
  sort_field: string | null
  created_at: string | null
}

export async function listSectionDefinitions(): Promise<SectionDefinition[]> {
  const { data } = await api.get<SectionDefinition[]>('/section-definitions')
  return data
}

export async function createSectionDefinition(defn: {
  label: string; layout: string; fields: SectionFieldDef[]; sort_field: string | null
}): Promise<SectionDefinition> {
  const { data } = await api.post<SectionDefinition>('/section-definitions', defn)
  return data
}

export async function updateSectionDefinition(id: number, defn: {
  label: string; layout: string; fields: SectionFieldDef[]; sort_field: string | null
}): Promise<SectionDefinition> {
  const { data } = await api.put<SectionDefinition>(`/section-definitions/${id}`, defn)
  return data
}

export async function deleteSectionDefinition(id: number): Promise<void> {
  await api.delete(`/section-definitions/${id}`)
}

// ---- Admin API ----

export interface AdminUserUpdate {
  is_active?: boolean
  is_admin?: boolean
  full_name?: string
}

export async function listUsers(): Promise<UserOut[]> {
  const { data } = await api.get<UserOut[]>('/admin/users')
  return data
}

export async function updateUser(userId: number, updates: AdminUserUpdate): Promise<UserOut> {
  const { data } = await api.patch<UserOut>(`/admin/users/${userId}`, updates)
  return data
}

export async function deleteUser(userId: number): Promise<void> {
  await api.delete(`/admin/users/${userId}`)
}

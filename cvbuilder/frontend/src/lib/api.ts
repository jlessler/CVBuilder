import axios from 'axios'

export const api = axios.create({
  baseURL: '/api',
  headers: { 'Content-Type': 'application/json' },
})

// ---- Types ----

export interface Profile {
  id: number
  name: string | null
  email: string | null
  phone: string | null
  website: string | null
  orcid: string | null
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

export interface PubAuthor {
  id: number
  author_name: string
  author_order: number
  student: boolean
}

export interface Publication {
  id: number
  type: string
  title: string | null
  year: string | null
  journal: string | null
  volume: string | null
  issue: string | null
  pages: string | null
  doi: string | null
  corr: boolean
  cofirsts: number
  coseniors: number
  select_flag: boolean
  conference: string | null
  pres_type: string | null
  publisher: string | null
  authors: PubAuthor[]
}

export interface TemplateSection {
  id: number
  section_key: string
  enabled: boolean
  section_order: number
  config: Record<string, string> | null
}

export interface CVTemplate {
  id: number
  name: string
  description: string | null
  theme_css: string
  sort_direction: string
  created_at: string
  updated_at: string
  sections: TemplateSection[]
}

export interface DashboardStats {
  total_publications: number
  papers: number
  preprints: number
  chapters: number
  letters: number
  scimeetings: number
  trainees: number
  grants: number
  profile_complete: boolean
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

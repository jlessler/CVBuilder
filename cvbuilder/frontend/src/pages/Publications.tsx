import { useState, useMemo } from 'react'
import { useSearchParams } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '../lib/api'
import type { Work, WorkAuthor, DOILookupResponse, Profile, PublicationCandidate, SyncCheckResponse, WorkDiff, CompleteFieldsResponse, FieldDiff } from '../lib/api'
import { Button, Card, Input, Modal, NavigableModal, PageHeader, Badge, Spinner, Textarea, Select, Checkbox } from '../components/ui'
import { useItemNavigation } from '../hooks/useItemNavigation'
import { Plus, Search, Trash2, Edit2, Copy, ExternalLink, GripVertical, RefreshCw, Pencil, AlertTriangle, Link2, BarChart3, ChevronDown, ChevronRight } from 'lucide-react'
import { CitationMetrics } from './Citations'

type AuthorRow = {
  author_name: string
  student: boolean
  corresponding: boolean
  cofirst: boolean
  cosenior: boolean
  given_name: string
  family_name: string
  suffix: string
  expanded: boolean
}

// Surname particles for name parsing
const PARTICLES = new Set([
  'van', 'von', 'de', 'del', 'della', 'di', 'du', 'des', 'der', 'den',
  'la', 'le', 'el', 'al', 'bin', 'ibn', 'ben', 'st', 'st.', 'mac', 'mc',
])
const SUFFIXES = new Set(['jr', 'jr.', 'sr', 'sr.', 'ii', 'iii', 'iv', 'v', 'phd', 'md'])

function isInitials(token: string): boolean {
  const cleaned = token.replace(/\./g, '')
  return cleaned.length <= 3 && cleaned.length > 0 && /^[A-Z]+$/.test(cleaned)
}

function splitInitials(token: string): [string, string | null] {
  const cleaned = token.replace(/\./g, '')
  if (cleaned.length === 1) return [cleaned, null]
  return [cleaned[0], cleaned.slice(1)]
}

function parseAuthorName(name: string): { given_name: string; family_name: string; suffix: string } {
  const result = { given_name: '', family_name: '', suffix: '' }
  if (!name?.trim()) return result
  const trimmed = name.trim().replace(/\s+/g, ' ')

  const makeGiven = (first: string, mid: string | null) => mid ? `${first} ${mid}` : first

  // Extract suffix from end
  const extractSuffix = (tokens: string[]): [string[], string] => {
    if (tokens.length > 0 && SUFFIXES.has(tokens[tokens.length - 1].replace(/[.,]/g, '').toLowerCase())) {
      return [tokens.slice(0, -1), tokens[tokens.length - 1].replace(/,/, '')]
    }
    return [tokens, '']
  }

  // Comma format
  if (trimmed.includes(',')) {
    const [famPart, ...rest] = trimmed.split(',').map(s => s.trim())
    let givenPart = rest[0] || ''
    // Check if second part is a suffix
    if (SUFFIXES.has(givenPart.replace(/[.,]/g, '').toLowerCase())) {
      result.suffix = givenPart.replace(/,/, '')
      givenPart = rest[1]?.trim() || ''
    }
    // Check suffix in family part
    const famTokens = famPart.split(' ')
    if (famTokens.length > 1 && SUFFIXES.has(famTokens[famTokens.length - 1].replace(/[.,]/g, '').toLowerCase())) {
      result.suffix = famTokens[famTokens.length - 1].replace(/,/, '')
      result.family_name = famTokens.slice(0, -1).join(' ')
    } else {
      result.family_name = famPart
    }
    const givenTokens = givenPart ? givenPart.split(' ') : []
    if (givenTokens.length === 1) {
      const tok = givenTokens[0].replace(/\.$/, '')
      if (isInitials(tok)) {
        const [f, m] = splitInitials(tok)
        result.given_name = makeGiven(f + '.', m ? [...m].join('.') + '.' : null)
      } else {
        result.given_name = givenTokens[0]
      }
    } else if (givenTokens.length > 1) {
      result.given_name = givenTokens.join(' ')
    }
    return result
  }

  // No comma
  let tokens = trimmed.split(' ')
  let suffix = ''
  ;[tokens, suffix] = extractSuffix(tokens)
  result.suffix = suffix

  if (tokens.length === 1) {
    result.family_name = tokens[0]
    return result
  }

  if (tokens.length === 2) {
    if (isInitials(tokens[1])) {
      result.family_name = tokens[0]
      const [f, m] = splitInitials(tokens[1])
      result.given_name = makeGiven(f + '.', m ? [...m].join('.') + '.' : null)
    } else if (isInitials(tokens[0])) {
      const [f, m] = splitInitials(tokens[0])
      result.given_name = makeGiven(f + '.', m ? [...m].join('.') + '.' : null)
      result.family_name = tokens[1]
    } else {
      result.given_name = tokens[0]
      result.family_name = tokens[1]
    }
    return result
  }

  // 3+ tokens: "Given Middle Family" or "Family G M"
  if (isInitials(tokens[0]) && !isInitials(tokens[tokens.length - 1])) {
    const firstGiven = tokens[0].includes('.') ? tokens[0] : tokens[0] + '.'
    let famStart = tokens.length - 1
    while (famStart > 1 && PARTICLES.has(tokens[famStart - 1].toLowerCase().replace(/,/, ''))) famStart--
    result.family_name = tokens.slice(famStart).join(' ')
    const midTokens = tokens.slice(1, famStart)
    result.given_name = midTokens.length ? makeGiven(firstGiven, midTokens.join(' ')) : firstGiven
  } else {
    const firstGiven = tokens[0]
    let famStart = tokens.length - 1
    while (famStart > 1 && PARTICLES.has(tokens[famStart - 1].toLowerCase().replace(/,/, ''))) famStart--
    result.family_name = tokens.slice(famStart).join(' ')
    const midTokens = tokens.slice(1, famStart)
    result.given_name = midTokens.length ? makeGiven(firstGiven, midTokens.join(' ')) : firstGiven
  }

  return result
}

function composeAuthorName(given: string, family: string, suffix: string): string {
  if (!family) return given || ''
  let initials = ''
  if (given) {
    for (const part of given.replace(/\./g, ' ').split(/\s+/)) {
      if (part) initials += part[0].toUpperCase()
    }
  }
  let name = family
  if (initials) name += ' ' + initials
  if (suffix) name += ' ' + suffix
  return name
}

const WORK_TYPES = [
  { value: 'papers', label: 'Papers' },
  { value: 'preprints', label: 'Preprints' },
  { value: 'chapters', label: 'Chapters' },
  { value: 'letters', label: 'Letters' },
  { value: 'scimeetings', label: 'Scientific Meetings' },
  { value: 'editorials', label: 'Non-Peer-Reviewed / Editorials' },
  { value: 'patents', label: 'Patents' },
  { value: 'seminars', label: 'Seminars' },
  { value: 'software', label: 'Software' },
  { value: 'dissertation', label: 'Dissertation' },
]

const TYPE_COLOR: Record<string, string> = {
  papers: 'blue', preprints: 'cyan', chapters: 'purple',
  letters: 'orange', scimeetings: 'green', editorials: 'gray',
  patents: 'yellow', seminars: 'pink', software: 'indigo', dissertation: 'red',
}

const SOURCE_COLOR: Record<string, string> = {
  pubmed: 'green', crossref: 'blue', orcid: 'orange', semanticscholar: 'purple',
}

// Work types that have journal/volume/issue/pages fields
const PUBLICATION_TYPES = new Set(['papers', 'preprints', 'chapters', 'letters', 'scimeetings', 'editorials'])
// Work types that support cross-ref DOIs
const CROSSREF_TYPES = new Set(['papers', 'preprints', 'chapters', 'letters'])

interface WorkForm {
  work_type: string
  title: string
  year: string
  doi: string
  // data fields (flattened for editing)
  journal: string
  volume: string
  issue: string
  pages: string
  select_flag: boolean
  preprint_doi: string
  published_doi: string
  // patent fields
  identifier: string
  status: string
  // seminar fields
  institution: string
  conference: string
  location: string
  // software fields
  publisher: string
  url: string
  // authors
  authorRows: AuthorRow[]
}

function blankWork(): WorkForm {
  return {
    work_type: 'papers', title: '', year: '', doi: '',
    journal: '', volume: '', issue: '', pages: '',
    select_flag: false, preprint_doi: '', published_doi: '',
    identifier: '', status: '',
    institution: '', conference: '', location: '',
    publisher: '', url: '',
    authorRows: [{ author_name: '', student: false, corresponding: false, cofirst: false, cosenior: false, given_name: '', family_name: '', suffix: '', expanded: false }],
  }
}

function workToForm(work: Work): WorkForm {
  const d = work.data || {}
  return {
    work_type: work.work_type,
    title: work.title || '',
    year: work.year != null ? String(work.year) : '',
    doi: work.doi || '',
    journal: (d.journal as string) || '',
    volume: (d.volume as string) || '',
    issue: (d.issue as string) || '',
    pages: (d.pages as string) || '',
    select_flag: !!d.select_flag,
    preprint_doi: (d.preprint_doi as string) || '',
    published_doi: (d.published_doi as string) || '',
    identifier: (d.identifier as string) || '',
    status: (d.status as string) || '',
    institution: (d.institution as string) || '',
    conference: (d.conference as string) || '',
    location: (d.location as string) || '',
    publisher: (d.publisher as string) || '',
    url: (d.url as string) || '',
    authorRows: work.authors.length
      ? work.authors.map(a => ({
          author_name: a.author_name,
          student: a.student,
          corresponding: a.corresponding,
          cofirst: a.cofirst,
          cosenior: a.cosenior,
          given_name: a.given_name || '',
          family_name: a.family_name || '',
          suffix: a.suffix || '',
          expanded: false,
        }))
      : [{ author_name: '', student: false, corresponding: false, cofirst: false, cosenior: false, given_name: '', family_name: '', suffix: '', expanded: false }],
  }
}

function formToPayload(form: WorkForm) {
  const data: Record<string, unknown> = {}
  const wt = form.work_type

  if (PUBLICATION_TYPES.has(wt)) {
    if (form.journal) data.journal = form.journal
    if (form.volume) data.volume = form.volume
    if (form.issue) data.issue = form.issue
    if (form.pages) data.pages = form.pages
  }
  if (form.select_flag) data.select_flag = true
  if (CROSSREF_TYPES.has(wt) || wt === 'preprints') {
    if (form.preprint_doi) data.preprint_doi = form.preprint_doi
    if (form.published_doi) data.published_doi = form.published_doi
  }
  if (wt === 'patents') {
    if (form.identifier) data.identifier = form.identifier
    if (form.status) data.status = form.status
  }
  if (wt === 'seminars') {
    if (form.institution) data.institution = form.institution
    if (form.conference) data.conference = form.conference
    if (form.location) data.location = form.location
  }
  if (wt === 'software') {
    if (form.publisher) data.publisher = form.publisher
    if (form.url) data.url = form.url
  }
  if (wt === 'dissertation') {
    if (form.institution) data.institution = form.institution
  }
  if (wt === 'scimeetings') {
    if (form.conference) data.conference = form.conference
    if (form.institution) data.institution = form.institution
  }

  const authors = form.authorRows
    .filter(r => r.author_name.trim())
    .map((r, i) => ({
      author_name: r.author_name.trim(),
      author_order: i,
      student: r.student,
      corresponding: r.corresponding,
      cofirst: r.cofirst,
      cosenior: r.cosenior,
      given_name: r.given_name || null,
      family_name: r.family_name || null,
      suffix: r.suffix || null,
    }))

  return {
    work_type: wt,
    title: form.title || null,
    year: parseInt(form.year) || null,
    doi: form.doi || null,
    data: Object.keys(data).length > 0 ? data : null,
    authors,
  }
}

type CitationSpan = { text: string; color?: 'green' | 'red' }

function buildCitationPreview(
  work: Work,
  diff: WorkDiff,
  accepted: Set<string>,
): CitationSpan[] {
  const spans: CitationSpan[] = []

  // Helper: get effective value for a field given the diff and accepted set
  const fieldVal = (field: string, currentVal: string | null | undefined): { text: string; color?: 'green' | 'red' } => {
    const fd = diff.field_diffs.find(d => d.field === field)
    if (!fd) return { text: currentVal || '' }
    if (accepted.has(field)) return { text: fd.proposed || '', color: 'green' }
    if (fd.current) return { text: fd.current, color: 'red' }
    return { text: '' }
  }

  // Authors
  const authorSpans: CitationSpan[] = []
  if (accepted.has('proposed_authors') && diff.proposed_authors.length > 0) {
    diff.proposed_authors.forEach((a, i) => {
      if (i > 0) authorSpans.push({ text: ', ' })
      authorSpans.push({ text: a.author_name, color: 'green' })
    })
  } else {
    const workAuthors = [...work.authors].sort((a, b) => a.author_order - b.author_order)
    workAuthors.forEach((a, i) => {
      if (i > 0) authorSpans.push({ text: ', ' })
      const ad = diff.author_diffs.find(d => d.author_order === a.author_order)
      if (ad && accepted.has(`author_rename_${ad.author_order}`)) {
        authorSpans.push({ text: ad.proposed_name, color: 'green' })
      } else if (ad && !accepted.has(`author_rename_${ad.author_order}`)) {
        authorSpans.push({ text: a.author_name, color: 'red' })
      } else {
        authorSpans.push({ text: a.author_name })
      }
    })
    if (accepted.has('additional_authors') && diff.additional_authors.length > 0) {
      diff.additional_authors.forEach(a => {
        authorSpans.push({ text: ', ' })
        authorSpans.push({ text: a.author_name, color: 'green' })
      })
    }
  }
  spans.push(...authorSpans)
  if (authorSpans.length > 0) spans.push({ text: '. ' })

  // Year
  const yearVal = fieldVal('year', work.year?.toString())
  if (yearVal.text) spans.push({ text: '(', }, { ...yearVal }, { text: '). ' })

  // Title
  const titleVal = fieldVal('title', work.title)
  if (titleVal.text) spans.push({ text: '"' }, { ...titleVal }, { text: '." ' })

  // Journal
  const data = work.data || {}
  const journalVal = fieldVal('journal', data.journal as string)
  if (journalVal.text) {
    spans.push({ text: '', color: journalVal.color }) // italic handled in render
    spans.push({ ...journalVal })
  }

  // Volume(Issue)
  const volVal = fieldVal('volume', data.volume as string)
  const issueVal = fieldVal('issue', data.issue as string)
  if (volVal.text) {
    spans.push({ text: ' ' })
    spans.push({ ...volVal })
    if (issueVal.text) {
      spans.push({ text: '(' })
      spans.push({ ...issueVal })
      spans.push({ text: ')' })
    }
  }

  // Pages
  const pagesVal = fieldVal('pages', data.pages as string)
  if (pagesVal.text) {
    spans.push({ text: ': ' })
    spans.push({ ...pagesVal })
  }

  if (journalVal.text || volVal.text || pagesVal.text) spans.push({ text: '. ' })

  // DOI
  const doiVal = fieldVal('doi', work.doi)
  if (doiVal.text) {
    spans.push({ text: 'doi:' })
    spans.push({ ...doiVal })
  }

  return spans
}

export function Publications() {
  const qc = useQueryClient()
  const [searchParams, setSearchParams] = useSearchParams()
  const typeFilter = searchParams.get('type') ?? 'papers'
  function setTypeFilter(type: string) {
    setSearchParams(type ? { type } : { type: 'all' }, { replace: true })
  }
  const [keyword, setKeyword] = useState('')
  const [editing, setEditing] = useState<Work | null>(null)
  const [creating, setCreating] = useState(false)
  const [form, setForm] = useState(blankWork())
  const [doiInput, setDoiInput] = useState('')
  const [doiLoading, setDoiLoading] = useState(false)

  // Find New state
  const [syncOpen, setSyncOpen] = useState(false)
  const [syncLoading, setSyncLoading] = useState(false)
  const [syncResult, setSyncResult] = useState<SyncCheckResponse | null>(null)
  const [syncError, setSyncError] = useState<string | null>(null)
  const [syncIndex, setSyncIndex] = useState(0)
  const [syncSaving, setSyncSaving] = useState(false)
  const [syncDecisions, setSyncDecisions] = useState<Map<number, 'added' | 'ignored' | 'skipped'>>(new Map())
  const [editingCandidate, setEditingCandidate] = useState<number | null>(null)
  const [candidateForm, setCandidateForm] = useState<PublicationCandidate | null>(null)
  // Ignored candidates management
  const [ignoredOpen, setIgnoredOpen] = useState(false)
  const [ignoredList, setIgnoredList] = useState<import('../lib/api').IgnoredCandidate[]>([])
  const [ignoredLoading, setIgnoredLoading] = useState(false)

  // Mass review state
  const [reviewSelection, setReviewSelection] = useState<Set<number>>(new Set())
  const [reviewMode, setReviewMode] = useState(false)

  // Complete missing fields state
  const [completeOpen, setCompleteOpen] = useState(false)
  const [completeLoading, setCompleteLoading] = useState(false)
  const [completeDiffs, setCompleteDiffs] = useState<WorkDiff[]>([])
  const [completeStats, setCompleteStats] = useState<{ skipped: number; errors: number }>({ skipped: 0, errors: 0 })
  const [completeIndex, setCompleteIndex] = useState(0)
  const [acceptedFields, setAcceptedFields] = useState<Map<number, Set<string>>>(new Map())
  const [completeSaving, setCompleteSaving] = useState(false)

  const { data: profile } = useQuery<Profile>({
    queryKey: ['profile'],
    queryFn: () => api.get('/profile').then(r => r.data),
  })

  function matchesSelf(authorName: string): boolean {
    const profileName = profile?.name
    if (!profileName || !authorName) return false
    const parts = profileName.trim().split(/\s+/)
    if (!parts.length) return false

    const last = parts[parts.length - 1]
    const firstInit = parts[0][0].toUpperCase()
    const midInit = parts.length >= 3 ? parts[1][0].toUpperCase() : ''

    if (!new RegExp(`\\b${last}\\b`, 'i').test(authorName)) return false

    const cleanWords = authorName.replace(/[,.]/g, ' ').split(/\s+/).filter(Boolean)
    const lastIdx = cleanWords.findIndex(w => w.toLowerCase() === last.toLowerCase())
    if (lastIdx === -1) return false

    const otherWords = cleanWords.filter((_, i) => i !== lastIdx)
    if (!otherWords.length) return false

    const toInitials = (w: string) => /^[A-Z]{1,3}$/.test(w) ? w : w[0].toUpperCase()
    const initials = otherWords.map(toInitials).join('').toUpperCase()

    if (!initials || initials[0] !== firstInit) return false
    if (midInit && initials.length >= 2 && initials[1] !== midInit) return false

    return true
  }

  function renderAuthors(authors: WorkAuthor[], max = 5) {
    const visible = authors.slice(0, max)
    return (
      <>
        {visible.map((a, i) => (
          <span key={a.id}>
            {i > 0 && ', '}
            {matchesSelf(a.author_name) ? <strong>{a.author_name}</strong> : a.author_name}
            {a.student && <sup>&dagger;</sup>}
            {a.corresponding && <sup>*</sup>}
          </span>
        ))}
        {authors.length > max && ` +${authors.length - max} more`}
      </>
    )
  }

  function renderCandidateAuthors(authors: string[], max = 5) {
    const visible = authors.slice(0, max)
    return (
      <>
        {visible.map((name, i) => (
          <span key={i}>
            {i > 0 && ', '}
            {matchesSelf(name) ? <strong>{name}</strong> : name}
          </span>
        ))}
        {authors.length > max && ` +${authors.length - max} more`}
      </>
    )
  }

  const { data = [], isLoading } = useQuery<Work[]>({
    queryKey: ['works', typeFilter, keyword],
    queryFn: () => api.get('/works', {
      params: { type: (typeFilter && typeFilter !== 'all') ? typeFilter : undefined, keyword: keyword || undefined, limit: 2000 }
    }).then(r => r.data),
  })

  const createMut = useMutation({
    mutationFn: () => api.post('/works', formToPayload(form)),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['works'] }); setCreating(false); setForm(blankWork()) },
  })

  const updateMut = useMutation({
    mutationFn: () => api.put(`/works/${editing!.id}`, formToPayload(form)),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['works'] }); setEditing(null) },
  })

  const deleteMut = useMutation({
    mutationFn: (id: number) => api.delete(`/works/${id}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['works'] }),
  })

  function openCreate() { setForm(blankWork()); setDoiInput(''); setCreating(true) }
  function openCopy(work: Work) {
    setForm(workToForm(work))
    setDoiInput('')
    setCreating(true)
  }
  function openEdit(work: Work) {
    setEditing(work)
    setForm(workToForm(work))
    setDoiInput(work.doi || '')
  }

  const navItems = useMemo(() => {
    if (reviewMode) return data.filter(w => reviewSelection.has(w.id))
    return data
  }, [data, reviewMode, reviewSelection])

  const nav = useItemNavigation({
    items: navItems,
    currentId: editing?.id ?? null,
    onSave: async () => {
      if (!editing) return
      const res = await api.put(`/works/${editing.id}`, formToPayload(form))
      const updated = res.data as Work
      // Update the cached data so navigating back shows saved values
      qc.setQueryData(['works', typeFilter, keyword], (old: Work[] | undefined) =>
        old?.map(w => w.id === editing.id ? updated : w)
      )
    },
    onNavigate: (work) => openEdit(work),
  })

  function closeEditModal() {
    if (nav.dirtyRef.current) {
      qc.invalidateQueries({ queryKey: ['works'] })
    }
    setEditing(null)
    if (reviewMode) setReviewMode(false)
  }

  function toggleReviewItem(id: number) {
    setReviewSelection(prev => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  function startReview() {
    const items = data.filter(w => reviewSelection.has(w.id))
    if (items.length === 0) return
    setReviewMode(true)
    openEdit(items[0])
  }

  // --- Complete missing fields handlers ---
  async function handleCompleteFields() {
    const ids = Array.from(reviewSelection)
    if (ids.length === 0) return
    setCompleteOpen(true)
    setCompleteLoading(true)
    setCompleteDiffs([])
    setCompleteIndex(0)
    setAcceptedFields(new Map())
    try {
      const res = await api.post<CompleteFieldsResponse>('/works/complete-fields', { work_ids: ids })
      const { diffs, skipped_no_match, errors } = res.data
      setCompleteDiffs(diffs)
      setCompleteStats({ skipped: skipped_no_match, errors })
      // Pre-accept: empty fields checked, conflicts unchecked
      const preAccepted = new Map<number, Set<string>>()
      for (const diff of diffs) {
        const accepted = new Set<string>()
        for (const fd of diff.field_diffs) {
          if (!fd.current) accepted.add(fd.field)
        }
        // Author diffs: pre-check (fuller names almost always wanted)
        for (const ad of diff.author_diffs) {
          accepted.add(`author_rename_${ad.author_order}`)
        }
        // Proposed/additional authors: pre-check
        if (diff.proposed_authors.length > 0) accepted.add('proposed_authors')
        if (diff.additional_authors.length > 0) accepted.add('additional_authors')
        preAccepted.set(diff.work_id, accepted)
      }
      setAcceptedFields(preAccepted)
    } catch {
      alert('Failed to fetch field completions.')
      setCompleteOpen(false)
    } finally {
      setCompleteLoading(false)
    }
  }

  function toggleCompleteField(workId: number, key: string) {
    setAcceptedFields(prev => {
      const next = new Map(prev)
      const s = new Set(next.get(workId) || [])
      if (s.has(key)) s.delete(key); else s.add(key)
      next.set(workId, s)
      return next
    })
  }

  function toggleAllCompleteFields(workId: number, allKeys: string[], checked: boolean) {
    setAcceptedFields(prev => {
      const next = new Map(prev)
      const s = checked ? new Set(allKeys) : new Set<string>()
      next.set(workId, s)
      return next
    })
  }

  async function saveCurrentCompleteWork() {
    const diff = completeDiffs[completeIndex]
    if (!diff) return
    const accepted = acceptedFields.get(diff.work_id) || new Set()
    if (accepted.size === 0) { advanceComplete(); return }

    // Find the current work from cache
    const currentWork = data.find(w => w.id === diff.work_id)
    if (!currentWork) { advanceComplete(); return }

    setCompleteSaving(true)
    try {
      // Build payload from current work, applying accepted diffs
      const newData = { ...(currentWork.data || {}) } as Record<string, unknown>
      let title = currentWork.title
      let year = currentWork.year
      let doi = currentWork.doi

      for (const fd of diff.field_diffs) {
        if (!accepted.has(fd.field)) continue
        if (fd.field === 'title') title = fd.proposed
        else if (fd.field === 'year') year = fd.proposed ? parseInt(fd.proposed) : null
        else if (fd.field === 'doi') doi = fd.proposed
        else newData[fd.field] = fd.proposed // journal, volume, issue, pages
      }

      // Build authors list
      let authors = currentWork.authors.map(a => ({
        author_name: a.author_name,
        author_order: a.author_order,
        student: a.student,
        corresponding: a.corresponding,
        cofirst: a.cofirst,
        cosenior: a.cosenior,
        given_name: a.given_name || null,
        family_name: a.family_name || null,
        suffix: a.suffix || null,
      }))

      // Apply author renames
      for (const ad of diff.author_diffs) {
        if (!accepted.has(`author_rename_${ad.author_order}`)) continue
        const match = authors.find(a => a.author_order === ad.author_order)
        if (match) {
          match.author_name = ad.proposed_name
          // Clear structured names so backend auto-parses from new display name
          match.given_name = null
          match.family_name = null
          match.suffix = null
        }
      }

      // Proposed authors (work had 0 authors)
      if (accepted.has('proposed_authors') && diff.proposed_authors.length > 0) {
        authors = diff.proposed_authors.map(pa => ({
          author_name: pa.author_name,
          author_order: pa.author_order,
          student: false,
          corresponding: false,
          cofirst: false,
          cosenior: false,
          given_name: pa.given_name || null,
          family_name: pa.family_name || null,
          suffix: pa.suffix || null,
        }))
      }

      // Additional authors
      if (accepted.has('additional_authors') && diff.additional_authors.length > 0) {
        for (const pa of diff.additional_authors) {
          authors.push({
            author_name: pa.author_name,
            author_order: pa.author_order,
            student: false,
            corresponding: false,
            cofirst: false,
            cosenior: false,
            given_name: pa.given_name || null,
            family_name: pa.family_name || null,
            suffix: pa.suffix || null,
          })
        }
      }

      await api.put(`/works/${diff.work_id}`, {
        work_type: currentWork.work_type,
        title,
        year,
        doi,
        data: Object.keys(newData).length > 0 ? newData : null,
        authors,
      })
      qc.invalidateQueries({ queryKey: ['works'] })
      advanceComplete()
    } catch {
      alert('Failed to save work.')
    } finally {
      setCompleteSaving(false)
    }
  }

  function advanceComplete() {
    if (completeIndex < completeDiffs.length - 1) {
      setCompleteIndex(i => i + 1)
    } else {
      setCompleteOpen(false)
    }
  }

  function skipCurrentCompleteWork() {
    advanceComplete()
  }

  async function lookupDoi() {
    if (!doiInput) return
    setDoiLoading(true)
    try {
      const res = await api.post<DOILookupResponse>('/works/doi-lookup', { doi: doiInput })
      const d = res.data
      setForm(f => ({
        ...f,
        title: d.title || f.title,
        year: d.year || f.year,
        journal: d.journal || f.journal,
        volume: d.volume || f.volume,
        issue: d.issue || f.issue,
        pages: d.pages || f.pages,
        doi: d.doi || f.doi,
        authorRows: d.authors.length
          ? d.authors.map(n => {
              const parsed = parseAuthorName(n)
              return { author_name: n, student: false, corresponding: false, cofirst: false, cosenior: false, ...parsed, expanded: false }
            })
          : f.authorRows,
      }))
    } catch {
      alert('DOI not found or lookup failed.')
    } finally {
      setDoiLoading(false)
    }
  }

  async function handleFindNew() {
    setSyncOpen(true)
    setSyncLoading(true)
    setSyncResult(null)
    setSyncError(null)
    setSyncIndex(0)
    setSyncDecisions(new Map())
    setEditingCandidate(null)
    setCandidateForm(null)
    try {
      const res = await api.get<SyncCheckResponse>('/works/sync-check')
      setSyncResult(res.data)
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      setSyncError(msg || 'Failed to fetch publications. Check your profile name/ORCID.')
    } finally {
      setSyncLoading(false)
    }
  }

  async function handleSyncAdd() {
    if (!syncResult) return
    const c = syncResult.candidates[syncIndex]
    setSyncSaving(true)
    try {
      await api.post('/works/sync-add', { publications: [c] })
      qc.invalidateQueries({ queryKey: ['works'] })
      setSyncDecisions(prev => new Map(prev).set(syncIndex, 'added'))
      advanceSync()
    } catch {
      alert('Failed to add publication.')
    } finally {
      setSyncSaving(false)
    }
  }

  async function handleSyncIgnore() {
    if (!syncResult) return
    const c = syncResult.candidates[syncIndex]
    setSyncSaving(true)
    try {
      await api.post('/works/sync-ignore', {
        source: c.source,
        title: c.title,
        doi: c.doi,
        pmid: c.pmid,
        year: c.year,
      })
      setSyncDecisions(prev => new Map(prev).set(syncIndex, 'ignored'))
      advanceSync()
    } catch {
      alert('Failed to ignore publication.')
    } finally {
      setSyncSaving(false)
    }
  }

  function handleSyncSkip() {
    setSyncDecisions(prev => new Map(prev).set(syncIndex, 'skipped'))
    advanceSync()
  }

  function advanceSync() {
    if (!syncResult) return
    // Find next unreviewed candidate after current index
    for (let i = syncIndex + 1; i < syncResult.candidates.length; i++) {
      if (!syncDecisions.has(i)) {
        setSyncIndex(i)
        setEditingCandidate(null)
        setCandidateForm(null)
        return
      }
    }
    // All reviewed — go to summary (index = length means summary screen)
    setSyncIndex(syncResult.candidates.length)
    setEditingCandidate(null)
    setCandidateForm(null)
  }

  function openCandidateEdit(idx: number) {
    if (!syncResult) return
    setEditingCandidate(idx)
    setCandidateForm({ ...syncResult.candidates[idx] })
  }

  function saveCandidateEdit() {
    if (!syncResult || editingCandidate === null || !candidateForm) return
    setSyncResult(prev => {
      if (!prev || editingCandidate === null) return prev
      const updated = [...prev.candidates]
      updated[editingCandidate] = { ...candidateForm }
      return { ...prev, candidates: updated }
    })
    setEditingCandidate(null)
    setCandidateForm(null)
  }

  async function loadIgnoredList() {
    setIgnoredLoading(true)
    try {
      const res = await api.get<import('../lib/api').IgnoredCandidate[]>('/works/sync-ignored')
      setIgnoredList(res.data)
    } catch {
      alert('Failed to load ignored list.')
    } finally {
      setIgnoredLoading(false)
    }
  }

  async function handleUnignore(id: number) {
    try {
      await api.delete(`/works/sync-ignored/${id}`)
      setIgnoredList(prev => prev.filter(r => r.id !== id))
    } catch {
      alert('Failed to un-ignore.')
    }
  }

  const wt = form.work_type
  const showPubFields = PUBLICATION_TYPES.has(wt)
  const showCrossref = CROSSREF_TYPES.has(wt)

  const WorkForm = (
    <div className="space-y-4">
      {/* DOI lookup */}
      <div className="flex gap-2 p-3 bg-blue-50 rounded-lg">
        <Input
          placeholder="Paste DOI to auto-fill..."
          value={doiInput}
          onChange={e => setDoiInput(e.target.value)}
          className="flex-1"
        />
        <Button variant="secondary" onClick={lookupDoi} loading={doiLoading} size="sm">
          Lookup DOI
        </Button>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <Select
          label="Type"
          options={WORK_TYPES}
          value={form.work_type}
          onChange={e => setForm(f => ({ ...f, work_type: e.target.value }))}
        />
        <Input label="Year" value={form.year} onChange={e => setForm(f => ({ ...f, year: e.target.value }))} />
      </div>

      <Textarea
        label="Title"
        value={form.title}
        onChange={e => setForm(f => ({ ...f, title: e.target.value }))}
        rows={2}
      />

      {/* Authors */}
      <div>
        <div className="flex items-center justify-between mb-1">
          <label className="block text-sm font-medium text-gray-700">Authors</label>
          <span className="text-xs text-gray-400">&dagger; student &nbsp; * corresponding &nbsp; 1 co-first &nbsp; S co-senior</span>
        </div>
        <div className="space-y-1 max-h-48 overflow-y-auto pr-1">
          {form.authorRows.map((row, i) => (
            <div key={i}>
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => setForm(f => {
                    const rows = [...f.authorRows]
                    rows[i] = { ...rows[i], expanded: !rows[i].expanded }
                    return { ...f, authorRows: rows }
                  })}
                  className="text-gray-400 hover:text-gray-600 flex-shrink-0"
                  title={row.expanded ? 'Hide name fields' : 'Edit name parts'}
                >
                  {row.expanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
                </button>
                <GripVertical size={14} className="text-gray-300 flex-shrink-0" />
                <input
                  className="flex-1 px-2 py-1 text-sm border border-gray-300 rounded focus:outline-none focus:ring-1 focus:ring-primary-500"
                  placeholder="Smith J"
                  value={row.author_name}
                  onChange={e => setForm(f => {
                    const rows = [...f.authorRows]
                    rows[i] = { ...rows[i], author_name: e.target.value }
                    return { ...f, authorRows: rows }
                  })}
                  onBlur={() => setForm(f => {
                    const rows = [...f.authorRows]
                    const parsed = parseAuthorName(rows[i].author_name)
                    rows[i] = { ...rows[i], ...parsed }
                    return { ...f, authorRows: rows }
                  })}
                />
                <label className="flex items-center gap-0.5 text-xs text-gray-500 cursor-pointer" title="Student/trainee">
                  <input type="checkbox" checked={row.student} className="rounded"
                    onChange={e => setForm(f => {
                      const rows = [...f.authorRows]; rows[i] = { ...rows[i], student: e.target.checked }
                      return { ...f, authorRows: rows }
                    })} />
                  <sup>&dagger;</sup>
                </label>
                <label className="flex items-center gap-0.5 text-xs text-gray-500 cursor-pointer" title="Corresponding">
                  <input type="checkbox" checked={row.corresponding} className="rounded"
                    onChange={e => setForm(f => {
                      const rows = [...f.authorRows]; rows[i] = { ...rows[i], corresponding: e.target.checked }
                      return { ...f, authorRows: rows }
                    })} />
                  <span>*</span>
                </label>
                <label className="flex items-center gap-0.5 text-xs text-gray-500 cursor-pointer" title="Co-first author">
                  <input type="checkbox" checked={row.cofirst} className="rounded"
                    onChange={e => setForm(f => {
                      const rows = [...f.authorRows]; rows[i] = { ...rows[i], cofirst: e.target.checked }
                      return { ...f, authorRows: rows }
                    })} />
                  <span>1</span>
                </label>
                <label className="flex items-center gap-0.5 text-xs text-gray-500 cursor-pointer" title="Co-senior author">
                  <input type="checkbox" checked={row.cosenior} className="rounded"
                    onChange={e => setForm(f => {
                      const rows = [...f.authorRows]; rows[i] = { ...rows[i], cosenior: e.target.checked }
                      return { ...f, authorRows: rows }
                    })} />
                  <span>S</span>
                </label>
                <button
                  type="button"
                  onClick={() => setForm(f => ({
                    ...f,
                    authorRows: f.authorRows.filter((_, j) => j !== i),
                  }))}
                  className="text-gray-300 hover:text-red-400 flex-shrink-0"
                  disabled={form.authorRows.length === 1}
                >
                  <Trash2 size={13} />
                </button>
              </div>
              {row.expanded && (
                <div className="ml-8 mt-1 mb-1 grid grid-cols-4 gap-1">
                  <input
                    className="px-2 py-0.5 text-xs border border-gray-200 rounded focus:outline-none focus:ring-1 focus:ring-primary-500"
                    placeholder="Given name"
                    value={row.given_name}
                    onChange={e => setForm(f => {
                      const rows = [...f.authorRows]
                      rows[i] = { ...rows[i], given_name: e.target.value, author_name: composeAuthorName(e.target.value, rows[i].family_name, rows[i].suffix) }
                      return { ...f, authorRows: rows }
                    })}
                  />
                  <input
                    className="px-2 py-0.5 text-xs border border-gray-200 rounded focus:outline-none focus:ring-1 focus:ring-primary-500"
                    placeholder="Family name"
                    value={row.family_name}
                    onChange={e => setForm(f => {
                      const rows = [...f.authorRows]
                      rows[i] = { ...rows[i], family_name: e.target.value, author_name: composeAuthorName(rows[i].given_name, e.target.value, rows[i].suffix) }
                      return { ...f, authorRows: rows }
                    })}
                  />
                  <input
                    className="px-2 py-0.5 text-xs border border-gray-200 rounded focus:outline-none focus:ring-1 focus:ring-primary-500"
                    placeholder="Suffix"
                    value={row.suffix}
                    onChange={e => setForm(f => {
                      const rows = [...f.authorRows]
                      rows[i] = { ...rows[i], suffix: e.target.value, author_name: composeAuthorName(rows[i].given_name, rows[i].family_name, e.target.value) }
                      return { ...f, authorRows: rows }
                    })}
                  />
                </div>
              )}
            </div>
          ))}
        </div>
        <button
          type="button"
          onClick={() => setForm(f => ({ ...f, authorRows: [...f.authorRows, { author_name: '', student: false, corresponding: false, cofirst: false, cosenior: false, given_name: '', family_name: '', suffix: '', expanded: false }] }))}
          className="mt-1.5 text-xs text-primary-600 hover:text-primary-800 flex items-center gap-1"
        >
          <Plus size={12} /> Add author
        </button>
      </div>

      {/* Publication-type fields */}
      {showPubFields && (
        <>
          <Input label="Journal / Conference" value={form.journal} onChange={e => setForm(f => ({ ...f, journal: e.target.value }))} />
          <div className="grid grid-cols-3 gap-3">
            <Input label="Volume" value={form.volume} onChange={e => setForm(f => ({ ...f, volume: e.target.value }))} />
            <Input label="Issue" value={form.issue} onChange={e => setForm(f => ({ ...f, issue: e.target.value }))} />
            <Input label="Pages" value={form.pages} onChange={e => setForm(f => ({ ...f, pages: e.target.value }))} />
          </div>
        </>
      )}

      {/* Patent fields */}
      {wt === 'patents' && (
        <div className="grid grid-cols-2 gap-4">
          <Input label="Patent Number" value={form.identifier} onChange={e => setForm(f => ({ ...f, identifier: e.target.value }))} />
          <Input label="Status" value={form.status} onChange={e => setForm(f => ({ ...f, status: e.target.value }))} />
        </div>
      )}

      {/* Seminar fields */}
      {wt === 'seminars' && (
        <>
          <Input label="Institution" value={form.institution} onChange={e => setForm(f => ({ ...f, institution: e.target.value }))} />
          <div className="grid grid-cols-2 gap-4">
            <Input label="Conference / Event" value={form.conference} onChange={e => setForm(f => ({ ...f, conference: e.target.value }))} />
            <Input label="Location" value={form.location} onChange={e => setForm(f => ({ ...f, location: e.target.value }))} />
          </div>
        </>
      )}

      {/* Software fields */}
      {wt === 'software' && (
        <div className="grid grid-cols-2 gap-4">
          <Input label="Publisher / Host" value={form.publisher} onChange={e => setForm(f => ({ ...f, publisher: e.target.value }))} />
          <Input label="URL" value={form.url} onChange={e => setForm(f => ({ ...f, url: e.target.value }))} />
        </div>
      )}

      {/* Dissertation fields */}
      {wt === 'dissertation' && (
        <Input label="Institution" value={form.institution} onChange={e => setForm(f => ({ ...f, institution: e.target.value }))} />
      )}

      {/* Scientific meeting extra fields */}
      {wt === 'scimeetings' && (
        <div className="grid grid-cols-2 gap-4">
          <Input label="Conference" value={form.conference} onChange={e => setForm(f => ({ ...f, conference: e.target.value }))} />
          <Input label="Institution" value={form.institution} onChange={e => setForm(f => ({ ...f, institution: e.target.value }))} />
        </div>
      )}

      <Input label="DOI" value={form.doi} onChange={e => setForm(f => ({ ...f, doi: e.target.value }))} />

      {/* Cross-reference DOI */}
      {showCrossref && (
        <div>
          <Input
            label={wt === 'preprints' ? 'Published DOI' : 'Preprint DOI'}
            placeholder="10.1234/..."
            value={wt === 'preprints' ? form.published_doi : form.preprint_doi}
            onChange={e => setForm(f => wt === 'preprints'
              ? { ...f, published_doi: e.target.value }
              : { ...f, preprint_doi: e.target.value }
            )}
          />
          <button
            type="button"
            className="mt-1 text-xs text-primary-600 hover:text-primary-800"
            onClick={() => {
              const targetDoi = form.doi
              if (!targetDoi) { alert('Enter a DOI first to search for cross-references.'); return }
              const match = data.find(w => w.doi && (
                (w.data?.preprint_doi as string) === targetDoi || (w.data?.published_doi as string) === targetDoi
              ))
              if (match) {
                setForm(f => wt === 'preprints'
                  ? { ...f, published_doi: match.doi || '' }
                  : { ...f, preprint_doi: match.doi || '' }
                )
              } else {
                alert('No matching work found in your library.')
              }
            }}
          >
            <Search size={10} className="inline mr-1" />Find in library
          </button>
        </div>
      )}

      <Checkbox label="Selected/highlighted" checked={form.select_flag} onChange={e => setForm(f => ({ ...f, select_flag: e.target.checked }))} />

      <div className="flex gap-2 justify-end pt-2 border-t">
        <Button variant="secondary" onClick={() => { setCreating(false); closeEditModal() }}>Cancel</Button>
        <Button
          onClick={() => creating ? createMut.mutate() : updateMut.mutate()}
          loading={createMut.isPending || updateMut.isPending}
        >
          {creating ? 'Add Work' : 'Save Changes'}
        </Button>
      </div>
    </div>
  )

  // Helper to get subtitle for a work
  function workSubtitle(work: Work): string {
    const d = work.data || {}
    if (PUBLICATION_TYPES.has(work.work_type)) {
      const parts = [d.journal as string]
      if (d.volume) parts.push(` ${d.volume}`)
      if (d.issue) parts.push(`(${d.issue})`)
      if (d.pages) parts.push(`: ${d.pages}`)
      return parts.filter(Boolean).join('')
    }
    if (work.work_type === 'patents') return [(d.identifier as string), d.status && `(${d.status})`].filter(Boolean).join(' ')
    if (work.work_type === 'seminars') return [(d.institution as string), d.conference && `– ${d.conference}`].filter(Boolean).join(' ')
    if (work.work_type === 'software') return [(d.publisher as string), d.url as string].filter(Boolean).join(' · ')
    if (work.work_type === 'dissertation') return (d.institution as string) || ''
    return ''
  }

  return (
    <div className="p-8">
      <PageHeader
        title="Scholarly Works"
        subtitle={`${data.length} total`}
        actions={
          <div className="flex items-center gap-2">
            <div className="relative">
              <Search size={16} className="absolute left-3 top-2.5 text-gray-400" />
              <input
                className="w-64 pl-9 pr-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
                placeholder="Search..."
                value={keyword}
                onChange={e => setKeyword(e.target.value)}
              />
            </div>
            <Button variant="secondary" onClick={handleFindNew}><RefreshCw size={15} /> Find New</Button>
            <Button onClick={openCreate}><Plus size={16} /> Add Work</Button>
          </div>
        }
      />

      {/* Filters */}
      <div className="flex gap-3 mb-6">
        <div className="flex gap-1 flex-wrap">
          {WORK_TYPES.map(pt => (
            <button
              key={pt.value}
              onClick={() => setTypeFilter(pt.value)}
              className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${typeFilter === pt.value ? 'bg-primary-600 text-white' : 'bg-white border border-gray-300 text-gray-600 hover:bg-gray-50'}`}
            >{pt.label}</button>
          ))}
          <button
            onClick={() => setTypeFilter('all')}
            className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${typeFilter === 'all' ? 'bg-primary-600 text-white' : 'bg-white border border-gray-300 text-gray-600 hover:bg-gray-50'}`}
          >All</button>
          <span className="border-l border-gray-300 mx-1" />
          <button
            onClick={() => setTypeFilter('citations')}
            className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors flex items-center gap-1.5 ${typeFilter === 'citations' ? 'bg-primary-600 text-white' : 'bg-white border border-gray-300 text-gray-600 hover:bg-gray-50'}`}
          ><BarChart3 size={14} /> Citations</button>
        </div>
      </div>

      {typeFilter === 'citations' ? <CitationMetrics /> : (<>

      {reviewSelection.size > 0 && (
        <div className="flex items-center gap-3 px-4 py-2 bg-primary-50 border border-primary-200 rounded-lg text-sm">
          <span className="font-medium text-primary-700">{reviewSelection.size} selected</span>
          <Button size="sm" onClick={startReview}>Review Selected</Button>
          <Button size="sm" variant="secondary" onClick={handleCompleteFields}>Complete Missing Fields</Button>
          <Button variant="ghost" size="sm" onClick={() => setReviewSelection(new Set(data.map(w => w.id)))}>Select All</Button>
          <Button variant="ghost" size="sm" onClick={() => setReviewSelection(new Set())}>Clear</Button>
        </div>
      )}

      {isLoading ? <Spinner /> : (
        <Card>
          <div className="divide-y divide-gray-100">
            {data.map(work => (
              <div key={work.id} className="px-5 py-4 hover:bg-gray-50 flex items-start justify-between gap-4">
                <div className="flex items-start gap-3 flex-1 min-w-0">
                  <input
                    type="checkbox"
                    checked={reviewSelection.has(work.id)}
                    onChange={() => toggleReviewItem(work.id)}
                    className="mt-1 rounded border-gray-300 text-primary-600 focus:ring-primary-500"
                  />
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <Badge color={TYPE_COLOR[work.work_type] || 'gray'}>{work.work_type}</Badge>
                    {work.data?.select_flag && <Badge color="yellow">Selected</Badge>}
                    {work.authors.some(a => a.corresponding) && <Badge color="green">Corr.</Badge>}
                    {work.year && <span className="text-xs text-gray-400">{work.year}</span>}
                  </div>
                  <p className="font-medium text-gray-900 text-sm truncate">{work.title}</p>
                  {work.authors.length > 0 && (
                    <p className="text-xs text-gray-500 mt-0.5">
                      {renderAuthors(work.authors)}
                    </p>
                  )}
                  {workSubtitle(work) && (
                    <p className="text-xs text-gray-400 mt-0.5 italic">{workSubtitle(work)}</p>
                  )}
                  {work.doi && (
                    <a
                      href={`https://doi.org/${work.doi}`} target="_blank" rel="noreferrer"
                      className="inline-flex items-center gap-1 text-xs text-blue-600 hover:underline mt-0.5"
                    >
                      <ExternalLink size={10} /> doi:{work.doi}
                    </a>
                  )}
                </div>
                </div>
                <div className="flex items-center gap-1 flex-shrink-0">
                  <Button variant="ghost" size="sm" onClick={() => openEdit(work)}>
                    <Edit2 size={14} />
                  </Button>
                  <Button variant="ghost" size="sm" onClick={() => openCopy(work)} title="Duplicate work">
                    <Copy size={14} />
                  </Button>
                  <Button variant="ghost" size="sm" onClick={() => {
                    if (confirm('Delete this work?')) deleteMut.mutate(work.id)
                  }}>
                    <Trash2 size={14} className="text-red-500" />
                  </Button>
                </div>
              </div>
            ))}
            {data.length === 0 && (
              <div className="py-16 text-center text-gray-400 text-sm">
                No scholarly works found.
              </div>
            )}
          </div>
        </Card>
      )}

      <Modal open={creating} onClose={() => setCreating(false)} title="Add Scholarly Work">
        {WorkForm}
      </Modal>
      <NavigableModal
        open={!!editing}
        onClose={closeEditModal}
        title="Edit Scholarly Work"
        navigation={{
          ...nav,
          label: reviewMode ? `Reviewing ${nav.currentIndex + 1} of ${nav.total} selected` : undefined,
        }}
      >
        {WorkForm}
      </NavigableModal>

      {/* Find New Publications Modal */}
      <Modal
        open={syncOpen}
        onClose={() => { if (!syncLoading && !syncSaving) setSyncOpen(false) }}
        title="Find New Publications"
      >
        {syncLoading && (
          <div className="py-12 flex flex-col items-center gap-4 text-gray-500">
            <Spinner />
            <p className="text-sm">Searching ORCID, PubMed, Crossref...</p>
          </div>
        )}

        {!syncLoading && syncError && (
          <div className="py-6 text-center">
            <p className="text-sm text-red-600">{syncError}</p>
            <Button variant="secondary" className="mt-4" onClick={() => setSyncOpen(false)}>Close</Button>
          </div>
        )}

        {!syncLoading && syncResult && (
          <div className="space-y-4">
            {/* Header */}
            <div className="text-sm text-gray-600">
              Found <strong>{syncResult.candidates.length}</strong> new publication{syncResult.candidates.length !== 1 ? 's' : ''}{' '}
              {syncResult.searched.length > 0 && <>across <em>{syncResult.searched.join(', ')}</em></>}
              {(syncResult.ignored_count || 0) > 0 && (
                <span className="text-gray-400"> ({syncResult.ignored_count} previously ignored)</span>
              )}
            </div>

            {Object.keys(syncResult.errors).length > 0 && (
              <div className="text-xs text-amber-700 bg-amber-50 border border-amber-200 rounded p-2 space-y-0.5">
                {Object.entries(syncResult.errors).map(([src, msg]) => (
                  <div key={src}><strong>{src}:</strong> {msg}</div>
                ))}
              </div>
            )}

            {syncResult.candidates.length === 0 ? (
              <div className="py-8 text-center text-gray-400 text-sm">
                No new publications found — your list is up to date!
                {(syncResult.ignored_count || 0) > 0 && (
                  <p className="mt-2">
                    <button className="text-primary-600 hover:underline" onClick={() => { setIgnoredOpen(true); loadIgnoredList() }}>
                      Manage {syncResult.ignored_count} ignored
                    </button>
                  </p>
                )}
              </div>
            ) : syncIndex >= syncResult.candidates.length ? (
              /* Summary screen */
              <div className="py-8 text-center space-y-4">
                <p className="text-sm font-medium text-gray-700">Review complete</p>
                <div className="flex justify-center gap-6 text-sm">
                  <span className="text-green-600">
                    {Array.from(syncDecisions.values()).filter(d => d === 'added').length} added
                  </span>
                  <span className="text-amber-600">
                    {Array.from(syncDecisions.values()).filter(d => d === 'ignored').length} ignored
                  </span>
                  <span className="text-gray-500">
                    {Array.from(syncDecisions.values()).filter(d => d === 'skipped').length} skipped
                  </span>
                </div>
                <Button onClick={() => setSyncOpen(false)}>Done</Button>
              </div>
            ) : (
              /* Arrow-through single candidate view */
              (() => {
                const c = syncResult.candidates[syncIndex]
                const decision = syncDecisions.get(syncIndex)
                const hasWarning = !!c.match_warning
                return (
                  <>
                    {/* Navigation */}
                    <div className="flex items-center justify-between">
                      <button
                        className="p-1 text-gray-400 hover:text-gray-700 disabled:opacity-30"
                        disabled={syncIndex === 0}
                        onClick={() => { setSyncIndex(syncIndex - 1); setEditingCandidate(null); setCandidateForm(null) }}
                      >&#9664;</button>
                      <span className="text-xs text-gray-500">{syncIndex + 1} of {syncResult.candidates.length}</span>
                      <button
                        className="p-1 text-gray-400 hover:text-gray-700 disabled:opacity-30"
                        disabled={syncIndex >= syncResult.candidates.length - 1}
                        onClick={() => { setSyncIndex(syncIndex + 1); setEditingCandidate(null); setCandidateForm(null) }}
                      >&#9654;</button>
                    </div>

                    {/* Decision badge for already-reviewed candidates */}
                    {decision && (
                      <div className="flex justify-center">
                        <Badge color={decision === 'added' ? 'green' : decision === 'ignored' ? 'yellow' : 'gray'}>
                          {decision.charAt(0).toUpperCase() + decision.slice(1)}
                        </Badge>
                      </div>
                    )}

                    {/* Single candidate card */}
                    <div className="border border-gray-200 rounded-lg">
                      <div className="px-4 py-3 flex items-start gap-3">
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2 mb-1 flex-wrap">
                            <Badge color={TYPE_COLOR[c.pub_type] || 'gray'}>{c.pub_type}</Badge>
                            {c.source.split('+').map(s => (
                              <Badge key={s} color={SOURCE_COLOR[s] || 'gray'}>{s}</Badge>
                            ))}
                            {c.match_warning && <Badge color="yellow">Possible duplicate</Badge>}
                            {c.year && <span className="text-xs text-gray-400">{c.year}</span>}
                          </div>
                          <p className="font-medium text-gray-900 text-sm">{c.title}</p>
                          {c.match_warning && (
                            <p className="text-xs text-amber-700 bg-amber-50 border border-amber-200 rounded px-2 py-1 mt-1 flex items-start gap-1.5">
                              <AlertTriangle size={11} className="flex-shrink-0 mt-0.5" />
                              <span>{c.match_warning}</span>
                            </p>
                          )}
                          {c.authors.length > 0 && (
                            <p className="text-xs text-gray-500 mt-0.5">
                              {renderCandidateAuthors(c.authors)}
                            </p>
                          )}
                          {c.journal && (
                            <p className="text-xs text-gray-400 mt-0.5 italic">
                              {c.journal}
                              {c.volume ? ` ${c.volume}` : ''}
                              {c.issue ? `(${c.issue})` : ''}
                              {c.pages ? `: ${c.pages}` : ''}
                            </p>
                          )}
                          {c.doi && (
                            <a
                              href={`https://doi.org/${c.doi}`} target="_blank" rel="noreferrer"
                              className="inline-flex items-center gap-1 text-xs text-blue-600 hover:underline mt-0.5"
                            >
                              <ExternalLink size={10} /> doi:{c.doi}
                            </a>
                          )}
                          {(c.preprint_doi || c.published_doi) && (
                            <span className="inline-flex items-center gap-1 text-xs text-purple-600 mt-0.5">
                              <Link2 size={10} />
                              {c.pub_type === 'preprints' ? 'Published' : 'Preprint'} DOI: {c.published_doi || c.preprint_doi}
                            </span>
                          )}
                        </div>
                        <button
                          className="flex-shrink-0 text-gray-400 hover:text-gray-700 p-1"
                          title="Edit before importing"
                          onClick={() => editingCandidate === syncIndex ? (setEditingCandidate(null), setCandidateForm(null)) : openCandidateEdit(syncIndex)}
                        >
                          <Pencil size={13} />
                        </button>
                      </div>

                      {/* Inline edit panel */}
                      {editingCandidate === syncIndex && candidateForm && (
                        <div className="px-4 py-3 bg-blue-50 border-t border-blue-100 space-y-3">
                          <div className="grid grid-cols-2 gap-3">
                            <Select
                              label="Type"
                              options={WORK_TYPES}
                              value={candidateForm.pub_type}
                              onChange={e => setCandidateForm(f => f ? { ...f, pub_type: e.target.value } : f)}
                            />
                            <Input
                              label="Year"
                              value={candidateForm.year || ''}
                              onChange={e => setCandidateForm(f => f ? { ...f, year: e.target.value } : f)}
                            />
                          </div>
                          <Textarea
                            label="Title"
                            value={candidateForm.title}
                            onChange={e => setCandidateForm(f => f ? { ...f, title: e.target.value } : f)}
                            rows={2}
                          />
                          <Input
                            label="Journal"
                            value={candidateForm.journal || ''}
                            onChange={e => setCandidateForm(f => f ? { ...f, journal: e.target.value } : f)}
                          />
                          <div className="grid grid-cols-3 gap-2">
                            <Input
                              label="Volume"
                              value={candidateForm.volume || ''}
                              onChange={e => setCandidateForm(f => f ? { ...f, volume: e.target.value } : f)}
                            />
                            <Input
                              label="Issue"
                              value={candidateForm.issue || ''}
                              onChange={e => setCandidateForm(f => f ? { ...f, issue: e.target.value } : f)}
                            />
                            <Input
                              label="Pages"
                              value={candidateForm.pages || ''}
                              onChange={e => setCandidateForm(f => f ? { ...f, pages: e.target.value } : f)}
                            />
                          </div>
                          <Input
                            label="DOI"
                            value={candidateForm.doi || ''}
                            onChange={e => setCandidateForm(f => f ? { ...f, doi: e.target.value } : f)}
                          />
                          <Input
                            label={candidateForm.pub_type === 'preprints' ? 'Published DOI' : 'Preprint DOI'}
                            value={candidateForm.pub_type === 'preprints' ? (candidateForm.published_doi || '') : (candidateForm.preprint_doi || '')}
                            onChange={e => setCandidateForm(f => f
                              ? f.pub_type === 'preprints'
                                ? { ...f, published_doi: e.target.value }
                                : { ...f, preprint_doi: e.target.value }
                              : f)}
                          />
                          <Textarea
                            label="Authors (one per line)"
                            value={candidateForm.authors.join('\n')}
                            onChange={e => setCandidateForm(f => f ? { ...f, authors: e.target.value.split('\n') } : f)}
                            rows={3}
                          />
                          <div className="flex gap-2 justify-end">
                            <Button variant="secondary" size="sm" onClick={() => { setEditingCandidate(null); setCandidateForm(null) }}>Cancel</Button>
                            <Button size="sm" onClick={saveCandidateEdit}>Save</Button>
                          </div>
                        </div>
                      )}
                    </div>

                    {/* Action buttons */}
                    <div className="flex items-center justify-between pt-2 border-t">
                      <button
                        className="text-xs text-primary-600 hover:underline"
                        onClick={() => { setIgnoredOpen(true); loadIgnoredList() }}
                      >
                        Manage ignored
                      </button>
                      <div className="flex gap-2">
                        {hasWarning ? (
                          <>
                            <Button variant="ghost" size="sm" onClick={handleSyncAdd} loading={syncSaving} disabled={syncSaving}>
                              Add
                            </Button>
                            <Button variant="secondary" size="sm" className="!text-amber-700 !border-amber-300 hover:!bg-amber-50" onClick={handleSyncIgnore} disabled={syncSaving}>
                              Ignore
                            </Button>
                            <Button size="sm" onClick={handleSyncSkip} disabled={syncSaving}>
                              {syncIndex < syncResult.candidates.length - 1 ? 'Skip & Next' : 'Skip & Finish'}
                            </Button>
                          </>
                        ) : (
                          <>
                            <Button variant="ghost" size="sm" onClick={handleSyncSkip} disabled={syncSaving}>
                              Skip
                            </Button>
                            <Button variant="secondary" size="sm" className="!text-amber-700 !border-amber-300 hover:!bg-amber-50" onClick={handleSyncIgnore} disabled={syncSaving}>
                              Ignore
                            </Button>
                            <Button size="sm" onClick={handleSyncAdd} loading={syncSaving} disabled={syncSaving}>
                              {syncIndex < syncResult.candidates.length - 1 ? 'Add & Next' : 'Add & Finish'}
                            </Button>
                          </>
                        )}
                      </div>
                    </div>
                  </>
                )
              })()
            )}
          </div>
        )}
      </Modal>

      {/* Manage Ignored Candidates Modal */}
      <Modal
        open={ignoredOpen}
        onClose={() => setIgnoredOpen(false)}
        title="Ignored Publications"
      >
        {ignoredLoading ? (
          <div className="py-8 flex justify-center"><Spinner /></div>
        ) : ignoredList.length === 0 ? (
          <div className="py-8 text-center text-gray-400 text-sm">No ignored publications.</div>
        ) : (
          <div className="max-h-[50vh] overflow-y-auto divide-y divide-gray-100">
            {ignoredList.map(row => (
              <div key={row.id} className="px-4 py-3 flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <p className="text-sm text-gray-900 font-medium truncate">{row.title_display || '(no title)'}</p>
                  <div className="flex items-center gap-2 text-xs text-gray-400 mt-0.5">
                    {row.year && <span>{row.year}</span>}
                    <Badge color={SOURCE_COLOR[row.source] || 'gray'}>{row.source}</Badge>
                    {row.ignored_at && <span>{new Date(row.ignored_at).toLocaleDateString()}</span>}
                  </div>
                </div>
                <Button variant="ghost" size="sm" onClick={() => handleUnignore(row.id)} className="flex-shrink-0">
                  Un-ignore
                </Button>
              </div>
            ))}
          </div>
        )}
      </Modal>
      {/* Complete Missing Fields Modal */}
      <Modal
        open={completeOpen}
        onClose={() => { if (!completeLoading && !completeSaving) setCompleteOpen(false) }}
        title="Complete Missing Fields"
      >
        {completeLoading && (
          <div className="py-12 flex flex-col items-center gap-4 text-gray-500">
            <Spinner />
            <p className="text-sm">Fetching metadata from Crossref...</p>
          </div>
        )}

        {!completeLoading && completeDiffs.length === 0 && (
          <div className="py-8 text-center">
            <p className="text-sm text-gray-500">
              No differences found.
              {completeStats.skipped > 0 && ` ${completeStats.skipped} work(s) skipped (no DOI).`}
              {completeStats.errors > 0 && ` ${completeStats.errors} error(s).`}
            </p>
            <Button variant="secondary" className="mt-4" onClick={() => setCompleteOpen(false)}>Close</Button>
          </div>
        )}

        {!completeLoading && completeDiffs.length > 0 && (() => {
          const diff = completeDiffs[completeIndex]
          const accepted = acceptedFields.get(diff.work_id) || new Set<string>()
          const allKeys: string[] = [
            ...diff.field_diffs.map(fd => fd.field),
            ...diff.author_diffs.map(ad => `author_rename_${ad.author_order}`),
            ...(diff.proposed_authors.length > 0 ? ['proposed_authors'] : []),
            ...(diff.additional_authors.length > 0 ? ['additional_authors'] : []),
          ]
          const allChecked = allKeys.length > 0 && allKeys.every(k => accepted.has(k))
          const isLast = completeIndex === completeDiffs.length - 1

          return (
            <div className="space-y-4">
              {/* Header with navigation */}
              <div className="flex items-center justify-between">
                <button
                  className="text-gray-400 hover:text-gray-600 disabled:opacity-30"
                  disabled={completeIndex === 0}
                  onClick={() => setCompleteIndex(i => i - 1)}
                >&#9664;</button>
                <span className="text-sm text-gray-500 font-medium">{completeIndex + 1} of {completeDiffs.length}</span>
                <button
                  className="text-gray-400 hover:text-gray-600 disabled:opacity-30"
                  disabled={isLast}
                  onClick={() => setCompleteIndex(i => i + 1)}
                >&#9654;</button>
              </div>

              {/* Citation preview */}
              {(() => {
                const currentWork = data.find(w => w.id === diff.work_id)
                if (!currentWork) return null
                const previewSpans = buildCitationPreview(currentWork, diff, accepted)
                return (
                  <div className="text-xs text-gray-700 bg-gray-50 border border-gray-200 rounded p-3 leading-relaxed">
                    {previewSpans.map((s, i) => (
                      <span
                        key={i}
                        className={
                          s.color === 'green' ? 'bg-green-100 text-green-800 rounded px-0.5' :
                          s.color === 'red' ? 'bg-red-100 text-red-800 rounded px-0.5' :
                          ''
                        }
                      >{s.text}</span>
                    ))}
                  </div>
                )
              })()}

              {completeStats.skipped > 0 && completeIndex === 0 && (
                <p className="text-xs text-amber-600">{completeStats.skipped} work(s) skipped (no DOI){completeStats.errors > 0 ? `, ${completeStats.errors} error(s)` : ''}</p>
              )}

              {/* Select all / Deselect all */}
              <label className="flex items-center gap-2 cursor-pointer text-sm text-gray-600">
                <input
                  type="checkbox"
                  className="rounded border-gray-300 text-primary-600 focus:ring-primary-500"
                  checked={allChecked}
                  onChange={(e) => toggleAllCompleteFields(diff.work_id, allKeys, e.target.checked)}
                />
                {allChecked ? 'Deselect all' : 'Select all'}
              </label>

              {/* Field diffs */}
              {diff.field_diffs.length > 0 && (
                <div className="space-y-2">
                  {diff.field_diffs.map(fd => {
                    const isConflict = !!fd.current
                    return (
                      <label
                        key={fd.field}
                        className={`flex items-start gap-2 p-2 rounded border cursor-pointer ${
                          isConflict ? 'border-amber-200 bg-amber-50' : 'border-gray-200 bg-gray-50'
                        }`}
                      >
                        <input
                          type="checkbox"
                          className="mt-0.5 rounded border-gray-300 text-primary-600 focus:ring-primary-500"
                          checked={accepted.has(fd.field)}
                          onChange={() => toggleCompleteField(diff.work_id, fd.field)}
                        />
                        <div className="flex-1 min-w-0 text-sm">
                          <span className="font-medium text-gray-700 uppercase text-xs">{fd.field}</span>
                          {isConflict && <Badge color="yellow" className="ml-2 text-[10px]">differs</Badge>}
                          <div className="mt-0.5">
                            <span className="text-gray-400 italic">{fd.current || '(empty)'}</span>
                            <span className="mx-2 text-gray-300">&rarr;</span>
                            <span className="text-green-700">{fd.proposed}</span>
                          </div>
                        </div>
                      </label>
                    )
                  })}
                </div>
              )}

              {/* Author diffs */}
              {diff.author_diffs.length > 0 && (
                <div className="space-y-2">
                  <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide">Author Name Updates</p>
                  {diff.author_diffs.map(ad => (
                    <label
                      key={ad.author_order}
                      className="flex items-start gap-2 p-2 rounded border border-gray-200 bg-gray-50 cursor-pointer"
                    >
                      <input
                        type="checkbox"
                        className="mt-0.5 rounded border-gray-300 text-primary-600 focus:ring-primary-500"
                        checked={accepted.has(`author_rename_${ad.author_order}`)}
                        onChange={() => toggleCompleteField(diff.work_id, `author_rename_${ad.author_order}`)}
                      />
                      <div className="text-sm">
                        <span className="text-gray-400">{ad.current_name}</span>
                        <span className="mx-2 text-gray-300">&rarr;</span>
                        <span className="text-green-700">{ad.proposed_name}</span>
                      </div>
                    </label>
                  ))}
                </div>
              )}

              {/* Proposed authors (work had 0) */}
              {diff.proposed_authors.length > 0 && (
                <div className="space-y-2">
                  <label className="flex items-start gap-2 p-2 rounded border border-gray-200 bg-gray-50 cursor-pointer">
                    <input
                      type="checkbox"
                      className="mt-0.5 rounded border-gray-300 text-primary-600 focus:ring-primary-500"
                      checked={accepted.has('proposed_authors')}
                      onChange={() => toggleCompleteField(diff.work_id, 'proposed_authors')}
                    />
                    <div className="text-sm">
                      <span className="font-medium text-gray-700">Add {diff.proposed_authors.length} author(s)</span>
                      <p className="text-xs text-gray-500 mt-0.5">
                        {diff.proposed_authors.map(a => a.author_name).join(', ')}
                      </p>
                    </div>
                  </label>
                </div>
              )}

              {/* Additional authors */}
              {diff.additional_authors.length > 0 && (
                <div className="space-y-2">
                  <label className="flex items-start gap-2 p-2 rounded border border-gray-200 bg-gray-50 cursor-pointer">
                    <input
                      type="checkbox"
                      className="mt-0.5 rounded border-gray-300 text-primary-600 focus:ring-primary-500"
                      checked={accepted.has('additional_authors')}
                      onChange={() => toggleCompleteField(diff.work_id, 'additional_authors')}
                    />
                    <div className="text-sm">
                      <span className="font-medium text-gray-700">Add {diff.additional_authors.length} additional author(s)</span>
                      <p className="text-xs text-gray-500 mt-0.5">
                        {diff.additional_authors.map(a => a.author_name).join(', ')}
                      </p>
                    </div>
                  </label>
                </div>
              )}

              {/* Footer */}
              <div className="flex items-center justify-between pt-3 border-t">
                <Button variant="ghost" size="sm" onClick={() => setCompleteOpen(false)}>Close</Button>
                <div className="flex gap-2">
                  <Button variant="secondary" size="sm" onClick={skipCurrentCompleteWork}>Skip</Button>
                  <Button
                    size="sm"
                    onClick={saveCurrentCompleteWork}
                    loading={completeSaving}
                  >
                    {isLast ? 'Accept & Finish' : 'Accept & Next'}
                  </Button>
                </div>
              </div>
            </div>
          )
        })()}
      </Modal>

      </>)}
    </div>
  )
}

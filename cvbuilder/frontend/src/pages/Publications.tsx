import { useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '../lib/api'
import type { Work, WorkAuthor, DOILookupResponse, Profile, PublicationCandidate, SyncCheckResponse } from '../lib/api'
import { Button, Card, Input, Modal, PageHeader, Badge, Spinner, Textarea, Select, Checkbox } from '../components/ui'
import { Plus, Search, Trash2, Edit2, Copy, ExternalLink, GripVertical, RefreshCw, Pencil, AlertTriangle, Link2 } from 'lucide-react'

type AuthorRow = {
  author_name: string
  student: boolean
  corresponding: boolean
  cofirst: boolean
  cosenior: boolean
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
    authorRows: [{ author_name: '', student: false, corresponding: false, cofirst: false, cosenior: false }],
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
        }))
      : [{ author_name: '', student: false, corresponding: false, cofirst: false, cosenior: false }],
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
  const [selectedIndices, setSelectedIndices] = useState<Set<number>>(new Set())
  const [addingSelected, setAddingSelected] = useState(false)
  const [editingCandidate, setEditingCandidate] = useState<number | null>(null)
  const [candidateForm, setCandidateForm] = useState<PublicationCandidate | null>(null)

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
          ? d.authors.map(n => ({ author_name: n, student: false, corresponding: false, cofirst: false, cosenior: false }))
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
    setSelectedIndices(new Set())
    setEditingCandidate(null)
    setCandidateForm(null)
    try {
      const res = await api.get<SyncCheckResponse>('/works/sync-check')
      setSyncResult(res.data)
      setSelectedIndices(new Set(
        res.data.candidates
          .map((c, i) => c.match_warning ? null : i)
          .filter((i): i is number => i !== null)
      ))
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      setSyncError(msg || 'Failed to fetch publications. Check your profile name/ORCID.')
    } finally {
      setSyncLoading(false)
    }
  }

  async function handleAddSelected() {
    if (!syncResult || selectedIndices.size === 0) return
    setAddingSelected(true)
    try {
      const pubs = Array.from(selectedIndices).map(i => syncResult.candidates[i])
      await api.post('/works/sync-add', { publications: pubs })
      qc.invalidateQueries({ queryKey: ['works'] })
      setSyncOpen(false)
    } catch {
      alert('Failed to add publications.')
    } finally {
      setAddingSelected(false)
    }
  }

  function toggleCandidate(idx: number) {
    setSelectedIndices(prev => {
      const next = new Set(prev)
      if (next.has(idx)) next.delete(idx)
      else next.add(idx)
      return next
    })
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
            <div key={i} className="flex items-center gap-2">
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
          ))}
        </div>
        <button
          type="button"
          onClick={() => setForm(f => ({ ...f, authorRows: [...f.authorRows, { author_name: '', student: false, corresponding: false, cofirst: false, cosenior: false }] }))}
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
        <Button variant="secondary" onClick={() => { setCreating(false); setEditing(null) }}>Cancel</Button>
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
        </div>
      </div>

      {isLoading ? <Spinner /> : (
        <Card>
          <div className="divide-y divide-gray-100">
            {data.map(work => (
              <div key={work.id} className="px-5 py-4 hover:bg-gray-50 flex items-start justify-between gap-4">
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
      <Modal open={!!editing} onClose={() => setEditing(null)} title="Edit Scholarly Work">
        {WorkForm}
      </Modal>

      {/* Find New Publications Modal */}
      <Modal
        open={syncOpen}
        onClose={() => { if (!syncLoading && !addingSelected) setSyncOpen(false) }}
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
            <div className="text-sm text-gray-600">
              Found <strong>{syncResult.candidates.length}</strong> new publication{syncResult.candidates.length !== 1 ? 's' : ''}{' '}
              {syncResult.searched.length > 0 && <>across <em>{syncResult.searched.join(', ')}</em></>}
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
              </div>
            ) : (
              <>
                <div className="flex gap-3 text-xs">
                  <button
                    className="text-primary-600 hover:underline"
                    onClick={() => setSelectedIndices(new Set(syncResult.candidates.map((_, i) => i)))}
                  >
                    Select all
                  </button>
                  <button
                    className="text-gray-500 hover:underline"
                    onClick={() => setSelectedIndices(new Set())}
                  >
                    Clear all
                  </button>
                </div>

                <div className="max-h-[50vh] overflow-y-auto divide-y divide-gray-100 border border-gray-200 rounded-lg">
                  {syncResult.candidates.map((c, idx) => (
                    <div key={idx}>
                      <div className={`px-4 py-3 flex items-start gap-3 ${selectedIndices.has(idx) ? 'bg-white' : 'bg-gray-50 opacity-60'}`}>
                        <input
                          type="checkbox"
                          className="mt-1 rounded flex-shrink-0"
                          checked={selectedIndices.has(idx)}
                          onChange={() => toggleCandidate(idx)}
                        />
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
                          onClick={() => editingCandidate === idx ? (setEditingCandidate(null), setCandidateForm(null)) : openCandidateEdit(idx)}
                        >
                          <Pencil size={13} />
                        </button>
                      </div>

                      {/* Inline edit panel */}
                      {editingCandidate === idx && candidateForm && (
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
                  ))}
                </div>
              </>
            )}

            <div className="flex items-center justify-between pt-2 border-t">
              <span className="text-xs text-gray-500">
                {selectedIndices.size} of {syncResult.candidates.length} selected
              </span>
              <div className="flex gap-2">
                <Button variant="secondary" onClick={() => setSyncOpen(false)} disabled={addingSelected}>
                  Cancel
                </Button>
                <Button
                  onClick={handleAddSelected}
                  loading={addingSelected}
                  disabled={selectedIndices.size === 0}
                >
                  Add Selected ({selectedIndices.size})
                </Button>
              </div>
            </div>
          </div>
        )}
      </Modal>
    </div>
  )
}

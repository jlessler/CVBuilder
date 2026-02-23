import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '../lib/api'
import type { Publication, DOILookupResponse, Profile, PublicationCandidate, SyncCheckResponse } from '../lib/api'
import { Button, Card, Input, Modal, PageHeader, Badge, Spinner, Textarea, Select, Checkbox } from '../components/ui'
import { Plus, Search, Trash2, Edit2, ExternalLink, GripVertical, RefreshCw, Pencil } from 'lucide-react'

type AuthorRow = { author_name: string; student: boolean }

const PUB_TYPES = [
  { value: 'papers', label: 'Papers' },
  { value: 'preprints', label: 'Preprints' },
  { value: 'chapters', label: 'Chapters' },
  { value: 'letters', label: 'Letters' },
  { value: 'scimeetings', label: 'Scientific Meetings' },
]

const TYPE_COLOR: Record<string, string> = {
  papers: 'blue', preprints: 'cyan', chapters: 'purple',
  letters: 'orange', scimeetings: 'green',
}

const SOURCE_COLOR: Record<string, string> = {
  pubmed: 'green', crossref: 'blue', orcid: 'orange', semanticscholar: 'purple',
}

function blankPub(): Omit<Publication, 'id' | 'authors'> & { authorRows: AuthorRow[] } {
  return {
    type: 'papers', title: '', year: '', journal: '', volume: '', issue: '',
    pages: '', doi: '', corr: false, cofirsts: 0, coseniors: 0, select_flag: false,
    conference: '', pres_type: '', publisher: '', authorRows: [{ author_name: '', student: false }],
  }
}

export function Publications() {
  const qc = useQueryClient()
  const [typeFilter, setTypeFilter] = useState('')
  const [keyword, setKeyword] = useState('')
  const [editing, setEditing] = useState<Publication | null>(null)
  const [creating, setCreating] = useState(false)
  const [form, setForm] = useState(blankPub())
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

  function renderAuthors(authors: Publication['authors'], max = 5) {
    const visible = authors.slice(0, max)
    return (
      <>
        {visible.map((a, i) => (
          <span key={a.id}>
            {i > 0 && ', '}
            {matchesSelf(a.author_name) ? <strong>{a.author_name}</strong> : a.author_name}
            {a.student && <sup>†</sup>}
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

  const { data = [], isLoading } = useQuery<Publication[]>({
    queryKey: ['publications', typeFilter, keyword],
    queryFn: () => api.get('/publications', {
      params: { type: typeFilter || undefined, keyword: keyword || undefined, limit: 2000 }
    }).then(r => r.data),
  })

  function toApiAuthors(rows: AuthorRow[]) {
    return rows
      .filter(r => r.author_name.trim())
      .map((r, i) => ({ author_name: r.author_name.trim(), author_order: i, student: r.student }))
  }

  const createMut = useMutation({
    mutationFn: (d: typeof form) => api.post('/publications', {
      ...d, authors: toApiAuthors(d.authorRows), authorRows: undefined,
    }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['publications'] }); setCreating(false); setForm(blankPub()) },
  })

  const updateMut = useMutation({
    mutationFn: (d: typeof form) => api.put(`/publications/${editing!.id}`, {
      ...d, authors: toApiAuthors(d.authorRows), authorRows: undefined,
    }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['publications'] }); setEditing(null) },
  })

  const deleteMut = useMutation({
    mutationFn: (id: number) => api.delete(`/publications/${id}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['publications'] }),
  })

  function openCreate() { setForm(blankPub()); setCreating(true) }
  function openEdit(pub: Publication) {
    setEditing(pub)
    setForm({
      ...pub,
      authorRows: pub.authors.length
        ? pub.authors.map(a => ({ author_name: a.author_name, student: a.student }))
        : [{ author_name: '', student: false }],
    } as typeof form)
  }

  async function lookupDoi() {
    if (!doiInput) return
    setDoiLoading(true)
    try {
      const res = await api.post<DOILookupResponse>('/publications/doi-lookup', { doi: doiInput })
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
          ? d.authors.map(n => ({ author_name: n, student: false }))
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
      const res = await api.get<SyncCheckResponse>('/publications/sync-check')
      setSyncResult(res.data)
      // Pre-select all candidates
      setSelectedIndices(new Set(res.data.candidates.map((_, i) => i)))
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
      await api.post('/publications/sync-add', { publications: pubs })
      qc.invalidateQueries({ queryKey: ['publications'] })
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

  const PubForm = (
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
          options={PUB_TYPES}
          value={form.type}
          onChange={e => setForm(f => ({ ...f, type: e.target.value }))}
        />
        <Input label="Year" value={form.year || ''} onChange={e => setForm(f => ({ ...f, year: e.target.value }))} />
      </div>

      <Textarea
        label="Title"
        value={form.title || ''}
        onChange={e => setForm(f => ({ ...f, title: e.target.value }))}
        rows={2}
      />

      {/* Authors */}
      <div>
        <div className="flex items-center justify-between mb-1">
          <label className="block text-sm font-medium text-gray-700">Authors</label>
          <span className="text-xs text-gray-400">Check &dagger; to mark student/trainee authors</span>
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
              <label className="flex items-center gap-1 text-xs text-gray-500 whitespace-nowrap flex-shrink-0 cursor-pointer">
                <input
                  type="checkbox"
                  checked={row.student}
                  onChange={e => setForm(f => {
                    const rows = [...f.authorRows]
                    rows[i] = { ...rows[i], student: e.target.checked }
                    return { ...f, authorRows: rows }
                  })}
                  className="rounded"
                />
                <sup>&dagger;</sup>
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
          onClick={() => setForm(f => ({ ...f, authorRows: [...f.authorRows, { author_name: '', student: false }] }))}
          className="mt-1.5 text-xs text-primary-600 hover:text-primary-800 flex items-center gap-1"
        >
          <Plus size={12} /> Add author
        </button>
      </div>

      <Input label="Journal / Conference" value={form.journal || ''} onChange={e => setForm(f => ({ ...f, journal: e.target.value }))} />

      <div className="grid grid-cols-3 gap-3">
        <Input label="Volume" value={form.volume || ''} onChange={e => setForm(f => ({ ...f, volume: e.target.value }))} />
        <Input label="Issue" value={form.issue || ''} onChange={e => setForm(f => ({ ...f, issue: e.target.value }))} />
        <Input label="Pages" value={form.pages || ''} onChange={e => setForm(f => ({ ...f, pages: e.target.value }))} />
      </div>

      <Input label="DOI" value={form.doi || ''} onChange={e => setForm(f => ({ ...f, doi: e.target.value }))} />

      <div className="grid grid-cols-3 gap-3">
        <Input label="Co-first authors" type="number" value={form.cofirsts} onChange={e => setForm(f => ({ ...f, cofirsts: parseInt(e.target.value) || 0 }))} />
        <Input label="Co-senior authors" type="number" value={form.coseniors} onChange={e => setForm(f => ({ ...f, coseniors: parseInt(e.target.value) || 0 }))} />
      </div>

      <div className="flex gap-4">
        <Checkbox label="Corresponding author" checked={form.corr} onChange={e => setForm(f => ({ ...f, corr: e.target.checked }))} />
        <Checkbox label="Selected/highlighted" checked={form.select_flag} onChange={e => setForm(f => ({ ...f, select_flag: e.target.checked }))} />
      </div>

      <div className="flex gap-2 justify-end pt-2 border-t">
        <Button variant="secondary" onClick={() => { setCreating(false); setEditing(null) }}>Cancel</Button>
        <Button
          onClick={() => creating ? createMut.mutate(form) : updateMut.mutate(form)}
          loading={createMut.isPending || updateMut.isPending}
        >
          {creating ? 'Add Publication' : 'Save Changes'}
        </Button>
      </div>
    </div>
  )

  return (
    <div className="p-8">
      <PageHeader
        title="Publications"
        subtitle={`${data.length} total`}
        actions={
          <div className="flex gap-2">
            <Button variant="secondary" onClick={handleFindNew}><RefreshCw size={15} /> Find New</Button>
            <Button onClick={openCreate}><Plus size={16} /> Add Publication</Button>
          </div>
        }
      />

      {/* Filters */}
      <div className="flex gap-3 mb-6">
        <div className="relative flex-1 max-w-sm">
          <Search size={16} className="absolute left-3 top-2.5 text-gray-400" />
          <input
            className="w-full pl-9 pr-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
            placeholder="Search title or journal..."
            value={keyword}
            onChange={e => setKeyword(e.target.value)}
          />
        </div>
        <div className="flex gap-1">
          <button
            onClick={() => setTypeFilter('')}
            className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${!typeFilter ? 'bg-primary-600 text-white' : 'bg-white border border-gray-300 text-gray-600 hover:bg-gray-50'}`}
          >All</button>
          {PUB_TYPES.map(pt => (
            <button
              key={pt.value}
              onClick={() => setTypeFilter(pt.value)}
              className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${typeFilter === pt.value ? 'bg-primary-600 text-white' : 'bg-white border border-gray-300 text-gray-600 hover:bg-gray-50'}`}
            >{pt.label}</button>
          ))}
        </div>
      </div>

      {isLoading ? <Spinner /> : (
        <Card>
          <div className="divide-y divide-gray-100">
            {data.map(pub => (
              <div key={pub.id} className="px-5 py-4 hover:bg-gray-50 flex items-start justify-between gap-4">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <Badge color={TYPE_COLOR[pub.type] || 'gray'}>{pub.type}</Badge>
                    {pub.select_flag && <Badge color="yellow">Selected</Badge>}
                    {pub.corr && <Badge color="green">Corr.</Badge>}
                    <span className="text-xs text-gray-400">{pub.year}</span>
                  </div>
                  <p className="font-medium text-gray-900 text-sm truncate">{pub.title}</p>
                  <p className="text-xs text-gray-500 mt-0.5">
                    {renderAuthors(pub.authors)}
                  </p>
                  {pub.journal && (
                    <p className="text-xs text-gray-400 mt-0.5 italic">{pub.journal}
                      {pub.volume ? ` ${pub.volume}` : ''}
                      {pub.issue ? `(${pub.issue})` : ''}
                      {pub.pages ? `: ${pub.pages}` : ''}
                    </p>
                  )}
                  {pub.doi && (
                    <a
                      href={`https://doi.org/${pub.doi}`} target="_blank" rel="noreferrer"
                      className="inline-flex items-center gap-1 text-xs text-blue-600 hover:underline mt-0.5"
                    >
                      <ExternalLink size={10} /> doi:{pub.doi}
                    </a>
                  )}
                </div>
                <div className="flex items-center gap-1 flex-shrink-0">
                  <Button variant="ghost" size="sm" onClick={() => openEdit(pub)}>
                    <Edit2 size={14} />
                  </Button>
                  <Button variant="ghost" size="sm" onClick={() => {
                    if (confirm('Delete this publication?')) deleteMut.mutate(pub.id)
                  }}>
                    <Trash2 size={14} className="text-red-500" />
                  </Button>
                </div>
              </div>
            ))}
            {data.length === 0 && (
              <div className="py-16 text-center text-gray-400 text-sm">
                No publications found.
              </div>
            )}
          </div>
        </Card>
      )}

      <Modal open={creating} onClose={() => setCreating(false)} title="Add Publication">
        {PubForm}
      </Modal>
      <Modal open={!!editing} onClose={() => setEditing(null)} title="Edit Publication">
        {PubForm}
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
            {/* Summary */}
            <div className="text-sm text-gray-600">
              Found <strong>{syncResult.candidates.length}</strong> new publication{syncResult.candidates.length !== 1 ? 's' : ''}{' '}
              {syncResult.searched.length > 0 && <>across <em>{syncResult.searched.join(', ')}</em></>}
            </div>

            {/* Source errors */}
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
                {/* Select all / clear all */}
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

                {/* Candidate list */}
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
                            {c.year && <span className="text-xs text-gray-400">{c.year}</span>}
                          </div>
                          <p className="font-medium text-gray-900 text-sm">{c.title}</p>
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
                              options={PUB_TYPES}
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

            {/* Footer */}
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

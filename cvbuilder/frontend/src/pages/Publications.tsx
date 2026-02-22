import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '../lib/api'
import type { Publication, DOILookupResponse } from '../lib/api'
import { Button, Card, Input, Modal, PageHeader, Badge, Spinner, Textarea, Select, Checkbox } from '../components/ui'
import { Plus, Search, Trash2, Edit2, ExternalLink } from 'lucide-react'

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

function blankPub(): Omit<Publication, 'id' | 'authors'> & { authorsText: string } {
  return {
    type: 'papers', title: '', year: '', journal: '', volume: '', issue: '',
    pages: '', doi: '', corr: false, cofirsts: 0, coseniors: 0, select_flag: false,
    conference: '', pres_type: '', publisher: '', authorsText: '',
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

  const { data = [], isLoading } = useQuery<Publication[]>({
    queryKey: ['publications', typeFilter, keyword],
    queryFn: () => api.get('/publications', {
      params: { type: typeFilter || undefined, keyword: keyword || undefined, limit: 2000 }
    }).then(r => r.data),
  })

  const createMut = useMutation({
    mutationFn: (d: typeof form) => api.post('/publications', {
      ...d,
      authors: d.authorsText.split('\n').filter(Boolean).map((n, i) => ({ author_name: n.trim(), author_order: i })),
      authorsText: undefined,
    }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['publications'] }); setCreating(false); setForm(blankPub()) },
  })

  const updateMut = useMutation({
    mutationFn: (d: typeof form) => api.put(`/publications/${editing!.id}`, {
      ...d,
      authors: d.authorsText.split('\n').filter(Boolean).map((n, i) => ({ author_name: n.trim(), author_order: i })),
      authorsText: undefined,
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
      authorsText: pub.authors.map(a => a.author_name).join('\n'),
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
        authorsText: d.authors.join('\n') || f.authorsText,
      }))
    } catch {
      alert('DOI not found or lookup failed.')
    } finally {
      setDoiLoading(false)
    }
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

      <Textarea
        label="Authors (one per line)"
        value={form.authorsText || ''}
        onChange={e => setForm(f => ({ ...f, authorsText: e.target.value }))}
        rows={4}
        placeholder="Smith J&#10;Jones A&#10;Doe B"
      />

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
        actions={<Button onClick={openCreate}><Plus size={16} /> Add Publication</Button>}
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
                    {pub.authors.slice(0, 5).map(a => a.author_name).join(', ')}
                    {pub.authors.length > 5 ? ` +${pub.authors.length - 5} more` : ''}
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
    </div>
  )
}

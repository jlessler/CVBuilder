import { useState, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '../lib/api'
import type { Work } from '../lib/api'
import { Button, Card, Input, PageHeader, Spinner } from '../components/ui'
import { Plus, Trash2, Download, Save, ChevronDown, ChevronRight } from 'lucide-react'

interface CitationData {
  yearly_counts: Record<string, number>
  total_citations: number
  h_index: number
  i10_index: number
  source: string
  retrieved_at: string
}

interface CVItem {
  id: number
  section: string
  data: CitationData
  sort_order: number
}

interface FetchResult extends CitationData {
  works_updated: number
  works_matched: number
  works_queried: number
}

export function Citations() {
  const qc = useQueryClient()

  // Load existing citation_metrics CVItem (aggregate data)
  const { data: items, isLoading: loadingItems } = useQuery<CVItem[]>({
    queryKey: ['cv', 'citation_metrics'],
    queryFn: () => api.get('/cv/citation_metrics').then(r => r.data),
  })

  // Load works that have citation data
  const { data: allWorks, isLoading: loadingWorks } = useQuery<Work[]>({
    queryKey: ['works'],
    queryFn: () => api.get('/works').then(r => r.data),
  })

  const existing = items?.[0] ?? null
  const worksWithCitations = (allWorks || []).filter(
    w => w.data && typeof w.data.cited_by_count === 'number'
  )

  const [form, setForm] = useState<CitationData>({
    yearly_counts: {},
    total_citations: 0,
    h_index: 0,
    i10_index: 0,
    source: '',
    retrieved_at: '',
  })

  const [yearRows, setYearRows] = useState<{ year: string; count: number }[]>([])
  const [fetchError, setFetchError] = useState('')
  const [fetchResult, setFetchResult] = useState<FetchResult | null>(null)
  const [fetching, setFetching] = useState(false)
  const [showWorks, setShowWorks] = useState(false)

  useEffect(() => {
    if (existing?.data) {
      const d = existing.data
      setForm({
        yearly_counts: d.yearly_counts || {},
        total_citations: d.total_citations || 0,
        h_index: d.h_index || 0,
        i10_index: d.i10_index || 0,
        source: d.source || '',
        retrieved_at: d.retrieved_at || '',
      })
      const rows = Object.entries(d.yearly_counts || {})
        .map(([year, count]) => ({ year, count: count as number }))
        .sort((a, b) => a.year.localeCompare(b.year))
      setYearRows(rows)
    }
  }, [existing])

  const saveMut = useMutation({
    mutationFn: () => {
      const counts: Record<string, number> = {}
      for (const r of yearRows) {
        if (r.year) counts[r.year] = r.count
      }
      const data = { ...form, yearly_counts: counts }
      if (existing) {
        return api.put(`/cv/${existing.id}`, { data })
      }
      return api.post('/cv', { section: 'citation_metrics', data, sort_order: 0 })
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ['cv', 'citation_metrics'] }),
  })

  async function handleFetch() {
    setFetchError('')
    setFetchResult(null)
    setFetching(true)
    try {
      const { data } = await api.post('/citations/fetch', null, { timeout: 120000 })
      setFetchResult(data)
      setForm({
        yearly_counts: data.yearly_counts || {},
        total_citations: data.total_citations || 0,
        h_index: data.h_index || 0,
        i10_index: data.i10_index || 0,
        source: data.source || 'OpenAlex',
        retrieved_at: data.retrieved_at || '',
      })
      const rows = Object.entries(data.yearly_counts || {})
        .map(([year, count]) => ({ year, count: count as number }))
        .sort((a, b) => a.year.localeCompare(b.year))
      setYearRows(rows)
      // Refresh works data too (per-work citations updated)
      qc.invalidateQueries({ queryKey: ['works'] })
      qc.invalidateQueries({ queryKey: ['cv', 'citation_metrics'] })
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
        || 'Fetch failed'
      setFetchError(msg)
    } finally {
      setFetching(false)
    }
  }

  function addYearRow() {
    const maxYear = yearRows.length > 0
      ? Math.max(...yearRows.map(r => parseInt(r.year) || 0))
      : new Date().getFullYear() - 1
    setYearRows([...yearRows, { year: String(maxYear + 1), count: 0 }])
  }

  function removeYearRow(idx: number) {
    setYearRows(yearRows.filter((_, i) => i !== idx))
  }

  function updateYearRow(idx: number, field: 'year' | 'count', value: string) {
    setYearRows(yearRows.map((r, i) =>
      i === idx ? { ...r, [field]: field === 'count' ? parseInt(value) || 0 : value } : r
    ))
  }

  if (loadingItems || loadingWorks) return <div className="p-8"><Spinner /></div>

  const maxCount = Math.max(...yearRows.map(r => r.count), 1)

  // Sort works by citation count descending for the per-work table
  const sortedWorks = [...worksWithCitations].sort(
    (a, b) => ((b.data?.cited_by_count as number) || 0) - ((a.data?.cited_by_count as number) || 0)
  )

  return (
    <div className="p-8">
      <PageHeader
        title="Citation Metrics"
        subtitle="Track your citation counts, h-index, and related metrics"
        actions={
          <Button onClick={() => saveMut.mutate()} loading={saveMut.isPending}>
            <Save size={16} /> Save
          </Button>
        }
      />

      {saveMut.isSuccess && (
        <div className="mb-4 px-4 py-2 bg-green-50 text-green-800 rounded-lg text-sm border border-green-200">
          Saved successfully.
        </div>
      )}

      {fetchError && (
        <div className="mb-4 px-4 py-2 bg-red-50 text-red-800 rounded-lg text-sm border border-red-200">
          {fetchError}
        </div>
      )}

      {fetchResult && (
        <div className="mb-4 px-4 py-2 bg-blue-50 text-blue-800 rounded-lg text-sm border border-blue-200">
          Updated {fetchResult.works_updated} works ({fetchResult.works_matched} matched
          out of {fetchResult.works_queried} queried). Data saved automatically.
        </div>
      )}

      {/* Auto-fetch */}
      <Card className="p-6 mb-6">
        <h3 className="font-semibold text-gray-900 mb-3">Fetch citation data</h3>
        <p className="text-sm text-gray-500 mb-4">
          Queries OpenAlex for citation counts on all your works that have DOIs.
          Updates per-work citation data and computes aggregate metrics.
        </p>
        <Button
          variant="secondary"
          onClick={handleFetch}
          loading={fetching}
        >
          <Download size={16} /> Fetch from OpenAlex
        </Button>
      </Card>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
        {/* Summary stats */}
        <Card className="p-6 space-y-4">
          <h3 className="font-semibold text-gray-900">Summary</h3>
          <Input
            label="Total Citations"
            type="number"
            value={String(form.total_citations)}
            onChange={e => setForm(f => ({ ...f, total_citations: parseInt(e.target.value) || 0 }))}
          />
          <Input
            label="h-index"
            type="number"
            value={String(form.h_index)}
            onChange={e => setForm(f => ({ ...f, h_index: parseInt(e.target.value) || 0 }))}
          />
          <Input
            label="i10-index"
            type="number"
            value={String(form.i10_index)}
            onChange={e => setForm(f => ({ ...f, i10_index: parseInt(e.target.value) || 0 }))}
          />
          <Input
            label="Source"
            placeholder="e.g. OpenAlex, Google Scholar"
            value={form.source}
            onChange={e => setForm(f => ({ ...f, source: e.target.value }))}
          />
          <Input
            label="Retrieved Date"
            type="date"
            value={form.retrieved_at}
            onChange={e => setForm(f => ({ ...f, retrieved_at: e.target.value }))}
          />
        </Card>

        {/* Yearly counts */}
        <Card className="p-6">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="font-semibold text-gray-900">Citations Received per Year</h3>
              <p className="text-xs text-gray-400">Number of times your works were cited in each year</p>
            </div>
            <Button variant="ghost" size="sm" onClick={addYearRow}>
              <Plus size={14} /> Add Year
            </Button>
          </div>

          {/* Mini bar chart */}
          {yearRows.length > 0 && (
            <div className="flex items-end gap-1 mb-4 h-24 border-b border-gray-200 pb-1">
              {yearRows.map((r, i) => (
                <div key={i} className="flex flex-col items-center flex-1 min-w-0">
                  <span className="text-[9px] text-gray-500 mb-0.5">{r.count}</span>
                  <div
                    className="w-full bg-blue-500 rounded-t min-h-[2px]"
                    style={{ height: `${(r.count / maxCount) * 80}px` }}
                  />
                  <span className="text-[9px] text-gray-400 mt-0.5">{r.year.slice(-2)}</span>
                </div>
              ))}
            </div>
          )}

          <div className="space-y-2 max-h-64 overflow-y-auto">
            {yearRows.map((r, i) => (
              <div key={i} className="flex gap-2 items-center">
                <Input
                  className="w-24"
                  placeholder="Year"
                  value={r.year}
                  onChange={e => updateYearRow(i, 'year', e.target.value)}
                />
                <Input
                  className="w-24"
                  type="number"
                  placeholder="Count"
                  value={String(r.count)}
                  onChange={e => updateYearRow(i, 'count', e.target.value)}
                />
                <button className="text-red-400 hover:text-red-600" onClick={() => removeYearRow(i)}>
                  <Trash2 size={16} />
                </button>
              </div>
            ))}
          </div>
        </Card>
      </div>

      {/* Per-work citation data */}
      {sortedWorks.length > 0 && (
        <Card className="p-6">
          <button
            className="flex items-center gap-2 font-semibold text-gray-900 w-full text-left"
            onClick={() => setShowWorks(!showWorks)}
          >
            {showWorks ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
            Per-Work Citations ({sortedWorks.length} works)
          </button>

          {showWorks && (
            <div className="mt-4 overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-gray-200 text-left text-gray-500">
                    <th className="pb-2 pr-4 font-medium">#</th>
                    <th className="pb-2 pr-4 font-medium">Title</th>
                    <th className="pb-2 pr-4 font-medium text-right">Year</th>
                    <th className="pb-2 pr-4 font-medium text-right">Citations</th>
                  </tr>
                </thead>
                <tbody>
                  {sortedWorks.map((w, i) => (
                    <tr key={w.id} className="border-b border-gray-100">
                      <td className="py-1.5 pr-4 text-gray-400">{i + 1}</td>
                      <td className="py-1.5 pr-4 max-w-md truncate" title={w.title || ''}>
                        {w.title || '(untitled)'}
                      </td>
                      <td className="py-1.5 pr-4 text-right text-gray-500">{w.year || ''}</td>
                      <td className="py-1.5 pr-4 text-right font-medium">
                        {(w.data?.cited_by_count as number) || 0}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Card>
      )}
    </div>
  )
}

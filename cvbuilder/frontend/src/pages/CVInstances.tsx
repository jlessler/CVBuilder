import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api, getToken, listSectionDefinitions } from '../lib/api'
import type { CVInstance, CVTemplate, AvailableItem, SectionDefinition } from '../lib/api'
import { Button, Card, Input, Modal, PageHeader, Badge, Spinner, Checkbox, Select } from '../components/ui'
import { Plus, Trash2, Edit2, Eye, FileDown } from 'lucide-react'
import { ALL_SECTIONS, SectionComposer, toSectionEntries } from '../components/SectionComposer'
import type { SectionEntry } from '../components/SectionComposer'
import type { PickerSection } from '../components/SectionPickerModal'

const HEADER_ALIGNMENTS = [
  { value: '', label: '(Inherit)' },
  { value: 'left', label: 'Left' },
  { value: 'center', label: 'Center' },
  { value: 'right', label: 'Right' },
]

const SECTION_DECORATIONS = [
  { value: '', label: '(Inherit)' },
  { value: 'bottom-border', label: 'Bottom border' },
  { value: 'left-border', label: 'Left border' },
  { value: 'none', label: 'None' },
]

const HEADING_TRANSFORMS = [
  { value: '', label: '(Inherit)' },
  { value: 'uppercase', label: 'UPPERCASE' },
  { value: 'none', label: 'Normal case' },
]

const SORT_DIRECTIONS = [
  { value: '', label: '(Inherit from template)' },
  { value: 'desc', label: 'Newest first' },
  { value: 'asc', label: 'Oldest first' },
]

// ---------------------------------------------------------------------------
// Item Curator — shows checkboxes for selecting items in a section
// ---------------------------------------------------------------------------

function ItemCurator({ instanceId, sectionKey, curated, onCuratedChange }: {
  instanceId: number
  sectionKey: string
  curated: boolean
  onCuratedChange: (curated: boolean) => void
}) {
  const qc = useQueryClient()
  const { data: items = [], isLoading } = useQuery<AvailableItem[]>({
    queryKey: ['cv-instance-items', instanceId, sectionKey],
    queryFn: () => api.get(`/cv-instances/${instanceId}/sections/${sectionKey}/items`).then(r => r.data),
  })

  const updateMut = useMutation({
    mutationFn: (itemIds: number[]) =>
      api.put(`/cv-instances/${instanceId}/sections/${sectionKey}/items`, { item_ids: itemIds }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['cv-instance-items', instanceId, sectionKey] }),
  })

  function toggleItem(itemId: number, selected: boolean) {
    const current = items.filter(i => i.selected).map(i => i.id)
    const next = selected ? [...current, itemId] : current.filter(id => id !== itemId)
    updateMut.mutate(next)
  }

  function selectAll() {
    updateMut.mutate(items.map(i => i.id))
  }

  function deselectAll() {
    updateMut.mutate([])
  }

  if (isLoading) return <div className="py-2 px-4"><Spinner /></div>

  if (items.length === 0) {
    return <p className="text-xs text-gray-400 px-4 py-2">No items in this section.</p>
  }

  const selectedCount = items.filter(i => i.selected).length

  return (
    <div className="px-4 py-2 space-y-2">
      <div className="flex items-center gap-3 mb-2">
        <Checkbox
          label="Curate items (select specific items)"
          checked={curated}
          onChange={() => onCuratedChange(!curated)}
        />
        <span className="text-xs text-gray-400">
          {curated ? `${selectedCount}/${items.length} selected` : 'Including all items'}
        </span>
      </div>
      {curated && (
        <>
          <div className="flex gap-2 mb-1">
            <button onClick={selectAll} className="text-xs text-primary-600 hover:underline">Select all</button>
            <button onClick={deselectAll} className="text-xs text-primary-600 hover:underline">Deselect all</button>
          </div>
          <div className="max-h-60 overflow-y-auto space-y-1 border border-gray-100 rounded-lg p-2">
            {items.map(item => (
              <label key={item.id} className="flex items-start gap-2 py-1 cursor-pointer hover:bg-gray-50 rounded px-1">
                <input
                  type="checkbox"
                  className="mt-0.5 rounded border-gray-300 text-primary-600 focus:ring-primary-500"
                  checked={item.selected}
                  onChange={() => toggleItem(item.id, !item.selected)}
                />
                <span className="text-xs text-gray-700 leading-tight">{item.label}</span>
              </label>
            ))}
          </div>
        </>
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Style Override Editor
// ---------------------------------------------------------------------------

function StyleOverrideEditor({ overrides, onChange }: { overrides: Record<string, string>; onChange: (o: Record<string, string>) => void }) {
  function set(key: string, value: string) {
    onChange({ ...overrides, [key]: value })
  }

  return (
    <details className="border border-gray-200 rounded-lg">
      <summary className="px-3 py-2 text-xs font-medium text-gray-600 cursor-pointer hover:text-gray-800 select-none">
        Style overrides (leave empty to inherit from template)
      </summary>
      <div className="px-3 pb-3 space-y-3">
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Primary color</label>
            <div className="flex items-center gap-2">
              <input type="color" value={overrides.primary_color || '#000000'} onChange={e => set('primary_color', e.target.value)} className="w-6 h-6 rounded border border-gray-200 cursor-pointer" />
              <input type="text" value={overrides.primary_color || ''} onChange={e => set('primary_color', e.target.value)} className="flex-1 px-2 py-1 text-xs border border-gray-200 rounded" placeholder="(inherit)" />
            </div>
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Accent color</label>
            <div className="flex items-center gap-2">
              <input type="color" value={overrides.accent_color || '#000000'} onChange={e => set('accent_color', e.target.value)} className="w-6 h-6 rounded border border-gray-200 cursor-pointer" />
              <input type="text" value={overrides.accent_color || ''} onChange={e => set('accent_color', e.target.value)} className="flex-1 px-2 py-1 text-xs border border-gray-200 rounded" placeholder="(inherit)" />
            </div>
          </div>
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Body font</label>
            <input type="text" value={overrides.font_body || ''} onChange={e => set('font_body', e.target.value)} className="w-full px-2 py-1 text-xs border border-gray-200 rounded" placeholder="(inherit)" />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Heading font</label>
            <input type="text" value={overrides.font_heading || ''} onChange={e => set('font_heading', e.target.value)} className="w-full px-2 py-1 text-xs border border-gray-200 rounded" placeholder="(inherit)" />
          </div>
        </div>
        <div className="grid grid-cols-3 gap-3">
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Header alignment</label>
            <select value={overrides.header_alignment || ''} onChange={e => set('header_alignment', e.target.value)} className="w-full px-2 py-1 text-xs border border-gray-200 rounded">
              {HEADER_ALIGNMENTS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Section decoration</label>
            <select value={overrides.section_decoration || ''} onChange={e => set('section_decoration', e.target.value)} className="w-full px-2 py-1 text-xs border border-gray-200 rounded">
              {SECTION_DECORATIONS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Heading transform</label>
            <select value={overrides.heading_transform || ''} onChange={e => set('heading_transform', e.target.value)} className="w-full px-2 py-1 text-xs border border-gray-200 rounded">
              {HEADING_TRANSFORMS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
            </select>
          </div>
        </div>
      </div>
    </details>
  )
}

// ---------------------------------------------------------------------------
// CV Instance Curator — full editing view
// ---------------------------------------------------------------------------

function CVInstanceCurator({ instance, onClose, customSections }: { instance: CVInstance; onClose: () => void; customSections: PickerSection[] }) {
  const qc = useQueryClient()
  const [name, setName] = useState(instance.name)
  const [description, setDescription] = useState(instance.description || '')
  const [styleOverrides, setStyleOverrides] = useState<Record<string, string>>(instance.style_overrides || {})
  const [sortOverride, setSortOverride] = useState(instance.sort_direction_override || '')
  const [preview, setPreview] = useState(false)

  const sorted = [...instance.sections].sort((a, b) => (a.section_order ?? 0) - (b.section_order ?? 0))
  const initialSections = toSectionEntries(
    sorted,
    (s, i): SectionEntry => {
      const meta = ALL_SECTIONS.find(m => m.key === s.section_key) || customSections.find(m => m.key === s.section_key)
      return {
        section_key: s.section_key,
        label: s.section_key === 'group_heading'
          ? (s.heading_override || 'Group Heading')
          : (meta?.label || s.section_key),
        enabled: true,
        section_order: s.section_order ?? i,
        heading: s.heading_override || '',
        config: s.config_overrides || {},
        extra: { curated: s.curated ?? false },
        depth: s.depth ?? 0,
      }
    },
  )

  const [sections, setSections] = useState(initialSections)

  const saveMut = useMutation({
    mutationFn: async () => {
      // Filter out empty style override values
      const cleanOverrides: Record<string, string> = {}
      for (const [k, v] of Object.entries(styleOverrides)) {
        if (v) cleanOverrides[k] = v
      }
      await api.put(`/cv-instances/${instance.id}`, {
        name,
        description: description || null,
        style_overrides: Object.keys(cleanOverrides).length > 0 ? cleanOverrides : null,
        sort_direction_override: sortOverride || null,
      })
      await api.put(`/cv-instances/${instance.id}/sections`, {
        sections: sections.map((s, i) => ({
          section_key: s.section_key,
          enabled: true,
          section_order: i,
          heading_override: s.heading || null,
          config_overrides: Object.keys(s.config).length > 0 ? s.config : null,
          depth: s.depth,
          curated: !!s.extra.curated,
        })),
      })
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['cv-instances'] })
      onClose()
    },
  })

  return (
    <div className="flex gap-6">
      <div className="flex-1 space-y-4">
        <div className="grid grid-cols-2 gap-4">
          <Input label="CV Name" value={name} onChange={e => setName(e.target.value)} />
          <Input label="Description" value={description} onChange={e => setDescription(e.target.value)} placeholder="Optional description..." />
        </div>
        <Select label="Sort Override" options={SORT_DIRECTIONS} value={sortOverride} onChange={e => setSortOverride(e.target.value)} />
        <StyleOverrideEditor overrides={styleOverrides} onChange={setStyleOverrides} />
        <div className="text-xs text-gray-400">
          Template: {instance.template_name || 'Unknown'}
        </div>

        <SectionComposer
          sections={sections}
          onChange={setSections}
          customSections={customSections}
          sectionLabel="Sections (drag to reorder, expand to curate items)"
          renderExpandedContent={(sec, idx) => (
            <ItemCurator
              instanceId={instance.id}
              sectionKey={sec.section_key}
              curated={!!sec.extra.curated}
              onCuratedChange={curated => setSections(ss =>
                ss.map((s, i) => i === idx ? { ...s, extra: { ...s.extra, curated } } : s)
              )}
            />
          )}
          renderBadges={(sec) => (
            sec.extra.curated ? <Badge color="purple">Curated</Badge> : null
          )}
        />

        <div className="flex gap-2 pt-2 border-t justify-end">
          <Button variant="secondary" onClick={() => setPreview(true)}>
            <Eye size={14} /> Preview
          </Button>
          <Button onClick={() => saveMut.mutate()} loading={saveMut.isPending}>
            Save CV
          </Button>
        </div>
      </div>

      {preview && (
        <div className="w-96 border border-gray-200 rounded-lg overflow-hidden flex-shrink-0">
          <div className="flex items-center justify-between px-3 py-2 bg-gray-100 border-b border-gray-200">
            <span className="text-xs font-medium text-gray-600">Preview</span>
            <button onClick={() => setPreview(false)} className="text-xs text-gray-500 hover:text-gray-700">Hide</button>
          </div>
          <iframe
            src={`/api/cv-instances/${instance.id}/preview?token=${encodeURIComponent(getToken() || '')}`}
            className="w-full h-[600px]"
            title="CV Preview"
          />
        </div>
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Main CVInstances page — list + create
// ---------------------------------------------------------------------------

export function CVInstances() {
  const qc = useQueryClient()
  const [editing, setEditing] = useState<CVInstance | null>(null)
  const [creating, setCreating] = useState(false)
  const [newName, setNewName] = useState('')
  const [newTemplateId, setNewTemplateId] = useState<number | ''>('')
  const [exportingPdf, setExportingPdf] = useState<number | null>(null)

  const { data: instances = [], isLoading } = useQuery<CVInstance[]>({
    queryKey: ['cv-instances'],
    queryFn: () => api.get('/cv-instances').then(r => r.data),
  })

  const { data: templates = [] } = useQuery<CVTemplate[]>({
    queryKey: ['templates'],
    queryFn: () => api.get('/templates').then(r => r.data),
  })

  const { data: customDefs = [] } = useQuery<SectionDefinition[]>({
    queryKey: ['section-definitions'],
    queryFn: listSectionDefinitions,
  })

  const customPickerSections: PickerSection[] = customDefs.map(d => ({
    key: d.section_key,
    label: d.label,
    group: 'Custom',
  }))

  const createMut = useMutation({
    mutationFn: () => api.post('/cv-instances', {
      name: newName,
      template_id: newTemplateId,
    }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['cv-instances'] })
      setCreating(false)
      setNewName('')
      setNewTemplateId('')
    },
  })

  const deleteMut = useMutation({
    mutationFn: (id: number) => api.delete(`/cv-instances/${id}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['cv-instances'] }),
  })

  async function downloadPdf(id: number, name: string) {
    setExportingPdf(id)
    try {
      const res = await api.post(`/cv-instances/${id}/export/pdf`, {}, { responseType: 'blob' })
      const url = URL.createObjectURL(new Blob([res.data], { type: 'application/pdf' }))
      const a = document.createElement('a'); a.href = url; a.download = `${name}.pdf`; a.click()
      URL.revokeObjectURL(url)
    } catch (err) {
      console.error('PDF export failed:', err)
      alert('PDF export failed. Check the browser console for details.')
    } finally {
      setExportingPdf(null)
    }
  }

  if (isLoading) return <div className="p-8"><Spinner /></div>

  return (
    <div className="p-8">
      <PageHeader
        title="CVs"
        subtitle="Create curated CV versions from your templates"
        actions={<Button onClick={() => setCreating(true)}><Plus size={16} /> New CV</Button>}
      />

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {instances.map(inst => (
          <Card key={inst.id} className="p-5">
            <div className="flex items-start justify-between mb-2">
              <div>
                <h3 className="font-semibold text-gray-900">{inst.name}</h3>
                <div className="flex gap-1 mt-1 flex-wrap">
                  <Badge color="blue">{inst.template_name || 'Unknown template'}</Badge>
                  {inst.style_overrides && Object.keys(inst.style_overrides).length > 0 && <Badge color="purple">Custom style</Badge>}
                  <Badge color="gray">{inst.sections.filter(s => s.section_key !== 'group_heading').length} sections</Badge>
                  {inst.sections.some(s => s.curated) && <Badge color="green">Curated</Badge>}
                </div>
              </div>
              <button
                className="text-red-400 hover:text-red-600"
                onClick={() => { if (confirm('Delete this CV?')) deleteMut.mutate(inst.id) }}
              >
                <Trash2 size={14} />
              </button>
            </div>
            {inst.description && <p className="text-xs text-gray-500 mb-3">{inst.description}</p>}
            <div className="flex gap-2">
              <Button variant="secondary" size="sm" onClick={() => setEditing(inst)}>
                <Edit2 size={12} /> Edit
              </Button>
              <a href={`/api/cv-instances/${inst.id}/preview?token=${encodeURIComponent(getToken() || '')}`} target="_blank" rel="noreferrer">
                <Button variant="ghost" size="sm"><Eye size={12} /> Preview</Button>
              </a>
              <Button variant="ghost" size="sm" onClick={() => downloadPdf(inst.id, inst.name)} loading={exportingPdf === inst.id}>
                <FileDown size={12} /> PDF
              </Button>
            </div>
          </Card>
        ))}

        {instances.length === 0 && (
          <div className="col-span-3 py-16 text-center text-gray-400 text-sm">
            No CVs yet. Create one from a template to get started.
          </div>
        )}
      </div>

      {/* Create modal */}
      <Modal open={creating} onClose={() => setCreating(false)} title="New CV">
        <div className="space-y-4">
          <Input label="CV Name" value={newName} onChange={e => setNewName(e.target.value)} placeholder="e.g. Short CV for Grant Application" />
          <Select
            label="Based on Template"
            options={[
              { value: '', label: 'Select a template...' },
              ...templates.map(t => ({ value: String(t.id), label: t.name })),
            ]}
            value={String(newTemplateId)}
            onChange={e => setNewTemplateId(e.target.value ? Number(e.target.value) : '')}
          />
          <p className="text-sm text-gray-500">
            The CV will inherit all sections from the template. You can then customize which items to include.
          </p>
          <div className="flex gap-2 justify-end">
            <Button variant="secondary" onClick={() => setCreating(false)}>Cancel</Button>
            <Button
              onClick={() => createMut.mutate()}
              loading={createMut.isPending}
              disabled={!newName || !newTemplateId}
            >
              Create CV
            </Button>
          </div>
        </div>
      </Modal>

      {/* Curator modal */}
      {editing && (
        <Modal open={!!editing} onClose={() => setEditing(null)} title={`Edit: ${editing.name}`}>
          <CVInstanceCurator instance={editing} onClose={() => setEditing(null)} customSections={customPickerSections} />
        </Modal>
      )}
    </div>
  )
}

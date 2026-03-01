import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api, getToken } from '../lib/api'
import type { CVInstance, CVInstanceSection, CVTemplate, AvailableItem } from '../lib/api'
import { Button, Card, Input, Modal, PageHeader, Badge, Spinner, Checkbox, Select } from '../components/ui'
import { Plus, Trash2, Edit2, Eye, FileDown, GripVertical, ChevronDown, ChevronRight } from 'lucide-react'
import {
  DndContext, closestCenter, PointerSensor, useSensor, useSensors,
} from '@dnd-kit/core'
import type { DragEndEvent } from '@dnd-kit/core'
import {
  SortableContext, verticalListSortingStrategy, useSortable, arrayMove,
} from '@dnd-kit/sortable'
import { CSS } from '@dnd-kit/utilities'

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

const ALL_SECTIONS = [
  { key: 'education', label: 'Education' },
  { key: 'experience', label: 'Experience' },
  { key: 'consulting', label: 'Consulting' },
  { key: 'memberships', label: 'Professional Memberships' },
  { key: 'panels_advisory', label: 'Advisory Panels' },
  { key: 'panels_grantreview', label: 'Grant Review Panels' },
  { key: 'patents', label: 'Patents' },
  { key: 'symposia', label: 'Symposia Organized' },
  { key: 'committees', label: 'Committee Memberships' },
  { key: 'editorial', label: 'Editorial Activities' },
  { key: 'peerrev', label: 'Peer Review' },
  { key: 'classes', label: 'Teaching' },
  { key: 'grants', label: 'Grants & Funding' },
  { key: 'awards', label: 'Honors & Awards' },
  { key: 'press', label: 'Press Coverage' },
  { key: 'trainees_advisees', label: 'Graduate Advisees' },
  { key: 'trainees_postdocs', label: 'Postdoctoral Fellows' },
  { key: 'seminars', label: 'Invited Seminars & Lectures' },
  { key: 'publications_papers', label: 'Papers' },
  { key: 'publications_preprints', label: 'Preprints' },
  { key: 'publications_chapters', label: 'Book Chapters' },
  { key: 'publications_letters', label: 'Letters & Commentaries' },
  { key: 'publications_scimeetings', label: 'Scientific Meeting Presentations' },
  { key: 'publications_editorials', label: 'Non-Peer-Reviewed Articles & Editorials' },
  { key: 'software', label: 'Software' },
  { key: 'policypres', label: 'Policy Presentations' },
  { key: 'policycons', label: 'Policy Consulting' },
  { key: 'otherservice', label: 'Other Service' },
  { key: 'dissertation', label: 'Dissertation' },
  { key: 'chairedsessions', label: 'Chaired Sessions' },
  { key: 'otherpractice', label: 'Other Practice Activities' },
  { key: 'departmentalOrals', label: 'Departmental Oral Exams' },
  { key: 'finaldefense', label: 'Final Dissertation Defenses' },
  { key: 'schoolwideOrals', label: 'School-wide Oral Exams' },
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
// Sortable section row for the curator view
// ---------------------------------------------------------------------------

type SectionState = {
  section_key: string
  label: string
  enabled: boolean
  section_order: number
  heading_override: string
  config_overrides: Record<string, unknown> | null
  curated: boolean
}

const PUB_CROSSREF_SECTIONS = ['publications_papers', 'publications_preprints']

function SortableSectionRow({
  section, instanceId,
  onToggle, onHeadingChange, onConfigOverridesChange, onCuratedChange,
}: {
  section: SectionState
  instanceId: number
  onToggle: () => void
  onHeadingChange: (h: string) => void
  onConfigOverridesChange: (overrides: Record<string, unknown>) => void
  onCuratedChange: (curated: boolean) => void
}) {
  const [expanded, setExpanded] = useState(false)
  const { attributes, listeners, setNodeRef, transform, transition } = useSortable({ id: section.section_key })
  const hasCrossrefOptions = PUB_CROSSREF_SECTIONS.includes(section.section_key)
  const isPreprints = section.section_key === 'publications_preprints'
  const overrides = section.config_overrides || {}

  return (
    <div
      ref={setNodeRef}
      style={{ transform: CSS.Transform.toString(transform), transition }}
      className={`rounded-lg border mb-1.5 ${
        section.enabled ? 'bg-white border-gray-200' : 'bg-gray-50 border-gray-100 opacity-60'
      }`}
    >
      <div className="flex items-center gap-3 px-4 py-2.5">
        <button {...attributes} {...listeners} className="cursor-grab text-gray-400 hover:text-gray-600">
          <GripVertical size={16} />
        </button>
        <Checkbox checked={section.enabled} onChange={onToggle} />
        <button
          className="text-gray-400 hover:text-gray-600"
          onClick={() => setExpanded(!expanded)}
        >
          {expanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
        </button>
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium text-gray-800">{section.label}</p>
        </div>
        {section.curated && (
          <Badge color="purple">Curated</Badge>
        )}
        <input
          className="w-40 px-2 py-1 text-xs border border-gray-200 rounded focus:outline-none focus:ring-1 focus:ring-primary-400"
          placeholder="Heading override..."
          value={section.heading_override || ''}
          onChange={e => onHeadingChange(e.target.value)}
        />
      </div>
      {expanded && section.enabled && (
        <div className="border-t border-gray-100">
          {hasCrossrefOptions && (
            <div className="px-4 py-2 border-b border-gray-100 space-y-1">
              <label className="flex items-center gap-1.5 text-xs text-gray-500 cursor-pointer">
                <input
                  type="checkbox"
                  className="rounded border-gray-300"
                  checked={overrides.show_crossref !== false}
                  onChange={e => onConfigOverridesChange({ ...overrides, show_crossref: e.target.checked })}
                />
                Show cross-ref DOI
              </label>
              {isPreprints && (
                <label className="flex items-center gap-1.5 text-xs text-gray-500 cursor-pointer">
                  <input
                    type="checkbox"
                    className="rounded border-gray-300"
                    checked={!!overrides.hide_if_published}
                    onChange={e => onConfigOverridesChange({ ...overrides, hide_if_published: e.target.checked })}
                  />
                  Hide if published version exists
                </label>
              )}
            </div>
          )}
          <ItemCurator
            instanceId={instanceId}
            sectionKey={section.section_key}
            curated={section.curated}
            onCuratedChange={onCuratedChange}
          />
        </div>
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// CV Instance Curator — full editing view
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

function CVInstanceCurator({ instance, onClose }: { instance: CVInstance; onClose: () => void }) {
  const qc = useQueryClient()
  const [name, setName] = useState(instance.name)
  const [description, setDescription] = useState(instance.description || '')
  const [styleOverrides, setStyleOverrides] = useState<Record<string, string>>(instance.style_overrides || {})
  const [sortOverride, setSortOverride] = useState(instance.sort_direction_override || '')
  const [preview, setPreview] = useState(false)

  const initialSections: SectionState[] = (() => {
    const existing = new Map(instance.sections.map(s => [s.section_key, s]))
    const orderedKeys = instance.sections
      .sort((a, b) => (a.section_order ?? 0) - (b.section_order ?? 0))
      .map(s => s.section_key)
    const missingKeys = ALL_SECTIONS.map(s => s.key).filter(k => !existing.has(k))
    const allKeys = [...orderedKeys, ...missingKeys]
    return allKeys.map((key, i) => {
      const sec = existing.get(key)
      const meta = ALL_SECTIONS.find(s => s.key === key)
      return {
        section_key: key,
        label: meta?.label || key,
        enabled: sec?.enabled ?? false,
        section_order: sec?.section_order ?? i,
        heading_override: sec?.heading_override || '',
        config_overrides: sec?.config_overrides || null,
        curated: sec?.curated ?? false,
      }
    })
  })()

  const [sections, setSections] = useState(initialSections)
  const sensors = useSensors(useSensor(PointerSensor))

  function handleDragEnd(event: DragEndEvent) {
    const { active, over } = event
    if (over && active.id !== over.id) {
      setSections(items => {
        const oldIndex = items.findIndex(i => i.section_key === active.id)
        const newIndex = items.findIndex(i => i.section_key === over.id)
        return arrayMove(items, oldIndex, newIndex)
      })
    }
  }

  const saveMut = useMutation({
    mutationFn: async () => {
      // Update instance metadata
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
      // Update sections
      await api.put(`/cv-instances/${instance.id}/sections`, {
        sections: sections.map((s, i) => ({
          section_key: s.section_key,
          enabled: s.enabled,
          section_order: i,
          heading_override: s.heading_override || null,
          config_overrides: s.config_overrides,
          curated: s.curated,
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

        <div>
          <p className="text-sm font-medium text-gray-700 mb-2">Sections (drag to reorder, expand to curate items)</p>
          <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={handleDragEnd}>
            <SortableContext items={sections.map(s => s.section_key)} strategy={verticalListSortingStrategy}>
              {sections.map(sec => (
                <SortableSectionRow
                  key={sec.section_key}
                  section={sec}
                  instanceId={instance.id}
                  onToggle={() => setSections(ss =>
                    ss.map(s => s.section_key === sec.section_key ? { ...s, enabled: !s.enabled } : s)
                  )}
                  onHeadingChange={h => setSections(ss =>
                    ss.map(s => s.section_key === sec.section_key ? { ...s, heading_override: h } : s)
                  )}
                  onConfigOverridesChange={overrides => setSections(ss =>
                    ss.map(s => s.section_key === sec.section_key ? { ...s, config_overrides: overrides } : s)
                  )}
                  onCuratedChange={curated => setSections(ss =>
                    ss.map(s => s.section_key === sec.section_key ? { ...s, curated } : s)
                  )}
                />
              ))}
            </SortableContext>
          </DndContext>
        </div>

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
                  <Badge color="gray">{inst.sections.filter(s => s.enabled).length} sections</Badge>
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
          <CVInstanceCurator instance={editing} onClose={() => setEditing(null)} />
        </Modal>
      )}
    </div>
  )
}

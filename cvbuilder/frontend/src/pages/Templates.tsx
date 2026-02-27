import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api, getToken } from '../lib/api'
import type { CVTemplate, TemplateSection } from '../lib/api'
import { Button, Card, Input, Modal, PageHeader, Badge, Spinner, Checkbox, Select } from '../components/ui'
import { Plus, Trash2, Edit2, Eye, GripVertical } from 'lucide-react'
import {
  DndContext, closestCenter, PointerSensor, useSensor, useSensors,
} from '@dnd-kit/core'
import type { DragEndEvent } from '@dnd-kit/core'
import {
  SortableContext, verticalListSortingStrategy, useSortable, arrayMove,
} from '@dnd-kit/sortable'
import { CSS } from '@dnd-kit/utilities'

const SORT_DIRECTIONS = [
  { value: 'desc', label: 'Newest first' },
  { value: 'asc',  label: 'Oldest first' },
]

const HEADER_ALIGNMENTS = [
  { value: 'left', label: 'Left' },
  { value: 'center', label: 'Center' },
  { value: 'right', label: 'Right' },
]

const SECTION_DECORATIONS = [
  { value: 'bottom-border', label: 'Bottom border' },
  { value: 'left-border', label: 'Left border' },
  { value: 'none', label: 'None' },
]

const HEADING_TRANSFORMS = [
  { value: 'uppercase', label: 'UPPERCASE' },
  { value: 'none', label: 'Normal case' },
]

const THEME_PRESETS: Record<string, Record<string, string>> = {
  academic: {
    primary_color: '#1a3a5c', accent_color: '#2e6da4',
    font_body: '"Times New Roman", Times, serif',
    font_heading: 'Arial, Helvetica, sans-serif',
    body_font_size: '11pt', heading_font_size: '12pt',
    name_font_size: '20pt', header_alignment: 'center',
    section_decoration: 'bottom-border', heading_transform: 'uppercase',
    text_color: '#222222', muted_color: '#666666', border_color: '#cccccc',
    page_width: '8.5in', page_padding: '0.75in 0.75in 1in 0.75in',
    date_column_width: '1.3in', header_border_style: '2px solid',
    name_font_weight: 'bold', name_letter_spacing: '0.05em',
    section_margin_bottom: '1.2em', heading_letter_spacing: '0.08em',
    line_height: '1.4',
  },
  unc: {
    primary_color: '#13294B', accent_color: '#4B9CD3',
    font_body: 'Helvetica, Arial, sans-serif',
    font_heading: 'Helvetica, Arial, sans-serif',
    body_font_size: '10.5pt', heading_font_size: '11pt',
    name_font_size: '18pt', header_alignment: 'left',
    section_decoration: 'bottom-border', heading_transform: 'none',
    text_color: '#222222', muted_color: '#666666', border_color: '#c0d0e0',
    page_width: '8.5in', page_padding: '0.75in',
    date_column_width: '1.1in', header_border_style: '2px solid',
    name_font_weight: 'bold', name_letter_spacing: '0.02em',
    section_margin_bottom: '1.1em', heading_letter_spacing: '0',
    line_height: '1.4',
  },
  hopkins: {
    primary_color: '#002D72', accent_color: '#002D72',
    font_body: '"Times New Roman", Times, serif',
    font_heading: '"Times New Roman", Times, serif',
    body_font_size: '12pt', heading_font_size: '12pt',
    name_font_size: '14pt', header_alignment: 'center',
    section_decoration: 'bottom-border', heading_transform: 'uppercase',
    text_color: '#111111', muted_color: '#555555', border_color: '#aaaaaa',
    page_width: '8.5in', page_padding: '1in',
    date_column_width: '1.3in', header_border_style: 'none',
    name_font_weight: 'bold', name_letter_spacing: '0.04em',
    section_margin_bottom: '1.2em', heading_letter_spacing: '0.05em',
    line_height: '1.5',
  },
  unige: {
    primary_color: '#C01584', accent_color: '#a8127a',
    font_body: '"Latin Modern Sans", "DejaVu Sans", Helvetica, Arial, sans-serif',
    font_heading: '"Latin Modern Sans", "DejaVu Sans", Helvetica, Arial, sans-serif',
    body_font_size: '11pt', heading_font_size: '12pt',
    name_font_size: '14pt', header_alignment: 'right',
    section_decoration: 'none', heading_transform: 'none',
    text_color: '#1a1a1a', muted_color: '#666666', border_color: '#dddddd',
    page_width: '8.27in', page_padding: '1in 0.75in',
    date_column_width: '1.1in', header_border_style: '1px solid',
    name_font_weight: 'bold', name_letter_spacing: '0',
    section_margin_bottom: '1.2em', heading_letter_spacing: '0',
    line_height: '1.45',
  },
  minimal: {
    primary_color: '#333333', accent_color: '#555555',
    font_body: '"Helvetica Neue", Helvetica, Arial, sans-serif',
    font_heading: '"Helvetica Neue", Helvetica, Arial, sans-serif',
    body_font_size: '10.5pt', heading_font_size: '9pt',
    name_font_size: '22pt', header_alignment: 'left',
    section_decoration: 'bottom-border', heading_transform: 'uppercase',
    text_color: '#333333', muted_color: '#888888', border_color: '#dddddd',
    page_width: '8.5in', page_padding: '0.75in',
    date_column_width: '1.2in', header_border_style: 'none',
    name_font_weight: '300', name_letter_spacing: '0.1em',
    section_margin_bottom: '1.5em', heading_letter_spacing: '0.12em',
    line_height: '1.5',
  },
  modern: {
    primary_color: '#7c3aed', accent_color: '#5b21b6',
    font_body: '"Georgia", serif',
    font_heading: '"Arial", sans-serif',
    body_font_size: '10.5pt', heading_font_size: '11pt',
    name_font_size: '24pt', header_alignment: 'left',
    section_decoration: 'left-border', heading_transform: 'uppercase',
    text_color: '#1f2937', muted_color: '#6b7280', border_color: '#e5e7eb',
    page_width: '8.5in', page_padding: '0',
    date_column_width: '1.2in', header_border_style: 'none',
    header_bg_color: '#7c3aed',
    name_font_weight: 'bold', name_letter_spacing: '0.02em',
    section_margin_bottom: '1.2em', heading_letter_spacing: '0.1em',
    line_height: '1.45',
  },
}

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

function ColorInput({ label, value, onChange }: { label: string; value: string; onChange: (v: string) => void }) {
  return (
    <div>
      <label className="block text-xs font-medium text-gray-600 mb-1">{label}</label>
      <div className="flex items-center gap-2">
        <input type="color" value={value || '#000000'} onChange={e => onChange(e.target.value)} className="w-8 h-8 rounded border border-gray-200 cursor-pointer" />
        <input type="text" value={value || ''} onChange={e => onChange(e.target.value)} className="flex-1 px-2 py-1 text-xs border border-gray-200 rounded focus:outline-none focus:ring-1 focus:ring-primary-400" placeholder="#000000" />
      </div>
    </div>
  )
}

function StyleEditor({ style, onChange }: { style: Record<string, string>; onChange: (s: Record<string, string>) => void }) {
  const [showAdvanced, setShowAdvanced] = useState(false)

  function set(key: string, value: string) {
    onChange({ ...style, [key]: value })
  }

  return (
    <div className="space-y-3">
      <p className="text-sm font-medium text-gray-700">Style</p>
      <div className="grid grid-cols-2 gap-3">
        <ColorInput label="Primary color" value={style.primary_color || ''} onChange={v => set('primary_color', v)} />
        <ColorInput label="Accent color" value={style.accent_color || ''} onChange={v => set('accent_color', v)} />
      </div>
      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1">Body font</label>
          <input type="text" value={style.font_body || ''} onChange={e => set('font_body', e.target.value)} className="w-full px-2 py-1 text-xs border border-gray-200 rounded focus:outline-none focus:ring-1 focus:ring-primary-400" />
        </div>
        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1">Heading font</label>
          <input type="text" value={style.font_heading || ''} onChange={e => set('font_heading', e.target.value)} className="w-full px-2 py-1 text-xs border border-gray-200 rounded focus:outline-none focus:ring-1 focus:ring-primary-400" />
        </div>
      </div>
      <div className="grid grid-cols-3 gap-3">
        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1">Body size</label>
          <input type="text" value={style.body_font_size || ''} onChange={e => set('body_font_size', e.target.value)} className="w-full px-2 py-1 text-xs border border-gray-200 rounded focus:outline-none focus:ring-1 focus:ring-primary-400" />
        </div>
        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1">Name size</label>
          <input type="text" value={style.name_font_size || ''} onChange={e => set('name_font_size', e.target.value)} className="w-full px-2 py-1 text-xs border border-gray-200 rounded focus:outline-none focus:ring-1 focus:ring-primary-400" />
        </div>
        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1">Header alignment</label>
          <select value={style.header_alignment || 'center'} onChange={e => set('header_alignment', e.target.value)} className="w-full px-2 py-1 text-xs border border-gray-200 rounded focus:outline-none focus:ring-1 focus:ring-primary-400">
            {HEADER_ALIGNMENTS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
          </select>
        </div>
      </div>
      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1">Section decoration</label>
          <select value={style.section_decoration || 'bottom-border'} onChange={e => set('section_decoration', e.target.value)} className="w-full px-2 py-1 text-xs border border-gray-200 rounded focus:outline-none focus:ring-1 focus:ring-primary-400">
            {SECTION_DECORATIONS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
          </select>
        </div>
        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1">Heading transform</label>
          <select value={style.heading_transform || 'uppercase'} onChange={e => set('heading_transform', e.target.value)} className="w-full px-2 py-1 text-xs border border-gray-200 rounded focus:outline-none focus:ring-1 focus:ring-primary-400">
            {HEADING_TRANSFORMS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
          </select>
        </div>
      </div>

      <details open={showAdvanced} onToggle={e => setShowAdvanced((e.target as HTMLDetailsElement).open)}>
        <summary className="text-xs font-medium text-gray-500 cursor-pointer hover:text-gray-700 select-none">
          Advanced style options
        </summary>
        <div className="mt-2 space-y-3">
          <div className="grid grid-cols-3 gap-3">
            <ColorInput label="Text color" value={style.text_color || ''} onChange={v => set('text_color', v)} />
            <ColorInput label="Muted color" value={style.muted_color || ''} onChange={v => set('muted_color', v)} />
            <ColorInput label="Border color" value={style.border_color || ''} onChange={v => set('border_color', v)} />
          </div>
          <div className="grid grid-cols-3 gap-3">
            {([
              ['heading_font_size', 'Heading size'],
              ['page_width', 'Page width'],
              ['page_padding', 'Page padding'],
              ['date_column_width', 'Date col width'],
              ['header_border_style', 'Header border'],
              ['name_font_weight', 'Name weight'],
              ['name_letter_spacing', 'Name spacing'],
              ['section_margin_bottom', 'Section margin'],
              ['heading_letter_spacing', 'Heading spacing'],
              ['line_height', 'Line height'],
            ] as const).map(([key, label]) => (
              <div key={key}>
                <label className="block text-xs font-medium text-gray-600 mb-1">{label}</label>
                <input type="text" value={style[key] || ''} onChange={e => set(key, e.target.value)} className="w-full px-2 py-1 text-xs border border-gray-200 rounded focus:outline-none focus:ring-1 focus:ring-primary-400" />
              </div>
            ))}
          </div>
          <ColorInput label="Header bg color (empty = transparent)" value={style.header_bg_color || ''} onChange={v => set('header_bg_color', v)} />
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Custom CSS</label>
            <textarea value={style.custom_css || ''} onChange={e => set('custom_css', e.target.value)} rows={4} className="w-full px-2 py-1 text-xs border border-gray-200 rounded focus:outline-none focus:ring-1 focus:ring-primary-400 font-mono" placeholder="/* Additional CSS rules */" />
          </div>
        </div>
      </details>
    </div>
  )
}

function SortableRow({
  section, onToggle, onHeadingChange,
}: {
  section: TemplateSection & { label: string }
  onToggle: () => void
  onHeadingChange: (h: string) => void
}) {
  const { attributes, listeners, setNodeRef, transform, transition } = useSortable({ id: section.section_key })
  return (
    <div
      ref={setNodeRef}
      style={{ transform: CSS.Transform.toString(transform), transition }}
      className={`flex items-center gap-3 px-4 py-2.5 rounded-lg border mb-1.5 ${
        section.enabled ? 'bg-white border-gray-200' : 'bg-gray-50 border-gray-100 opacity-60'
      }`}
    >
      <button {...attributes} {...listeners} className="cursor-grab text-gray-400 hover:text-gray-600">
        <GripVertical size={16} />
      </button>
      <Checkbox checked={section.enabled} onChange={onToggle} />
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-gray-800">{section.label}</p>
      </div>
      <input
        className="w-40 px-2 py-1 text-xs border border-gray-200 rounded focus:outline-none focus:ring-1 focus:ring-primary-400"
        placeholder="Section heading..."
        value={section.config?.heading || ''}
        onChange={e => onHeadingChange(e.target.value)}
      />
    </div>
  )
}

function TemplateComposer({ template, onClose }: { template: CVTemplate; onClose: () => void }) {
  const qc = useQueryClient()
  const [name, setName] = useState(template.name)
  const [description, setDescription] = useState(template.description || '')
  const [style, setStyle] = useState<Record<string, string>>(template.style || THEME_PRESETS.academic)
  const [sortDirection, setSortDirection] = useState(template.sort_direction ?? 'desc')

  // Build sections list with labels
  const initialSections = (() => {
    const existing = new Map(template.sections.map(s => [s.section_key, s]))
    const orderedKeys = template.sections.map(s => s.section_key)
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
        config: sec?.config || {},
        id: sec?.id ?? 0,
      }
    })
  })()

  const [sections, setSections] = useState(initialSections)
  const [preview, setPreview] = useState(false)

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
    mutationFn: () => api.put(`/templates/${template.id}`, {
      name, description: description || null, style,
      sort_direction: sortDirection,
      sections: sections.map((s, i) => ({
        section_key: s.section_key,
        enabled: s.enabled,
        section_order: i,
        config: s.config,
      })),
    }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['templates'] }); onClose() },
  })

  return (
    <div className="flex gap-6">
      {/* Composer panel */}
      <div className="flex-1 space-y-4">
        <div className="grid grid-cols-2 gap-4">
          <Input label="Template Name" value={name} onChange={e => setName(e.target.value)} />
          <Select label="Item Sort Order" options={SORT_DIRECTIONS} value={sortDirection} onChange={e => setSortDirection(e.target.value)} />
        </div>
        <Input label="Description" value={description} onChange={e => setDescription(e.target.value)} placeholder="Optional description of this template..." />

        <StyleEditor style={style} onChange={setStyle} />

        <div>
          <p className="text-sm font-medium text-gray-700 mb-2">Sections (drag to reorder)</p>
          <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={handleDragEnd}>
            <SortableContext items={sections.map(s => s.section_key)} strategy={verticalListSortingStrategy}>
              {sections.map(sec => (
                <SortableRow
                  key={sec.section_key}
                  section={sec as TemplateSection & { label: string }}
                  onToggle={() => setSections(ss =>
                    ss.map(s => s.section_key === sec.section_key ? { ...s, enabled: !s.enabled } : s)
                  )}
                  onHeadingChange={h => setSections(ss =>
                    ss.map(s => s.section_key === sec.section_key
                      ? { ...s, config: { ...s.config, heading: h } } : s)
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
            Save Template
          </Button>
        </div>
      </div>

      {/* Preview iframe */}
      {preview && (
        <div className="w-96 border border-gray-200 rounded-lg overflow-hidden">
          <div className="flex items-center justify-between px-3 py-2 bg-gray-100 border-b border-gray-200">
            <span className="text-xs font-medium text-gray-600">Preview</span>
            <button onClick={() => setPreview(false)} className="text-xs text-gray-500 hover:text-gray-700">Hide</button>
          </div>
          <iframe
            src={`/api/templates/${template.id}/preview?token=${encodeURIComponent(getToken() || '')}`}
            className="w-full h-[600px]"
            title="CV Preview"
          />
        </div>
      )}
    </div>
  )
}

export function Templates() {
  const qc = useQueryClient()
  const [composing, setComposing] = useState<CVTemplate | null>(null)
  const [creating, setCreating] = useState(false)
  const [newName, setNewName] = useState('')
  const [copyStyleFrom, setCopyStyleFrom] = useState('')

  const { data = [], isLoading } = useQuery<CVTemplate[]>({
    queryKey: ['templates'],
    queryFn: () => api.get('/templates').then(r => r.data),
  })

  const createMut = useMutation({
    mutationFn: () => {
      // Determine initial style: copy from existing template or use academic defaults
      let initialStyle = THEME_PRESETS.academic
      if (copyStyleFrom) {
        const source = data.find(t => String(t.id) === copyStyleFrom)
        if (source?.style) initialStyle = source.style
      }
      return api.post('/templates', {
        name: newName, style: initialStyle, sort_direction: 'desc',
        sections: ALL_SECTIONS.map((s, i) => ({
          section_key: s.key, enabled: true, section_order: i,
          config: { heading: s.label },
        })),
      })
    },
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['templates'] }); setCreating(false); setNewName(''); setCopyStyleFrom('') },
  })

  const deleteMut = useMutation({
    mutationFn: (id: number) => api.delete(`/templates/${id}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['templates'] }),
  })

  if (isLoading) return <div className="p-8"><Spinner /></div>

  return (
    <div className="p-8">
      <PageHeader
        title="Templates"
        subtitle="Define section layout, order, and style for your CVs"
        actions={<Button onClick={() => setCreating(true)}><Plus size={16} /> New Template</Button>}
      />

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {data.map(tmpl => (
          <Card key={tmpl.id} className="p-5">
            <div className="flex items-start justify-between mb-2">
              <div>
                <h3 className="font-semibold text-gray-900">{tmpl.name}</h3>
                <div className="flex gap-1 mt-1 items-center">
                  {tmpl.style?.primary_color && (
                    <span className="inline-block w-3 h-3 rounded-full border border-gray-300" style={{ backgroundColor: tmpl.style.primary_color }} />
                  )}
                  <Badge color="gray">{tmpl.sections.filter(s => s.enabled).length} sections</Badge>
                  <Badge color="blue">{tmpl.sort_direction === 'desc' ? 'Newest first' : 'Oldest first'}</Badge>
                </div>
              </div>
              <button
                className="text-red-400 hover:text-red-600"
                onClick={() => { if (confirm('Delete template?')) deleteMut.mutate(tmpl.id) }}
              >
                <Trash2 size={14} />
              </button>
            </div>
            {tmpl.description && <p className="text-xs text-gray-500 mb-3">{tmpl.description}</p>}
            <div className="flex gap-2">
              <Button variant="secondary" size="sm" onClick={() => setComposing(tmpl)}>
                <Edit2 size={12} /> Edit
              </Button>
              <a href={`/api/templates/${tmpl.id}/preview?token=${encodeURIComponent(getToken() || '')}`} target="_blank" rel="noreferrer">
                <Button variant="ghost" size="sm"><Eye size={12} /> Preview</Button>
              </a>
            </div>
          </Card>
        ))}

        {data.length === 0 && (
          <div className="col-span-3 py-16 text-center text-gray-400 text-sm">
            No templates yet. Create one to get started.
          </div>
        )}
      </div>

      {/* Create modal */}
      <Modal open={creating} onClose={() => setCreating(false)} title="New Template">
        <div className="space-y-4">
          <Input label="Template Name" value={newName} onChange={e => setNewName(e.target.value)} placeholder="e.g. Full Academic CV" />
          {data.length > 0 && (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Copy style from</label>
              <select
                value={copyStyleFrom}
                onChange={e => setCopyStyleFrom(e.target.value)}
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-400"
              >
                <option value="">Academic (default)</option>
                {data.map(t => <option key={t.id} value={String(t.id)}>{t.name}</option>)}
              </select>
            </div>
          )}
          <p className="text-sm text-gray-500">All sections will be enabled by default. You can customize in the composer.</p>
          <div className="flex gap-2 justify-end">
            <Button variant="secondary" onClick={() => setCreating(false)}>Cancel</Button>
            <Button onClick={() => createMut.mutate()} loading={createMut.isPending} disabled={!newName}>
              Create Template
            </Button>
          </div>
        </div>
      </Modal>

      {/* Composer modal */}
      {composing && (
        <Modal open={!!composing} onClose={() => setComposing(null)} title={`Compose: ${composing.name}`}>
          <TemplateComposer template={composing} onClose={() => setComposing(null)} />
        </Modal>
      )}
    </div>
  )
}

import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '../lib/api'
import type { CVTemplate, TemplateSection } from '../lib/api'
import { Button, Card, Input, Modal, PageHeader, Badge, Spinner, Checkbox, Select } from '../components/ui'
import { Plus, Trash2, Edit2, Eye, FileDown, GripVertical } from 'lucide-react'
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

const THEMES = [
  { value: 'academic', label: 'Academic (Times, formal)' },
  { value: 'unc', label: 'UNC (sans-serif, Carolina Blue)' },
  { value: 'hopkins', label: 'Hopkins (serif, Heritage Blue)' },
  { value: 'unige', label: 'UNIGE (sans-serif, RedViolet)' },
  { value: 'minimal', label: 'Minimal (Helvetica, clean)' },
  { value: 'modern', label: 'Modern (colored header)' },
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
  { key: 'software', label: 'Software' },
  { key: 'policypres', label: 'Policy Presentations' },
  { key: 'policycons', label: 'Policy Consulting' },
  { key: 'otherservice', label: 'Other Service' },
]

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
  const [theme, setTheme] = useState(template.theme_css)
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
      name, description: template.description, theme_css: theme,
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
        <div className="grid grid-cols-3 gap-4">
          <Input label="Template Name" value={name} onChange={e => setName(e.target.value)} />
          <Select label="Theme" options={THEMES} value={theme} onChange={e => setTheme(e.target.value)} />
          <Select label="Item Sort Order" options={SORT_DIRECTIONS} value={sortDirection} onChange={e => setSortDirection(e.target.value)} />
        </div>

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
            src={`/api/templates/${template.id}/preview`}
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

  const { data = [], isLoading } = useQuery<CVTemplate[]>({
    queryKey: ['templates'],
    queryFn: () => api.get('/templates').then(r => r.data),
  })

  const createMut = useMutation({
    mutationFn: () => api.post('/templates', {
      name: newName, theme_css: 'academic', sort_direction: 'desc',
      sections: ALL_SECTIONS.map((s, i) => ({
        section_key: s.key, enabled: true, section_order: i,
        config: { heading: s.label },
      })),
    }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['templates'] }); setCreating(false); setNewName('') },
  })

  const deleteMut = useMutation({
    mutationFn: (id: number) => api.delete(`/templates/${id}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['templates'] }),
  })

  async function downloadPdf(id: number, name: string) {
    const res = await api.post(`/templates/${id}/export/pdf`, {}, { responseType: 'blob' })
    const url = URL.createObjectURL(new Blob([res.data], { type: 'application/pdf' }))
    const a = document.createElement('a'); a.href = url; a.download = `${name}.pdf`; a.click()
    URL.revokeObjectURL(url)
  }

  if (isLoading) return <div className="p-8"><Spinner /></div>

  return (
    <div className="p-8">
      <PageHeader
        title="Templates"
        subtitle="Compose and export your CV"
        actions={<Button onClick={() => setCreating(true)}><Plus size={16} /> New Template</Button>}
      />

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {data.map(tmpl => (
          <Card key={tmpl.id} className="p-5">
            <div className="flex items-start justify-between mb-2">
              <div>
                <h3 className="font-semibold text-gray-900">{tmpl.name}</h3>
                <div className="flex gap-1 mt-1">
                  <Badge color="purple">{tmpl.theme_css}</Badge>
                  <Badge color="gray">{tmpl.sections.filter(s => s.enabled).length} sections</Badge>
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
              <a href={`/api/templates/${tmpl.id}/preview`} target="_blank" rel="noreferrer">
                <Button variant="ghost" size="sm"><Eye size={12} /> Preview</Button>
              </a>
              <Button variant="ghost" size="sm" onClick={() => downloadPdf(tmpl.id, tmpl.name)}>
                <FileDown size={12} /> PDF
              </Button>
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

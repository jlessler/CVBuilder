import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Modal, Button, Input, Spinner } from './ui'
import { Plus, Trash2, Edit2, GripVertical } from 'lucide-react'
import type { SectionDefinition, SectionFieldDef } from '../lib/api'
import { listSectionDefinitions, createSectionDefinition, updateSectionDefinition, deleteSectionDefinition } from '../lib/api'

const FIELD_TYPES: { value: SectionFieldDef['type']; label: string }[] = [
  { value: 'text', label: 'Text' },
  { value: 'date', label: 'Date' },
  { value: 'url', label: 'URL' },
  { value: 'multiline', label: 'Multiline' },
  { value: 'boolean', label: 'Boolean' },
]

const LAYOUT_OPTIONS = [
  { value: 'entry', label: 'Entry-based (date + details)' },
  { value: 'list', label: 'List-based (bulleted items)' },
]

function FieldEditor({ fields, onChange }: {
  fields: SectionFieldDef[]
  onChange: (fields: SectionFieldDef[]) => void
}) {
  function addField() {
    onChange([...fields, { key: '', label: '', type: 'text' }])
  }

  function removeField(index: number) {
    onChange(fields.filter((_, i) => i !== index))
  }

  function updateField(index: number, patch: Partial<SectionFieldDef>) {
    onChange(fields.map((f, i) => {
      if (i !== index) return f
      const updated = { ...f, ...patch }
      // Auto-generate key from label if key is empty or was auto-generated
      if (patch.label && (!f.key || f.key === slugify(f.label))) {
        updated.key = slugify(patch.label)
      }
      return updated
    }))
  }

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <label className="text-xs font-medium text-gray-600">Fields</label>
        <button onClick={addField} className="text-xs text-primary-600 hover:underline flex items-center gap-1">
          <Plus size={12} /> Add field
        </button>
      </div>
      {fields.length === 0 && (
        <p className="text-xs text-gray-400 py-2">No fields defined. Add at least one field.</p>
      )}
      {fields.map((field, i) => (
        <div key={i} className="flex items-center gap-2 p-2 bg-gray-50 rounded-lg border border-gray-100">
          <GripVertical size={12} className="text-gray-300 flex-shrink-0" />
          <input
            type="text"
            placeholder="Label"
            value={field.label}
            onChange={e => updateField(i, { label: e.target.value })}
            className="flex-1 px-2 py-1 text-xs border border-gray-200 rounded focus:outline-none focus:ring-1 focus:ring-primary-400"
          />
          <input
            type="text"
            placeholder="key"
            value={field.key}
            onChange={e => updateField(i, { key: e.target.value })}
            className="w-24 px-2 py-1 text-xs border border-gray-200 rounded focus:outline-none focus:ring-1 focus:ring-primary-400 font-mono"
          />
          <select
            value={field.type}
            onChange={e => updateField(i, { type: e.target.value as SectionFieldDef['type'] })}
            className="w-24 px-2 py-1 text-xs border border-gray-200 rounded focus:outline-none focus:ring-1 focus:ring-primary-400"
          >
            {FIELD_TYPES.map(t => <option key={t.value} value={t.value}>{t.label}</option>)}
          </select>
          <button onClick={() => removeField(i)} className="text-red-400 hover:text-red-600">
            <Trash2 size={12} />
          </button>
        </div>
      ))}
    </div>
  )
}

function slugify(s: string): string {
  return s.toLowerCase().replace(/[^a-z0-9]+/g, '_').replace(/^_|_$/g, '')
}

function DefinitionForm({
  initial,
  onSave,
  onCancel,
  saving,
}: {
  initial?: SectionDefinition
  onSave: (data: { label: string; layout: string; fields: SectionFieldDef[]; sort_field: string | null }) => void
  onCancel: () => void
  saving: boolean
}) {
  const [label, setLabel] = useState(initial?.label || '')
  const [layout, setLayout] = useState(initial?.layout || 'entry')
  const [fields, setFields] = useState<SectionFieldDef[]>(initial?.fields || [])
  const [sortField, setSortField] = useState(initial?.sort_field || '')

  const dateFields = fields.filter(f => f.type === 'date' && f.key)

  return (
    <div className="space-y-4">
      <Input label="Section Name" value={label} onChange={e => setLabel(e.target.value)} placeholder="e.g. Professional Development" />

      <div>
        <label className="block text-xs font-medium text-gray-600 mb-1">Layout</label>
        <select
          value={layout}
          onChange={e => setLayout(e.target.value)}
          className="w-full px-2 py-1.5 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-400"
        >
          {LAYOUT_OPTIONS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
        </select>
      </div>

      <FieldEditor fields={fields} onChange={setFields} />

      {layout === 'entry' && dateFields.length > 0 && (
        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1">Date field (for sorting & date column)</label>
          <select
            value={sortField}
            onChange={e => setSortField(e.target.value)}
            className="w-full px-2 py-1.5 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-400"
          >
            <option value="">None</option>
            {dateFields.map(f => <option key={f.key} value={f.key}>{f.label}</option>)}
          </select>
        </div>
      )}

      <div className="flex gap-2 justify-end pt-2 border-t">
        <Button variant="secondary" onClick={onCancel}>Cancel</Button>
        <Button onClick={() => onSave({ label, layout, fields, sort_field: sortField || null })} loading={saving} disabled={!label || fields.length === 0}>
          {initial ? 'Update' : 'Create'}
        </Button>
      </div>
    </div>
  )
}

export function SectionDefinitionEditor({ open, onClose }: { open: boolean; onClose: () => void }) {
  const qc = useQueryClient()
  const [editing, setEditing] = useState<SectionDefinition | null>(null)
  const [creating, setCreating] = useState(false)

  const { data: definitions = [], isLoading } = useQuery({
    queryKey: ['section-definitions'],
    queryFn: listSectionDefinitions,
    enabled: open,
  })

  const createMut = useMutation({
    mutationFn: createSectionDefinition,
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['section-definitions'] }); setCreating(false) },
  })

  const updateMut = useMutation({
    mutationFn: ({ id, ...data }: { id: number; label: string; layout: string; fields: SectionFieldDef[]; sort_field: string | null }) =>
      updateSectionDefinition(id, data),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['section-definitions'] }); setEditing(null) },
  })

  const deleteMut = useMutation({
    mutationFn: deleteSectionDefinition,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['section-definitions'] }),
  })

  if (!open) return null

  return (
    <Modal open onClose={onClose} title="Manage Custom Sections">
      {isLoading ? <Spinner /> : (
        <div className="space-y-4">
          {!creating && !editing && (
            <>
              {definitions.length === 0 ? (
                <p className="text-sm text-gray-400 text-center py-4">No custom sections yet.</p>
              ) : (
                <div className="space-y-2">
                  {definitions.map(defn => (
                    <div key={defn.id} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg border border-gray-100">
                      <div>
                        <p className="text-sm font-medium text-gray-800">{defn.label}</p>
                        <p className="text-xs text-gray-500">
                          {defn.section_key} &middot; {defn.layout} &middot; {defn.fields.length} field(s)
                        </p>
                      </div>
                      <div className="flex gap-1">
                        <button onClick={() => setEditing(defn)} className="text-gray-400 hover:text-gray-600 p-1">
                          <Edit2 size={14} />
                        </button>
                        <button
                          onClick={() => { if (confirm(`Delete "${defn.label}"?`)) deleteMut.mutate(defn.id) }}
                          className="text-red-400 hover:text-red-600 p-1"
                        >
                          <Trash2 size={14} />
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
              <Button variant="secondary" size="sm" onClick={() => setCreating(true)}>
                <Plus size={14} /> New Custom Section
              </Button>
            </>
          )}

          {creating && (
            <DefinitionForm
              onSave={data => createMut.mutate(data)}
              onCancel={() => setCreating(false)}
              saving={createMut.isPending}
            />
          )}

          {editing && (
            <DefinitionForm
              initial={editing}
              onSave={data => updateMut.mutate({ id: editing.id, ...data })}
              onCancel={() => setEditing(null)}
              saving={updateMut.isPending}
            />
          )}
        </div>
      )}
    </Modal>
  )
}

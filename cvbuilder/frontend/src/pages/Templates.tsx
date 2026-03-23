import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api, getToken, listSectionDefinitions } from '../lib/api'
import type { CVTemplate, SectionDefinition } from '../lib/api'
import { Button, Card, Input, Modal, PageHeader, Badge, Spinner, Select } from '../components/ui'
import { Plus, Trash2, Edit2, Eye, Settings, ExternalLink, Copy, Download, Upload } from 'lucide-react'
import { ALL_SECTIONS, SectionComposer, toSectionEntries } from '../components/SectionComposer'
import type { SectionEntry } from '../components/SectionComposer'
import type { PickerSection } from '../components/SectionPickerModal'
import { SectionDefinitionEditor } from '../components/SectionDefinitionEditor'

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
  harvard_fas: {
    primary_color: '#A51C30', accent_color: '#A51C30',
    font_body: '"Times New Roman", Times, serif',
    font_heading: '"Times New Roman", Times, serif',
    body_font_size: '11pt', heading_font_size: '12pt',
    name_font_size: '14pt', header_alignment: 'left',
    section_decoration: 'bottom-border', heading_transform: 'none',
    text_color: '#111111', muted_color: '#555555', border_color: '#A51C30',
    page_width: '8.5in', page_padding: '1in',
    date_column_width: '1.3in', header_border_style: 'none',
    name_font_weight: 'bold', name_letter_spacing: '0.02em',
    section_margin_bottom: '1.2em', heading_letter_spacing: '0',
    line_height: '1.15',
  },
  harvard_med: {
    primary_color: '#111111', accent_color: '#111111',
    font_body: '"Times New Roman", Times, serif',
    font_heading: '"Times New Roman", Times, serif',
    body_font_size: '12pt', heading_font_size: '12pt',
    name_font_size: '12pt', header_alignment: 'left',
    section_decoration: 'none', heading_transform: 'none',
    text_color: '#111111', muted_color: '#555555', border_color: '#aaaaaa',
    page_width: '8.5in', page_padding: '1in',
    date_column_width: '1.3in', header_border_style: 'none',
    name_font_weight: 'bold', name_letter_spacing: '0',
    section_margin_bottom: '1.0em', heading_letter_spacing: '0',
    line_height: '1.3',
  },
  stanford_med: {
    primary_color: '#8C1515', accent_color: '#8C1515',
    font_body: '"Source Sans Pro", Helvetica, Arial, sans-serif',
    font_heading: '"Source Sans Pro", Helvetica, Arial, sans-serif',
    body_font_size: '11pt', heading_font_size: '11pt',
    name_font_size: '14pt', header_alignment: 'left',
    section_decoration: 'bottom-border', heading_transform: 'uppercase',
    text_color: '#111111', muted_color: '#555555', border_color: '#8C1515',
    page_width: '8.5in', page_padding: '1in',
    date_column_width: '1.3in', header_border_style: 'none',
    name_font_weight: 'bold', name_letter_spacing: '0.02em',
    section_margin_bottom: '1.2em', heading_letter_spacing: '0.06em',
    line_height: '1.45',
  },
  mit: {
    primary_color: '#750014', accent_color: '#750014',
    font_body: '"Helvetica Neue", Helvetica, Arial, sans-serif',
    font_heading: '"Helvetica Neue", Helvetica, Arial, sans-serif',
    body_font_size: '11pt', heading_font_size: '12pt',
    name_font_size: '14pt', header_alignment: 'left',
    section_decoration: 'none', heading_transform: 'uppercase',
    text_color: '#111111', muted_color: '#555555', border_color: '#cccccc',
    page_width: '8.5in', page_padding: '1in',
    date_column_width: '1.3in', header_border_style: 'none',
    name_font_weight: 'bold', name_letter_spacing: '0.02em',
    section_margin_bottom: '1.2em', heading_letter_spacing: '0.06em',
    line_height: '1.45',
  },
  michigan_eng: {
    primary_color: '#00274C', accent_color: '#FFCB05',
    font_body: '"Georgia", serif',
    font_heading: '"Arial", Helvetica, sans-serif',
    body_font_size: '11pt', heading_font_size: '14pt',
    name_font_size: '16pt', header_alignment: 'center',
    section_decoration: 'none', heading_transform: 'none',
    text_color: '#111111', muted_color: '#555555', border_color: '#00274C',
    page_width: '8.5in', page_padding: '1in',
    date_column_width: '1.3in', header_border_style: 'none',
    name_font_weight: 'bold', name_letter_spacing: '0.02em',
    section_margin_bottom: '1.2em', heading_letter_spacing: '0',
    line_height: '1.5',
  },
  columbia_cuimc: {
    primary_color: '#1D4F91', accent_color: '#1D4F91',
    font_body: '"Times New Roman", Times, serif',
    font_heading: '"Times New Roman", Times, serif',
    body_font_size: '11pt', heading_font_size: '12pt',
    name_font_size: '14pt', header_alignment: 'left',
    section_decoration: 'none', heading_transform: 'none',
    text_color: '#111111', muted_color: '#555555', border_color: '#1D4F91',
    page_width: '8.5in', page_padding: '1in',
    date_column_width: '1.3in', header_border_style: 'none',
    name_font_weight: 'bold', name_letter_spacing: '0.02em',
    section_margin_bottom: '1.0em', heading_letter_spacing: '0',
    line_height: '1.4',
  },
  imperial: {
    primary_color: '#003E74', accent_color: '#003E74',
    font_body: '"Arial", Helvetica, sans-serif',
    font_heading: '"Arial", Helvetica, sans-serif',
    body_font_size: '11pt', heading_font_size: '12pt',
    name_font_size: '16pt', header_alignment: 'left',
    section_decoration: 'bottom-border', heading_transform: 'uppercase',
    text_color: '#111111', muted_color: '#555555', border_color: '#003E74',
    page_width: '8.27in', page_padding: '1in 0.75in',
    date_column_width: '1.2in', header_border_style: '2px solid',
    name_font_weight: 'bold', name_letter_spacing: '0.02em',
    section_margin_bottom: '1.2em', heading_letter_spacing: '0.04em',
    line_height: '1.4',
  },
  oxford: {
    primary_color: '#002147', accent_color: '#002147',
    font_body: '"Times New Roman", Times, serif',
    font_heading: '"Times New Roman", Times, serif',
    body_font_size: '11pt', heading_font_size: '12pt',
    name_font_size: '14pt', header_alignment: 'left',
    section_decoration: 'bottom-border', heading_transform: 'uppercase',
    text_color: '#111111', muted_color: '#555555', border_color: '#002147',
    page_width: '8.27in', page_padding: '1in 0.75in',
    date_column_width: '1.2in', header_border_style: 'none',
    name_font_weight: 'bold', name_letter_spacing: '0.02em',
    section_margin_bottom: '1.2em', heading_letter_spacing: '0',
    line_height: '1.4',
  },
  hku: {
    primary_color: '#005A32', accent_color: '#005A32',
    font_body: '"Arial", Helvetica, sans-serif',
    font_heading: '"Arial", Helvetica, sans-serif',
    body_font_size: '11pt', heading_font_size: '12pt',
    name_font_size: '14pt', header_alignment: 'left',
    section_decoration: 'bottom-border', heading_transform: 'none',
    text_color: '#111111', muted_color: '#555555', border_color: '#005A32',
    page_width: '8.27in', page_padding: '1in 0.75in',
    date_column_width: '1.2in', header_border_style: 'none',
    name_font_weight: 'bold', name_letter_spacing: '0.02em',
    section_margin_bottom: '1.1em', heading_letter_spacing: '0',
    line_height: '1.4',
  },
  melbourne: {
    primary_color: '#094183', accent_color: '#094183',
    font_body: '"Times New Roman", Times, serif',
    font_heading: '"Arial", Helvetica, sans-serif',
    body_font_size: '12pt', heading_font_size: '12pt',
    name_font_size: '16pt', header_alignment: 'left',
    section_decoration: 'bottom-border', heading_transform: 'none',
    text_color: '#111111', muted_color: '#555555', border_color: '#094183',
    page_width: '8.27in', page_padding: '0.79in',
    date_column_width: '1.2in', header_border_style: '2px solid',
    name_font_weight: 'bold', name_letter_spacing: '0.02em',
    section_margin_bottom: '1.2em', heading_letter_spacing: '0.04em',
    line_height: '1.45',
  },
}

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
              ['subgroup_font_size', 'Sub-heading size'],
              ['section_indent_per_level', 'Indent / level'],
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

function TemplateComposer({ template, onClose, customSections }: { template: CVTemplate; onClose: () => void; customSections: PickerSection[] }) {
  const qc = useQueryClient()
  const [name, setName] = useState(template.name)
  const [description, setDescription] = useState(template.description || '')
  const [style, setStyle] = useState<Record<string, string>>(template.style || THEME_PRESETS.academic)
  const [sortDirection, setSortDirection] = useState(template.sort_direction ?? 'desc')
  const [author, setAuthor] = useState(template.author || '')
  const [authorContact, setAuthorContact] = useState(template.author_contact || '')
  const [guidanceUrl, setGuidanceUrl] = useState(template.guidance_url || '')

  const initialSections = toSectionEntries(
    template.sections,
    (s, i): SectionEntry => {
      const meta = ALL_SECTIONS.find(m => m.key === s.section_key) || customSections.find(m => m.key === s.section_key)
      return {
        section_key: s.section_key,
        label: s.section_key === 'group_heading'
          ? (s.config?.heading as string || 'Group Heading')
          : (meta?.label || s.section_key),
        enabled: true,
        section_order: s.section_order ?? i,
        heading: (s.config?.heading as string) || '',
        config: { ...s.config },
        extra: { id: s.id ?? 0 },
        depth: s.depth ?? 0,
      }
    },
  )

  const [sections, setSections] = useState(initialSections)
  const [preview, setPreview] = useState(false)

  const saveMut = useMutation({
    mutationFn: () => api.put(`/templates/${template.id}`, {
      name, description: description || null, style,
      sort_direction: sortDirection,
      author: author || null, author_contact: authorContact || null,
      guidance_url: guidanceUrl || null,
      sections: sections.map((s, i) => ({
        section_key: s.section_key,
        enabled: true,
        section_order: i,
        config: { ...s.config, heading: s.heading },
        depth: s.depth,
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

        <details className="border border-gray-200 rounded-lg">
          <summary className="px-3 py-2 text-sm font-medium text-gray-700 cursor-pointer hover:bg-gray-50">Template Metadata</summary>
          <div className="px-3 pb-3 space-y-3">
            <div className="grid grid-cols-2 gap-4">
              <Input label="Author" value={author} onChange={e => setAuthor(e.target.value)} placeholder="e.g. CVBuilder" />
              <Input label="Author Contact" value={authorContact} onChange={e => setAuthorContact(e.target.value)} placeholder="e.g. email or URL" />
            </div>
            <Input label="Guidance URL" value={guidanceUrl} onChange={e => setGuidanceUrl(e.target.value)} placeholder="URL to institutional CV guidelines" />
            {template.created_at && (
              <p className="text-xs text-gray-500">Created: {new Date(template.created_at).toLocaleDateString()}</p>
            )}
          </div>
        </details>

        <StyleEditor style={style} onChange={setStyle} />

        <SectionComposer sections={sections} onChange={setSections} customSections={customSections} templateId={template.id} />

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
  const [managingCustom, setManagingCustom] = useState(false)
  const [importFile, setImportFile] = useState<File | null>(null)

  const { data = [], isLoading } = useQuery<CVTemplate[]>({
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
    mutationFn: () => {
      // Determine initial style: copy from existing template or use academic defaults
      let initialStyle = THEME_PRESETS.academic
      if (copyStyleFrom) {
        const source = data.find(t => String(t.id) === copyStyleFrom)
        if (source?.style) initialStyle = source.style
      }
      return api.post('/templates', {
        name: newName, style: initialStyle, sort_direction: 'desc',
        sections: [],
      })
    },
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['templates'] }); setCreating(false); setNewName(''); setCopyStyleFrom('') },
  })

  const deleteMut = useMutation({
    mutationFn: (id: number) => api.delete(`/templates/${id}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['templates'] }),
  })

  const copyMut = useMutation({
    mutationFn: (id: number) => api.post(`/templates/${id}/copy`).then(r => r.data as CVTemplate),
    onSuccess: (newTmpl) => {
      qc.invalidateQueries({ queryKey: ['templates'] })
      setComposing(newTmpl)
    },
  })

  const exportYaml = (id: number) => {
    const token = getToken()
    window.open(`/api/templates/${id}/export-definition?token=${encodeURIComponent(token || '')}`, '_blank')
  }

  const importMut = useMutation({
    mutationFn: (file: File) => {
      const form = new FormData()
      form.append('file', file)
      return api.post('/templates/import-definition', form, {
        headers: { 'Content-Type': 'multipart/form-data' },
      }).then(r => r.data as CVTemplate)
    },
    onSuccess: (newTmpl) => {
      qc.invalidateQueries({ queryKey: ['templates'] })
      setCreating(false)
      setImportFile(null)
      setComposing(newTmpl)
    },
  })

  if (isLoading) return <div className="p-8"><Spinner /></div>

  const systemTemplates = data.filter(t => t.is_system)
  const userTemplates = data.filter(t => !t.is_system)

  return (
    <div className="p-8">
      <PageHeader
        title="Templates"
        subtitle="Define section layout, order, and style for your CVs"
        actions={
          <div className="flex gap-2">
            <Button variant="secondary" onClick={() => setManagingCustom(true)}><Settings size={16} /> Custom Sections</Button>
            <Button onClick={() => setCreating(true)}><Plus size={16} /> New Template</Button>
          </div>
        }
      />

      {/* User templates */}
      {userTemplates.length > 0 && (
        <>
          <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-3">My Templates</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mb-8">
            {userTemplates.map(tmpl => (
              <Card key={tmpl.id} className="p-5">
                <div className="flex items-start justify-between mb-2">
                  <div>
                    <h3 className="font-semibold text-gray-900">{tmpl.name}</h3>
                    <div className="flex gap-1 mt-1 items-center">
                      {tmpl.style?.primary_color && (
                        <span className="inline-block w-3 h-3 rounded-full border border-gray-300" style={{ backgroundColor: tmpl.style.primary_color }} />
                      )}
                      <Badge color="gray">{tmpl.sections.filter(s => s.section_key !== 'group_heading').length} sections</Badge>
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
                {(tmpl.author || tmpl.guidance_url) && (
                  <div className="text-xs text-gray-400 mb-3 space-y-0.5">
                    {tmpl.author && <p>By {tmpl.author}{tmpl.author_contact ? ` · ${tmpl.author_contact}` : ''}</p>}
                    {tmpl.guidance_url && (
                      <a href={tmpl.guidance_url} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 text-blue-500 hover:underline">
                        Guidance <ExternalLink size={10} />
                      </a>
                    )}
                  </div>
                )}
                <div className="flex gap-2">
                  <Button variant="secondary" size="sm" onClick={() => setComposing(tmpl)}>
                    <Edit2 size={12} /> Edit
                  </Button>
                  <a href={`/api/templates/${tmpl.id}/preview?token=${encodeURIComponent(getToken() || '')}`} target="_blank" rel="noreferrer">
                    <Button variant="ghost" size="sm"><Eye size={12} /> Preview</Button>
                  </a>
                  <Button variant="ghost" size="sm" onClick={() => exportYaml(tmpl.id)}>
                    <Download size={12} /> YAML
                  </Button>
                </div>
              </Card>
            ))}
          </div>
        </>
      )}

      {/* System templates */}
      {systemTemplates.length > 0 && (
        <>
          <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-3">System Templates</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mb-8">
            {systemTemplates.map(tmpl => (
              <Card key={tmpl.id} className="p-5">
                <div className="flex items-start justify-between mb-2">
                  <div>
                    <h3 className="font-semibold text-gray-900">{tmpl.name}</h3>
                    <div className="flex gap-1 mt-1 items-center">
                      {tmpl.style?.primary_color && (
                        <span className="inline-block w-3 h-3 rounded-full border border-gray-300" style={{ backgroundColor: tmpl.style.primary_color }} />
                      )}
                      <Badge color="purple">System</Badge>
                      <Badge color="gray">{tmpl.sections.filter(s => s.section_key !== 'group_heading').length} sections</Badge>
                    </div>
                  </div>
                </div>
                {tmpl.description && <p className="text-xs text-gray-500 mb-3">{tmpl.description}</p>}
                {(tmpl.author || tmpl.guidance_url) && (
                  <div className="text-xs text-gray-400 mb-3 space-y-0.5">
                    {tmpl.author && <p>By {tmpl.author}{tmpl.author_contact ? ` · ${tmpl.author_contact}` : ''}</p>}
                    {tmpl.guidance_url && (
                      <a href={tmpl.guidance_url} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 text-blue-500 hover:underline">
                        Guidance <ExternalLink size={10} />
                      </a>
                    )}
                  </div>
                )}
                <div className="flex gap-2">
                  <Button variant="secondary" size="sm" onClick={() => copyMut.mutate(tmpl.id)} loading={copyMut.isPending}>
                    <Copy size={12} /> Copy
                  </Button>
                  <a href={`/api/templates/${tmpl.id}/preview?token=${encodeURIComponent(getToken() || '')}`} target="_blank" rel="noreferrer">
                    <Button variant="ghost" size="sm"><Eye size={12} /> Preview</Button>
                  </a>
                  <Button variant="ghost" size="sm" onClick={() => exportYaml(tmpl.id)}>
                    <Download size={12} /> YAML
                  </Button>
                </div>
              </Card>
            ))}
          </div>
        </>
      )}

      {data.length === 0 && (
        <div className="py-16 text-center text-gray-400 text-sm">
          No templates yet. Create one to get started.
        </div>
      )}

      {/* Create modal */}
      <Modal open={creating} onClose={() => { setCreating(false); setImportFile(null) }} title="New Template">
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
          <p className="text-sm text-gray-500">You can add sections in the composer after creating the template.</p>
          <div className="flex gap-2 justify-end">
            <Button variant="secondary" onClick={() => setCreating(false)}>Cancel</Button>
            <Button onClick={() => createMut.mutate()} loading={createMut.isPending} disabled={!newName}>
              Create Template
            </Button>
          </div>

          <div className="relative flex items-center py-2">
            <div className="flex-grow border-t border-gray-300" />
            <span className="mx-3 text-xs text-gray-400">or</span>
            <div className="flex-grow border-t border-gray-300" />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Import from YAML file</label>
            <input
              type="file"
              accept=".yml,.yaml"
              onChange={e => setImportFile(e.target.files?.[0] || null)}
              className="block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-sm file:font-semibold file:bg-primary-50 file:text-primary-700 hover:file:bg-primary-100"
            />
          </div>
          {importFile && (
            <div className="flex gap-2 justify-end">
              <Button variant="secondary" onClick={() => setImportFile(null)}>Cancel</Button>
              <Button onClick={() => importMut.mutate(importFile)} loading={importMut.isPending}>
                <Upload size={14} /> Import Template
              </Button>
            </div>
          )}
        </div>
      </Modal>

      {/* Composer modal */}
      {composing && (
        <Modal open={!!composing} onClose={() => setComposing(null)} title={`Compose: ${composing.name}`}>
          <TemplateComposer template={composing} onClose={() => setComposing(null)} customSections={customPickerSections} />
        </Modal>
      )}

      {/* Custom section definitions editor */}
      <SectionDefinitionEditor open={managingCustom} onClose={() => setManagingCustom(false)} />
    </div>
  )
}

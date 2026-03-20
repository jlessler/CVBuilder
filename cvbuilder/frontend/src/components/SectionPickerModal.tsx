import { useState, useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import { api } from '../lib/api'
import type { CVTemplate } from '../lib/api'
import { Modal, Button, Spinner } from './ui'
import { Search, ChevronDown, ChevronRight, Layers, Download } from 'lucide-react'
import { ALL_SECTIONS } from './SectionComposer'
import type { SectionEntry } from './SectionComposer'

export type PickerSection = {
  key: string
  label: string
  group?: string
}

type PickerTab = 'sections' | 'import'

const GROUPS = [
  'Education & Experience',
  'Publications',
  'Teaching & Mentorship',
  'Grants & Awards',
  'Service',
  'Other',
]

const GROUP_MAP: Record<string, string> = {
  education: 'Education & Experience',
  experience: 'Education & Experience',
  consulting: 'Education & Experience',
  dissertation: 'Education & Experience',
  memberships: 'Education & Experience',
  publications_papers: 'Publications',
  publications_preprints: 'Publications',
  publications_chapters: 'Publications',
  publications_letters: 'Publications',
  publications_scimeetings: 'Publications',
  publications_editorials: 'Publications',
  patents: 'Publications',
  citation_metrics: 'Publications',
  classes: 'Teaching & Mentorship',
  trainees_advisees: 'Teaching & Mentorship',
  trainees_postdocs: 'Teaching & Mentorship',
  mentorship: 'Teaching & Mentorship',
  departmentalOrals: 'Teaching & Mentorship',
  finaldefense: 'Teaching & Mentorship',
  schoolwideOrals: 'Teaching & Mentorship',
  grants: 'Grants & Awards',
  awards: 'Grants & Awards',
  panels_advisory: 'Service',
  panels_grantreview: 'Service',
  committees: 'Service',
  editorial: 'Service',
  peerrev: 'Service',
  otherservice: 'Service',
  seminars: 'Other',
  symposia: 'Other',
  press: 'Other',
  software: 'Other',
  policypres: 'Other',
  policycons: 'Other',
  otherpractice: 'Other',
  chairedsessions: 'Other',
}

// ---------------------------------------------------------------------------
// Import from Template sub-view
// ---------------------------------------------------------------------------

interface SectionGroup {
  heading: SectionEntry
  children: SectionEntry[]
}

function groupSections(sections: SectionEntry[]): SectionGroup[] {
  const groups: SectionGroup[] = []
  let currentGroup: SectionGroup | null = null

  for (const sec of sections) {
    if (sec.section_key === 'group_heading') {
      if (currentGroup && sec.depth <= currentGroup.heading.depth) {
        groups.push(currentGroup)
        currentGroup = null
      }
      currentGroup = { heading: sec, children: [] }
    } else if (currentGroup) {
      currentGroup.children.push(sec)
    }
  }
  if (currentGroup) groups.push(currentGroup)
  return groups
}

function TemplateImportRow({
  template,
  customSections,
  onImport,
}: {
  template: CVTemplate
  customSections: PickerSection[]
  onImport: (sections: SectionEntry[]) => void
}) {
  const [expanded, setExpanded] = useState(false)
  const [selected, setSelected] = useState<Set<number>>(new Set())

  const entries: SectionEntry[] = template.sections.map((s, i) => {
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
      extra: {},
      depth: s.depth ?? 0,
    }
  })

  const groups = groupSections(entries)

  function toggleGroup(idx: number) {
    setSelected(prev => {
      const next = new Set(prev)
      if (next.has(idx)) next.delete(idx)
      else next.add(idx)
      return next
    })
  }

  function handleImport() {
    const toImport: SectionEntry[] = []
    for (const idx of selected) {
      const group = groups[idx]
      if (!group) continue
      toImport.push(group.heading)
      for (const child of group.children) {
        toImport.push(child)
      }
    }
    onImport(toImport)
  }

  if (groups.length === 0) {
    return (
      <div className="p-3 bg-gray-50 rounded-lg border border-gray-100">
        <p className="text-sm text-gray-600">{template.name}</p>
        <p className="text-xs text-gray-400">No group headings to import</p>
      </div>
    )
  }

  return (
    <div className="border border-gray-200 rounded-lg overflow-hidden">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center gap-2 px-3 py-2.5 bg-gray-50 hover:bg-gray-100 transition-colors text-left"
      >
        {expanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
        <span className="text-sm font-medium text-gray-800">{template.name}</span>
        <span className="text-xs text-gray-400 ml-auto">{groups.length} group(s)</span>
      </button>

      {expanded && (
        <div className="px-3 py-2 space-y-1.5">
          {groups.map((group, idx) => (
            <label key={idx} className="flex items-start gap-2 py-1.5 cursor-pointer hover:bg-gray-50 rounded px-1">
              <input
                type="checkbox"
                className="mt-0.5 rounded border-gray-300 text-primary-600 focus:ring-primary-500"
                checked={selected.has(idx)}
                onChange={() => toggleGroup(idx)}
              />
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-1.5">
                  <Layers size={12} className="text-blue-500 flex-shrink-0" />
                  <span className="text-sm font-medium text-gray-800">{group.heading.heading || '(untitled heading)'}</span>
                </div>
                {group.children.length > 0 && (
                  <p className="text-xs text-gray-500 ml-5 mt-0.5">
                    {group.children.map(c => c.label).join(', ')}
                  </p>
                )}
              </div>
            </label>
          ))}

          {selected.size > 0 && (
            <div className="pt-2 border-t border-gray-100">
              <Button size="sm" onClick={handleImport}>
                Import {selected.size} group(s)
              </Button>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

function ImportFromTemplateView({
  currentTemplateId,
  customSections,
  onImport,
}: {
  currentTemplateId?: number
  customSections: PickerSection[]
  onImport: (sections: SectionEntry[]) => void
}) {
  const { data: templates = [], isLoading } = useQuery<CVTemplate[]>({
    queryKey: ['templates'],
    queryFn: () => api.get('/templates').then(r => r.data),
  })

  const otherTemplates = templates.filter(t => t.id !== currentTemplateId)

  if (isLoading) return <Spinner />

  if (otherTemplates.length === 0) {
    return <p className="text-sm text-gray-400 text-center py-4">No other templates to import from.</p>
  }

  return (
    <div className="space-y-3">
      <p className="text-xs text-gray-500">
        Select group headings and their children to import into the current template.
      </p>
      {otherTemplates.map(t => (
        <TemplateImportRow
          key={t.id}
          template={t}
          customSections={customSections}
          onImport={onImport}
        />
      ))}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Main picker modal
// ---------------------------------------------------------------------------

export function SectionPickerModal({
  availableSections,
  existingKeys,
  onSelect,
  onClose,
  currentTemplateId,
  customSections,
  onImportSections,
}: {
  availableSections: PickerSection[]
  existingKeys?: Set<string>
  onSelect: (section: PickerSection) => void
  onClose: () => void
  currentTemplateId?: number
  customSections?: PickerSection[]
  onImportSections?: (sections: SectionEntry[]) => void
}) {
  const [search, setSearch] = useState('')
  const [activeTab, setActiveTab] = useState<PickerTab>('sections')

  const filtered = useMemo(() => {
    if (!search.trim()) return availableSections
    const q = search.toLowerCase()
    return availableSections.filter(s => s.label.toLowerCase().includes(q) || s.key.toLowerCase().includes(q))
  }, [availableSections, search])

  const grouped = useMemo(() => {
    const groups: Record<string, PickerSection[]> = {}
    for (const sec of filtered) {
      const g = sec.group || GROUP_MAP[sec.key] || 'Other'
      if (!groups[g]) groups[g] = []
      groups[g].push(sec)
    }
    return groups
  }, [filtered])

  const showImportTab = !!onImportSections

  return (
    <Modal open onClose={onClose} title="Add Section">
      <div className="space-y-3">
        {/* Tab bar */}
        {showImportTab && (
          <div className="flex gap-1 border-b border-gray-200">
            <button
              onClick={() => setActiveTab('sections')}
              className={`px-4 py-2 text-sm font-medium -mb-px transition-colors ${
                activeTab === 'sections'
                  ? 'border-b-2 border-primary-600 text-primary-700'
                  : 'text-gray-500 hover:text-gray-700'
              }`}
            >
              Sections
            </button>
            <button
              onClick={() => setActiveTab('import')}
              className={`px-4 py-2 text-sm font-medium -mb-px transition-colors flex items-center gap-1.5 ${
                activeTab === 'import'
                  ? 'border-b-2 border-primary-600 text-primary-700'
                  : 'text-gray-500 hover:text-gray-700'
              }`}
            >
              <Download size={14} /> Import from Template
            </button>
          </div>
        )}

        {activeTab === 'sections' && (
          <>
            <div className="relative">
              <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
              <input
                autoFocus
                type="text"
                placeholder="Search sections..."
                value={search}
                onChange={e => setSearch(e.target.value)}
                className="w-full pl-9 pr-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-400"
              />
            </div>

            {filtered.length === 0 ? (
              <p className="text-sm text-gray-400 text-center py-4">
                {search ? 'No matching sections found.' : 'All sections have been added.'}
              </p>
            ) : (
              <div className="max-h-96 overflow-y-auto space-y-4">
                {GROUPS.filter(g => grouped[g]?.length).map(group => (
                  <div key={group}>
                    <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1">{group}</p>
                    <div className="space-y-0.5">
                      {grouped[group].map(sec => (
                        <button
                          key={sec.key}
                          onClick={() => onSelect(sec)}
                          className="w-full text-left px-3 py-2 text-sm rounded-lg hover:bg-primary-50 hover:text-primary-700 transition-colors"
                        >
                          {sec.label}
                          {sec.group === 'Custom' && (
                            <span className="ml-2 text-xs text-purple-500 font-medium">Custom</span>
                          )}
                        </button>
                      ))}
                    </div>
                  </div>
                ))}
                {/* Render any groups not in GROUPS (e.g. 'Custom') */}
                {Object.keys(grouped).filter(g => !GROUPS.includes(g)).map(group => (
                  <div key={group}>
                    <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1">{group}</p>
                    <div className="space-y-0.5">
                      {grouped[group].map(sec => (
                        <button
                          key={sec.key}
                          onClick={() => onSelect(sec)}
                          className="w-full text-left px-3 py-2 text-sm rounded-lg hover:bg-primary-50 hover:text-primary-700 transition-colors"
                        >
                          {sec.label}
                          <span className="ml-2 text-xs text-purple-500 font-medium">Custom</span>
                        </button>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </>
        )}

        {activeTab === 'import' && onImportSections && (
          <ImportFromTemplateView
            currentTemplateId={currentTemplateId}
            customSections={customSections || []}
            onImport={(imported) => { onImportSections(imported); onClose() }}
          />
        )}
      </div>
    </Modal>
  )
}

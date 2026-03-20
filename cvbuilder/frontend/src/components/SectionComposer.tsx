import { useState, useMemo } from 'react'
import { Button, Badge } from './ui'
import { GripVertical, ChevronDown, ChevronRight, Layers, Trash2, IndentIncrease, IndentDecrease, Plus } from 'lucide-react'
import {
  DndContext, closestCenter, PointerSensor, useSensor, useSensors,
} from '@dnd-kit/core'
import type { DragEndEvent } from '@dnd-kit/core'
import {
  SortableContext, verticalListSortingStrategy, useSortable, arrayMove,
} from '@dnd-kit/sortable'
import { CSS } from '@dnd-kit/utilities'
import { SectionPickerModal } from './SectionPickerModal'
import type { PickerSection } from './SectionPickerModal'

export const ALL_SECTIONS: PickerSection[] = [
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
  { key: 'mentorship', label: 'Mentorship' },
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
  { key: 'citation_metrics', label: 'Citation Metrics' },
  { key: 'otherpractice', label: 'Other Practice Activities' },
  { key: 'departmentalOrals', label: 'Departmental Oral Exams' },
  { key: 'finaldefense', label: 'Final Dissertation Defenses' },
  { key: 'schoolwideOrals', label: 'School-wide Oral Exams' },
]

const PUB_CROSSREF_SECTIONS = ['publications_papers', 'publications_preprints']

export type SectionEntry = {
  section_key: string
  label: string
  enabled: boolean
  section_order: number
  heading: string
  config: Record<string, unknown>
  extra: Record<string, unknown>
  depth: number
}

/** @deprecated Use `toSectionEntries` instead — sections are no longer padded with missing entries */
export function buildInitialSections<T>(
  existingSections: T[],
  toEntry: (s: T, index: number) => SectionEntry,
): SectionEntry[] {
  return existingSections.map(toEntry)
}

/** Convert raw API section data to SectionEntry array (no padding with missing sections) */
export function toSectionEntries<T>(
  existingSections: T[],
  toEntry: (s: T, index: number) => SectionEntry,
): SectionEntry[] {
  return existingSections.map(toEntry)
}

// ---------------------------------------------------------------------------
// Sortable row internals
// ---------------------------------------------------------------------------

function SortableGroupHeadingRow({
  section, sortableId, onHeadingChange, onDelete, onDepthChange,
}: {
  section: SectionEntry
  sortableId: string
  onHeadingChange: (h: string) => void
  onDelete: () => void
  onDepthChange: (depth: number) => void
}) {
  const { attributes, listeners, setNodeRef, transform, transition } = useSortable({ id: sortableId })

  return (
    <div
      ref={setNodeRef}
      style={{ transform: CSS.Transform.toString(transform), transition, marginLeft: `${section.depth * 1.5}rem` }}
      className="rounded-lg border mb-1.5 bg-blue-50 border-blue-200"
    >
      <div className="flex items-center gap-3 px-4 py-2.5">
        <button {...attributes} {...listeners} className="cursor-grab text-gray-400 hover:text-gray-600">
          <GripVertical size={16} />
        </button>
        <Layers size={14} className="text-blue-500 flex-shrink-0" />
        <div className="flex-1 min-w-0">
          <input
            className="w-full px-2 py-1 text-sm font-semibold border border-blue-200 rounded bg-white focus:outline-none focus:ring-1 focus:ring-blue-400"
            placeholder="Group heading text..."
            value={section.heading}
            onChange={e => onHeadingChange(e.target.value)}
          />
        </div>
        <div className="flex gap-0.5">
          <button
            onClick={() => onDepthChange(Math.max(0, section.depth - 1))}
            className="text-gray-400 hover:text-gray-600 disabled:opacity-30"
            disabled={section.depth === 0}
            title="Outdent"
          >
            <IndentDecrease size={14} />
          </button>
          <button
            onClick={() => onDepthChange(Math.min(3, section.depth + 1))}
            className="text-gray-400 hover:text-gray-600 disabled:opacity-30"
            disabled={section.depth >= 3}
            title="Indent"
          >
            <IndentIncrease size={14} />
          </button>
        </div>
        <button onClick={onDelete} className="text-red-400 hover:text-red-600">
          <Trash2 size={14} />
        </button>
      </div>
    </div>
  )
}

function SortableDataRow({
  section, sortableId, onHeadingChange, onConfigChange,
  onDepthChange, onRemove, renderExpandedContent, renderBadges, alwaysExpandable,
}: {
  section: SectionEntry
  sortableId: string
  onHeadingChange: (h: string) => void
  onConfigChange: (config: Record<string, unknown>) => void
  onDepthChange: (depth: number) => void
  onRemove: () => void
  renderExpandedContent?: () => React.ReactNode
  renderBadges?: () => React.ReactNode
  alwaysExpandable?: boolean
}) {
  const [expanded, setExpanded] = useState(false)
  const { attributes, listeners, setNodeRef, transform, transition } = useSortable({ id: sortableId })
  const hasCrossrefOptions = PUB_CROSSREF_SECTIONS.includes(section.section_key)
  const isPreprints = section.section_key === 'publications_preprints'
  const isExpandable = alwaysExpandable || hasCrossrefOptions

  return (
    <div
      ref={setNodeRef}
      style={{ transform: CSS.Transform.toString(transform), transition, marginLeft: `${section.depth * 1.5}rem` }}
      className="rounded-lg border mb-1.5 bg-white border-gray-200"
    >
      <div className="flex items-center gap-3 px-4 py-2.5">
        <button {...attributes} {...listeners} className="cursor-grab text-gray-400 hover:text-gray-600">
          <GripVertical size={16} />
        </button>
        {isExpandable && (
          <button
            className="text-gray-400 hover:text-gray-600"
            onClick={() => setExpanded(!expanded)}
          >
            {expanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
          </button>
        )}
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium text-gray-800">{section.label}</p>
        </div>
        {renderBadges?.()}
        <div className="flex gap-0.5">
          <button
            onClick={() => onDepthChange(Math.max(0, section.depth - 1))}
            className="text-gray-400 hover:text-gray-600 disabled:opacity-30"
            disabled={section.depth === 0}
            title="Outdent"
          >
            <IndentDecrease size={14} />
          </button>
          <button
            onClick={() => onDepthChange(Math.min(3, section.depth + 1))}
            className="text-gray-400 hover:text-gray-600 disabled:opacity-30"
            disabled={section.depth >= 3}
            title="Indent"
          >
            <IndentIncrease size={14} />
          </button>
        </div>
        <input
          className="w-40 px-2 py-1 text-xs border border-gray-200 rounded focus:outline-none focus:ring-1 focus:ring-primary-400"
          placeholder="Section heading..."
          value={section.heading}
          onChange={e => onHeadingChange(e.target.value)}
        />
        <button onClick={onRemove} className="text-red-400 hover:text-red-600" title="Remove section">
          <Trash2 size={14} />
        </button>
      </div>
      {expanded && (
        <div className="border-t border-gray-100">
          {hasCrossrefOptions && (
            <div className="px-4 py-2 border-b border-gray-100 space-y-1">
              <label className="flex items-center gap-1.5 text-xs text-gray-500 cursor-pointer">
                <input
                  type="checkbox"
                  className="rounded border-gray-300"
                  checked={section.config.show_crossref !== false}
                  onChange={e => onConfigChange({ ...section.config, show_crossref: e.target.checked })}
                />
                Show cross-ref DOI
              </label>
              {isPreprints && (
                <label className="flex items-center gap-1.5 text-xs text-gray-500 cursor-pointer">
                  <input
                    type="checkbox"
                    className="rounded border-gray-300"
                    checked={!!section.config.hide_if_published}
                    onChange={e => onConfigChange({ ...section.config, hide_if_published: e.target.checked })}
                  />
                  Hide if published version exists
                </label>
              )}
            </div>
          )}
          {renderExpandedContent?.()}
        </div>
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Main SectionComposer component
// ---------------------------------------------------------------------------

export function SectionComposer({
  sections, onChange, renderExpandedContent, renderBadges, sectionLabel,
  customSections, templateId,
}: {
  sections: SectionEntry[]
  onChange: (sections: SectionEntry[]) => void
  renderExpandedContent?: (section: SectionEntry, index: number) => React.ReactNode
  renderBadges?: (section: SectionEntry, index: number) => React.ReactNode
  sectionLabel?: string
  customSections?: PickerSection[]
  templateId?: number
}) {
  const [pickerOpen, setPickerOpen] = useState(false)
  const sensors = useSensors(useSensor(PointerSensor))
  const sortableIds = sections.map((_, i) => `row_${i}`)

  const allPickerSections = useMemo(() => {
    const custom = (customSections || []).map(s => ({ ...s, group: s.group || 'Custom' }))
    return [...ALL_SECTIONS, ...custom]
  }, [customSections])

  function handleDragEnd(event: DragEndEvent) {
    const { active, over } = event
    if (over && active.id !== over.id) {
      const oldIndex = sortableIds.indexOf(active.id as string)
      const newIndex = sortableIds.indexOf(over.id as string)
      onChange(arrayMove(sections, oldIndex, newIndex))
    }
  }

  function addGroupHeading() {
    onChange([
      ...sections,
      {
        section_key: 'group_heading',
        label: 'Group Heading',
        enabled: true,
        section_order: sections.length,
        heading: '',
        config: {},
        extra: {},
        depth: 0,
      },
    ])
  }

  function addSection(picked: PickerSection) {
    onChange([
      ...sections,
      {
        section_key: picked.key,
        label: picked.label,
        enabled: true,
        section_order: sections.length,
        heading: '',
        config: {},
        extra: {},
        depth: 0,
      },
    ])
    setPickerOpen(false)
  }

  function importSections(imported: SectionEntry[]) {
    onChange([
      ...sections,
      ...imported.map((s, i) => ({ ...s, section_order: sections.length + i })),
    ])
  }

  function removeSection(index: number) {
    onChange(sections.filter((_, i) => i !== index))
  }

  function updateSection(index: number, patch: Partial<SectionEntry>) {
    onChange(sections.map((s, i) => i === index ? { ...s, ...patch } : s))
  }

  // Determine if any row has expandable content beyond crossref
  const hasExpandableContent = !!renderExpandedContent

  return (
    <div>
      <div className="flex items-center justify-between mb-2">
        <p className="text-sm font-medium text-gray-700">{sectionLabel || 'Sections (drag to reorder)'}</p>
        <div className="flex gap-2">
          <Button variant="secondary" size="sm" onClick={() => setPickerOpen(true)}>
            <Plus size={14} /> Add Section
          </Button>
          <Button variant="secondary" size="sm" onClick={addGroupHeading}>
            <Layers size={14} /> Add Group Heading
          </Button>
        </div>
      </div>

      {sections.length === 0 && (
        <div className="py-8 text-center text-gray-400 text-sm border border-dashed border-gray-200 rounded-lg mb-2">
          No sections added yet. Click "Add Section" to get started.
        </div>
      )}

      <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={handleDragEnd}>
        <SortableContext items={sortableIds} strategy={verticalListSortingStrategy}>
          {sections.map((sec, idx) =>
            sec.section_key === 'group_heading' ? (
              <SortableGroupHeadingRow
                key={sortableIds[idx]}
                sortableId={sortableIds[idx]}
                section={sec}
                onHeadingChange={h => updateSection(idx, { heading: h })}
                onDelete={() => removeSection(idx)}
                onDepthChange={depth => updateSection(idx, { depth })}
              />
            ) : (
              <SortableDataRow
                key={sortableIds[idx]}
                sortableId={sortableIds[idx]}
                section={sec}
                onHeadingChange={h => updateSection(idx, { heading: h })}
                onConfigChange={config => updateSection(idx, { config })}
                onDepthChange={depth => updateSection(idx, { depth })}
                onRemove={() => removeSection(idx)}
                alwaysExpandable={hasExpandableContent}
                renderExpandedContent={renderExpandedContent ? () => renderExpandedContent(sec, idx) : undefined}
                renderBadges={renderBadges ? () => renderBadges(sec, idx) : undefined}
              />
            ),
          )}
        </SortableContext>
      </DndContext>

      {pickerOpen && (
        <SectionPickerModal
          availableSections={allPickerSections}
          onSelect={addSection}
          onClose={() => setPickerOpen(false)}
          currentTemplateId={templateId}
          customSections={customSections}
          onImportSections={importSections}
        />
      )}
    </div>
  )
}

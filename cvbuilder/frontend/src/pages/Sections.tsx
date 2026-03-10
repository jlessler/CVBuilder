import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '../lib/api'
import { Button, Card, Input, Modal, PageHeader, Spinner } from '../components/ui'
import { Plus, Trash2, Edit2 } from 'lucide-react'

// ---------------------------------------------------------------------------
// Tab configuration — all sections are CVItems stored in data JSON blobs
// ---------------------------------------------------------------------------

type SectionKey =
  | 'education' | 'experience' | 'consulting' | 'memberships'
  | 'grants' | 'awards' | 'classes' | 'symposia'
  | 'panels_advisory' | 'panels_grantreview'
  | 'trainees_advisees' | 'trainees_postdocs'
  | 'press' | 'committees'
  | 'misc_editor' | 'misc_peerrev' | 'misc_policypres' | 'misc_policycons'
  | 'misc_otherservice'
  | 'misc_chairedsessions' | 'misc_otherpractice'

interface TabDef {
  key: SectionKey
  label: string
  group: string
  section: string           // DB section key(s) for GET — comma-separated for multi-section
  createSection?: string    // section to use on create (if different from `section`)
  subtypeField?: string     // form field whose value overrides section on create
}

const TABS: TabDef[] = [
  // --- Experience & positions ---
  { key: 'education',           label: 'Education',        group: 'Education and Experience', section: 'education' },
  { key: 'experience',          label: 'Experience',       group: 'Education and Experience', section: 'experience' },
  { key: 'consulting',          label: 'Consulting',       group: 'Education and Experience', section: 'consulting' },
  { key: 'awards',              label: 'Awards',           group: 'Education and Experience', section: 'awards' },
  // --- Teaching & trainees ---
  { key: 'classes',             label: 'Classes',          group: 'Teaching',   section: 'classes' },
  { key: 'trainees_advisees',   label: 'Advisees',         group: 'Teaching',   section: 'trainees_advisees' },
  { key: 'trainees_postdocs',   label: 'Postdocs',         group: 'Teaching',   section: 'trainees_postdocs' },
  // --- Grants ---
  { key: 'grants',              label: 'Grants',           group: 'Grants',     section: 'grants' },
  // --- Service ---
  { key: 'panels_advisory',     label: 'Advisory Panels',  group: 'Service',    section: 'panels_advisory' },
  { key: 'panels_grantreview',  label: 'Grant Review',     group: 'Service',    section: 'panels_grantreview' },
  { key: 'symposia',            label: 'Symposia',         group: 'Service',    section: 'symposia' },
  { key: 'committees',          label: 'Committees',       group: 'Service',    section: 'committees' },
  { key: 'memberships',         label: 'Memberships',      group: 'Service',    section: 'memberships' },
  { key: 'misc_editor',         label: 'Editorial',        group: 'Service',    section: 'editor,assocedit,otheredit,editorial', subtypeField: 'subtype' },
  { key: 'misc_peerrev',        label: 'Peer Review',      group: 'Service',    section: 'peerrev', createSection: 'peerrev' },
  { key: 'misc_otherservice',   label: 'Other Service',    group: 'Service',    section: 'otherservice', createSection: 'otherservice' },
  // --- Misc ---
  { key: 'misc_policypres',   label: 'Policy Pres.',    group: 'Misc', section: 'policypres', createSection: 'policypres' },
  { key: 'misc_policycons',   label: 'Policy Consult.', group: 'Misc', section: 'policycons', createSection: 'policycons' },
  { key: 'press',             label: 'Press / Media',    group: 'Misc', section: 'press' },
  { key: 'misc_chairedsessions', label: 'Chaired Sessions',    group: 'Service', section: 'chairedsessions', createSection: 'chairedsessions' },
  { key: 'misc_otherpractice',   label: 'Other Practice',      group: 'Misc', section: 'otherpractice', createSection: 'otherpractice' },
]

const GROUPS = ['Education and Experience', 'Teaching', 'Grants', 'Service', 'Misc']

// ---------------------------------------------------------------------------
// Field definitions per section
// ---------------------------------------------------------------------------

type FieldDef = { key: string; label: string; type?: string; textarea?: boolean; options?: { value: string; label: string }[] }

const FIELDS: Partial<Record<SectionKey, FieldDef[]>> = {
  education: [
    { key: 'degree', label: 'Degree' },
    { key: 'year', label: 'Year', type: 'number' },
    { key: 'subject', label: 'Subject / Field' },
    { key: 'school', label: 'Institution' },
  ],
  experience: [
    { key: 'title', label: 'Title / Position' },
    { key: 'years_start', label: 'Start Year' },
    { key: 'years_end', label: 'End Year' },
    { key: 'employer', label: 'Employer / Institution' },
  ],
  consulting: [
    { key: 'title', label: 'Role / Title' },
    { key: 'years', label: 'Years' },
    { key: 'employer', label: 'Client / Employer' },
  ],
  memberships: [
    { key: 'org', label: 'Organization' },
    { key: 'years', label: 'Years' },
  ],
  grants: [
    { key: 'title', label: 'Title' },
    { key: 'agency', label: 'Funding Agency / Organization' },
    { key: 'pi', label: 'Principal Investigator' },
    { key: 'amount', label: 'Amount' },
    { key: 'years_start', label: 'Start Date' },
    { key: 'years_end', label: 'End Date' },
    { key: 'role', label: 'Your Role' },
    { key: 'id_number', label: 'Grant Number' },
    { key: 'grant_type', label: 'Grant Type' },
    { key: 'pcteffort', label: '% Effort', type: 'number' },
    { key: 'status', label: 'Status (active / completed)' },
    { key: 'description', label: 'Description', textarea: true },
  ],
  awards: [
    { key: 'name', label: 'Award / Honor' },
    { key: 'org', label: 'Awarding Organization' },
    { key: 'date', label: 'Date' },
    { key: 'year', label: 'Year' },
  ],
  classes: [
    { key: 'class_name', label: 'Course Name' },
    { key: 'year', label: 'Year', type: 'number' },
    { key: 'role', label: 'Role' },
    { key: 'school', label: 'Institution' },
    { key: 'students', label: 'Students' },
    { key: 'lectures', label: 'Lectures' },
  ],
  symposia: [
    { key: 'title', label: 'Title' },
    { key: 'meeting', label: 'Meeting / Conference' },
    { key: 'date', label: 'Date' },
    { key: 'role', label: 'Role' },
  ],
  panels_advisory: [
    { key: 'panel', label: 'Panel Name' },
    { key: 'org', label: 'Organization' },
    { key: 'role', label: 'Role' },
    { key: 'date', label: 'Date' },
    { key: 'panel_id', label: 'Panel ID' },
  ],
  panels_grantreview: [
    { key: 'panel', label: 'Panel / Study Section' },
    { key: 'org', label: 'Agency / Organization' },
    { key: 'role', label: 'Role' },
    { key: 'date', label: 'Date' },
    { key: 'panel_id', label: 'Review ID' },
  ],
  trainees_advisees: [
    { key: 'name', label: 'Name' },
    { key: 'degree', label: 'Degree' },
    { key: 'type', label: 'Advisor Type' },
    { key: 'school', label: 'Institution' },
    { key: 'years_start', label: 'Start' },
    { key: 'years_end', label: 'End' },
    { key: 'thesis', label: 'Thesis Title' },
    { key: 'current_position', label: 'Current Position' },
  ],
  trainees_postdocs: [
    { key: 'name', label: 'Name' },
    { key: 'years_start', label: 'Start' },
    { key: 'years_end', label: 'End' },
    { key: 'current_position', label: 'Current Position' },
  ],
  press: [
    { key: 'topic', label: 'Topic' },
    { key: 'outlet', label: 'Outlet / Publication' },
    { key: 'date', label: 'Date' },
    { key: 'url', label: 'URL' },
  ],
  committees: [
    { key: 'committee', label: 'Committee Name' },
    { key: 'org', label: 'Organization / University' },
    { key: 'role', label: 'Role' },
    { key: 'dates', label: 'Dates' },
  ],
  misc_editor: [
    { key: 'subtype', label: 'Role Type', options: [
      { value: 'editor',     label: 'Editor' },
      { value: 'assocedit',  label: 'Associate Editor' },
      { value: 'otheredit',  label: 'Guest Editor / Other' },
    ]},
    { key: 'journal', label: 'Journal' },
    { key: 'role', label: 'Specific Role (e.g., Guest Editor, Statistical Advisor)' },
    { key: 'term', label: 'Term / Years' },
  ],
  misc_peerrev: [
    { key: 'value', label: 'Journal / Publication' },
  ],
  misc_policypres: [
    { key: 'title', label: 'Title' },
    { key: 'org', label: 'Organization / Audience' },
    { key: 'date', label: 'Date' },
    { key: 'description', label: 'Description', textarea: true },
  ],
  misc_policycons: [
    { key: 'title', label: 'Title / Project' },
    { key: 'org', label: 'Organization' },
    { key: 'date', label: 'Date / Period' },
    { key: 'description', label: 'Description', textarea: true },
  ],
  misc_otherservice: [
    { key: 'description', label: 'Description' },
    { key: 'department', label: 'Department / Context' },
    { key: 'dates', label: 'Dates' },
  ],
  misc_chairedsessions: [
    { key: 'date', label: 'Year / Date' },
    { key: 'title', label: 'Session Title' },
    { key: 'meeting', label: 'Meeting / Conference' },
  ],
  misc_otherpractice: [
    { key: 'years', label: 'Years / Period' },
    { key: 'title', label: 'Activity' },
    { key: 'description', label: 'Description', textarea: true },
  ],
}

function blankForm(tab: TabDef): Record<string, string | number> {
  const fields = FIELDS[tab.key] ?? []
  return Object.fromEntries(fields.map(f => [
    f.key,
    f.options ? f.options[0].value : f.type === 'number' ? 0 : '',
  ]))
}

// ---------------------------------------------------------------------------
// Item display row
// ---------------------------------------------------------------------------

function ItemRow({
  item, onEdit, onDelete,
}: {
  item: Record<string, unknown>
  onEdit: () => void
  onDelete: () => void
}) {
  // item.data is flattened into top-level by the query, so we can access fields directly
  const title = (
    item.name || item.title || item.class_name || item.degree ||
    item.panel || item.committee || item.org || item.journal ||
    item.value || item.description || ''
  ) as string

  const SECTION_LABELS: Record<string, string> = {
    editor: 'Editor', assocedit: 'Associate Editor', otheredit: 'Guest Editor / Other',
  }
  const sub = (
    item.employer || item.agency || item.school || item.meeting ||
    item.org || item.outlet || item.topic ||
    item.department || item.publisher || item.role ||
    (item.section && SECTION_LABELS[item.section as string]) ||
    ''
  ) as string

  const date = (
    item.dates || item.years || item.year || item.date ||
    `${item.years_start || ''}${item.years_end ? `–${item.years_end}` : ''}`
  ) as string

  return (
    <div className="flex items-start justify-between px-5 py-3 hover:bg-gray-50">
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-gray-900 truncate">{title || '(no title)'}</p>
        {sub && <p className="text-xs text-gray-500 truncate">{sub}</p>}
        {date && <p className="text-xs text-gray-400">{date}</p>}
      </div>
      <div className="flex items-center gap-1 ml-3">
        <Button variant="ghost" size="sm" onClick={onEdit}><Edit2 size={14} /></Button>
        <Button variant="ghost" size="sm" onClick={onDelete}><Trash2 size={14} className="text-red-500" /></Button>
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Sections page
// ---------------------------------------------------------------------------

export function Sections() {
  const qc = useQueryClient()
  const [tab, setTab] = useState<SectionKey>('education')
  const [activeGroup, setActiveGroup] = useState('Education and Experience')
  const [modal, setModal] = useState<{ open: boolean; item: Record<string, unknown> | null }>({ open: false, item: null })
  const [form, setForm] = useState<Record<string, string | number>>({})

  const currentTab = TABS.find(t => t.key === tab)!
  const url = `/cv/${currentTab.section}`

  const { data = [], isLoading } = useQuery<Record<string, unknown>[]>({
    queryKey: [tab],
    queryFn: () => api.get(url).then(r =>
      // Flatten item.data into top-level for display compatibility
      r.data.map((item: Record<string, unknown>) => ({
        ...item,
        ...((item.data as Record<string, unknown>) || {}),
      }))
    ),
  })

  function getCreateSection(d: Record<string, string | number>): string {
    if (currentTab.subtypeField) {
      return String(d[currentTab.subtypeField] || currentTab.createSection || currentTab.section.split(',')[0])
    }
    return currentTab.createSection || currentTab.section
  }

  function buildData(d: Record<string, string | number>): Record<string, unknown> {
    const fields = FIELDS[tab] ?? []
    const fieldKeys = fields.map(f => f.key).filter(k => k !== currentTab.subtypeField)
    return Object.fromEntries(fieldKeys.map(k => [k, d[k] ?? '']).filter(([, v]) => v !== ''))
  }

  const createMut = useMutation({
    mutationFn: (d: Record<string, string | number>) =>
      api.post('/cv', { section: getCreateSection(d), data: buildData(d) }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: [tab] }); closeModal() },
  })

  const updateMut = useMutation({
    mutationFn: (d: Record<string, string | number>) =>
      api.put(`/cv/${d.id}`, { data: buildData(d) }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: [tab] }); closeModal() },
  })

  const deleteMut = useMutation({
    mutationFn: (id: number) => api.delete(`/cv/${id}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: [tab] }),
  })

  function openCreate() {
    setForm(blankForm(currentTab))
    setModal({ open: true, item: null })
  }

  function openEdit(item: Record<string, unknown>) {
    // For editorial, map section back to the subtype field
    const extra: Record<string, unknown> = {}
    if (currentTab.subtypeField && item.section) {
      extra[currentTab.subtypeField] = item.section
    }
    // Data fields are already flattened into top-level by the query
    const fields = FIELDS[tab] ?? []
    const fieldKeys = fields.map(f => f.key)
    const formData: Record<string, string | number> = { id: item.id as number }
    for (const k of fieldKeys) {
      if (item[k] !== undefined && item[k] !== null) {
        formData[k] = item[k] as string | number
      }
    }
    Object.assign(formData, extra)
    setForm(formData)
    setModal({ open: true, item })
  }

  function closeModal() {
    setModal({ open: false, item: null })
    setForm({})
  }

  function setField(key: string, value: string | number) {
    setForm(f => ({ ...f, [key]: value }))
  }

  const groupTabs = TABS.filter(t => t.group === activeGroup)
  const fields = FIELDS[tab] ?? []

  return (
    <div className="p-8">
      <PageHeader
        title="CV Sections"
        subtitle="Manage all CV sections"
        actions={
          <Button onClick={openCreate}><Plus size={16} /> Add Entry</Button>
        }
      />

      {/* Group bar */}
      <div className="flex gap-2 mb-3 flex-wrap">
        {GROUPS.map(g => (
          <button
            key={g}
            onClick={() => {
              setActiveGroup(g)
              const first = TABS.find(t => t.group === g)
              if (first) setTab(first.key)
            }}
            className={`px-3 py-1 text-xs font-semibold rounded-full transition-colors
              ${activeGroup === g
                ? 'bg-primary-600 text-white'
                : 'bg-gray-100 text-gray-600 hover:bg-gray-200'}`}
          >{g}</button>
        ))}
      </div>

      {/* Section tabs within group */}
      <div className="flex gap-1 mb-6 border-b border-gray-200 flex-wrap">
        {groupTabs.map(t => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            className={`px-4 py-2 text-sm font-medium -mb-px transition-colors rounded-t-lg
              ${tab === t.key
                ? 'bg-white border border-b-white border-gray-200 text-primary-700'
                : 'text-gray-500 hover:text-gray-700'}`}
          >{t.label}</button>
        ))}
      </div>

      {isLoading ? <Spinner /> : (
        <Card>
          <div className="divide-y divide-gray-100">
            {(data as Record<string, unknown>[]).map((item) => (
              <ItemRow
                key={item.id as number}
                item={item}
                onEdit={() => openEdit(item)}
                onDelete={() => {
                  if (confirm('Delete this entry?')) deleteMut.mutate(item.id as number)
                }}
              />
            ))}
            {data.length === 0 && (
              <div className="py-12 text-center text-gray-400 text-sm">
                No entries yet. Click "Add Entry" to add one.
              </div>
            )}
          </div>
        </Card>
      )}

      <Modal
        open={modal.open}
        onClose={closeModal}
        title={modal.item ? 'Edit Entry' : 'Add Entry'}
      >
        <div className="space-y-4 max-h-[70vh] overflow-y-auto pr-1">
          {fields.map(field => (
            <div key={field.key}>
              <label className="block text-xs font-medium text-gray-600 mb-1">{field.label}</label>
              {field.options ? (
                <select
                  className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
                  value={String(form[field.key] ?? field.options[0].value)}
                  onChange={e => setField(field.key, e.target.value)}
                >
                  {field.options.map(o => (
                    <option key={o.value} value={o.value}>{o.label}</option>
                  ))}
                </select>
              ) : field.textarea ? (
                <textarea
                  rows={3}
                  className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
                  value={String(form[field.key] ?? '')}
                  onChange={e => setField(field.key, e.target.value)}
                />
              ) : (
                <Input
                  type={field.type || 'text'}
                  value={String(form[field.key] ?? '')}
                  onChange={e => setField(field.key, field.type === 'number' ? parseInt(e.target.value) || 0 : e.target.value)}
                />
              )}
            </div>
          ))}
          <div className="flex gap-2 justify-end pt-2 border-t">
            <Button variant="secondary" onClick={closeModal}>Cancel</Button>
            <Button
              loading={createMut.isPending || updateMut.isPending}
              onClick={() => modal.item ? updateMut.mutate(form) : createMut.mutate(form)}
            >
              {modal.item ? 'Save Changes' : 'Add Entry'}
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  )
}

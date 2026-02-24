import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '../lib/api'
import { Button, Card, Input, Modal, PageHeader, Spinner } from '../components/ui'
import { Plus, Trash2, Edit2 } from 'lucide-react'

// ---------------------------------------------------------------------------
// Tab configuration
// ---------------------------------------------------------------------------

type SectionKey =
  | 'education' | 'experience' | 'consulting' | 'memberships'
  | 'grants' | 'awards' | 'classes' | 'symposia'
  | 'panels_advisory' | 'panels_grantreview'
  | 'patents' | 'trainees_advisees' | 'trainees_postdocs'
  | 'press' | 'seminars' | 'committees'
  | 'misc_editor' | 'misc_peerrev' | 'misc_policypres' | 'misc_policycons'
  | 'misc_software' | 'misc_otherservice'
  | 'misc_dissertation' | 'misc_chairedsessions' | 'misc_otherpractice'

interface TabDef {
  key: SectionKey
  label: string
  group: string
  endpoint: string           // API path (without leading slash) used for GET
  queryParams?: string       // appended as ?key=val
  defaultValues?: Record<string, string | number>
  readOnly?: boolean         // misc sections shown read-only
  dataFields?: string[]      // when set, form flattens item.data into top-level keys
  sectionValue?: string      // the `section` string sent in MiscSection POST/PUT body
  subtypeField?: string      // form field whose value is used as the MiscSection.section
}

const TABS: TabDef[] = [
  // --- Experience & positions ---
  { key: 'education',           label: 'Education',        group: 'Education and Experience', endpoint: 'education' },
  { key: 'experience',          label: 'Experience',       group: 'Education and Experience', endpoint: 'experience' },
  { key: 'consulting',          label: 'Consulting',       group: 'Education and Experience', endpoint: 'consulting' },
  { key: 'awards',              label: 'Awards',           group: 'Education and Experience', endpoint: 'awards' },
  // --- Teaching & trainees ---
  { key: 'classes',             label: 'Classes',          group: 'Teaching',   endpoint: 'classes' },
  { key: 'trainees_advisees',   label: 'Advisees',         group: 'Teaching',   endpoint: 'trainees', queryParams: 'trainee_type=advisee', defaultValues: { trainee_type: 'advisee' } },
  { key: 'trainees_postdocs',   label: 'Postdocs',         group: 'Teaching',   endpoint: 'trainees', queryParams: 'trainee_type=postdoc', defaultValues: { trainee_type: 'postdoc' } },
  // --- Grants ---
  { key: 'grants',              label: 'Grants',           group: 'Grants',     endpoint: 'grants' },
  // --- Service ---
  { key: 'panels_advisory',     label: 'Advisory Panels',  group: 'Service',    endpoint: 'panels', queryParams: 'panel_type=advisory', defaultValues: { type: 'advisory' } },
  { key: 'panels_grantreview',  label: 'Grant Review',     group: 'Service',    endpoint: 'panels', queryParams: 'panel_type=grant_review', defaultValues: { type: 'grant_review' } },
  { key: 'symposia',            label: 'Symposia',         group: 'Service',    endpoint: 'symposia' },
  { key: 'committees',          label: 'Committees',       group: 'Service',    endpoint: 'committees' },
  { key: 'memberships',         label: 'Memberships',      group: 'Service',    endpoint: 'memberships' },
  { key: 'misc_editor',         label: 'Editorial',        group: 'Service',    endpoint: 'misc/editorial',    dataFields: ['journal', 'term', 'role'], subtypeField: 'subtype' },
  { key: 'misc_peerrev',        label: 'Peer Review',      group: 'Service',    endpoint: 'misc/peerrev',      dataFields: ['value'],            sectionValue: 'peerrev' },
  { key: 'misc_otherservice',   label: 'Other Service',    group: 'Service',    endpoint: 'misc/otherservice', dataFields: ['description', 'department', 'dates'], sectionValue: 'otherservice' },
  // --- Scholarly Output ---
  { key: 'misc_dissertation',    label: 'Dissertation',        group: 'Scholarly Output', endpoint: 'misc/dissertation',    dataFields: ['year', 'title', 'institution'],               sectionValue: 'dissertation' },
  { key: 'patents',             label: 'Patents',              group: 'Scholarly Output', endpoint: 'patents' },
  { key: 'seminars',            label: 'Seminars',             group: 'Scholarly Output', endpoint: 'seminars' },
  { key: 'misc_software',     label: 'Software',               group: 'Scholarly Output', endpoint: 'misc/software',     dataFields: ['title', 'year', 'publisher', 'url', 'authors'], sectionValue: 'software' },
  // --- Misc (editable) ---
  { key: 'misc_policypres',   label: 'Policy Pres.',    group: 'Misc', endpoint: 'misc/policypres',   dataFields: ['title', 'org', 'date', 'description'], sectionValue: 'policypres' },
  { key: 'misc_policycons',   label: 'Policy Consult.', group: 'Misc', endpoint: 'misc/policycons',   dataFields: ['title', 'org', 'date', 'description'], sectionValue: 'policycons' },
  { key: 'press',             label: 'Press / Media',    group: 'Misc', endpoint: 'press' },
  { key: 'misc_chairedsessions', label: 'Chaired Sessions',    group: 'Service', endpoint: 'misc/chairedsessions', dataFields: ['date', 'title', 'meeting'],                 sectionValue: 'chairedsessions' },
  { key: 'misc_otherpractice',   label: 'Other Practice',      group: 'Misc', endpoint: 'misc/otherpractice',   dataFields: ['years', 'title', 'description'],              sectionValue: 'otherpractice' },
]

const GROUPS = ['Education and Experience', 'Teaching', 'Scholarly Output', 'Grants', 'Service', 'Misc']

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
  patents: [
    { key: 'name', label: 'Patent Name' },
    { key: 'number', label: 'Patent Number' },
    { key: 'status', label: 'Status' },
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
  seminars: [
    { key: 'title', label: 'Title' },
    { key: 'org', label: 'Host Institution / Organization' },
    { key: 'date', label: 'Date' },
    { key: 'location', label: 'Location' },
    { key: 'event', label: 'Event / Seminar Series' },
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
  misc_software: [
    { key: 'title', label: 'Software Name' },
    { key: 'year', label: 'Year', type: 'number' },
    { key: 'publisher', label: 'Publisher / Host' },
    { key: 'url', label: 'URL' },
    { key: 'authors', label: 'Authors (comma-separated)', textarea: true },
  ],
  misc_otherservice: [
    { key: 'description', label: 'Description' },
    { key: 'department', label: 'Department / Context' },
    { key: 'dates', label: 'Dates' },
  ],
  misc_dissertation: [
    { key: 'year', label: 'Year', type: 'number' },
    { key: 'title', label: 'Title', textarea: true },
    { key: 'institution', label: 'Institution / Department' },
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
  const base = Object.fromEntries(fields.map(f => [
    f.key,
    f.options ? f.options[0].value : f.type === 'number' ? 0 : '',
  ]))
  return { ...base, ...(tab.defaultValues ?? {}) }
}

// ---------------------------------------------------------------------------
// Item display row
// ---------------------------------------------------------------------------

function ItemRow({
  item, onEdit, onDelete, readOnly,
}: {
  item: Record<string, unknown>
  onEdit: () => void
  onDelete: () => void
  readOnly?: boolean
}) {
  const title = (
    item.name || item.title || item.class_name || item.degree ||
    item.panel || item.committee || item.org ||
    (item.data && (item.data as Record<string, unknown>).journal) ||
    (item.data && (item.data as Record<string, unknown>).title) ||
    (item.data && (item.data as Record<string, unknown>).value) ||
    (item.data && (item.data as Record<string, unknown>).description) ||
    ''
  ) as string

  const SECTION_LABELS: Record<string, string> = {
    editor: 'Editor', assocedit: 'Associate Editor', otheredit: 'Guest Editor / Other',
  }
  const sub = (
    item.employer || item.agency || item.school || item.meeting ||
    item.org || item.outlet || item.topic ||
    (item.data && (item.data as Record<string, unknown>).org) ||
    (item.data && (item.data as Record<string, unknown>).department) ||
    (item.data && (item.data as Record<string, unknown>).publisher) ||
    (item.data && (item.data as Record<string, unknown>).role) ||
    (item.section && SECTION_LABELS[item.section as string]) ||
    ''
  ) as string

  const date = (
    item.dates || item.years || item.year || item.date ||
    (item.data && (item.data as Record<string, unknown>).date) ||
    (item.data && (item.data as Record<string, unknown>).dates) ||
    (item.data && (item.data as Record<string, unknown>).year) ||
    `${item.years_start || ''}${item.years_end ? `–${item.years_end}` : ''}`
  ) as string

  return (
    <div className="flex items-start justify-between px-5 py-3 hover:bg-gray-50">
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-gray-900 truncate">{title || '(no title)'}</p>
        {sub && <p className="text-xs text-gray-500 truncate">{sub}</p>}
        {date && <p className="text-xs text-gray-400">{date}</p>}
      </div>
      {!readOnly && (
        <div className="flex items-center gap-1 ml-3">
          <Button variant="ghost" size="sm" onClick={onEdit}><Edit2 size={14} /></Button>
          <Button variant="ghost" size="sm" onClick={onDelete}><Trash2 size={14} className="text-red-500" /></Button>
        </div>
      )}
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
  const url = currentTab.queryParams
    ? `/${currentTab.endpoint}?${currentTab.queryParams}`
    : `/${currentTab.endpoint}`

  const { data = [], isLoading } = useQuery<Record<string, unknown>[]>({
    queryKey: [tab],
    queryFn: () => api.get(url).then(r => r.data),
  })

  function buildMiscPayload(d: Record<string, string | number>) {
    const section = currentTab.subtypeField
      ? String(d[currentTab.subtypeField] || currentTab.sectionValue || '')
      : (currentTab.sectionValue ?? '')
    const dataKeys = (currentTab.dataFields ?? []).filter(k => k !== currentTab.subtypeField)
    const dataObj = Object.fromEntries(dataKeys.map(k => [k, d[k] ?? '']))
    return { section, data: dataObj }
  }

  const createMut = useMutation({
    mutationFn: (d: Record<string, string | number>) =>
      currentTab.dataFields
        ? api.post('/misc', buildMiscPayload(d))
        : api.post(`/${currentTab.endpoint}`, { ...d, ...(currentTab.defaultValues ?? {}) }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: [tab] }); closeModal() },
  })

  const updateMut = useMutation({
    mutationFn: (d: Record<string, string | number>) =>
      currentTab.dataFields
        ? api.put(`/misc/${d.id}`, buildMiscPayload(d))
        : api.put(`/${currentTab.endpoint}/${d.id}`, d),
    onSuccess: () => { qc.invalidateQueries({ queryKey: [tab] }); closeModal() },
  })

  const deleteMut = useMutation({
    mutationFn: (id: number) =>
      currentTab.dataFields
        ? api.delete(`/misc/${id}`)
        : api.delete(`/${currentTab.endpoint}/${id}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: [tab] }),
  })

  function openCreate() {
    setForm(blankForm(currentTab))
    setModal({ open: true, item: null })
  }

  function openEdit(item: Record<string, unknown>) {
    if (currentTab.dataFields && item.data) {
      const nested = item.data as Record<string, unknown>
      const extra = currentTab.subtypeField ? { [currentTab.subtypeField]: item.section } : {}
      setForm({ id: item.id as number, ...nested, ...extra } as Record<string, string | number>)
    } else {
      setForm(item as Record<string, string | number>)
    }
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
          !currentTab.readOnly
            ? <Button onClick={openCreate}><Plus size={16} /> Add Entry</Button>
            : undefined
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
          {currentTab.readOnly && (
            <p className="px-5 pt-3 text-xs text-gray-400 italic">
              These entries are imported from your YAML. Re-run import to refresh.
            </p>
          )}
          <div className="divide-y divide-gray-100">
            {(data as Record<string, unknown>[]).map((item) => (
              <ItemRow
                key={item.id as number}
                item={item}
                readOnly={currentTab.readOnly}
                onEdit={() => openEdit(item)}
                onDelete={() => {
                  if (confirm('Delete this entry?')) deleteMut.mutate(item.id as number)
                }}
              />
            ))}
            {data.length === 0 && (
              <div className="py-12 text-center text-gray-400 text-sm">
                No entries yet.{currentTab.readOnly ? ' Re-run YAML import to populate.' : ' Click "Add Entry" to add one.'}
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

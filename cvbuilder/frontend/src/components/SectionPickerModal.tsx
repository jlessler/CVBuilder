import { useState, useMemo } from 'react'
import { Modal } from './ui'
import { Search } from 'lucide-react'

export type PickerSection = {
  key: string
  label: string
  group?: string
}

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

export function SectionPickerModal({
  availableSections,
  existingKeys,
  onSelect,
  onClose,
}: {
  availableSections: PickerSection[]
  existingKeys?: Set<string>
  onSelect: (section: PickerSection) => void
  onClose: () => void
}) {
  const [search, setSearch] = useState('')

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

  return (
    <Modal open onClose={onClose} title="Add Section">
      <div className="space-y-3">
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
      </div>
    </Modal>
  )
}

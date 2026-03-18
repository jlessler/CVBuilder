import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { api } from '../lib/api'
import type {
  DashboardData,
  ScholarlyOutputStats,
  TeachingMentorshipStats,
  MentorshipCategory,
  FundingStats,
  GrantCategoryStats,
  ServiceStats,
} from '../lib/api'
import { Spinner } from '../components/ui'
import {
  BookOpen, Users, DollarSign, Briefcase,
  CheckCircle, AlertCircle, ArrowUpRight,
} from 'lucide-react'

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const WORK_TYPE_LABELS: Record<string, string> = {
  papers: 'Peer-Reviewed Papers',
  preprints: 'Preprints',
  chapters: 'Books & Chapters',
  letters: 'Letters',
  scimeetings: 'Meeting Presentations',
  editorials: 'Editorials',
}

const MENTORSHIP_CATEGORIES: { key: string; label: string }[] = [
  { key: 'postdoctoral', label: 'Post-Doctoral' },
  { key: 'doctoral', label: 'Doctoral' },
  { key: 'masters', label: 'Masters' },
  { key: 'undergraduate', label: 'Undergraduate' },
  { key: 'other', label: 'Other' },
]

// ---------------------------------------------------------------------------
// Reusable chart components
// ---------------------------------------------------------------------------

function YearBarChart({ entries, barClass }: { entries: { year: number; count: number }[]; barClass: string }) {
  if (!entries.length) return <p className="text-sm text-gray-400">No data yet.</p>
  const maxVal = Math.max(...entries.map(e => e.count))
  const BAR_H = 96

  return (
    <div className="overflow-x-auto pb-1">
      <div className="flex items-end gap-1.5" style={{ minHeight: BAR_H + 48 }}>
        {entries.map(({ year, count }) => {
          const h = Math.max(Math.round((count / maxVal) * BAR_H), 4)
          return (
            <div key={year} className="flex flex-col items-center gap-0.5 flex-shrink-0 w-7">
              <span className="text-[10px] text-gray-500 leading-none">{count}</span>
              <div className={`w-full rounded-t ${barClass}`} style={{ height: h }} />
              <span className="text-[10px] text-gray-400 leading-none">{String(year).slice(2)}</span>
            </div>
          )
        })}
      </div>
    </div>
  )
}

function BreakdownBars({ rows, total, barClass }: {
  rows: { label: string; value: number }[]; total: number; barClass: string
}) {
  const filtered = rows.filter(r => r.value > 0)
  if (!filtered.length) return <p className="text-sm text-gray-400">None yet.</p>
  return (
    <div className="space-y-2.5">
      {filtered.map(({ label, value }) => {
        const pct = total > 0 ? (value / total) * 100 : 0
        return (
          <div key={label}>
            <div className="flex justify-between text-sm mb-1">
              <span className="text-gray-700">{label}</span>
              <span className="font-medium text-gray-900">{value}</span>
            </div>
            <div className="h-2 bg-gray-100 rounded-full">
              <div className={`h-2 rounded-full ${barClass}`} style={{ width: `${pct}%` }} />
            </div>
          </div>
        )
      })}
    </div>
  )
}

function SectionPanel({ title, icon: Icon, iconColor, linkLabel, onLink, children }: {
  title: string; icon: React.ElementType; iconColor: string
  linkLabel?: string; onLink?: () => void; children: React.ReactNode
}) {
  return (
    <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-6">
      <div className="flex items-center justify-between mb-5">
        <div className="flex items-center gap-3">
          <div className={`p-2.5 rounded-xl ${iconColor}`}>
            <Icon size={18} />
          </div>
          <h3 className="text-lg font-semibold text-gray-900">{title}</h3>
        </div>
        {linkLabel && onLink && (
          <button
            onClick={onLink}
            className="flex items-center gap-1 text-sm text-primary-600 hover:underline"
          >
            {linkLabel} <ArrowUpRight size={13} />
          </button>
        )}
      </div>
      {children}
    </div>
  )
}

function StatBox({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="text-center">
      <p className="text-2xl font-bold text-gray-900">{value}</p>
      <p className="text-xs text-gray-500 mt-0.5">{label}</p>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Donut chart (pure SVG, no dependencies)
// ---------------------------------------------------------------------------

const DONUT_COLORS = [
  '#3b82f6', '#6366f1', '#8b5cf6', '#ec4899', '#f97316', '#14b8a6',
]

function DonutChart({ slices, size = 120, strokeWidth = 24 }: {
  slices: { label: string; value: number; color: string }[]
  size?: number; strokeWidth?: number
}) {
  const total = slices.reduce((s, sl) => s + sl.value, 0)
  if (total === 0) return null
  const radius = (size - strokeWidth) / 2
  const circumference = 2 * Math.PI * radius
  let offset = 0

  return (
    <div className="flex items-center gap-4">
      <svg width={size} height={size} className="flex-shrink-0">
        {slices.map((sl, i) => {
          const pct = sl.value / total
          const dash = pct * circumference
          const gap = circumference - dash
          const currentOffset = offset
          offset += dash
          return (
            <circle
              key={i}
              cx={size / 2} cy={size / 2} r={radius}
              fill="none" stroke={sl.color} strokeWidth={strokeWidth}
              strokeDasharray={`${dash} ${gap}`}
              strokeDashoffset={-currentOffset}
              className="transition-all"
            />
          )
        })}
        <text x="50%" y="50%" textAnchor="middle" dominantBaseline="central"
          className="text-lg font-bold fill-gray-900">{total}</text>
      </svg>
      <div className="space-y-1.5 text-xs min-w-0">
        {slices.map((sl, i) => (
          <div key={i} className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full flex-shrink-0" style={{ backgroundColor: sl.color }} />
            <span className="text-gray-600 truncate">{sl.label}</span>
            <span className="text-gray-900 font-medium ml-auto">{sl.value}</span>
          </div>
        ))}
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Scholarly Output Section
// ---------------------------------------------------------------------------

function ScholarlyOutputSection({ data }: { data: ScholarlyOutputStats }) {
  const navigate = useNavigate()
  const typeRows = Object.entries(data.counts_by_type).map(([type, count]) => ({
    label: WORK_TYPE_LABELS[type] ?? type,
    value: count,
  }))

  return (
    <SectionPanel
      title="Scholarly Output"
      icon={BookOpen}
      iconColor="bg-blue-50 text-blue-700"
      linkLabel="View works"
      onLink={() => navigate('/publications')}
    >
      {/* Top row: publications by year + citations by year */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        <div>
          <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-3">Publications by Year</p>
          <YearBarChart entries={data.works_by_year} barClass="bg-blue-500" />
        </div>
        <div>
          <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-3">Citations by Year</p>
          {data.citations_by_year.length > 0
            ? <YearBarChart entries={data.citations_by_year} barClass="bg-indigo-400" />
            : <p className="text-sm text-gray-400">No citation data yet.</p>
          }
        </div>
      </div>

      {/* Bottom row: publication summary + citation metrics + type donut */}
      <div className="mt-6 pt-5 border-t border-gray-100 grid grid-cols-1 lg:grid-cols-[1fr_1fr_auto] gap-8">
        {/* Publication summary */}
        <div>
          <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-3 text-center">Publication Summary</p>
          <div className="grid grid-cols-2 gap-4">
            <StatBox label="Total Works" value={data.total_works} />
            <StatBox label="First Author" value={data.first_author_count} />
            <StatBox label="Corresponding" value={data.corresponding_author_count} />
            <StatBox label="Senior Author" value={data.senior_author_count} />
            {data.student_led_count > 0 && (
              <StatBox label="Student-Led" value={data.student_led_count} />
            )}
          </div>
        </div>

        {/* Citation metrics */}
        <div>
          <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-3 text-center">Citation Metrics</p>
          {data.total_citations > 0 ? (
            <div className="space-y-4">
              <StatBox label="Total" value={data.total_citations.toLocaleString()} />
              <StatBox label="h-index" value={data.h_index} />
              <StatBox label="i10-index" value={data.i10_index} />
            </div>
          ) : (
            <p className="text-sm text-gray-400">No citation data yet.</p>
          )}
        </div>

        {/* Work type donut */}
        {typeRows.length > 0 && (
          <div>
            <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-3 text-center">By Type</p>
            <DonutChart
              slices={typeRows.map((r, i) => ({
                label: r.label,
                value: r.value,
                color: DONUT_COLORS[i % DONUT_COLORS.length],
              }))}
            />
          </div>
        )}
      </div>
    </SectionPanel>
  )
}

// ---------------------------------------------------------------------------
// Teaching & Mentorship Section
// ---------------------------------------------------------------------------

function MentorshipCategoryPanel({ label, category }: {
  label: string; category: MentorshipCategory
}) {
  if (category.count === 0) return null
  return (
    <div>
      <h4 className="text-sm font-semibold text-gray-800">{label}</h4>
      <div className="flex items-center gap-3 mt-1">
        <span className="text-sm text-gray-600">{category.count} total</span>
        <span className="text-sm text-green-700 font-medium">{category.current} current</span>
      </div>
    </div>
  )
}

function TeachingSection({ data }: { data: TeachingMentorshipStats }) {
  const navigate = useNavigate()
  const { teaching, mentorship } = data

  return (
    <SectionPanel
      title="Teaching & Mentorship"
      icon={Users}
      iconColor="bg-green-50 text-green-700"
      linkLabel="Manage sections"
      onLink={() => navigate('/sections')}
    >
      <div className="space-y-8">
        {/* Teaching */}
        <div>
          <h3 className="text-sm font-bold text-gray-700 uppercase tracking-wide mb-3">Teaching</h3>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
            <div>
              <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-3">Overall ({teaching.courses_total} courses)</p>
              {teaching.by_role.length > 0 ? (
                <DonutChart
                  slices={teaching.by_role.map((r, i) => ({
                    label: r.role,
                    value: r.count,
                    color: DONUT_COLORS[i % DONUT_COLORS.length],
                  }))}
                />
              ) : (
                <p className="text-sm text-gray-400">No teaching data yet.</p>
              )}
            </div>
            <div>
              <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-3">Past 5 Years</p>
              {teaching.by_role_five_year.length > 0 ? (
                <DonutChart
                  slices={teaching.by_role_five_year.map((r, i) => ({
                    label: r.role,
                    value: r.count,
                    color: DONUT_COLORS[i % DONUT_COLORS.length],
                  }))}
                />
              ) : (
                <p className="text-sm text-gray-400">No teaching data in the past 5 years.</p>
              )}
            </div>
          </div>
        </div>

        {/* Mentorship */}
        <div>
          <h3 className="text-sm font-bold text-gray-700 uppercase tracking-wide mb-4">Mentorship</h3>
          <div className="space-y-5">
            {MENTORSHIP_CATEGORIES.map(({ key, label }) => (
              <MentorshipCategoryPanel
                key={key}
                label={label}
                category={mentorship[key as keyof typeof mentorship] as MentorshipCategory}
              />
            ))}
          </div>
        </div>
      </div>
    </SectionPanel>
  )
}

// ---------------------------------------------------------------------------
// Funding Section
// ---------------------------------------------------------------------------

function GrantTable({ grants, emptyMsg }: { grants: GrantCategoryStats['grants']; emptyMsg: string }) {
  return (
    <div className="overflow-auto rounded border border-gray-200">
      <table className="w-full text-sm">
        <thead className="bg-gray-50 border-b border-gray-200">
          <tr className="text-xs text-gray-500 text-left">
            <th className="py-2 px-3 font-semibold">Title</th>
            <th className="py-2 px-3 font-semibold">Agency</th>
            <th className="py-2 px-3 font-semibold">Role</th>
            <th className="py-2 px-3 font-semibold">Period</th>
            <th className="py-2 px-3 font-semibold">Amount</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100">
          {grants.map((g, i) => (
            <tr key={i} className="hover:bg-gray-50">
              <td className="py-2 px-3 font-medium text-gray-900 max-w-xs">
                <span className="line-clamp-2">{g.title || '—'}</span>
              </td>
              <td className="py-2 px-3 text-gray-600 whitespace-nowrap">{g.agency || '—'}</td>
              <td className="py-2 px-3 text-gray-600 whitespace-nowrap">{g.role || '—'}</td>
              <td className="py-2 px-3 text-gray-500 whitespace-nowrap">{g.period || '—'}</td>
              <td className="py-2 px-3 text-gray-600 whitespace-nowrap">{g.amount || '—'}</td>
            </tr>
          ))}
          {grants.length === 0 && (
            <tr><td colSpan={5} className="py-8 text-center text-gray-400 text-sm">{emptyMsg}</td></tr>
          )}
        </tbody>
      </table>
    </div>
  )
}

function GrantCategoryPanel({ label, category }: {
  label: string; category: GrantCategoryStats
}) {
  const roleRows = category.by_role.map(({ role, count }) => ({ label: role, value: count }))

  return (
    <div>
      <h4 className="text-sm font-semibold text-gray-800 mb-3">{label}</h4>
      <div className="flex items-center gap-4 mb-4">
        <StatBox label="Grants" value={category.count} />
        {category.total_amount_display && (
          <StatBox label="Funding" value={category.total_amount_display} />
        )}
        {roleRows.length > 0 && (
          <div className="flex items-center gap-3 ml-4 text-xs text-gray-600">
            {roleRows.map(r => (
              <span key={r.label}>{r.label}: <span className="font-semibold text-gray-900">{r.value}</span></span>
            ))}
          </div>
        )}
      </div>
      <GrantTable grants={category.grants} emptyMsg={`No ${label.toLowerCase()} grants.`} />
    </div>
  )
}

function FundingSection({ data }: { data: FundingStats }) {
  const navigate = useNavigate()

  return (
    <SectionPanel
      title="Funding"
      icon={DollarSign}
      iconColor="bg-purple-50 text-purple-700"
      linkLabel="Manage grants"
      onLink={() => navigate('/sections')}
    >
      <div className="space-y-8">
        <GrantCategoryPanel label="Active Grants" category={data.active} />
        {data.completed.count > 0 && (
          <GrantCategoryPanel label="Completed Grants" category={data.completed} />
        )}
      </div>
    </SectionPanel>
  )
}

// ---------------------------------------------------------------------------
// Service Section
// ---------------------------------------------------------------------------

function ServiceSection({ data }: { data: ServiceStats }) {
  const navigate = useNavigate()
  const rows = data.service_breakdown.map(({ label, count }) => ({
    label,
    value: count,
  }))
  const total = rows.reduce((s, r) => s + r.value, 0)

  return (
    <SectionPanel
      title="Service"
      icon={Briefcase}
      iconColor="bg-orange-50 text-orange-700"
      linkLabel="Manage sections"
      onLink={() => navigate('/sections')}
    >
      {total > 0 ? (
        <div className="max-w-xl">
          <BreakdownBars rows={rows} total={total} barClass="bg-orange-500" />
          <p className="text-sm text-gray-500 mt-4">{total} total service activities</p>
        </div>
      ) : (
        <p className="text-sm text-gray-400">No service activities recorded yet.</p>
      )}
    </SectionPanel>
  )
}

// ---------------------------------------------------------------------------
// Tab definitions
// ---------------------------------------------------------------------------

type TabKey = 'scholarly' | 'teaching' | 'funding' | 'service'

const TABS: { key: TabKey; label: string; icon: React.ElementType; color: string }[] = [
  { key: 'scholarly', label: 'Scholarly Output',       icon: BookOpen,  color: 'blue' },
  { key: 'teaching',  label: 'Teaching & Mentorship',  icon: Users,     color: 'green' },
  { key: 'funding',   label: 'Funding',                icon: DollarSign, color: 'purple' },
  { key: 'service',   label: 'Service',                icon: Briefcase, color: 'orange' },
]

const TAB_COLORS: Record<string, { active: string; inactive: string }> = {
  blue:   { active: 'border-blue-500 text-blue-700',     inactive: 'text-gray-500 hover:text-blue-600' },
  green:  { active: 'border-green-500 text-green-700',   inactive: 'text-gray-500 hover:text-green-600' },
  purple: { active: 'border-purple-500 text-purple-700', inactive: 'text-gray-500 hover:text-purple-600' },
  orange: { active: 'border-orange-500 text-orange-700', inactive: 'text-gray-500 hover:text-orange-600' },
}

// ---------------------------------------------------------------------------
// Dashboard
// ---------------------------------------------------------------------------

export function Dashboard() {
  const [activeTab, setActiveTab] = useState<TabKey>('scholarly')

  const { data, isLoading } = useQuery<DashboardData>({
    queryKey: ['dashboard'],
    queryFn: () => api.get('/dashboard').then(r => r.data),
  })

  if (isLoading) return <div className="p-8"><Spinner /></div>
  if (!data) return null

  return (
    <div className="p-8">
      <div className="mb-6">
        <h2 className="text-2xl font-bold text-gray-900">Dashboard</h2>
        <p className="text-sm text-gray-500 mt-1">Overview of your CV data</p>
      </div>

      {/* Profile status */}
      <div className={`flex items-center gap-2 mb-6 px-4 py-3 rounded-lg text-sm font-medium ${
        data.profile_complete
          ? 'bg-green-50 text-green-800 border border-green-200'
          : 'bg-amber-50 text-amber-800 border border-amber-200'
      }`}>
        {data.profile_complete
          ? <><CheckCircle size={16} /> Profile complete</>
          : <><AlertCircle size={16} /> Profile incomplete — visit the Profile page to fill in your details</>
        }
      </div>

      {/* Tab bar */}
      <div className="border-b border-gray-200 mb-6">
        <nav className="flex gap-6 -mb-px">
          {TABS.map(({ key, label, icon: Icon, color }) => {
            const isActive = activeTab === key
            const colors = TAB_COLORS[color]
            return (
              <button
                key={key}
                onClick={() => setActiveTab(key)}
                className={`flex items-center gap-2 pb-3 border-b-2 text-sm font-medium transition-colors ${
                  isActive ? colors.active : `border-transparent ${colors.inactive}`
                }`}
              >
                <Icon size={16} />
                {label}
              </button>
            )
          })}
        </nav>
      </div>

      {/* Tab content */}
      {activeTab === 'scholarly' && <ScholarlyOutputSection data={data.scholarly_output} />}
      {activeTab === 'teaching' && <TeachingSection data={data.teaching_mentorship} />}
      {activeTab === 'funding' && <FundingSection data={data.funding} />}
      {activeTab === 'service' && <ServiceSection data={data.service} />}
    </div>
  )
}

import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { api } from '../lib/api'
import type { DashboardStats, Work } from '../lib/api'
import { Spinner } from '../components/ui'
import {
  BookOpen, Users, DollarSign, CheckCircle, AlertCircle,
  Presentation, ChevronDown, ChevronUp, ArrowUpRight,
} from 'lucide-react'

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const TRAINEE_LABELS: Record<string, string> = {
  advisee: 'Graduate Student Advisees',
  postdoc:  'Postdoctoral Fellows',
}

type ExpandedPanel = 'papers' | 'trainees' | 'grants' | 'presentations' | null

function buildYearCounts(works: Work[]): [string, number][] {
  const m: Record<string, number> = {}
  for (const w of works) if (w.year) m[String(w.year)] = (m[String(w.year)] ?? 0) + 1
  return Object.entries(m).sort(([a], [b]) => a.localeCompare(b))
}

// CVItem shape from /api/cv/{section}
interface CVItem {
  id: number
  section: string
  data: Record<string, unknown>
  sort_date: number | null
  sort_order: number
}

// ---------------------------------------------------------------------------
// Stat card
// ---------------------------------------------------------------------------

function StatCard({ label, value, subtitle, icon: Icon, color = 'blue', onClick, expanded }: {
  label: string; value: number; subtitle?: string; icon: React.ElementType
  color?: string; onClick: () => void; expanded: boolean
}) {
  const iconBg: Record<string, string> = {
    blue:   'bg-blue-50   text-blue-700',
    green:  'bg-green-50  text-green-700',
    purple: 'bg-purple-50 text-purple-700',
    orange: 'bg-orange-50 text-orange-700',
  }
  return (
    <div
      className={`bg-white rounded-xl border shadow-sm p-5 cursor-pointer hover:shadow-md transition-all select-none ${
        expanded ? 'border-primary-400 ring-1 ring-primary-300' : 'border-gray-200'
      }`}
      onClick={onClick}
    >
      <div className="flex items-start justify-between">
        <div>
          <p className="text-sm text-gray-500 font-medium">{label}</p>
          <p className="text-3xl font-bold text-gray-900 mt-1">{value}</p>
          {subtitle && <p className="text-xs text-gray-400 mt-0.5">{subtitle}</p>}
        </div>
        <div className="flex flex-col items-end gap-2">
          <div className={`p-3 rounded-xl ${iconBg[color] ?? iconBg.blue}`}>
            <Icon size={20} />
          </div>
          <span className="text-gray-400">
            {expanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
          </span>
        </div>
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Year bar chart
// ---------------------------------------------------------------------------

function YearBarChart({ entries, barClass }: { entries: [string, number][]; barClass: string }) {
  if (!entries.length) return <p className="text-sm text-gray-400">No data.</p>
  const maxVal = Math.max(...entries.map(([, n]) => n))
  const BAR_H = 96 // px max bar height

  return (
    <div className="overflow-x-auto pb-1">
      <div className="flex items-end gap-1.5" style={{ minHeight: BAR_H + 48 }}>
        {entries.map(([year, count]) => {
          const h = Math.max(Math.round((count / maxVal) * BAR_H), 4)
          return (
            <div key={year} className="flex flex-col items-center gap-0.5 flex-shrink-0 w-7">
              <span className="text-[10px] text-gray-500 leading-none">{count}</span>
              <div className={`w-full rounded-t ${barClass}`} style={{ height: h }} />
              <span className="text-[10px] text-gray-400 leading-none">{year.slice(2)}</span>
            </div>
          )
        })}
      </div>
      <p className="text-[10px] text-gray-400 mt-1 text-right">year ('xx)</p>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Breakdown bars (horizontal, for type/role summaries)
// ---------------------------------------------------------------------------

function BreakdownBars({ rows, total, barClass }: {
  rows: { label: string; value: number }[]; total: number; barClass: string
}) {
  return (
    <div className="space-y-2.5">
      {rows.filter(r => r.value > 0).map(({ label, value }) => {
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

// ---------------------------------------------------------------------------
// Panel wrapper
// ---------------------------------------------------------------------------

function Panel({ title, linkLabel, onLink, children }: {
  title: string; linkLabel: string; onLink: () => void; children: React.ReactNode
}) {
  return (
    <div className="mt-4 bg-white rounded-xl border border-gray-200 shadow-sm p-6">
      <div className="flex items-center justify-between mb-5">
        <h3 className="text-lg font-semibold text-gray-900">{title}</h3>
        <button
          onClick={onLink}
          className="flex items-center gap-1 text-sm text-primary-600 hover:underline"
        >
          {linkLabel} <ArrowUpRight size={13} />
        </button>
      </div>
      {children}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Papers / Presentations panel
// ---------------------------------------------------------------------------

function PubPanel({ pubType, title }: { pubType: string; title: string }) {
  const navigate = useNavigate()
  const barClass = pubType === 'papers' ? 'bg-blue-500' : 'bg-orange-500'

  const { data: works = [], isLoading } = useQuery<Work[]>({
    queryKey: ['dashboard-works', pubType],
    queryFn: () => api.get('/works', { params: { type: pubType, limit: 2000 } }).then(r => r.data),
  })

  const yearEntries = buildYearCounts(works)
  const recent = works.slice(0, 6)

  return (
    <Panel
      title={title}
      linkLabel="View all"
      onLink={() => navigate(`/publications?type=${pubType}`)}
    >
      {isLoading ? <Spinner /> : (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          {/* Year chart */}
          <div>
            <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-3">By Year</p>
            <YearBarChart entries={yearEntries} barClass={barClass} />
          </div>

          {/* Recent list */}
          <div>
            <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-3">Most Recent</p>
            <div className="space-y-3 max-h-72 overflow-y-auto pr-1">
              {recent.map(work => (
                <div key={work.id} className="border-b border-gray-100 pb-3 last:border-0 last:pb-0">
                  <p className="text-sm font-medium text-gray-900 leading-snug line-clamp-2">{work.title}</p>
                  {work.authors.length > 0 && (
                    <p className="text-xs text-gray-500 mt-0.5">
                      {work.authors.slice(0, 4).map(a => a.author_name).join(', ')}
                      {work.authors.length > 4 && ` +${work.authors.length - 4} more`}
                    </p>
                  )}
                  {work.data?.journal && (
                    <p className="text-xs text-gray-400 mt-0.5 italic">
                      {work.data.journal as string}{work.year ? ` (${work.year})` : ''}
                    </p>
                  )}
                </div>
              ))}
              {works.length === 0 && <p className="text-sm text-gray-400">None yet.</p>}
            </div>
          </div>
        </div>
      )}
    </Panel>
  )
}

// ---------------------------------------------------------------------------
// Trainees panel
// ---------------------------------------------------------------------------

function TraineesPanel({ breakdown, total }: {
  breakdown: DashboardStats['trainee_breakdown']; total: number
}) {
  const navigate = useNavigate()
  const { data: trainees = [], isLoading } = useQuery<CVItem[]>({
    queryKey: ['trainees-dashboard'],
    queryFn: () => api.get('/cv/trainees_advisees,trainees_postdocs').then(r => r.data),
  })

  const sorted = [...trainees].sort((a, b) => {
    const ya = parseInt(String(a.data?.years_start ?? '0')) || 0
    const yb = parseInt(String(b.data?.years_start ?? '0')) || 0
    return yb - ya
  })

  const breakdownRows = breakdown.map(({ type, count }) => ({
    label: TRAINEE_LABELS[type] ?? type,
    value: count,
  }))

  return (
    <Panel title="Trainees" linkLabel="Manage in Sections" onLink={() => navigate('/sections')}>
      {isLoading ? <Spinner /> : (
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-8">
          {/* Breakdown */}
          <div>
            <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-3">By Type</p>
            <BreakdownBars rows={breakdownRows} total={total} barClass="bg-green-500" />
          </div>

          {/* Table */}
          <div className="lg:col-span-3">
            <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-3">All Trainees</p>
            <div className="overflow-auto max-h-72 rounded border border-gray-200">
              <table className="w-full text-sm">
                <thead className="sticky top-0 bg-gray-50 border-b border-gray-200">
                  <tr className="text-xs text-gray-500 text-left">
                    <th className="py-2 px-3 font-semibold">Name</th>
                    <th className="py-2 px-3 font-semibold">Type</th>
                    <th className="py-2 px-3 font-semibold">Degree</th>
                    <th className="py-2 px-3 font-semibold">Years</th>
                    <th className="py-2 px-3 font-semibold">Institution</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {sorted.map(t => {
                    const d = t.data || {}
                    return (
                      <tr key={t.id} className="hover:bg-gray-50">
                        <td className="py-1.5 px-3 font-medium text-gray-900">{(d.name as string) ?? '—'}</td>
                        <td className="py-1.5 px-3 text-gray-600">{TRAINEE_LABELS[d.trainee_type as string] ?? (d.trainee_type as string) ?? '—'}</td>
                        <td className="py-1.5 px-3 text-gray-600">{(d.degree as string) ?? '—'}</td>
                        <td className="py-1.5 px-3 text-gray-500 whitespace-nowrap">
                          {(d.years_start as string) ?? ''}
                          {d.years_end ? `–${d.years_end}` : d.years_start ? '–present' : ''}
                        </td>
                        <td className="py-1.5 px-3 text-gray-600">{(d.school as string) ?? '—'}</td>
                      </tr>
                    )
                  })}
                  {sorted.length === 0 && (
                    <tr><td colSpan={5} className="py-8 text-center text-gray-400 text-sm">No trainees yet.</td></tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}
    </Panel>
  )
}

// ---------------------------------------------------------------------------
// Grants panel
// ---------------------------------------------------------------------------

function GrantsPanel({ breakdown, activeCount, totalCount }: {
  breakdown: DashboardStats['active_grant_breakdown']; activeCount: number; totalCount: number
}) {
  const navigate = useNavigate()
  const { data: allGrants = [], isLoading } = useQuery<CVItem[]>({
    queryKey: ['grants-dashboard'],
    queryFn: () => api.get('/cv/grants').then(r => r.data),
  })

  const active = allGrants.filter(g => (g.data?.status as string) === 'active')

  const breakdownRows = breakdown.map(({ role, count }) => ({ label: role, value: count }))

  return (
    <Panel title="Active Grants" linkLabel="Manage in Sections" onLink={() => navigate('/sections')}>
      {isLoading ? <Spinner /> : (
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-8">
          {/* Breakdown */}
          <div>
            <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-3">By Role</p>
            <BreakdownBars rows={breakdownRows} total={activeCount} barClass="bg-purple-500" />
            <p className="text-xs text-gray-400 mt-4">{activeCount} active of {totalCount} total</p>
          </div>

          {/* Table */}
          <div className="lg:col-span-3">
            <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-3">Active Grants</p>
            <div className="overflow-auto rounded border border-gray-200">
              <table className="w-full text-sm">
                <thead className="bg-gray-50 border-b border-gray-200">
                  <tr className="text-xs text-gray-500 text-left">
                    <th className="py-2 px-3 font-semibold">Title</th>
                    <th className="py-2 px-3 font-semibold">Agency</th>
                    <th className="py-2 px-3 font-semibold">Role</th>
                    <th className="py-2 px-3 font-semibold">Period</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {active.map(g => {
                    const d = g.data || {}
                    return (
                      <tr key={g.id} className="hover:bg-gray-50">
                        <td className="py-2 px-3 font-medium text-gray-900 max-w-xs">
                          <span className="line-clamp-2">{(d.title as string) ?? '—'}</span>
                        </td>
                        <td className="py-2 px-3 text-gray-600 whitespace-nowrap">{(d.agency as string) ?? '—'}</td>
                        <td className="py-2 px-3 text-gray-600 whitespace-nowrap">{(d.role as string) ?? '—'}</td>
                        <td className="py-2 px-3 text-gray-500 whitespace-nowrap">
                          {(d.years_start as string) ?? ''}
                          {d.years_end ? `–${d.years_end}` : d.years_start ? '–present' : ''}
                        </td>
                      </tr>
                    )
                  })}
                  {active.length === 0 && (
                    <tr><td colSpan={4} className="py-8 text-center text-gray-400 text-sm">No active grants.</td></tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}
    </Panel>
  )
}

// ---------------------------------------------------------------------------
// Dashboard
// ---------------------------------------------------------------------------

export function Dashboard() {
  const [expanded, setExpanded] = useState<ExpandedPanel>(null)

  const { data: stats, isLoading } = useQuery<DashboardStats>({
    queryKey: ['dashboard'],
    queryFn: () => api.get('/dashboard').then(r => r.data),
  })

  if (isLoading) return <div className="p-8"><Spinner /></div>
  if (!stats) return null

  function toggle(panel: NonNullable<ExpandedPanel>) {
    setExpanded(prev => prev === panel ? null : panel)
  }

  return (
    <div className="p-8">
      <div className="mb-6">
        <h2 className="text-2xl font-bold text-gray-900">Dashboard</h2>
        <p className="text-sm text-gray-500 mt-1">Overview of your CV data</p>
      </div>

      {/* Profile status */}
      <div className={`flex items-center gap-2 mb-6 px-4 py-3 rounded-lg text-sm font-medium ${
        stats.profile_complete
          ? 'bg-green-50 text-green-800 border border-green-200'
          : 'bg-amber-50 text-amber-800 border border-amber-200'
      }`}>
        {stats.profile_complete
          ? <><CheckCircle size={16} /> Profile complete</>
          : <><AlertCircle size={16} /> Profile incomplete — visit the Profile page to fill in your details</>
        }
      </div>

      {/* Stat cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          label="Peer-Reviewed Papers" value={stats.papers}
          icon={BookOpen} color="blue"
          onClick={() => toggle('papers')} expanded={expanded === 'papers'}
        />
        <StatCard
          label="Trainees" value={stats.trainees}
          icon={Users} color="green"
          onClick={() => toggle('trainees')} expanded={expanded === 'trainees'}
        />
        <StatCard
          label="Grants" value={stats.grants}
          subtitle={`${stats.active_grants} active`}
          icon={DollarSign} color="purple"
          onClick={() => toggle('grants')} expanded={expanded === 'grants'}
        />
        <StatCard
          label="Presentations" value={stats.scimeetings}
          icon={Presentation} color="orange"
          onClick={() => toggle('presentations')} expanded={expanded === 'presentations'}
        />
      </div>

      {/* Full-width expandable panels */}
      {expanded === 'papers' && (
        <PubPanel pubType="papers" title="Peer-Reviewed Papers" />
      )}
      {expanded === 'trainees' && (
        <TraineesPanel breakdown={stats.trainee_breakdown} total={stats.trainees} />
      )}
      {expanded === 'grants' && (
        <GrantsPanel
          breakdown={stats.active_grant_breakdown}
          activeCount={stats.active_grants}
          totalCount={stats.grants}
        />
      )}
      {expanded === 'presentations' && (
        <PubPanel pubType="scimeetings" title="Scientific Meeting Presentations" />
      )}
    </div>
  )
}

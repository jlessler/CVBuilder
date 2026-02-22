import { useQuery } from '@tanstack/react-query'
import { api } from '../lib/api'
import type { DashboardStats } from '../lib/api'
import { Card, Spinner } from '../components/ui'
import { BookOpen, Users, DollarSign, CheckCircle, AlertCircle } from 'lucide-react'

function StatCard({ label, value, icon: Icon, color = 'blue' }: {
  label: string; value: number | string; icon: React.ElementType; color?: string
}) {
  const colors: Record<string, string> = {
    blue: 'bg-blue-50 text-blue-700',
    green: 'bg-green-50 text-green-700',
    purple: 'bg-purple-50 text-purple-700',
    orange: 'bg-orange-50 text-orange-700',
  }
  return (
    <Card className="p-5">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm text-gray-500 font-medium">{label}</p>
          <p className="text-3xl font-bold text-gray-900 mt-1">{value}</p>
        </div>
        <div className={`p-3 rounded-xl ${colors[color] || colors.blue}`}>
          <Icon size={22} />
        </div>
      </div>
    </Card>
  )
}

export function Dashboard() {
  const { data: stats, isLoading } = useQuery<DashboardStats>({
    queryKey: ['dashboard'],
    queryFn: () => api.get('/dashboard').then(r => r.data),
  })

  if (isLoading) return <div className="p-8"><Spinner /></div>
  if (!stats) return null

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

      {/* Stats grid */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <StatCard label="Total Publications" value={stats.total_publications} icon={BookOpen} color="blue" />
        <StatCard label="Trainees" value={stats.trainees} icon={Users} color="green" />
        <StatCard label="Grants" value={stats.grants} icon={DollarSign} color="purple" />
        <StatCard label="Papers" value={stats.papers} icon={BookOpen} color="orange" />
      </div>

      {/* Publication breakdown */}
      <Card className="p-6">
        <h3 className="text-base font-semibold text-gray-900 mb-4">Publications Breakdown</h3>
        <div className="space-y-3">
          {[
            { label: 'Peer-Reviewed Papers', value: stats.papers, color: 'bg-blue-500' },
            { label: 'Preprints', value: stats.preprints, color: 'bg-cyan-500' },
            { label: 'Book Chapters', value: stats.chapters, color: 'bg-purple-500' },
            { label: 'Letters & Commentaries', value: stats.letters, color: 'bg-orange-500' },
            { label: 'Scientific Meeting Presentations', value: stats.scimeetings, color: 'bg-green-500' },
          ].map(({ label, value, color }) => {
            const pct = stats.total_publications > 0 ? (value / stats.total_publications) * 100 : 0
            return (
              <div key={label}>
                <div className="flex justify-between text-sm mb-1">
                  <span className="text-gray-700">{label}</span>
                  <span className="font-medium">{value}</span>
                </div>
                <div className="h-2 bg-gray-100 rounded-full">
                  <div className={`h-2 rounded-full ${color}`} style={{ width: `${pct}%` }} />
                </div>
              </div>
            )
          })}
        </div>
      </Card>
    </div>
  )
}

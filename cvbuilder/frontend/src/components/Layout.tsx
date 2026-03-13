import { Link, useLocation } from 'react-router-dom'
import {
  LayoutDashboard, User, BookOpen, Layout, Download, GraduationCap,
  LogOut, Files, BarChart3,
} from 'lucide-react'
import { useAuth } from '../contexts/AuthContext'

const navItems = [
  { to: '/', label: 'Dashboard', icon: LayoutDashboard },
  { to: '/profile', label: 'Profile', icon: User },
  { to: '/sections', label: 'CV Sections', icon: GraduationCap },
  { to: '/publications', label: 'Scholarly Works', icon: BookOpen },
  { to: '/citations', label: 'Citations', icon: BarChart3 },
  { to: '/cvs', label: 'CVs', icon: Files },
  { to: '/export', label: 'Import/Export', icon: Download },
  { to: '/templates', label: 'Templates', icon: Layout },
]

export function AppLayout({ children }: { children: React.ReactNode }) {
  const location = useLocation()
  const { user, logout } = useAuth()

  return (
    <div className="flex h-screen bg-gray-50">
      {/* Sidebar */}
      <aside className="w-56 bg-primary-900 text-white flex flex-col flex-shrink-0">
        <div className="px-4 py-5 border-b border-primary-800">
          <h1 className="text-lg font-bold tracking-wide">CVBuilder</h1>
          <p className="text-xs text-primary-200 mt-0.5">Academic CV Manager</p>
        </div>
        <nav className="flex-1 py-4 space-y-0.5 px-2">
          {navItems.map(({ to, label, icon: Icon }) => {
            const active = location.pathname === to ||
              (to !== '/' && location.pathname.startsWith(to))
            return (
              <Link
                key={to}
                to={to}
                className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors
                  ${active
                    ? 'bg-primary-700 text-white'
                    : 'text-primary-200 hover:bg-primary-800 hover:text-white'
                  }`}
              >
                <Icon size={16} />
                {label}
              </Link>
            )
          })}
        </nav>
        <div className="px-4 py-3 border-t border-primary-800">
          {user && (
            <div className="flex items-center justify-between">
              <span className="text-xs text-primary-300 truncate max-w-[120px]" title={user.email}>
                {user.email}
              </span>
              <button
                onClick={logout}
                className="text-primary-400 hover:text-white transition-colors"
                title="Sign out"
              >
                <LogOut size={14} />
              </button>
            </div>
          )}
          <p className="text-xs text-primary-400 mt-1">v1.0.0</p>
        </div>
      </aside>

      {/* Main content */}
      <main className="flex-1 overflow-auto">
        {children}
      </main>
    </div>
  )
}

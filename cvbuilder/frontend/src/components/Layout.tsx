import { Link, useLocation } from 'react-router-dom'
import {
  LayoutDashboard, User, BookOpen, Layout, Download, GraduationCap,
} from 'lucide-react'

const navItems = [
  { to: '/', label: 'Dashboard', icon: LayoutDashboard },
  { to: '/profile', label: 'Profile', icon: User },
  { to: '/sections', label: 'CV Sections', icon: GraduationCap },
  { to: '/publications', label: 'Publications', icon: BookOpen },
  { to: '/templates', label: 'Templates', icon: Layout },
  { to: '/export', label: 'Export', icon: Download },
]

export function AppLayout({ children }: { children: React.ReactNode }) {
  const location = useLocation()

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
        <div className="px-4 py-3 border-t border-primary-800 text-xs text-primary-400">
          v1.0.0
        </div>
      </aside>

      {/* Main content */}
      <main className="flex-1 overflow-auto">
        {children}
      </main>
    </div>
  )
}

import { NavLink, Route, Routes } from 'react-router-dom'
import { useHealth } from '@/api/hooks'
import { cn } from '@/lib/utils'
import CompetitorsPage from '@/pages/CompetitorsPage'
import PosesPage from '@/pages/PosesPage'
import ProjectPage from '@/pages/ProjectPage'
import ProjectsPage from '@/pages/ProjectsPage'
import SettingsPage from '@/pages/SettingsPage'

function HealthBanner() {
  const health = useHealth()
  if (health.isError) {
    return (
      <div className="bg-brand-red px-4 py-1.5 text-center text-sm text-paper">
        Бэкенд недоступен. Запустите сервер и обновите страницу.
      </div>
    )
  }
  if (health.data?.db === 'unreachable') {
    return (
      <div className="bg-brand-yellow px-4 py-1.5 text-center text-sm text-ink">
        База данных недоступна. {health.data.db_hint ?? 'Возможно, проект Supabase на паузе — откройте dashboard → Resume project.'}
      </div>
    )
  }
  return null
}

const nav = [
  { to: '/', label: 'Проекты', end: true },
  { to: '/competitors', label: 'Анализ конкурентов' },
  { to: '/poses', label: 'Библиотека поз' },
  { to: '/settings', label: 'Настройки' },
]

export default function App() {
  return (
    <div className="min-h-screen">
      <HealthBanner />
      <header className="border-b bg-paper">
        <div className="mx-auto flex h-14 max-w-[1400px] items-center gap-6 px-4">
          <NavLink to="/" className="flex items-center gap-2 font-bold tracking-tight">
            <span className="grid size-7 place-items-center rounded-md bg-brand-red text-sm text-paper">B</span>
            Basqasha
          </NavLink>
          <nav className="flex gap-1">
            {nav.map((n) => (
              <NavLink
                key={n.to}
                to={n.to}
                end={n.end}
                className={({ isActive }) =>
                  cn(
                    'rounded-md px-3 py-1.5 text-sm font-medium transition-colors',
                    isActive ? 'bg-ink text-paper' : 'text-muted-foreground hover:bg-muted hover:text-ink',
                  )
                }
              >
                {n.label}
              </NavLink>
            ))}
          </nav>
        </div>
      </header>
      <main className="mx-auto max-w-[1400px] px-4 py-6">
        <Routes>
          <Route path="/" element={<ProjectsPage />} />
          <Route path="/projects/:projectId" element={<ProjectPage />} />
          <Route path="/competitors" element={<CompetitorsPage />} />
          <Route path="/poses" element={<PosesPage />} />
          <Route path="/settings" element={<SettingsPage />} />
          <Route path="*" element={<p className="text-muted-foreground">Страница не найдена.</p>} />
        </Routes>
      </main>
    </div>
  )
}

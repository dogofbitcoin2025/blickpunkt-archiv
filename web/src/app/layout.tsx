import type { Metadata } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: 'BlickPUNKT Archiv',
  description: 'Redaktionelles Archiv aller BlickPUNKT-Ausgaben',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="de">
      <body>
        <header className="site-header">
          <div className="header-inner">
            <a href="/" className="logo">
              <span className="logo-blick">Blick</span><span className="logo-punkt">PUNKT</span>
              <span className="logo-sub">Archiv</span>
            </a>
            <nav className="main-nav">
              <a href="/">Suche</a>
              <a href="/dashboard">Dashboard</a>
            </nav>
          </div>
        </header>
        <main className="main-content">{children}</main>
        <footer className="site-footer">
          <p>BlickPUNKT Archiv – Nur für interne redaktionelle Nutzung</p>
        </footer>
      </body>
    </html>
  )
}

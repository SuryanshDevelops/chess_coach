import GameReview from "./GameReview";
import { useState } from "react";
import "./App.css";

const navigation = [
  { name: "Dashboard", icon: "⌂" },
   { name: "Game Review", icon: "♞" },
  { name: "My Games", icon: "♟" },
  { name: "Statistics", icon: "▥" },
  { name: "Settings", icon: "⚙" },
];

function App() {
  const [activePage, setActivePage] = useState("Dashboard");

  return (
    <div className="app">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-icon">♞</div>
          <div>
            <h1>Chess Coach</h1>
            <span>YOUR PERSONAL ANALYST</span>
          </div>
        </div>

        <div className="nav-label">WORKSPACE</div>

        <nav>
          {navigation.map((item) => (
            <button
              key={item.name}
              className={`nav-item ${
                activePage === item.name ? "active" : ""
              }`}
              onClick={() => setActivePage(item.name)}
            >
              <span className="nav-icon">{item.icon}</span>
              {item.name}
            </button>
          ))}
        </nav>

        <div className="sidebar-bottom">
          <div className="profile-avatar">S</div>
          <div className="profile-info">
            <strong>Chess Player</strong>
            <span>Personal workspace</span>
          </div>
          <span className="profile-menu">···</span>
        </div>
      </aside>

      <main className="main-content">
        <header className="topbar">
          <div>
            <span className="breadcrumb">WORKSPACE /</span>
            <span className="current-page">{activePage}</span>
          </div>
          <div className="topbar-right">
            <span className="connection-dot" />
            <span>Local workspace</span>
          </div>
        </header>

       {activePage === "Dashboard" && <Dashboard />}
       {activePage === "Game Review" && <GameReview />}
       {activePage === "My Games" && <Placeholder title="My Games" description="Your saved Chess.com games will appear here once we connect the Python backend." />}
       {activePage === "Statistics" && <Placeholder title="Statistics" description="Your performance charts and game statistics will appear here." />}
       {activePage === "Settings" && <Placeholder title="Settings" description="Configure your Chess Coach preferences here." />}
      </main>
    </div>
  );
}

function Dashboard() {
  return (
    <section className="page">
      <div className="page-heading">
        <div>
          <div className="eyebrow">OVERVIEW</div>
          <h2>Dashboard</h2>
          <p>Your chess performance, all in one place.</p>
        </div>
        <div className="date-label">PERSONAL WORKSPACE</div>
      </div>

      <div className="welcome-panel">
        <div>
          <div className="eyebrow green-text">CHESS COACH</div>
          <h3>Understand your game.<br />Improve your decisions.</h3>
          <p>
            Review your games, discover patterns and understand
            where your chess can improve.
          </p>
        </div>
        <div className="welcome-piece">♞</div>
      </div>

      <div className="section-heading">
        <h3>Performance overview</h3>
        <span>EXAMPLE DATA</span>
      </div>

      <div className="stats-grid">
        <StatCard label="Games analysed" value="—" detail="Connect your game database" />
        <StatCard label="Win rate" value="—" detail="Calculated from saved games" />
        <StatCard label="Current form" value="—" detail="Based on recent games" />
        <StatCard label="Average accuracy" value="—" detail="Requires engine analysis" />
      </div>

      <div className="bottom-grid">
        <div className="panel">
          <div className="panel-heading">
            <h3>Recent activity</h3>
            <span>GAME HISTORY</span>
          </div>
          <div className="empty-state">
            <div className="empty-icon">♟</div>
            <strong>No games loaded yet</strong>
            <p>Your recent games will appear here after we connect your existing database.</p>
          </div>
        </div>

        <div className="panel">
          <div className="panel-heading">
            <h3>Quick access</h3>
            <span>TOOLS</span>
          </div>
          <div className="quick-link">
            <div className="quick-icon">♟</div>
            <div>
              <strong>Game review</strong>
              <p>Explore your moves and positions</p>
            </div>
            <span>→</span>
          </div>
          <div className="quick-link">
            <div className="quick-icon">▥</div>
            <div>
              <strong>Statistics</strong>
              <p>Understand your performance</p>
            </div>
            <span>→</span>
          </div>
        </div>
      </div>

      <footer className="footer">
        CHESS COACH <span>•</span> DEVELOPMENT VERSION
      </footer>
    </section>
  );
}

function StatCard({
  label,
  value,
  detail,
}: {
  label: string;
  value: string;
  detail: string;
}) {
  return (
    <div className="stat-card">
      <span className="stat-label">{label}</span>
      <strong className="stat-value">{value}</strong>
      <span className="stat-detail">{detail}</span>
    </div>
  );
}

function Placeholder({
  title,
  description,
}: {
  title: string;
  description: string;
}) {
  return (
    <section className="page">
      <div className="page-heading">
        <div>
          <div className="eyebrow">WORKSPACE</div>
          <h2>{title}</h2>
          <p>{description}</p>
        </div>
      </div>
      <div className="panel placeholder-panel">
        <div className="empty-icon">♞</div>
        <strong>{title} is being built</strong>
        <p>{description}</p>
      </div>
    </section>
  );
}

export default App;
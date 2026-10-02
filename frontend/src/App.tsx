import './App.css'

function App() {
  return (
    <main className="app-shell">
      <header className="hero">
        <p className="eyebrow">Milestone 1 foundation</p>
        <h1>OpenShelf</h1>
        <p className="subtitle">
          A local, free book-discovery app for finding legitimate reading, lending,
          preview, and download options.
        </p>
      </header>

      <section className="status-grid" aria-label="Project foundation status">
        <article className="status-card">
          <span className="label">Frontend</span>
          <strong>React + Vite + TypeScript</strong>
        </article>
        <article className="status-card">
          <span className="label">Backend</span>
          <strong>Python + FastAPI</strong>
        </article>
        <article className="status-card">
          <span className="label">Project goal</span>
          <strong>Safe, legal book discovery</strong>
        </article>
      </section>
    </main>
  )
}

export default App

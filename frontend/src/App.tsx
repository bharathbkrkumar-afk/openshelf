import { useState } from 'react'
import type { FormEvent } from 'react'
import './App.css'

type SourceLink = {
  label: string
  url: string
}

type AccessInfo = {
  full_text: boolean
  preview: boolean
  note: string
}

type BookResult = {
  provider?: string
  title: string
  authors: string[]
  publication_year?: number | null
  cover_url?: string | null
  source_links: SourceLink[]
  access?: AccessInfo
}

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000'

function App() {
  const [query, setQuery] = useState('')
  const [books, setBooks] = useState<BookResult[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [hasSearched, setHasSearched] = useState(false)

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()

    const trimmedQuery = query.trim()
    if (!trimmedQuery) {
      setBooks([])
      setError('Please enter a book title or author.')
      setHasSearched(true)
      return
    }

    setLoading(true)
    setError('')
    setHasSearched(true)

    try {
      const response = await fetch(
        `${API_BASE_URL}/api/books/search?q=${encodeURIComponent(trimmedQuery)}`,
      )
      const payload = await response.json()

      if (!response.ok) {
        throw new Error(payload.detail || 'The search could not be completed.')
      }

      setBooks(Array.isArray(payload.results) ? payload.results : [])
    } catch (fetchError) {
      setBooks([])
      setError(
        fetchError instanceof Error
          ? fetchError.message
          : 'The book search service is unavailable right now.',
      )
    } finally {
      setLoading(false)
    }
  }

  return (
    <main className="app-shell">
      <header className="hero">
        <p className="eyebrow">OpenShelf</p>
        <h1>Find free and legal book options</h1>
        <p className="subtitle">
          Search by title or author to discover books with legitimate Open Library
          listings and supported access details.
        </p>
      </header>

      <form className="search-form" onSubmit={handleSubmit}>
        <label className="sr-only" htmlFor="book-search">
          Search books
        </label>
        <input
          id="book-search"
          type="text"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="Try: Pride and Prejudice or George Orwell"
          aria-label="Book title or author"
        />
        <button type="submit" disabled={loading}>
          {loading ? 'Searching...' : 'Search'}
        </button>
      </form>

      {error && <p className="status-message error">{error}</p>}

      {hasSearched && !loading && books.length === 0 && !error && (
        <p className="status-message">No results found. Try a different title or author.</p>
      )}

      {loading && <p className="status-message">Loading books...</p>}

      <section className="results-grid" aria-live="polite">
        {books.map((book, index) => {
          const accessTags = [
            book.access?.full_text ? 'FULL TEXT' : null,
            book.access?.preview ? 'PREVIEW' : null,
          ].filter(Boolean) as string[]

          return (
            <article
              key={`${book.provider ?? 'provider'}-${book.title}-${book.authors.join(',')}-${index}`}
              className="book-card"
            >
              <div className="cover-wrap">
                {book.cover_url ? (
                  <img src={book.cover_url} alt={`${book.title} cover`} className="cover" />
                ) : (
                  <div className="cover-placeholder" aria-label="No cover available">
                    {book.title.charAt(0).toUpperCase()}
                  </div>
                )}
              </div>

              <div className="book-content">
                <h2>{book.title}</h2>
                <p className="author-list">{book.authors.join(', ')}</p>
                {book.publication_year ? (
                  <p className="publication-year">First published: {book.publication_year}</p>
                ) : null}

                <div className="access-wrap">
                  {accessTags.length > 0 ? (
                    accessTags.map((tag) => (
                      <span key={`${book.title}-${book.authors.join(',')}-${tag}-${index}`} className="access-pill">
                        {tag}
                      </span>
                    ))
                  ) : (
                    <span className="access-pill muted">No suitable free full-text version was found from our supported sources.</span>
                  )}
                </div>

                {book.access?.note ? (
                  <p className="access-note">{book.access.note}</p>
                ) : null}

                {book.source_links.length > 0 ? (
                  <div className="links-wrap">
                    {book.source_links.map((link) => (
                      <a key={`${link.label}-${link.url}`} href={link.url} target="_blank" rel="noreferrer">
                        {link.label}
                      </a>
                    ))}
                  </div>
                ) : (
                  <p className="no-links">No verified external links were returned for this edition.</p>
                )}
              </div>
            </article>
          )
        })}
      </section>
    </main>
  )
}

export default App

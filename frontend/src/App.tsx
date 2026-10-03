import { useState } from 'react'
import type { FormEvent } from 'react'
import './App.css'
import PdfScanner from './PdfScanner'
import PriceComparison from './PriceComparison'

type SourceLink = {
  label: string
  url: string
}

type AccessInfo = {
  is_verified_full_book: boolean;
  is_borrowable: boolean;
  is_preview: boolean;
  is_unverified: boolean;
  free_download: boolean;
  read_online: boolean;
  category: string;
  note: string;
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
  const [filter, setFilter] = useState('All Results')

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
    setFilter('All Results')

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

  const filteredBooks = books.filter(book => {
    const a = book.access
    if (!a) return filter === 'All Results' || filter === 'Completeness Unverified'
    
    switch (filter) {
      case 'All Results': return true
      case 'Verified Full Books': return a.is_verified_full_book
      case 'Free Full-Text Downloads': return a.free_download
      case 'Read Online': return a.read_online
      case 'Borrow Full Book': return a.is_borrowable
      case 'Preview / Partial': return a.is_preview
      case 'Completeness Unverified': return a.is_unverified
      default: return true
    }
  })

  return (
    <main className="app-shell">
      <header className="hero">
        <p className="eyebrow">OpenShelf</p>
        <h1>Find free and legal book options</h1>
        <p className="subtitle">
          Search by title or author to discover books with legitimate sources and supported access details.
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

      <PdfScanner />

      {error && <p className="status-message error">{error}</p>}

      {hasSearched && !loading && books.length === 0 && !error && (
        <p className="status-message">No results found. Try a different title or author.</p>
      )}

      {loading && <p className="status-message">Loading books...</p>}

      {hasSearched && !loading && books.length > 0 ? (
        <div className="filters-wrap">
          <label htmlFor="filter-select">Filter access: </label>
          <select 
            id="filter-select" 
            value={filter} 
            onChange={e => setFilter(e.target.value)}
          >
            <option value="All Results">All Results</option>
            <option value="Verified Full Books">Verified Full Books</option>
            <option value="Free Full-Text Downloads">Free Full-Text Downloads</option>
            <option value="Read Online">Read Online</option>
            <option value="Borrow Full Book">Borrow Full Book</option>
            <option value="Preview / Partial">Preview / Partial</option>
            <option value="Completeness Unverified">Completeness Unverified</option>
          </select>
        </div>
      ) : null}

      <section className="results-grid" aria-live="polite">
        {filteredBooks.map((book, index) => {
          const access = book.access ?? {
            is_verified_full_book: false,
            is_borrowable: false,
            is_preview: false,
            is_unverified: true,
            free_download: false,
            read_online: false,
            category: "COMPLETENESS_UNVERIFIED",
            note: "No verified full-text version was found from our supported sources."
          }

          const accessTags = [
            access.is_verified_full_book ? 'FULL BOOK — VERIFIED' : null,
            access.is_borrowable ? 'BORROWABLE FULL BOOK' : null,
            access.is_preview ? 'PREVIEW / SAMPLE' : null,
            access.is_unverified ? 'COMPLETENESS UNVERIFIED' : null,
          ].filter(Boolean) as string[]

          const primaryLink = book.source_links[0]

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
                    <span className="access-pill muted">COMPLETENESS UNVERIFIED</span>
                  )}
                </div>

                {access.free_download && primaryLink ? (
                  <a className="primary-action" href={primaryLink.url} target="_blank" rel="noreferrer">
                    Download Full Book
                  </a>
                ) : null}
                
                {access.read_online && primaryLink ? (
                  <a className="primary-action" href={primaryLink.url} target="_blank" rel="noreferrer">
                    Read Full Book Online
                  </a>
                ) : null}

                {access.is_borrowable && primaryLink ? (
                  <a className="secondary-action" href={primaryLink.url} target="_blank" rel="noreferrer">
                    Borrow Full Book
                  </a>
                ) : null}

                {access.is_preview && primaryLink ? (
                  <a className="secondary-action" href={primaryLink.url} target="_blank" rel="noreferrer">
                    Preview Only
                  </a>
                ) : null}
                
                {access.is_unverified && primaryLink ? (
                  <a className="secondary-action" href={primaryLink.url} target="_blank" rel="noreferrer">
                    Search / View Source
                  </a>
                ) : null}

                {access.note ? <p className="access-note">{access.note}</p> : null}

                <PriceComparison query={`${book.title} ${book.authors.join(' ')}`} />

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
      
      {hasSearched && !loading && filteredBooks.length === 0 && books.length > 0 && (
         <p className="status-message">No results match this filter. Try selecting 'All Results'.</p>
      )}
    </main>
  )
}

export default App

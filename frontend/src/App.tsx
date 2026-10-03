import { useState } from 'react'
import type { FormEvent } from 'react'
import './App.css'

type SourceLink = {
  label: string
  url: string
}

type AccessInfo = {
  full_text_available: boolean
  preview_only: boolean
  borrow_available: boolean
  no_verified_full_text: boolean
  full_text?: boolean
  preview?: boolean
  borrow?: boolean
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
const GOOGLE_PDF_SEARCH_URL = 'https://www.google.com/search'

function parseSearchTitleAndAuthor(searchText: string | null | undefined) {
  const trimmedSearch = searchText?.trim() ?? ''
  if (!trimmedSearch) {
    return { title: '', author: '' }
  }

  const splitPattern = /\s[-—–]\s|\s\|\s/
  const splitMatch = trimmedSearch.split(splitPattern)
  if (splitMatch.length >= 2) {
    const [title, ...rest] = splitMatch
    return {
      title: title.trim(),
      author: rest.join(' ').trim(),
    }
  }

  return { title: trimmedSearch, author: '' }
}

function buildGooglePdfSearchUrl(searchText: string | null | undefined) {
  const { title, author } = parseSearchTitleAndAuthor(searchText)
  if (!title) {
    return null
  }

  const queryParts = [`"${title}"`]
  if (author) {
    queryParts.push(`"${author}"`)
  }
  queryParts.push('filetype:pdf')

  const params = new URLSearchParams({ q: queryParts.join(' ') })
  return `${GOOGLE_PDF_SEARCH_URL}?${params.toString()}`
}

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

    const googlePdfUrl = buildGooglePdfSearchUrl(trimmedQuery)
    if (googlePdfUrl) {
      window.open(googlePdfUrl, '_blank', 'noopener,noreferrer')
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

      {hasSearched && !loading && query.trim() ? (
        (() => {
          const pdfSearchUrl = buildGooglePdfSearchUrl(query)
          if (!pdfSearchUrl) {
            return null
          }

          return (
            <div className="pdf-search-bar">
              <p>Leave OpenShelf and open Google to search for public PDF copies in a new tab.</p>
              <a href={pdfSearchUrl} target="_blank" rel="noreferrer">
                Find Book PDFs
              </a>
            </div>
          )
        })()
      ) : null}

      <section className="results-grid" aria-live="polite">
        {books.map((book, index) => {
          const access = book.access ?? {
            full_text_available: false,
            preview_only: false,
            borrow_available: false,
            no_verified_full_text: true,
            note: 'No verified full-text version was found from our supported sources.',
          }

          const accessTags = [
            access.full_text_available ? 'FULL TEXT' : null,
            access.preview_only ? 'PREVIEW ONLY' : null,
            access.borrow_available ? 'BORROW AVAILABLE' : null,
            access.no_verified_full_text ? 'NO VERIFIED FULL TEXT' : null,
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
                    <span className="access-pill muted">No verified full-text version was found from our supported sources.</span>
                  )}
                </div>

                {access.full_text_available && primaryLink ? (
                  <a className="primary-action" href={primaryLink.url} target="_blank" rel="noreferrer">
                    Read Full Book
                  </a>
                ) : null}

                {access.preview_only && primaryLink ? (
                  <a className="secondary-action" href={primaryLink.url} target="_blank" rel="noreferrer">
                    Preview Only
                  </a>
                ) : null}

                {access.note ? <p className="access-note">{access.note}</p> : null}

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

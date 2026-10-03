import { useState } from 'react'
import './PriceComparison.css'

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000'

export type PriceOffer = {
  retailer: string
  title: string
  author?: string
  edition?: string
  isbn?: string
  format: string
  price_inr: number
  discount_percentage?: number
  availability: string
  shipping_cost_inr?: number
  product_url: string
  last_checked: string
  is_approximate_match: boolean
}

export type SearchLink = {
  retailer: string
  url: string
}

export type PricingResult = {
  query: string
  offers: PriceOffer[]
  search_links: SearchLink[]
  errors: string[]
}

interface PriceComparisonProps {
  query: string
}

export default function PriceComparison({ query }: PriceComparisonProps) {
  const [isOpen, setIsOpen] = useState(false)
  const [loading, setLoading] = useState(false)
  const [data, setData] = useState<PricingResult | null>(null)
  const [error, setError] = useState('')

  const handleFetchPrices = async () => {
    if (!isOpen) {
      setIsOpen(true)
    }

    setLoading(true)
    setError('')

    try {
      const response = await fetch(`${API_BASE_URL}/api/books/prices?q=${encodeURIComponent(query)}`)
      const payload = await response.json()

      if (!response.ok) {
        throw new Error(payload.detail || 'Could not fetch prices.')
      }

      setData(payload)
    } catch (err: any) {
      setError(err.message || 'The price comparison service is unavailable.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="price-comparison-container">
      <div className="price-controls">
        <button 
          className="secondary-action compare-btn" 
          onClick={() => {
            if (!isOpen) {
              handleFetchPrices()
            } else {
              setIsOpen(false)
            }
          }}
          aria-expanded={isOpen}
        >
          {isOpen ? 'Hide Retailer Prices' : 'Compare Print Prices (India)'}
        </button>
        {isOpen && (
          <button className="refresh-btn" onClick={handleFetchPrices} disabled={loading}>
            Refresh Prices
          </button>
        )}
      </div>

      {isOpen && (
        <div className="price-results-panel">
          {loading && <p className="status-message">Fetching live prices...</p>}
          
          {error && <p className="status-message error">{error}</p>}

          {data && (
            <div className="pricing-content">
              {data.offers.length > 0 ? (
                <div className="offers-list">
                  <h4>Verified Prices</h4>
                  {data.offers.map((offer, idx) => (
                    <div key={idx} className="offer-card">
                      <div className="offer-header">
                        <strong>{offer.retailer}</strong>
                        <span className="price">₹{offer.price_inr.toFixed(2)}</span>
                      </div>
                      <div className="offer-details">
                        <p>{offer.title} {offer.edition ? `(${offer.edition})` : ''}</p>
                        <p className="format">{offer.format} {offer.is_approximate_match ? '(Approx. match)' : ''}</p>
                        <p className="availability">
                          {offer.availability} 
                          {offer.shipping_cost_inr ? ` | +₹${offer.shipping_cost_inr} shipping` : ''}
                        </p>
                        <p className="timestamp">Verified: {new Date(offer.last_checked).toLocaleTimeString()}</p>
                      </div>
                      <a href={offer.product_url} target="_blank" rel="noreferrer" className="buy-link">
                        View Offer
                      </a>
                    </div>
                  ))}
                </div>
              ) : null}

              {data.search_links.length > 0 ? (
                <div className="search-links-list">
                  <h4>Search Retailers</h4>
                  <p className="note">Live pricing API not available for these retailers without credentials. Search directly:</p>
                  <div className="retailer-chips">
                    {data.search_links.map((link, idx) => (
                      <a key={idx} href={link.url} target="_blank" rel="noreferrer" className="retailer-chip">
                        Search {link.retailer}
                      </a>
                    ))}
                  </div>
                </div>
              ) : null}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

import { type SubmitEvent, useState } from 'react'
import styles from './App.module.css'

type SearchResult = {
  url: string
  score: number
}

type SearchResponse = {
  query: string
  total: number
  elapsed_ms: number
  results: SearchResult[]
}

type ApiError = {
  detail?: string
}

function App() {
  const [query, setQuery] = useState('')
  const [response, setResponse] = useState<SearchResponse | null>(null)
  const [error, setError] = useState('')
  const [isLoading, setIsLoading] = useState(false)

  async function handleSubmit(event: SubmitEvent<HTMLFormElement>) {
    event.preventDefault()

    const trimmedQuery = query.trim()

    if (!trimmedQuery) {
      setError('Enter at least one search term.')
      return
    }

    setIsLoading(true)
    setError('')

    try {
      const request = await fetch(
        `/api/search?q=${encodeURIComponent(trimmedQuery)}&limit=10`,
      )

      if (!request.ok) {
        const apiError = (await request.json()) as ApiError
        throw new Error(apiError.detail ?? 'The search request failed.')
      }

      const data = (await request.json()) as SearchResponse
      setResponse(data)
    } catch (caughtError) {
      const message =
        caughtError instanceof Error
          ? caughtError.message
          : 'An unexpected error occurred.'

      setError(message)
      setResponse(null)
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <main className={styles.page}>
      <section className={styles.searchSection}>
        <h1 className={styles.title}>Full Search Engine</h1>
        <p className={styles.subtitle}>
          Search the documents in the local index.
        </p>

        <form className={styles.searchForm} onSubmit={handleSubmit}>
          <label className={styles.visuallyHidden} htmlFor="search-query">
            Search query
          </label>

          <input
            id="search-query"
            className={styles.searchInput}
            type="search"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Enter a search query"
            autoComplete="off"
          />

          <button
            className={styles.searchButton}
            type="submit"
            disabled={isLoading}
          >
            {isLoading ? 'Searching…' : 'Search'}
          </button>
        </form>

        {error && <p className={styles.error}>{error}</p>}
      </section>

      {response && (
        <section className={styles.results} aria-live="polite">
          <p className={styles.summary}>
            {response.total} results in {response.elapsed_ms.toFixed(2)} ms
          </p>

          {response.results.length === 0 ? (
            <p>No documents matched every search term.</p>
          ) : (
            <ol className={styles.resultList}>
              {response.results.map((result) => (
                <li className={styles.resultCard} key={result.url}>
                  <a
                    className={styles.resultLink}
                    href={result.url}
                    target="_blank"
                    rel="noreferrer"
                  >
                    {result.url}
                  </a>

                  <p className={styles.score}>
                    Relevance score: {result.score.toFixed(4)}
                  </p>
                </li>
              ))}
            </ol>
          )}
        </section>
      )}
    </main>
  )
}

export default App
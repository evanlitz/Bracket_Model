import { useState, useEffect } from 'react'
import SearchPanel from './components/SearchPanel'
import QueryCard from './components/QueryCard'
import MatchCarousel from './components/MatchCarousel'
import BracketViewer from './components/BracketViewer'
import FeatureImportanceViewer from './components/FeatureImportanceViewer'
import AnalyticsViewer from './components/AnalyticsViewer'
import MatchupBuilder from './components/MatchupBuilder'
import BracketSimulator from './components/BracketSimulator'
import Scorecard from './components/Scorecard'
import UpsetFinder from './components/UpsetFinder'
import ModelReport from './components/ModelReport'

export default function App() {
  const [activeTab, setActiveTab]       = useState('similarity')
  const [allTeams, setAllTeams]         = useState([])
  const [loading, setLoading]           = useState(false)
  const [error, setError]               = useState(null)
  const [results, setResults]           = useState(null)
  const [teamWeight, setTeamWeight]     = useState(40)
  const [playerWeight, setPlayerWeight] = useState(60)

  useEffect(() => {
    fetch('/api/teams')
      .then(r => r.json())
      .then(setAllTeams)
      .catch(() => setError('Failed to load team list. Is the backend running?'))
  }, [])

  const handleSearch = async ({ year, team }) => {
    setLoading(true)
    setError(null)
    setResults(null)
    try {
      const tw = teamWeight / 100
      const pw = playerWeight / 100
      const res = await fetch(
        `/api/similar/${year}/${encodeURIComponent(team)}?top_n=10&team_weight=${tw}&player_weight=${pw}`
      )
      if (!res.ok) {
        const err = await res.json().catch(() => ({}))
        throw new Error(err.detail || `${res.status} ${res.statusText}`)
      }
      const data = await res.json()
      setResults(data)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="app">
      <header className="app-header">
        <div>
          <h1 className="display">March Madness Model</h1>
          <div className="subtitle">NCAA Tournament · 2002–2025 · Leave-Year-Out Prediction</div>
        </div>
      </header>

      <nav className="tab-bar">
        <button
          className={`tab-btn${activeTab === 'similarity' ? ' active' : ''}`}
          onClick={() => setActiveTab('similarity')}
        >
          Team Similarity
        </button>
        <button
          className={`tab-btn${activeTab === 'bracket' ? ' active' : ''}`}
          onClick={() => setActiveTab('bracket')}
        >
          Bracket Predictor
        </button>
        <button
          className={`tab-btn${activeTab === 'features' ? ' active' : ''}`}
          onClick={() => setActiveTab('features')}
        >
          Feature Importance
        </button>
        <button
          className={`tab-btn${activeTab === 'matchup' ? ' active' : ''}`}
          onClick={() => setActiveTab('matchup')}
        >
          Matchup Builder
        </button>
        <button
          className={`tab-btn${activeTab === 'simulator' ? ' active' : ''}`}
          onClick={() => setActiveTab('simulator')}
        >
          Simulator
        </button>
        <button
          className={`tab-btn${activeTab === 'scorecard' ? ' active' : ''}`}
          onClick={() => setActiveTab('scorecard')}
        >
          2026 Scorecard
        </button>
        <button
          className={`tab-btn${activeTab === 'upsets' ? ' active' : ''}`}
          onClick={() => setActiveTab('upsets')}
        >
          Upset Finder
        </button>
        <button
          className={`tab-btn${activeTab === 'report' ? ' active' : ''}`}
          onClick={() => setActiveTab('report')}
        >
          Model Report
        </button>
        <button
          className={`tab-btn${activeTab === 'analytics' ? ' active' : ''}`}
          onClick={() => setActiveTab('analytics')}
        >
          Analytics
        </button>
      </nav>

      <div className="app-body">
        {activeTab === 'similarity' && (
          <>
            <SearchPanel
              allTeams={allTeams}
              onSearch={handleSearch}
              loading={loading}
              teamWeight={teamWeight}
              playerWeight={playerWeight}
              onWeightChange={(tw, pw) => { setTeamWeight(tw); setPlayerWeight(pw) }}
            />

            {error && (
              <div className="state-msg" style={{ color: 'var(--red-bright)' }}>
                {error}
              </div>
            )}

            {loading && (
              <div className="state-msg loading">Finding similar teams</div>
            )}

            {!loading && !error && !results && allTeams.length > 0 && (
              <div className="state-msg">
                Select a team and year above to find the 10 most similar historical tournament teams.
              </div>
            )}

            {!loading && !error && !results && allTeams.length === 0 && (
              <div className="state-msg loading">Connecting to backend</div>
            )}

            {results && (
              <>
                <div className="query-section">
                  <QueryCard profile={results.query} />
                </div>
                <div className="results-section">
                  <div className="results-header display">
                    Top {results.matches.length} Historical Matches
                    <span className="mono" style={{ fontSize: '0.75rem', color: 'var(--cream-dim)', fontFamily: 'var(--font-mono)', textTransform: 'none', letterSpacing: 0 }}>
                      — sorted by combined similarity
                    </span>
                  </div>
                  <MatchCarousel matches={results.matches} queryStats={results.query?.key_stats} />
                </div>
              </>
            )}
          </>
        )}

        {activeTab === 'bracket' && <BracketViewer allTeams={allTeams} />}
        {activeTab === 'features' && <FeatureImportanceViewer />}
        {activeTab === 'matchup'   && <MatchupBuilder allTeams={allTeams} />}
        {activeTab === 'simulator' && <BracketSimulator allTeams={allTeams} />}
        {activeTab === 'scorecard' && <Scorecard />}
        {activeTab === 'upsets'    && <UpsetFinder />}
        {activeTab === 'report'    && <ModelReport />}
        {activeTab === 'analytics' && <AnalyticsViewer />}
      </div>
    </div>
  )
}

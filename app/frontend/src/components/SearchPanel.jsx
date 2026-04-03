import { useState, useMemo } from 'react'

export default function SearchPanel({
  allTeams, onSearch, loading,
  teamWeight, playerWeight, onWeightChange,
}) {
  const [year, setYear]   = useState('')
  const [team, setTeam]   = useState('')

  // Unique years, descending
  const years = useMemo(() => {
    const s = [...new Set(allTeams.map(t => t.year))].sort((a, b) => b - a)
    return s
  }, [allTeams])

  // Teams for selected year, sorted by seed then name
  const teamsForYear = useMemo(() => {
    if (!year) return []
    return allTeams
      .filter(t => t.year === parseInt(year))
      .sort((a, b) => (a.seed || 99) - (b.seed || 99) || a.team.localeCompare(b.team))
  }, [allTeams, year])

  const handleYearChange = (e) => {
    setYear(e.target.value)
    setTeam('')
  }

  const handleSubmit = (e) => {
    e.preventDefault()
    if (!year || !team) return
    onSearch({ year: parseInt(year), team })
  }

  const totalW = teamWeight + playerWeight
  const normTW = totalW > 0 ? teamWeight / totalW : 0.5
  const normPW = totalW > 0 ? playerWeight / totalW : 0.5

  const handleTWChange = (e) => {
    const tw = parseInt(e.target.value)
    onWeightChange(tw, 100 - tw)
  }

  return (
    <form className="search-panel" onSubmit={handleSubmit}>
      <label>
        Season
        <select value={year} onChange={handleYearChange} required>
          <option value="">— select year —</option>
          {years.map(y => (
            <option key={y} value={y}>{y}</option>
          ))}
        </select>
      </label>

      <label>
        Team
        <select value={team} onChange={e => setTeam(e.target.value)} required disabled={!year}>
          <option value="">— select team —</option>
          {teamsForYear.map(t => (
            <option key={`${t.year}-${t.team}`} value={t.team}>
              {t.seed ? `#${t.seed} ` : ''}{t.team}{t.conf ? ` (${t.conf})` : ''}
            </option>
          ))}
        </select>
      </label>

      <label className="weight-control" style={{ flexDirection: 'column', gap: 6 }}>
        Team Weight: {teamWeight}%
        <input
          type="range" min={0} max={100} step={5}
          value={teamWeight}
          onChange={handleTWChange}
        />
        <span style={{ fontSize: '0.6rem', color: 'var(--cream-dim)' }}>
          Player: {100 - teamWeight}%
        </span>
      </label>

      <button className="search-btn" type="submit" disabled={loading || !year || !team}>
        {loading ? 'Searching…' : 'Find Matches'}
      </button>
    </form>
  )
}

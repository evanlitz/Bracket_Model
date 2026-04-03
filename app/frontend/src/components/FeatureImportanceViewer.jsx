import { useState, useEffect } from 'react'

const ROUND_KEYS  = ['1', '2', '3', '4', '5', '6']
const ROUND_LABELS = { '1': 'R64', '2': 'R32', '3': 'S16', '4': 'E8', '5': 'F4', '6': 'NCG' }
const TRAJ_ROUNDS  = ['1', '2', '3', '4', '5'] // skip NCG (tiny sample)

const FEATURE_COLORS = [
  '#c9a84c', '#3b82f6', '#22c55e', '#f87171',
  '#a78bfa', '#fb923c', '#38bdf8', '#f472b6',
]

// ── Accuracy bar across rounds ────────────────────────────────────────────────

function AccuracyStrip({ data }) {
  const rounds = ROUND_KEYS.map(rk => ({
    key: rk,
    label: ROUND_LABELS[rk],
    cv:   data.rounds[rk]?.cv_acc,
    seed: data.rounds[rk]?.seed_acc,
    n:    data.rounds[rk]?.n_games ?? 0,
  })).filter(r => r.cv != null)

  return (
    <div className="fi-accuracy-strip">
      {rounds.map(r => {
        const delta     = r.cv - (r.seed ?? r.cv)
        const deltaSign = delta > 0.005 ? 'pos' : delta < -0.005 ? 'neg' : 'zero'
        return (
          <div key={r.key} className="fi-acc-card">
            <div className="fi-acc-round">{r.label}</div>
            <div className="fi-acc-pct mono">{(r.cv * 100).toFixed(0)}%</div>
            {r.seed != null && (
              <div className={`fi-acc-delta mono fi-delta ${deltaSign}`}>
                {delta >= 0 ? '+' : ''}{(delta * 100).toFixed(1)}%
              </div>
            )}
            <div className="fi-acc-n mono">{r.n}g</div>
            {/* bar fill */}
            <div className="fi-acc-bar-track">
              <div className="fi-acc-bar-fill" style={{ width: `${r.cv * 100}%` }} />
              {r.seed != null && (
                <div className="fi-acc-bar-seed" style={{ left: `${r.seed * 100}%` }} />
              )}
            </div>
          </div>
        )
      })}
    </div>
  )
}

// ── Horizontal bar chart (permutation or correlation) ────────────────────────

function FeatureChart({ title, items, colorClass, showAll, onToggle, coverageMap }) {
  if (!items || items.length === 0) {
    return (
      <div className="fi-chart-card">
        <div className="fi-chart-title">{title}</div>
        <div className="fi-no-data">Not computed — sample too small</div>
      </div>
    )
  }

  const displayed = showAll ? items : items.slice(0, 15)
  const maxAbs = Math.max(...items.map(d => Math.abs(d.value)), 0.0001)

  return (
    <div className="fi-chart-card">
      <div className="fi-chart-title">{title}</div>

      {displayed.map((d, i) => {
        const pct      = (Math.abs(d.value) / maxAbs) * 100
        const isNeg    = d.value < 0
        const barClass = `fi-bar ${isNeg ? 'neg' : colorClass}`
        const cov      = coverageMap[d.feature]
        const lowCov   = cov !== undefined && cov < 0.80

        return (
          <div className="fi-row" key={d.feature}>
            <span className={`fi-feat-label${i < 5 ? ' top' : ''}`} title={d.label}>
              {d.label}
            </span>
            <div className="fi-bar-wrap">
              <div className={barClass} style={{ width: `${pct}%` }} />
              <span className={`fi-val${isNeg ? ' neg-val' : ''}`}>
                {d.value >= 0 ? '+' : ''}{d.value.toFixed(4)}
              </span>
              {lowCov && (
                <span className="fi-cov-flag" title={`Coverage: ${(cov * 100).toFixed(0)}%`}>*</span>
              )}
            </div>
          </div>
        )
      })}

      {items.length > 15 && (
        <button className="fi-show-toggle" onClick={onToggle}>
          {showAll ? 'Show Top 15' : `Show All ${items.length}`}
        </button>
      )}
    </div>
  )
}

// ── Sortable full-feature table ───────────────────────────────────────────────

function FeatureTable({ roundData, featLabels }) {
  const hasPerm = !!(roundData?.permutation)
  const [sortCol, setSortCol] = useState(hasPerm ? 'perm' : 'corr')
  const [sortAsc, setSortAsc] = useState(false)

  if (!roundData) return null

  const permMap = {}
  const corrMap = {}
  const covMap  = {}

  if (roundData.permutation) {
    roundData.permutation.forEach(d => { permMap[d.feature] = d.value })
  }
  roundData.correlation.forEach(d => { corrMap[d.feature] = d.value })
  roundData.coverage.forEach(d   => { covMap[d.feature]   = d.value })

  const features = Object.keys(featLabels)

  const sorted = [...features].sort((a, b) => {
    let va, vb
    if (sortCol === 'perm') {
      va = permMap[a] !== undefined ? Math.abs(permMap[a]) : -1
      vb = permMap[b] !== undefined ? Math.abs(permMap[b]) : -1
    } else if (sortCol === 'corr') {
      va = corrMap[a] !== undefined ? Math.abs(corrMap[a]) : -Infinity
      vb = corrMap[b] !== undefined ? Math.abs(corrMap[b]) : -Infinity
    } else {
      va = covMap[a] !== undefined ? covMap[a] : -Infinity
      vb = covMap[b] !== undefined ? covMap[b] : -Infinity
    }
    return sortAsc ? va - vb : vb - va
  })

  const handleSort = col => {
    if (sortCol === col) setSortAsc(a => !a)
    else { setSortCol(col); setSortAsc(false) }
  }

  const permTop = roundData.permutation
    ? [...roundData.permutation].sort((a, b) => b.value - a.value).slice(0, 10).map(d => d.feature)
    : []

  function covClass(v) {
    if (v === undefined) return ''
    if (v > 0.90) return 'cov-hi'
    if (v >= 0.80) return 'cov-md'
    return 'cov-lo'
  }

  return (
    <div className="fi-table-section">
      <div className="fi-table-title">Full Feature Rankings</div>
      <div style={{ overflowX: 'auto' }}>
        <table className="fi-table">
          <thead>
            <tr>
              <th style={{ width: 32 }}>#</th>
              <th>Feature</th>
              <th
                className={`sortable${sortCol === 'perm' ? ' sorted' + (sortAsc ? ' asc' : '') : ''}`}
                onClick={() => handleSort('perm')}
                title="Sort by permutation importance"
              >Permutation</th>
              <th
                className={`sortable${sortCol === 'corr' ? ' sorted' + (sortAsc ? ' asc' : '') : ''}`}
                onClick={() => handleSort('corr')}
                title="Sort by correlation"
              >Correlation</th>
              <th
                className={`sortable${sortCol === 'cov' ? ' sorted' + (sortAsc ? ' asc' : '') : ''}`}
                onClick={() => handleSort('cov')}
                title="Sort by coverage"
              >Coverage</th>
            </tr>
          </thead>
          <tbody>
            {sorted.map((feat, idx) => {
              const pv  = permMap[feat]
              const cv  = corrMap[feat]
              const cov = covMap[feat]
              return (
                <tr key={feat}>
                  <td className="rank">{idx + 1}</td>
                  <td className="feat">{featLabels[feat]}</td>
                  <td className={`mono${permTop.includes(feat) ? ' top10' : ''}${pv !== undefined && pv < 0 ? ' neg' : ''}`}>
                    {pv !== undefined
                      ? `${pv >= 0 ? '+' : ''}${pv.toFixed(4)}`
                      : <span style={{ opacity: 0.35 }}>—</span>}
                  </td>
                  <td className="mono">
                    {cv !== undefined
                      ? `${cv >= 0 ? '+' : ''}${cv.toFixed(3)}`
                      : <span style={{ opacity: 0.35 }}>—</span>}
                  </td>
                  <td className={`mono ${covClass(cov)}`}>
                    {cov !== undefined ? `${(cov * 100).toFixed(0)}%` : '—'}
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
      {roundData.coverage.some(d => d.value < 0.80) && (
        <div className="fi-footnote">
          * Features with &lt;80% coverage have NaN data for early seasons — model handles these
          natively via HistGradientBoosting but importance may be understated.
        </div>
      )}
    </div>
  )
}

// ── Trajectory bump chart ─────────────────────────────────────────────────────

function TrajectoryChart({ data }) {
  // Build rank maps per round
  const rankMaps = {}
  TRAJ_ROUNDS.forEach(rk => {
    rankMaps[rk] = {}
    ;(data.rounds[rk]?.permutation || []).forEach((d, i) => {
      rankMaps[rk][d.feature] = i + 1
    })
  })

  // Top 8 features by overall permutation importance
  const top8 = (data.rounds['overall']?.permutation || []).slice(0, 8)
  if (top8.length === 0) return <div className="fi-no-data">No overall data</div>

  // SVG layout
  const W = 960, H = 340
  const ML = 186, MR = 50, MT = 38, MB = 20
  const cW = W - ML - MR
  const cH = H - MT - MB
  const cols = TRAJ_ROUNDS.length  // 5

  // Determine Y range: show ranks 1–N where N = max rank any top8 feature hits
  const allRanks = top8.flatMap(f =>
    TRAJ_ROUNDS.map(rk => rankMaps[rk][f.feature]).filter(Boolean)
  )
  const maxRank = Math.min(Math.max(...allRanks, 8), 15)

  const xOf  = i    => ML + (i / (cols - 1)) * cW
  const yOf  = rank => MT + ((rank - 1) / (maxRank - 1)) * cH

  // Nudge labels so they don't overlap at the left edge (positioned by R64 rank)
  function nudgeLabels(items) {
    const MIN_GAP = 15
    const placed = items
      .map((f, fi) => {
        const rank = rankMaps[TRAJ_ROUNDS[0]][f.feature]
        return { fi, rank, y: rank ? yOf(rank) : null }
      })
      .filter(d => d.y !== null)
      .sort((a, b) => a.y - b.y)

    for (let i = 1; i < placed.length; i++) {
      if (placed[i].y - placed[i - 1].y < MIN_GAP) {
        placed[i].y = placed[i - 1].y + MIN_GAP
      }
    }

    const result = {}
    placed.forEach(d => { result[d.fi] = d.y })
    return result
  }

  const labelY = nudgeLabels(top8)

  return (
    <div className="fi-trajectory-wrap">
      <div className="fi-trajectory-legend">
        {top8.map((f, fi) => (
          <span key={f.feature} className="fi-legend-item">
            <span className="fi-legend-dot" style={{ background: FEATURE_COLORS[fi] }} />
            {f.label}
          </span>
        ))}
      </div>

      <svg
        viewBox={`0 0 ${W} ${H}`}
        width="100%"
        style={{ display: 'block', overflow: 'visible' }}
        aria-label="Feature importance rank trajectory across tournament rounds"
      >
        {/* Vertical grid lines */}
        {TRAJ_ROUNDS.map((rk, i) => (
          <line key={rk}
            x1={xOf(i)} x2={xOf(i)} y1={MT} y2={MT + cH}
            stroke="rgba(255,255,255,0.06)" strokeWidth={1}
          />
        ))}

        {/* Horizontal rank guide lines */}
        {[1, 3, 5, 8, 10].filter(r => r <= maxRank).map(r => (
          <g key={r}>
            <line
              x1={ML} x2={ML + cW} y1={yOf(r)} y2={yOf(r)}
              stroke="rgba(255,255,255,0.04)" strokeWidth={1} strokeDasharray="3 4"
            />
            <text x={ML - 6} y={yOf(r) + 4} textAnchor="end"
              fill="rgba(255,255,255,0.2)" fontSize={9} fontFamily="monospace">
              #{r}
            </text>
          </g>
        ))}

        {/* Round column headers */}
        {TRAJ_ROUNDS.map((rk, i) => (
          <text key={rk} x={xOf(i)} y={MT - 14} textAnchor="middle"
            fill="#c9a84c" fontSize={11} fontFamily="monospace" letterSpacing={1.5}
            fontWeight="bold">
            {ROUND_LABELS[rk]}
          </text>
        ))}

        {/* Feature lines + dots */}
        {top8.map((f, fi) => {
          const color  = FEATURE_COLORS[fi]
          const points = TRAJ_ROUNDS.map((rk, i) => {
            const rank = rankMaps[rk][f.feature]
            return rank ? { x: xOf(i), y: yOf(rank), rank } : null
          })

          // Build continuous path segments (skip nulls)
          const segments = []
          let current = []
          points.forEach(p => {
            if (p) { current.push(p) }
            else if (current.length) { segments.push(current); current = [] }
          })
          if (current.length) segments.push(current)

          return (
            <g key={f.feature}>
              {segments.map((seg, si) => {
                const d = seg.map((p, pi) => `${pi === 0 ? 'M' : 'L'}${p.x},${p.y}`).join(' ')
                return (
                  <path key={si} d={d} fill="none"
                    stroke={color} strokeWidth={2.5} strokeLinejoin="round" opacity={0.85}
                  />
                )
              })}

              {/* Dots + rank labels */}
              {points.map((p, i) => p && (
                <g key={i}>
                  <circle cx={p.x} cy={p.y} r={5}
                    fill={color} stroke="var(--bg)" strokeWidth={2} />
                  <text x={p.x} y={p.y - 9} textAnchor="middle"
                    fill={color} fontSize={9} fontFamily="monospace" opacity={0.75}>
                    #{p.rank}
                  </text>
                </g>
              ))}

              {/* Left label at R64 position */}
              {labelY[fi] != null && (
                <>
                  {/* connector dot → label */}
                  {rankMaps[TRAJ_ROUNDS[0]][f.feature] && (
                    <line
                      x1={ML - 4} x2={ML - 12}
                      y1={yOf(rankMaps[TRAJ_ROUNDS[0]][f.feature])}
                      y2={labelY[fi]}
                      stroke={color} strokeWidth={1} opacity={0.4}
                    />
                  )}
                  <text x={ML - 14} y={labelY[fi] + 4} textAnchor="end"
                    fill={color} fontSize={11} fontFamily="sans-serif">
                    {f.label.length > 22 ? f.label.slice(0, 21) + '…' : f.label}
                  </text>
                </>
              )}
            </g>
          )
        })}
      </svg>

      <div className="fi-trajectory-note mono">
        Rank = permutation importance position within that round · 1 = most predictive ·
        Top 8 features by overall importance shown · F4 has small sample, ranks less stable
      </div>
    </div>
  )
}

// ── Main viewer ───────────────────────────────────────────────────────────────

const TAB_ORDER = ['overview', 'trajectory', ...ROUND_KEYS]
const TAB_LABELS = {
  overview:   'Overview',
  trajectory: 'Trajectory',
  ...ROUND_LABELS,
}

export default function FeatureImportanceViewer() {
  const [data, setData]         = useState(null)
  const [loading, setLoading]   = useState(true)
  const [error, setError]       = useState(null)
  const [activeTab, setActiveTab] = useState('overview')
  const [showAllPerm, setShowAllPerm] = useState(false)
  const [showAllCorr, setShowAllCorr] = useState(false)

  useEffect(() => {
    fetch('/api/feature-importance')
      .then(r => {
        if (!r.ok) return r.json().then(e => { throw new Error(e.detail || r.statusText) })
        return r.json()
      })
      .then(d => { setData(d); setLoading(false) })
      .catch(e => { setError(e.message); setLoading(false) })
  }, [])

  if (loading) return <div className="state-msg loading">Loading feature importance data…</div>
  if (error)   return <div className="state-msg" style={{ color: 'var(--red-bright)' }}>{error}</div>
  if (!data)   return null

  // Decide which round data to show for bar charts
  const roundKey  = activeTab === 'overview' ? 'overall' : activeTab
  const rd        = data.rounds[roundKey]
  const coverageMap = {}
  rd?.coverage?.forEach(d => { coverageMap[d.feature] = d.value })

  const delta      = rd?.cv_acc != null && rd?.seed_acc != null ? rd.cv_acc - rd.seed_acc : null
  const deltaClass = delta == null ? 'zero' : delta > 0.005 ? 'pos' : delta < -0.005 ? 'neg' : 'zero'

  function switchTab(t) {
    setActiveTab(t)
    setShowAllPerm(false)
    setShowAllCorr(false)
  }

  return (
    <div className="fi-viewer">

      {/* ── Tab bar ── */}
      <div className="fi-round-bar">
        {TAB_ORDER.map(key => (
          <button
            key={key}
            className={`tab-btn fi-round-btn${key === 'trajectory' ? ' fi-traj-btn' : ''}${activeTab === key ? ' active' : ''}`}
            onClick={() => switchTab(key)}
          >
            {TAB_LABELS[key]}
          </button>
        ))}
      </div>

      {/* ── Overview: accuracy strip + overall charts + table ── */}
      {activeTab === 'overview' && (
        <>
          <div className="fi-overview-header">
            <div>
              <div className="fi-stats-title">
                {data.rounds['overall']?.name ?? 'Overall'} &nbsp;·&nbsp;
                {data.rounds['overall']?.n_games ?? data.n_games} games
              </div>
              <div style={{ fontSize: '0.72rem', color: 'var(--cream-dim)', marginTop: 3 }}>
                {data.n_features} features · {data.generated_at}
              </div>
            </div>
            {delta != null && (
              <div className="fi-stats-metrics">
                <div className="fi-metric">
                  <span className="fi-stats-label">Model Accuracy</span>
                  <span className="fi-stats-val">{(rd.cv_acc * 100).toFixed(1)}%</span>
                </div>
                {rd.seed_acc != null && (
                  <div className="fi-metric">
                    <span className="fi-stats-label">Seed Baseline</span>
                    <span className="fi-stats-val">{(rd.seed_acc * 100).toFixed(1)}%</span>
                  </div>
                )}
                <div className="fi-metric">
                  <span className="fi-stats-label">Delta</span>
                  <span className={`fi-stats-val fi-delta ${deltaClass}`}>
                    {delta >= 0 ? '+' : ''}{(delta * 100).toFixed(1)}%
                  </span>
                </div>
              </div>
            )}
          </div>

          <AccuracyStrip data={data} />

          <div className="fi-charts-row">
            <FeatureChart
              title="Permutation Importance · Accuracy drop when feature shuffled"
              items={rd?.permutation}
              colorClass="gold"
              showAll={showAllPerm}
              onToggle={() => setShowAllPerm(v => !v)}
              coverageMap={coverageMap}
            />
            <FeatureChart
              title="Univariate Correlation · With win/loss outcome"
              items={rd?.correlation}
              colorClass="blue"
              showAll={showAllCorr}
              onToggle={() => setShowAllCorr(v => !v)}
              coverageMap={coverageMap}
            />
          </div>

          <FeatureTable roundData={rd} featLabels={data.feature_labels} />
        </>
      )}

      {/* ── Trajectory view ── */}
      {activeTab === 'trajectory' && (
        <div style={{ padding: '12px 0' }}>
          <div className="fi-section-heading">
            How Feature Importance Shifts Across Rounds
          </div>
          <div className="fi-section-sub mono">
            Top 8 features by overall permutation importance · rank = position in that round's importance list
          </div>
          <TrajectoryChart data={data} />
        </div>
      )}

      {/* ── Per-round view (R64–NCG) ── */}
      {ROUND_KEYS.includes(activeTab) && rd && (
        <>
          <div className="fi-stats-header">
            <div>
              <div className="fi-stats-title">
                {rd.name} &nbsp;·&nbsp; {rd.n_games} games
              </div>
              <div style={{ fontSize: '0.72rem', color: 'var(--cream-dim)', marginTop: 3 }}>
                {data.n_features} features · {data.generated_at}
              </div>
            </div>
            {rd.cv_acc != null && (
              <div className="fi-stats-metrics">
                <div className="fi-metric">
                  <span className="fi-stats-label">Model Accuracy</span>
                  <span className="fi-stats-val">{(rd.cv_acc * 100).toFixed(1)}%</span>
                </div>
                {rd.seed_acc != null && (
                  <div className="fi-metric">
                    <span className="fi-stats-label">Seed Baseline</span>
                    <span className="fi-stats-val">{(rd.seed_acc * 100).toFixed(1)}%</span>
                  </div>
                )}
                {delta != null && (
                  <div className="fi-metric">
                    <span className="fi-stats-label">Delta</span>
                    <span className={`fi-stats-val fi-delta ${deltaClass}`}>
                      {delta >= 0 ? '+' : ''}{(delta * 100).toFixed(1)}%
                    </span>
                  </div>
                )}
              </div>
            )}
          </div>

          <div className="fi-charts-row">
            {rd.permutation ? (
              <FeatureChart
                title="Permutation Importance · Accuracy drop when feature shuffled"
                items={rd.permutation}
                colorClass="gold"
                showAll={showAllPerm}
                onToggle={() => setShowAllPerm(v => !v)}
                coverageMap={coverageMap}
              />
            ) : (
              <div className="fi-chart-card" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', flexDirection: 'column', gap: 6, padding: '28px 20px', opacity: 0.5 }}>
                <div className="fi-chart-title">Permutation Importance</div>
                <div className="mono" style={{ fontSize: '0.65rem', color: 'var(--cream-dim)', textAlign: 'center' }}>
                  Not computed for {rd.name}<br />
                  Only {rd.n_games} games — sample too small for reliable permutation testing
                </div>
              </div>
            )}
            <FeatureChart
              title="Univariate Correlation · With win/loss outcome"
              items={rd.correlation}
              colorClass="blue"
              showAll={showAllCorr}
              onToggle={() => setShowAllCorr(v => !v)}
              coverageMap={coverageMap}
            />
          </div>

          <FeatureTable roundData={rd} featLabels={data.feature_labels} />
        </>
      )}

      {/* ── Empty state for NCG (tiny sample) ── */}
      {ROUND_KEYS.includes(activeTab) && !rd && (
        <div className="state-msg">No data for {TAB_LABELS[activeTab]}</div>
      )}

    </div>
  )
}

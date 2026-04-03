import { useRef } from 'react'
import MatchCard from './MatchCard'

export default function MatchCarousel({ matches = [], queryStats = {} }) {
  const scrollRef = useRef(null)

  const scrollBy = (dir) => {
    const el = scrollRef.current
    if (!el) return
    el.scrollBy({ left: dir * 400, behavior: 'smooth' })
  }

  return (
    <div className="carousel-wrapper">
      <div className="carousel-nav">
        <button className="carousel-btn" onClick={() => scrollBy(-1)} title="Previous">‹</button>
        <button className="carousel-btn" onClick={() => scrollBy(1)} title="Next">›</button>
        <span className="mono" style={{ fontSize: '0.7rem', color: 'var(--cream-dim)', alignSelf: 'center', marginLeft: 8 }}>
          {matches.length} matches · scroll or use arrows
        </span>
      </div>
      <div className="carousel" ref={scrollRef}>
        {matches.map((m, i) => (
          <MatchCard
            key={`${m.team}-${m.year}`}
            match={m}
            rank={i + 1}
            queryStats={queryStats}
          />
        ))}
      </div>
    </div>
  )
}

"""
Build the March Madness Model Obsidian vault graph.
Generates all markdown concept notes, team notes, and conference notes.
Run: python build_obsidian_vault.py
"""

import os
import pandas as pd
from pathlib import Path

VAULT = Path(r"C:\Users\evan\OneDrive\CODE\Bracket_Model_26\March Madness Model")

def write(path: Path, content: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    print(f"  wrote {path.relative_to(VAULT)}")

# ─────────────────────────────────────────────
# 1. MASTER HUB
# ─────────────────────────────────────────────
write(VAULT / "00 - Data Overview.md", """\
---
tags: [hub]
---

# March Madness Model — Data Overview

Central reference for every data type in the model.
Covers **371 D1 teams**, seasons **2002–2025** (no 2020).

## Data Divisions
- [[Stats Hub]] — all statistical features by source
- [[Teams Hub]] — all teams with D1 and tournament history
- [[Conferences Hub]] — all conferences and members

## Source Files
| File | Pattern | Granularity |
|------|---------|-------------|
| conferences.parquet | data/conferences.parquet | team × season |
| summary_pt.csv | data/{year}/summary{YY}_pt.csv | team × season |
| scouting.parquet | data/{year}/{team}_scouting.parquet | team × season |
| players.parquet | data/{year}/{team}_players.parquet | player × season |
| gameplan.parquet | data/{year}/{team}_gameplan.parquet | per game |
| bracket.csv | data/{year}/bracket.csv | per matchup |
""")

# ─────────────────────────────────────────────
# 2. STATS HUB
# ─────────────────────────────────────────────
write(VAULT / "Stats" / "Stats Hub.md", """\
---
tags: [hub, stats]
---

# Stats Hub

All statistical data categories available in the model.

## Categories
- [[KenPom Overview]] — tempo & efficiency ratings (2001–2025)
- [[Four Factors Overview]] — shooting / TO / rebound / FT (2024–2025)
- [[Scouting Overview]] — advanced scouting metrics (2024–2025)
- [[Player Stats Overview]] — individual player stats aggregated (2024–2025)
- [[Game Log Overview]] — per-game efficiency & shot data (2024–2025)
- [[Season Record Overview]] — W/L records & rating systems (2002–2025)
""")

# ─────────────────────────────────────────────
# 3. KENPOM NOTES
# ─────────────────────────────────────────────
write(VAULT / "Stats" / "KenPom" / "KenPom Overview.md", """\
---
tags: [stats, kenpom]
source: summary{YY}_pt.csv
seasons: 2001-2025
---

# KenPom Overview

Season-level efficiency and tempo ratings from KenPom.
One row per team per season.

## Sub-Categories
- [[Tempo]]
- [[Offensive Efficiency]]
- [[Defensive Efficiency]]
- [[Adjusted Efficiency Margin]]

## Identifier Fields
- `Season` — year
- `TeamName` — team name
- `seed` — NCAA tournament seed (NaN if not in tourney)

## Back to [[Stats Hub]]
""")

write(VAULT / "Stats" / "KenPom" / "Tempo.md", """\
---
tags: [stats, kenpom, feature]
source: summary{YY}_pt.csv
---

# Tempo

Pace of play — possessions per 40 minutes.

| Field | Description |
|-------|-------------|
| `Tempo` | Raw possessions per 40 min |
| `RankTempo` | National rank (raw tempo) |
| `AdjTempo` | Schedule-adjusted possessions per 40 min |
| `RankAdjTempo` | National rank (adjusted tempo) |

## Back to [[KenPom Overview]]
""")

write(VAULT / "Stats" / "KenPom" / "Offensive Efficiency.md", """\
---
tags: [stats, kenpom, feature]
source: summary{YY}_pt.csv
---

# Offensive Efficiency

Points scored per 100 possessions.

| Field | Description |
|-------|-------------|
| `OE` | Raw offensive efficiency |
| `RankOE` | National rank (raw OE) |
| `AdjOE` | Schedule-adjusted offensive efficiency |
| `RankAdjOE` | National rank (adjusted OE) |

## Back to [[KenPom Overview]]
""")

write(VAULT / "Stats" / "KenPom" / "Defensive Efficiency.md", """\
---
tags: [stats, kenpom, feature]
source: summary{YY}_pt.csv
---

# Defensive Efficiency

Points allowed per 100 possessions.

| Field | Description |
|-------|-------------|
| `DE` | Raw defensive efficiency |
| `RankDE` | National rank (raw DE) |
| `AdjDE` | Schedule-adjusted defensive efficiency |
| `RankAdjDE` | National rank (adjusted DE) |

## Back to [[KenPom Overview]]
""")

write(VAULT / "Stats" / "KenPom" / "Adjusted Efficiency Margin.md", """\
---
tags: [stats, kenpom, feature]
source: summary{YY}_pt.csv
---

# Adjusted Efficiency Margin

AdjOE − AdjDE. Overall team strength metric.

| Field | Description |
|-------|-------------|
| `AdjEM` | Adjusted efficiency margin |
| `RankAdjEM` | National rank |
| `seed` | NCAA tournament seed (NaN if not in tourney) |

## Back to [[KenPom Overview]]
""")

# ─────────────────────────────────────────────
# 4. FOUR FACTORS NOTES
# ─────────────────────────────────────────────
write(VAULT / "Stats" / "Four Factors" / "Four Factors Overview.md", """\
---
tags: [stats, four-factors]
source: "{team}_scouting.parquet"
seasons: 2024-2025
---

# Four Factors Overview

Dean Oliver's Four Factors of basketball success — measured for both
offensive (off) and defensive (def) sides.

## Sub-Categories
- [[Effective FG Pct]]
- [[Turnover Rate]]
- [[Offensive Rebound Pct]]
- [[Free Throw Rate]]

## Note
These fields also appear inside [[Scouting Overview]].
All four factors have paired `_rank` fields (national rank).

## Back to [[Stats Hub]]
""")

write(VAULT / "Stats" / "Four Factors" / "Effective FG Pct.md", """\
---
tags: [stats, four-factors, feature]
source: "{team}_scouting.parquet"
---

# Effective FG%

(FGM + 0.5 × 3PM) / FGA — weights 3-pointers by 1.5x.

| Field | Description |
|-------|-------------|
| `efg_pct_off` | Team's own eFG% |
| `efg_pct_off_rank` | National rank |
| `efg_pct_def` | Opponent eFG% allowed |
| `efg_pct_def_rank` | National rank |

## Back to [[Four Factors Overview]]
""")

write(VAULT / "Stats" / "Four Factors" / "Turnover Rate.md", """\
---
tags: [stats, four-factors, feature]
source: "{team}_scouting.parquet"
---

# Turnover Rate

Turnovers per 100 possessions.

| Field | Description |
|-------|-------------|
| `to_pct_off` | Team's own turnover rate |
| `to_pct_off_rank` | National rank |
| `to_pct_def` | Opponent turnover rate forced |
| `to_pct_def_rank` | National rank |

## Back to [[Four Factors Overview]]
""")

write(VAULT / "Stats" / "Four Factors" / "Offensive Rebound Pct.md", """\
---
tags: [stats, four-factors, feature]
source: "{team}_scouting.parquet"
---

# Offensive Rebound %

% of available offensive rebounds captured.

| Field | Description |
|-------|-------------|
| `or_pct_off` | Team's offensive rebound % |
| `or_pct_off_rank` | National rank |
| `or_pct_def` | Opponent offensive rebound % allowed |
| `or_pct_def_rank` | National rank |

## Back to [[Four Factors Overview]]
""")

write(VAULT / "Stats" / "Four Factors" / "Free Throw Rate.md", """\
---
tags: [stats, four-factors, feature]
source: "{team}_scouting.parquet"
---

# Free Throw Rate

FTA / FGA — ability to get to the line.

| Field | Description |
|-------|-------------|
| `ftr_off` | Team's FTA/FGA ratio |
| `ftr_off_rank` | National rank |
| `ftr_def` | Opponent FTA/FGA ratio allowed |
| `ftr_def_rank` | National rank |

## Back to [[Four Factors Overview]]
""")

# ─────────────────────────────────────────────
# 5. SCOUTING ADVANCED NOTES
# ─────────────────────────────────────────────
write(VAULT / "Stats" / "Scouting Advanced" / "Scouting Overview.md", """\
---
tags: [stats, scouting]
source: "{team}_scouting.parquet"
seasons: 2024-2025
---

# Scouting Overview

Advanced scouting metrics. One row per team per season.
Also contains KenPom efficiency mirrors (adj_oe, adj_de, adj_tempo).

## Sub-Categories
- [[Four Factors Overview]] (efg, TO, OR, FTR)
- [[Shooting Advanced]]
- [[Playmaking]]
- [[Defense Advanced]]
- [[Point Distribution]]
- [[Strength of Schedule]]
- [[Team Composition]]

## Identifier Fields
- `team`, `season`

## Back to [[Stats Hub]]
""")

write(VAULT / "Stats" / "Scouting Advanced" / "Shooting Advanced.md", """\
---
tags: [stats, scouting, feature]
source: "{team}_scouting.parquet"
---

# Shooting Advanced

Detailed shot-type breakdowns and shot distance.

| Field | Description |
|-------|-------------|
| `fg3_pct_off` / `_rank` | 3-point % (offense) |
| `fg3_pct_def` / `_rank` | 3-point % allowed |
| `fg2_pct_off` / `_rank` | 2-point % (offense) |
| `fg2_pct_def` / `_rank` | 2-point % allowed |
| `ft_pct_off` / `_rank` | Free throw % (offense) |
| `ft_pct_def` / `_rank` | Free throw % allowed |
| `fg3a_rate_off` / `_rank` | 3PA / total FGA (offense) |
| `fg3a_rate_def` / `_rank` | Opponent 3PA rate allowed |
| `shot_dist_off` / `_rank` | Avg shot distance (offense, feet) |
| `shot_dist_def` / `_rank` | Avg shot distance allowed |

## Back to [[Scouting Overview]]
""")

write(VAULT / "Stats" / "Scouting Advanced" / "Playmaking.md", """\
---
tags: [stats, scouting, feature]
source: "{team}_scouting.parquet"
---

# Playmaking

Assist-based and ball-movement metrics.

| Field | Description |
|-------|-------------|
| `ast_rate_off` / `_rank` | Assist rate (% of FGM assisted, offense) |
| `ast_rate_def` / `_rank` | Assist rate allowed |
| `apl_off` / `_rank` | Assists per loss (offense) |
| `apl_def` / `_rank` | Assists per loss (defense) |
| `nst_rate_off` / `_rank` | Non-steal turnover rate (offense) |
| `nst_rate_def` / `_rank` | Non-steal TO rate allowed |

## Back to [[Scouting Overview]]
""")

write(VAULT / "Stats" / "Scouting Advanced" / "Defense Advanced.md", """\
---
tags: [stats, scouting, feature]
source: "{team}_scouting.parquet"
---

# Defense Advanced

Block rate, steal rate, and fouling behavior.

| Field | Description |
|-------|-------------|
| `blk_pct_off` / `_rank` | Block % against team (shots blocked by opponents) |
| `blk_pct_def` / `_rank` | Block % by team (shots blocked on defense) |
| `stl_rate_off` / `_rank` | Steal rate against (steals allowed per 100 poss) |
| `stl_rate_def` / `_rank` | Steal rate forced |
| `foul2_pct` / `_rank` | Double foul percentage |

## Back to [[Scouting Overview]]
""")

write(VAULT / "Stats" / "Scouting Advanced" / "Point Distribution.md", """\
---
tags: [stats, scouting, feature]
source: "{team}_scouting.parquet"
---

# Point Distribution

Share of points scored from each shot type.

| Field | Description |
|-------|-------------|
| `pd3_off` / `_rank` | % of team's pts from 3-pointers |
| `pd3_def` / `_rank` | % of opponent's pts from 3s |
| `pd2_off` / `_rank` | % of team's pts from 2-pointers |
| `pd2_def` / `_rank` | % of opponent's pts from 2s |
| `pd1_off` / `_rank` | % of team's pts from free throws |
| `pd1_def` / `_rank` | % of opponent's pts from FTs |

## Back to [[Scouting Overview]]
""")

write(VAULT / "Stats" / "Scouting Advanced" / "Strength of Schedule.md", """\
---
tags: [stats, scouting, feature]
source: "{team}_scouting.parquet"
---

# Strength of Schedule

Scouting-based SOS metrics (separate from SRS-based SOS in conferences.parquet).

| Field | Description |
|-------|-------------|
| `sos_off` / `_rank` | Offensive strength of schedule |
| `sos_def` / `_rank` | Defensive strength of schedule |
| `sos_overall` / `_rank` | Overall SOS |
| `sos_nc` / `_rank` | Non-conference SOS |

## Back to [[Scouting Overview]]
""")

write(VAULT / "Stats" / "Scouting Advanced" / "Team Composition.md", """\
---
tags: [stats, scouting, feature]
source: "{team}_scouting.parquet"
---

# Team Composition

Roster depth, experience, continuity, and size.

| Field | Description |
|-------|-------------|
| `bench_min` / `_rank` | % of team minutes played by bench |
| `d1_exp` / `_rank` | Avg D1 experience of all players (years) |
| `min_cont` / `_rank` | Returning minute continuity % |
| `avg_height` / `_rank` | Average team height |

## Back to [[Scouting Overview]]
""")

# ─────────────────────────────────────────────
# 6. PLAYER STATS NOTES
# ─────────────────────────────────────────────
write(VAULT / "Stats" / "Player Stats" / "Player Stats Overview.md", """\
---
tags: [stats, players]
source: "{team}_players.parquet"
seasons: 2024-2025
---

# Player Stats Overview

Individual player stats. One row per player per season.
**Identity fields (not model features):** name, jersey
**Metadata:** team, season, height, weight, year (Fr/So/Jr/Sr), games, starts

## Sub-Categories
- [[Player Usage and Role]]
- [[Player Per-Possession]]
- [[Player Shooting]]
- [[Player Defense]]

## Back to [[Stats Hub]]
""")

write(VAULT / "Stats" / "Player Stats" / "Player Usage and Role.md", """\
---
tags: [stats, players, feature]
source: "{team}_players.parquet"
---

# Player Usage and Role

How much a player is used and in what capacity.

| Field | Description |
|-------|-------------|
| `starter` | Boolean — is starter |
| `pct_min` | % of team minutes played |
| `pct_poss` | % of team possessions used |
| `pct_shots` | % of team shots taken |
| `games` | Games played |
| `starts` | Games started |

## Back to [[Player Stats Overview]]
""")

write(VAULT / "Stats" / "Player Stats" / "Player Per-Possession.md", """\
---
tags: [stats, players, feature]
source: "{team}_players.parquet"
---

# Player Per-Possession Stats

Efficiency and activity per 100 possessions or per 40 minutes.

| Field | Description |
|-------|-------------|
| `ortg` | Offensive rating (pts per 100 poss) |
| `or_pct` | Offensive rebound % |
| `dr_pct` | Defensive rebound % |
| `a_rate` | Assist rate |
| `to_rate` | Turnover rate |
| `fc_per40` | Fouls committed per 40 min |
| `fd_per40` | Fouls drawn per 40 min |

## Back to [[Player Stats Overview]]
""")

write(VAULT / "Stats" / "Player Stats" / "Player Shooting.md", """\
---
tags: [stats, players, feature]
source: "{team}_players.parquet"
---

# Player Shooting

Shot efficiency and volume by type.

| Field | Description |
|-------|-------------|
| `efg_pct` | Effective FG% |
| `ts_pct` | True shooting % |
| `ft_rate` | FTA / FGA ratio |
| `ftm` | Free throw makes |
| `fta` | Free throw attempts |
| `ft_pct` | Free throw % |
| `fg2m` | 2-point makes |
| `fg2a` | 2-point attempts |
| `fg2_pct` | 2-point % |
| `fg3m` | 3-point makes |
| `fg3a` | 3-point attempts |
| `fg3_pct` | 3-point % |

## Back to [[Player Stats Overview]]
""")

write(VAULT / "Stats" / "Player Stats" / "Player Defense.md", """\
---
tags: [stats, players, feature]
source: "{team}_players.parquet"
---

# Player Defense

Defensive activity rates.

| Field | Description |
|-------|-------------|
| `blk_pct` | Block % |
| `stl_pct` | Steal % |
| `dr_pct` | Defensive rebound % |

## Back to [[Player Stats Overview]]
""")

# ─────────────────────────────────────────────
# 7. GAME LOG NOTES
# ─────────────────────────────────────────────
write(VAULT / "Stats" / "Game Log" / "Game Log Overview.md", """\
---
tags: [stats, game-log]
source: "{team}_gameplan.parquet"
seasons: 2024-2025
---

# Game Log Overview

Per-game data. One row per game played by the team.

## Game Metadata Fields
- `team`, `year`, `date`
- `opponent` — opponent team name
- `opp_kp_rank` — opponent's KenPom rank that season
- `outcome` — W or L
- `team_score`, `opp_score`
- `location` — H (home), A (away), N (neutral)

## Sub-Categories
- [[Per-Game Efficiency]]
- [[Per-Game Four Factors]]
- [[Shot Volume]]

## Back to [[Stats Hub]]
""")

write(VAULT / "Stats" / "Game Log" / "Per-Game Efficiency.md", """\
---
tags: [stats, game-log, feature]
source: "{team}_gameplan.parquet"
---

# Per-Game Efficiency

Pace and point efficiency for a single game.

| Field | Description |
|-------|-------------|
| `pace` | Game possessions |
| `off_eff` | Offensive efficiency (pts/100 poss) |
| `off_eff_rank` | National rank for that game |
| `def_eff` | Defensive efficiency (pts allowed/100 poss) |
| `def_eff_rank` | National rank for that game |

## Back to [[Game Log Overview]]
""")

write(VAULT / "Stats" / "Game Log" / "Per-Game Four Factors.md", """\
---
tags: [stats, game-log, feature]
source: "{team}_gameplan.parquet"
---

# Per-Game Four Factors

Single-game four factors for both sides.

| Field | Description |
|-------|-------------|
| `off_efg` | Offensive eFG% |
| `off_to_pct` | Offensive turnover % |
| `off_or_pct` | Offensive rebound % |
| `off_ftr` | Offensive free throw rate |
| `def_efg` | Defensive eFG% allowed |
| `def_to_pct` | Defensive turnover % forced |
| `def_or_pct` | Defensive OR% allowed |
| `def_ftr` | Defensive FT rate allowed |

## Back to [[Game Log Overview]]
""")

write(VAULT / "Stats" / "Game Log" / "Shot Volume.md", """\
---
tags: [stats, game-log, feature]
source: "{team}_gameplan.parquet"
---

# Shot Volume

Per-game shot counts and percentages by type.

| Field | Description |
|-------|-------------|
| `off_2p_made`, `off_2p_att`, `off_2p_pct` | 2-point offense |
| `off_3p_made`, `off_3p_att`, `off_3p_pct` | 3-point offense |
| `off_3pa_rate` | 3PA / total FGA (offense) |
| `def_2p_made`, `def_2p_att`, `def_2p_pct` | 2-point defense |
| `def_3p_made`, `def_3p_att`, `def_3p_pct` | 3-point defense |
| `def_3pa_rate` | Opponent 3PA rate allowed |

## Back to [[Game Log Overview]]
""")

# ─────────────────────────────────────────────
# 8. SEASON RECORD NOTES
# ─────────────────────────────────────────────
write(VAULT / "Stats" / "Season Record" / "Season Record Overview.md", """\
---
tags: [stats, season-record]
source: conferences.parquet
seasons: 2002-2025
---

# Season Record Overview

Season-level W/L records, scoring, and rating systems.
One row per team per season. Source: conferences.parquet.

## Sub-Categories
- [[Win-Loss Record]]
- [[Scoring]]
- [[Rating Systems]]

## Identifier Fields
- `team`, `season`, `conf`, `conf_abbrev`

## Back to [[Stats Hub]] | [[Conferences Hub]]
""")

write(VAULT / "Stats" / "Season Record" / "Win-Loss Record.md", """\
---
tags: [stats, season-record, feature]
source: conferences.parquet
---

# Win-Loss Record

Overall and conference record.

| Field | Description |
|-------|-------------|
| `w` | Total wins |
| `l` | Total losses |
| `wl_pct` | Overall win % |
| `conf_w` | Conference wins |
| `conf_l` | Conference losses |
| `conf_wl_pct` | Conference win % |

## Back to [[Season Record Overview]]
""")

write(VAULT / "Stats" / "Season Record" / "Scoring.md", """\
---
tags: [stats, season-record, feature]
source: conferences.parquet
---

# Scoring

Points per game totals.

| Field | Description |
|-------|-------------|
| `pts_pg` | Team points per game |
| `opp_pts_pg` | Opponent points per game (allowed) |

## Back to [[Season Record Overview]]
""")

write(VAULT / "Stats" / "Season Record" / "Rating Systems.md", """\
---
tags: [stats, season-record, feature]
source: conferences.parquet
---

# Rating Systems

Simple rating metrics derived from schedule and margin.

| Field | Description |
|-------|-------------|
| `srs` | Simple Rating System (avg margin + SOS) |
| `sos` | Strength of schedule (SRS-based) |
| `ncaa_tourney` | Boolean — did team make NCAA tournament |

## Back to [[Season Record Overview]]
""")

# ─────────────────────────────────────────────
# 9. TEAMS
# ─────────────────────────────────────────────
print("\nBuilding team notes from conferences.parquet...")
conf_df = pd.read_parquet(
    r"C:\Users\evan\OneDrive\CODE\Bracket_Model_26\data\conferences.parquet"
)

all_years = conf_df.groupby("team")["season"].apply(sorted).reset_index()
all_years.columns = ["team", "d1_years"]

tourney = conf_df[conf_df["ncaa_tourney"] == True].groupby("team")["season"].apply(sorted).reset_index()
tourney.columns = ["team", "tourney_years"]

latest_conf = (
    conf_df.sort_values("season")
    .groupby("team")
    .last()[["conf", "conf_abbrev"]]
    .reset_index()
)

teams_df = all_years.merge(tourney, on="team", how="left").merge(latest_conf, on="team")
teams_df["tourney_years"] = teams_df["tourney_years"].apply(
    lambda x: x if isinstance(x, list) else []
)

# Build teams hub
team_links = "\n".join(f"- [[{row.team}]]" for _, row in teams_df.iterrows())
write(VAULT / "Teams" / "Teams Hub.md", f"""\
---
tags: [hub, teams]
---

# Teams Hub

All 371 D1 teams represented in the dataset (seasons 2002–2025).

{team_links}
""")

# Individual team notes
for _, row in teams_df.iterrows():
    safe_name = row["team"]
    d1_str = ", ".join(str(y) for y in row["d1_years"])
    t_str = ", ".join(str(y) for y in row["tourney_years"]) if row["tourney_years"] else "None"
    conf_link = row["conf"] if row["conf"] else "Unknown"
    content = f"""\
---
tags: [team]
conference: {row['conf']}
conf_abbrev: {row['conf_abbrev']}
---

# {safe_name}

## Conference
[[{conf_link}]] ({row['conf_abbrev']})

## D1 Seasons in Dataset
{d1_str}

## NCAA Tournament Appearances
{t_str}

## Back to [[Teams Hub]]
"""
    write(VAULT / "Teams" / f"{safe_name}.md", content)

# ─────────────────────────────────────────────
# 10. CONFERENCES
# ─────────────────────────────────────────────
print("\nBuilding conference notes...")

# Canonicalize: strip division suffixes like (East), (West), etc.
import re
def canon_conf(abbrev):
    return re.sub(r'\(.*\)', '', abbrev).strip()

conf_df["conf_base"] = conf_df["conf_abbrev"].apply(canon_conf)

# Group by base conference
conf_groups = {}
for _, row in conf_df.iterrows():
    base = row["conf_base"]
    if base not in conf_groups:
        conf_groups[base] = {"full_name": row["conf"], "teams": set(), "seasons": set()}
    conf_groups[base]["teams"].add(row["team"])
    conf_groups[base]["seasons"].add(row["season"])

conf_hub_links = []
for abbrev, data in sorted(conf_groups.items()):
    if not abbrev:
        continue
    teams_sorted = sorted(data["teams"])
    seasons_sorted = sorted(data["seasons"])
    team_links_c = "\n".join(f"- [[{t}]]" for t in teams_sorted)
    seasons_str = f"{min(seasons_sorted)}–{max(seasons_sorted)}"
    conf_hub_links.append(f"- [[{abbrev}]]")
    write(VAULT / "Conferences" / f"{abbrev}.md", f"""\
---
tags: [conference]
---

# {abbrev} — {data['full_name']}

**Seasons in dataset:** {seasons_str}
**Teams represented:** {len(teams_sorted)}

## Member Teams
{team_links}

## Back to [[Conferences Hub]]
""".replace(team_links, team_links_c))

write(VAULT / "Conferences" / "Conferences Hub.md", f"""\
---
tags: [hub, conferences]
---

# Conferences Hub

All conferences represented in the dataset (2002–2025).

{chr(10).join(conf_hub_links)}

## Back to [[00 - Data Overview]]
""")

print("\nDone! Vault built successfully.")
print(f"Location: {VAULT}")

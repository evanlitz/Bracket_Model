# Obsidian Vault Build Plan — March Madness Model

## Vault Location
`C:\Users\evan\OneDrive\CODE\Bracket_Model_26\March Madness Model`

## Purpose
A permanent reference graph of every data type, field, and feature available
in the March Madness Model dataset. Covers 371 D1 teams, seasons 2002–2025
(no 2020). Designed so any future session can open this vault and immediately
understand what data exists and how it connects.

---

## Folder Structure

```
March Madness Model/
├── 00 - Data Overview.md           ← master hub, links everything
├── Stats/
│   ├── Stats Hub.md
│   ├── KenPom/
│   │   ├── KenPom Overview.md
│   │   ├── Tempo.md
│   │   ├── Offensive Efficiency.md
│   │   ├── Defensive Efficiency.md
│   │   └── Adjusted Efficiency Margin.md
│   ├── Four Factors/
│   │   ├── Four Factors Overview.md
│   │   ├── Effective FG Pct.md
│   │   ├── Turnover Rate.md
│   │   ├── Offensive Rebound Pct.md
│   │   └── Free Throw Rate.md
│   ├── Scouting Advanced/
│   │   ├── Scouting Overview.md
│   │   ├── Shooting Advanced.md
│   │   ├── Playmaking.md
│   │   ├── Defense Advanced.md
│   │   ├── Point Distribution.md
│   │   ├── Strength of Schedule.md
│   │   └── Team Composition.md
│   ├── Player Stats/
│   │   ├── Player Stats Overview.md
│   │   ├── Player Shooting.md
│   │   ├── Player Per-Possession.md
│   │   ├── Player Defense.md
│   │   └── Player Usage and Role.md
│   ├── Game Log/
│   │   ├── Game Log Overview.md
│   │   ├── Per-Game Efficiency.md
│   │   ├── Per-Game Four Factors.md
│   │   └── Shot Volume.md
│   └── Season Record/
│       ├── Season Record Overview.md
│       ├── Win-Loss Record.md
│       ├── Scoring.md
│       └── Rating Systems.md
├── Teams/
│   ├── Teams Hub.md
│   └── [371 individual team .md files — see Teams section]
└── Conferences/
    ├── Conferences Hub.md
    └── [individual conference .md files — see Conferences section]
```

---

## Note Content Specs

### 00 - Data Overview.md (Master Hub)
Links to: [[Stats Hub]], [[Teams Hub]], [[Conferences Hub]]
Tags: `#hub`
- Brief description of data coverage (2002–2025, 371 teams)
- Source files listed: conferences.parquet, summary{YY}_pt.csv, {team}_scouting.parquet, {team}_players.parquet, {team}_gameplan.parquet, bracket.csv
- Data coverage years noted

---

## STATS SECTION

### Stats Hub.md
Links to all 6 stat categories:
- [[KenPom Overview]]
- [[Four Factors Overview]]
- [[Scouting Overview]]
- [[Player Stats Overview]]
- [[Game Log Overview]]
- [[Season Record Overview]]

---

### KenPom/ — Source: `data/{year}/summary{YY}_pt.csv`
Seasons covered: 2001–2025 (no 2020)

**KenPom Overview.md**
Links to: [[Tempo]], [[Offensive Efficiency]], [[Defensive Efficiency]], [[Adjusted Efficiency Margin]], [[Stats Hub]]
Key fields: Season, TeamName, seed

**Tempo.md**
- `Tempo` — raw possessions per 40 min
- `AdjTempo` — adjusted possessions per 40 min
- `RankTempo` — national rank raw
- `RankAdjTempo` — national rank adjusted

**Offensive Efficiency.md**
- `OE` — raw offensive efficiency (pts per 100 poss)
- `AdjOE` — adjusted offensive efficiency
- `RankOE`, `RankAdjOE`

**Defensive Efficiency.md**
- `DE` — raw defensive efficiency (pts allowed per 100 poss)
- `AdjDE` — adjusted defensive efficiency
- `RankDE`, `RankAdjDE`

**Adjusted Efficiency Margin.md**
- `AdjEM` — AdjOE minus AdjDE (overall strength)
- `RankAdjEM`
- `seed` — NCAA tournament seed (NaN if not in tournament)

---

### Four Factors/ — Source: `data/{year}/{team}_scouting.parquet`
Seasons covered: 2002–2025 (all D1 teams)

**Four Factors Overview.md**
Links to: [[Effective FG Pct]], [[Turnover Rate]], [[Offensive Rebound Pct]], [[Free Throw Rate]], [[Scouting Overview]]
Note: All four factors exist for both offensive (off) and defensive (def) sides.

**Effective FG Pct.md**
- `efg_pct_off` — team's own eFG%
- `efg_pct_off_rank`
- `efg_pct_def` — opponent's eFG% allowed
- `efg_pct_def_rank`

**Turnover Rate.md**
- `to_pct_off` — team's turnover rate
- `to_pct_off_rank`
- `to_pct_def` — opponent turnover rate forced
- `to_pct_def_rank`

**Offensive Rebound Pct.md**
- `or_pct_off` — team's offensive rebound %
- `or_pct_off_rank`
- `or_pct_def` — opponent's offensive rebound % allowed
- `or_pct_def_rank`

**Free Throw Rate.md**
- `ftr_off` — FTA/FGA ratio (offense)
- `ftr_off_rank`
- `ftr_def` — opponent FTA/FGA ratio allowed
- `ftr_def_rank`

---

### Scouting Advanced/ — Source: `data/{year}/{team}_scouting.parquet`

**Scouting Overview.md**
Links to: [[Four Factors Overview]], [[Shooting Advanced]], [[Playmaking]], [[Defense Advanced]], [[Point Distribution]], [[Strength of Schedule]], [[Team Composition]]
Fields also includes: team, season, adj_oe, adj_de, adj_tempo (mirrors KenPom)

**Shooting Advanced.md**
- `fg3_pct_off` / `fg3_pct_off_rank` — 3-point % (offense)
- `fg3_pct_def` / `fg3_pct_def_rank` — 3-point % allowed
- `fg2_pct_off` / `fg2_pct_off_rank` — 2-point % (offense)
- `fg2_pct_def` / `fg2_pct_def_rank` — 2-point % allowed
- `ft_pct_off` / `ft_pct_off_rank` — FT% (offense)
- `ft_pct_def` / `ft_pct_def_rank` — FT% allowed
- `fg3a_rate_off` / `fg3a_rate_off_rank` — 3PA rate (offense)
- `fg3a_rate_def` / `fg3a_rate_def_rank` — 3PA rate allowed
- `shot_dist_off` / `shot_dist_off_rank` — avg shot distance (offense)
- `shot_dist_def` / `shot_dist_def_rank` — avg shot distance allowed

**Playmaking.md**
- `ast_rate_off` / `ast_rate_off_rank` — assist rate (offense)
- `ast_rate_def` / `ast_rate_def_rank` — assist rate allowed
- `apl_off` / `apl_off_rank` — assists per loss (offense)
- `apl_def` / `apl_def_rank` — assists per loss (defense)
- `nst_rate_off` / `nst_rate_off_rank` — non-steal turnover rate (offense)
- `nst_rate_def` / `nst_rate_def_rank` — non-steal TO rate allowed

**Defense Advanced.md**
- `blk_pct_off` / `blk_pct_off_rank` — block % (offense, i.e., blocked by opponents)
- `blk_pct_def` / `blk_pct_def_rank` — block % (defense, i.e., blocks made)
- `stl_rate_off` / `stl_rate_off_rank` — steal rate allowed against
- `stl_rate_def` / `stl_rate_def_rank` — steal rate forced
- `foul2_pct` / `foul2_pct_rank` — double foul %

**Point Distribution.md**
- `pd3_off` / `pd3_off_rank` — % points from 3-pointers (offense)
- `pd3_def` / `pd3_def_rank` — % of opponent pts from 3s
- `pd2_off` / `pd2_off_rank` — % points from 2-pointers (offense)
- `pd2_def` / `pd2_def_rank` — % of opponent pts from 2s
- `pd1_off` / `pd1_off_rank` — % points from free throws (offense)
- `pd1_def` / `pd1_def_rank` — % of opponent pts from FTs

**Strength of Schedule.md**
- `sos_off` / `sos_off_rank` — offensive SOS
- `sos_def` / `sos_def_rank` — defensive SOS
- `sos_overall` / `sos_overall_rank` — overall SOS
- `sos_nc` / `sos_nc_rank` — non-conference SOS

**Team Composition.md**
- `bench_min` / `bench_min_rank` — % of minutes from bench
- `d1_exp` / `d1_exp_rank` — avg D1 experience of players (years)
- `min_cont` / `min_cont_rank` — returning minute continuity %
- `avg_height` / `avg_height_rank` — avg team height

---

### Player Stats/ — Source: `data/{year}/{team}_players.parquet`
Seasons covered: 2002–2025 (all D1 teams)
Note: Player identity fields (name, jersey) excluded from model features.

**Player Stats Overview.md**
Links to: [[Player Shooting]], [[Player Per-Possession]], [[Player Defense]], [[Player Usage and Role]]
Non-feature identity fields (excluded from model): name, jersey
Metadata fields: team, season, height, weight, year (Fr/So/Jr/Sr), games, starts

**Player Usage and Role.md**
- `starter` — boolean, starter flag
- `pct_min` — % of team minutes played
- `pct_poss` — % of possessions used
- `pct_shots` — % of team shots taken
- `games`, `starts` — game appearances

**Player Per-Possession.md**
- `ortg` — offensive rating (pts per 100 poss)
- `or_pct` — offensive rebound %
- `dr_pct` — defensive rebound %
- `a_rate` — assist rate
- `to_rate` — turnover rate
- `fc_per40` — fouls committed per 40 min
- `fd_per40` — fouls drawn per 40 min

**Player Shooting.md**
- `efg_pct` — effective FG%
- `ts_pct` — true shooting %
- `ft_rate` — FTA/FGA ratio
- `ftm`, `fta`, `ft_pct` — free throw makes, attempts, %
- `fg2m`, `fg2a`, `fg2_pct` — 2-point makes, attempts, %
- `fg3m`, `fg3a`, `fg3_pct` — 3-point makes, attempts, %

**Player Defense.md**
- `blk_pct` — block %
- `stl_pct` — steal %
- `dr_pct` — defensive rebound %

---

### Game Log/ — Source: `data/{year}/{team}_gameplan.parquet`
Seasons covered: 2024–2025 (team-level per-game files)
One row per game played.

**Game Log Overview.md**
Links to: [[Per-Game Efficiency]], [[Per-Game Four Factors]], [[Shot Volume]]
Game metadata fields: team, year, date, opponent, outcome (W/L), team_score, opp_score, location (H/A/N), opp_kp_rank

**Per-Game Efficiency.md**
- `pace` — game possessions
- `off_eff` / `off_eff_rank` — offensive efficiency that game
- `def_eff` / `def_eff_rank` — defensive efficiency that game

**Per-Game Four Factors.md**
- `off_efg` — offensive eFG%
- `off_to_pct` — offensive turnover %
- `off_or_pct` — offensive rebound %
- `off_ftr` — offensive free throw rate
- `def_efg` — defensive eFG% allowed
- `def_to_pct` — defensive turnover % forced
- `def_or_pct` — defensive offensive rebound % allowed
- `def_ftr` — defensive free throw rate allowed

**Shot Volume.md**
- `off_2p_pct`, `off_2p_made`, `off_2p_att`
- `off_3p_pct`, `off_3p_made`, `off_3p_att`
- `off_3pa_rate` — 3PA / total FGA (offense)
- `def_2p_pct`, `def_2p_made`, `def_2p_att`
- `def_3p_pct`, `def_3p_made`, `def_3p_att`
- `def_3pa_rate` — opponent 3PA rate allowed

---

### Season Record/ — Source: `data/conferences.parquet`
Seasons covered: 2002–2025. One row per team per season.

**Season Record Overview.md**
Links to: [[Win-Loss Record]], [[Scoring]], [[Rating Systems]], [[Conferences Hub]]
Identifier fields: team, season, conf, conf_abbrev

**Win-Loss Record.md**
- `w` — total wins
- `l` — total losses
- `wl_pct` — overall win %
- `conf_w` — conference wins
- `conf_l` — conference losses
- `conf_wl_pct` — conference win %

**Scoring.md**
- `pts_pg` — points per game (team)
- `opp_pts_pg` — opponent points per game allowed

**Rating Systems.md**
- `srs` — Simple Rating System (margin of victory + SOS)
- `sos` — strength of schedule (SRS-based)
- `ncaa_tourney` — boolean, did team make tournament

---

## TEAMS SECTION

### Teams Hub.md
Links to every individual team note.
Tags: `#hub #teams`
Summary: 371 unique D1 teams represented in dataset (2002–2025).

### Individual Team Notes: `Teams/{Team Name}.md`
**Content template per team:**
```yaml
---
tags: [team]
conference: {current_conf}
conf_abbrev: {conf_abbrev}
---
```
Body:
- `d1_seasons:` list of all years team appears in data
- `tournament_years:` list of years team made NCAA tournament
- Links to: [[{Conference Name}]], [[Teams Hub]]

**371 Teams (alphabetical):**
Abilene Christian, Air Force, Akron, Alabama, Alabama A&M, Alabama St, Albany,
Alcorn St, American, Appalachian St, Arizona, Arizona St, Arkansas,
Arkansas Pine Bluff, Arkansas St, Army, Auburn, Austin Peay, Ball St, Baylor,
Bellarmine, Belmont, Bethune Cookman, Binghamton, Boise St, Boston College,
Boston University, Bowling Green, Bradley, Brown, Bryant, Bucknell, Buffalo,
Butler, BYU, Cal Baptist, Cal Poly, Cal St Bakersfield, Cal St Fullerton,
California, Campbell, Canisius, Central Arkansas, Central Connecticut,
Central Michigan, Charleston, Charleston Southern, Charlotte, Chattanooga,
Chicago St, Cincinnati, Clemson, Cleveland St, Coastal Carolina, Colgate,
Colorado, Colorado St, Columbia, Connecticut, Coppin St, Cornell, Creighton,
CSUN, Dartmouth, Davidson, Dayton, Delaware, Delaware St, Denver, DePaul,
Detroit Mercy, Drake, Drexel, Duke, Duquesne, East Carolina, East Tennessee St,
East Texas A&M, Eastern Illinois, Eastern Kentucky, Eastern Michigan,
Eastern Washington, Elon, Evansville, Fairfield, Fairleigh Dickinson, FIU,
Florida, Florida A&M, Florida Atlantic, Florida Gulf Coast, Florida St, Fordham,
Fresno St, Furman, Gardner Webb, George Mason, George Washington, Georgetown,
Georgia, Georgia Southern, Georgia St, Georgia Tech, Gonzaga, Grand Canyon,
Green Bay, Hampton, Harvard, Hawaii, High Point, Hofstra, Holy Cross, Houston,
Howard, Idaho, Idaho St, Illinois, Illinois St, Indiana, Indiana St,
Iona, Iowa, Iowa St, IUPUI, Jackson St, Jacksonville, Jacksonville St,
James Madison, Kansas, Kansas St, Kennesaw St, Kent St, Kentucky,
La Salle, Lafayette, Lamar, Lehigh, Liberty, Lipscomb, Little Rock, Long Beach St,
Long Island University, Longwood, Louisiana, Louisiana Tech, Louisville,
Loyola Chicago, Loyola Maryland, Loyola Marymount, LSU, Maine, Manhattan,
Marist, Marquette, Marshall, Maryland, McNeese, Memphis, Mercer, Miami (FL),
Miami (OH), Michigan, Michigan St, Middle Tennessee, Milwaukee, Minnesota,
Mississippi Valley St, Missouri, Missouri St, Monmouth, Montana, Montana St,
Morehead St, Morgan St, Mount St Mary's, Murray St, Navy, Nebraska, Nevada,
New Hampshire, New Mexico, New Mexico St, Niagara, Norfolk St, North Alabama,
North Carolina, North Carolina A&T, North Carolina Central, North Dakota,
North Dakota St, North Florida, North Texas, Northeastern, Northern Arizona,
Northern Colorado, Northern Illinois, Northern Iowa, Northern Kentucky,
Northwestern, Northwestern St, Notre Dame, Oakland, Ohio, Ohio St, Oklahoma,
Oklahoma St, Old Dominion, Ole Miss, Oral Roberts, Oregon, Oregon St,
Pacific, Penn, Penn St, Pepperdine, Pittsburgh, Portland, Portland St,
Prairie View A&M, Presbyterian, Princeton, Providence, Purdue, Purdue Fort Wayne,
Queens, Quinnipiac, Radford, Rhode Island, Rice, Richmond, Rider, Robert Morris,
Rutgers, Sacramento St, Saint Francis PA, Saint Joseph's, Saint Louis,
Saint Mary's, Saint Peter's, Sam Houston, Samford, San Diego, San Diego St,
San Francisco, Santa Barbara, Seattle U, Seton Hall, Siena, SMU, South Carolina,
South Carolina St, South Dakota, South Dakota St, South Florida, Southeast Missouri St,
Southeastern Louisiana, Southern, Southern Illinois, Southern Mississippi,
Southern Utah, St Bonaventure, St Francis Brooklyn, St John's, Stanford,
Stephen F Austin, Stetson, Stony Brook, Syracuse, TCU, Temple, Tennessee,
Tennessee St, Tennessee Tech, Texas, Texas A&M, Texas A&M Corpus Christi,
Texas Southern, Texas St, Texas Tech, The Citadel, Toledo, Towson, Troy, Tulane,
Tulsa, UAB, UC Davis, UC Irvine, UC Riverside, UC San Diego, UC Santa Barbara,
UCF, UCLA, UIC, UMBC, UMass, UMass Lowell, UNC Asheville, UNC Greensboro,
UNC Wilmington, UNLV, USC, UT Arlington, UT Martin, UTEP, UTSA, Valparaiso,
VCU, Vermont, Villanova, Virginia, Virginia Tech, VMI, Wagner, Wake Forest,
Washington, Washington St, Weber St, West Virginia, Western Carolina,
Western Illinois, Western Kentucky, Western Michigan, Wichita St, William & Mary,
Winthrop, Wisconsin, Wofford, Wright St, Wyoming, Xavier, Yale, Youngstown St

---

## CONFERENCES SECTION

### Conferences Hub.md
Links to each unique conference note.
Note: Some conferences split into divisions (e.g., SEC(East)/SEC(West)) but group under parent.

**Unique base conferences (canonicalized):**
A-10, A-Sun, AAC, ACC, AmEast, Big 12, Big East, Big Sky, Big South,
Big Ten, Big West, CAA, CUSA, GWC, Horizon, Ind, Ivy, MAAC, MAC,
MEAC, Mid-Cont, MVC, MWC, NEC, OVC, Pac-10/Pac-12, Patriot, SEC,
SWAC, Southern, Southland, Summit, Sun Belt, WAC, WCC

### Individual Conference Notes: `Conferences/{Conference}.md`
**Content template:**
```yaml
---
tags: [conference]
---
```
Body:
- Conference full name and abbreviation
- Active seasons in dataset
- Links to [[Teams Hub]] and member team wikilinks

---

## Wikilink Graph Connections Summary

```
00 - Data Overview
  └── Stats Hub
        ├── KenPom Overview
        │     ├── Tempo
        │     ├── Offensive Efficiency
        │     ├── Defensive Efficiency
        │     └── Adjusted Efficiency Margin
        ├── Four Factors Overview
        │     ├── Effective FG Pct
        │     ├── Turnover Rate
        │     ├── Offensive Rebound Pct
        │     └── Free Throw Rate
        ├── Scouting Overview
        │     ├── [Four Factors Overview]
        │     ├── Shooting Advanced
        │     ├── Playmaking
        │     ├── Defense Advanced
        │     ├── Point Distribution
        │     ├── Strength of Schedule
        │     └── Team Composition
        ├── Player Stats Overview
        │     ├── Player Shooting
        │     ├── Player Per-Possession
        │     ├── Player Defense
        │     └── Player Usage and Role
        ├── Game Log Overview
        │     ├── Per-Game Efficiency
        │     ├── Per-Game Four Factors
        │     └── Shot Volume
        └── Season Record Overview
              ├── Win-Loss Record
              ├── Scoring
              └── Rating Systems
  └── Teams Hub
        └── [371 team notes] → each links to conference note
  └── Conferences Hub
        └── [35 conference notes] → each links to member teams
```

---

## Build Script Notes

A Python script `build_obsidian_vault.py` generates all markdown files:
1. Creates all folder structure
2. Writes all stat concept notes (with field lists)
3. Reads conferences.parquet to generate all 371 team notes with d1_years and tourney_years
4. Generates conference notes listing member teams
5. Writes hub notes with wikilinks

Execution: `python build_obsidian_vault.py`
Then: `obsidian reload` to refresh vault graph

---

## Tags Used
- `#hub` — top-level navigation notes
- `#stats` — stat category notes
- `#feature` — individual stat/feature notes
- `#team` — team notes
- `#conference` — conference notes

---

## Data Source File Reference

| Source File | Location Pattern | Seasons | Granularity |
|-------------|-----------------|---------|-------------|
| conferences.parquet | data/conferences.parquet | 2002–2025 | team × season |
| summary_pt.csv | data/{year}/summary{YY}_pt.csv | 2001–2025 | team × season |
| scouting.parquet | data/{year}/{team}_scouting.parquet | 2002–2025 | team × season |
| players.parquet | data/{year}/{team}_players.parquet | 2002–2025 | player × season |
| gameplan.parquet | data/{year}/{team}_gameplan.parquet | 2002–2025 | game |
| bracket.csv | data/{year}/bracket.csv | 2001–2025 | matchup |

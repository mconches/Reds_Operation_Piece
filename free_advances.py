"""Reds running game, 2026: free advances allowed."""

import matplotlib.pyplot as plt
from pybaseball import cache, playerid_reverse_lookup, statcast

cache.enable()  # save downloads on this computer so reruns are fast


season_start = "2026-03-25"
season_end = "2026-09-27"
month_start = "2026-06-01"  # one month of league-wide data
month_end = "2026-06-30"
min_opportunities = 150      # skip pitchers with too few runner-on pitches

runs_per_advance = 0.2       # Baseball Savant run value for a steal or balk advance
runs_per_win = 10            # common rule of thumb
dollars_per_win = 8_510_000  # FanGraphs, 1-2 WAR free-agent tier



def add_free_advances(df):
    """Flag pitches where a runner moved up a base mid-at-bat, and runner-on opportunities."""
    df = df.sort_values(["game_pk", "at_bat_number", "pitch_number"]).reset_index(drop=True)
    same_at_bat = df.groupby(["game_pk", "at_bat_number"])
    next_on_2b = same_at_bat["on_2b"].shift(-1)
    next_on_3b = same_at_bat["on_3b"].shift(-1)
    moved_to_2nd = (df["on_1b"] == next_on_2b).fillna(False)
    moved_to_3rd = (df["on_2b"] == next_on_3b).fillna(False)
    df["free_advance"] = moved_to_2nd | moved_to_3rd
    df["opportunity"] = df["on_1b"].notna() | df["on_2b"].notna()
    return df


# Reds Pitching
season = statcast(start_dt=season_start, end_dt=season_end, team="CIN")
print(season.shape)

season = add_free_advances(season)
print("Free advances:", season["free_advance"].sum())

staff_rate = season["free_advance"].sum() / season["opportunity"].sum() * 100
print("Staff free advances per 100 opportunities:", round(staff_rate, 2))

# Pitcher Data
by_pitcher = season.groupby("player_name").agg(
    advances=("free_advance", "sum"),
    opportunities=("opportunity", "sum"),
)
by_pitcher = by_pitcher[by_pitcher["opportunities"] >= min_opportunities]
by_pitcher["per_100"] = by_pitcher["advances"] / by_pitcher["opportunities"] * 100
print(by_pitcher.sort_values("advances", ascending=False).head(10))


# Catcher Data
by_catcher = season.groupby("fielder_2").agg(
    advances=("free_advance", "sum"),
    opportunities=("opportunity", "sum"),
)
by_catcher["per_100"] = by_catcher["advances"] / by_catcher["opportunities"] * 100
print(by_catcher)

names = playerid_reverse_lookup(list(by_catcher.index), key_type="mlbam")
print(names[["name_last", "name_first", "key_mlbam"]])


# June 2026
league = statcast(start_dt=month_start, end_dt=month_end)
print(league.shape)

league = add_free_advances(league)
# Top of the inning = home team pitching; bottom = away team pitching
league["pitching_team"] = league["home_team"].where(league["inning_topbot"] == "Top", league["away_team"])

team_rates = league.groupby("pitching_team").agg(
    advances=("free_advance", "sum"),
    opportunities=("opportunity", "sum"),
)
team_rates["per_100"] = team_rates["advances"] / team_rates["opportunities"] * 100
print(team_rates.sort_values("per_100", ascending=False))

league_avg = team_rates["advances"].sum() / team_rates["opportunities"].sum() * 100
print("League average per 100:", round(league_avg, 2))


# Cost
total_advances = season["free_advance"].sum()
print("Gross cost:", total_advances * runs_per_advance, "runs")

for reduction in [0.10, 0.25, 0.50]:
    runs_saved = total_advances * reduction * runs_per_advance
    wins = runs_saved / runs_per_win
    dollars = wins * dollars_per_win
    print(f"{int(reduction * 100)}% cut: {runs_saved:.1f} runs, {wins:.2f} wins, ${dollars / 1_000_000:.2f}M")


# Chart
sorted_rates = team_rates.sort_values("per_100")
colors = ["#C6011F" if team == "CIN" else "lightgray" for team in sorted_rates.index]

fig, ax = plt.subplots(figsize=(8, 9))
ax.barh(sorted_rates.index, sorted_rates["per_100"], color=colors)
ax.axvline(league_avg, color="black", linestyle="--", linewidth=1, label="League average")
ax.set_xlabel("Free advances per 100 opportunity pitches")
ax.set_title("Free advances by pitching team, June 2026")
ax.legend()
fig.tight_layout()
fig.savefig("free_advances_by_team.png", dpi=200)
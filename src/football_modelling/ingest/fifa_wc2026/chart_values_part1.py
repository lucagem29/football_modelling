# ruff: noqa: E501, E741
# Manually transcribed from chart pages (Tournament Overview, pages 9-38).
# Format: (page, metric, unit, normalisation, {tournament: value}) and team top-16 lists.
T = []  # tournament-level rows: page, metric, unit, normalisation, tournament, value
K = []  # team-level rows: page, metric, unit, normalisation, team, value, rank

def t(page, metric, unit, norm, v26, v22, v18):
    for tour, v in (("FWC2026", v26), ("FWC2022", v22), ("FWC2018", v18)):
        if v is not None:
            T.append((page, metric, unit, norm, tour, v))

def k(page, metric, unit, norm, pairs):
    for r, (team, v) in enumerate(pairs, 1):
        K.append((page, metric, unit, norm, team, v, r))

# Page 9 - ball in play (mm:ss per match, converted to seconds)
t(9, "ball_in_play_time", "seconds", "per_match", 57*60+52, 58*60+57, 55*60+6)
t(9, "in_contest_time", "seconds", "per_match", 5*60+5, 5*60+38, 5*60+45)

# Page 10 - average possession length
t(10, "average_possession_length", "seconds", "per_possession", 10.5, 9.5, 8.6)
k(10, "average_possession_length", "seconds", "per_possession", [
    ("ALG",14.5),("ARG",13.6),("KOR",13.4),("POR",13.2),("ESP",13.0),("BRA",12.5),
    ("NED",12.5),("MAR",12.3),("COL",12.3),("FRA",12.2),("NOR",12.2),("ENG",11.9),
    ("CRO",11.5),("SEN",11.3),("GER",11.3),("JPN",11.2)])

# Page 11 - tournament goals
t(11, "total_goals", "count", "tournament_total", 308, 172, 169)
k(11, "goals_scored", "count", "tournament_total", [
    ("FRA",20),("ENG",20),("ARG",18),("BEL",13),("ESP",13),("NOR",12),("GER",11),
    ("MAR",11),("SUI",11),("NED",10),("SEN",10),("MEX",10),("BRA",10),("EGY",10),
    ("USA",9),("JPN",8)])

# Page 12
t(12, "goals_per_game", "goals", "per_match", 2.96, 2.69, 2.64)
t(12, "average_winning_margin", "goals", "per_decided_match", 2.02, 1.84, 1.63)

# Page 13
t(13, "attempts_on_target_share", "percent", "of_attempts", 34.5, 35.2, 30.5)
t(13, "attempt_conversion_rate", "percent", "of_attempts", 11.4, 11.8, 9.7)
t(13, "on_target_conversion_rate", "percent", "of_attempts_on_target", 33.0, 33.6, 31.8)

# Page 14 / 15 - location splits (heatmap grids not transcribed)
t(14, "attempts_inside_penalty_area_share", "percent", "of_attempts", 61, 62, 56)
t(14, "attempts_outside_penalty_area_share", "percent", "of_attempts", 39, 38, 44)
t(15, "goals_inside_penalty_area_share", "percent", "of_goals", 84, 92, 84)
t(15, "goals_outside_penalty_area_share", "percent", "of_goals", 16, 8, 16)

# Page 16 - expected goals (scatter plot not transcribed)
t(16, "expected_goals", "xG", "per_team_per_match", 1.16, 1.21, 1.09)

# Page 17
t(17, "expected_goals_per_attempt", "xG", "per_attempt", 0.103, 0.096, 0.077)
k(17, "expected_goals_per_attempt", "xG", "per_attempt", [
    ("NOR",0.153),("BRA",0.149),("ARG",0.134),("SUI",0.130),("ENG",0.127),("AUT",0.125),
    ("ESP",0.125),("IRN",0.123),("CIV",0.122),("FRA",0.121),("GER",0.117),("MEX",0.116),
    ("CAN",0.111),("ECU",0.111),("QAT",0.111),("NED",0.109)])

# Page 18 - goal timings, share of goals per period
periods = ["0-15","15-30","30-45","45+","45-60","60-75","75-90","90+","extra_time_1","extra_time_2"]
g26 = [11.9,11.2,14.3,3.7,16.3,13.6,15.6,10.9,1.0,1.4]
g22 = [8.8,9.4,17.6,2.9,15.9,18.8,15.3,8.8,0.6,1.8]
g18 = [12.1,8.9,14.0,1.9,21.0,18.5,10.8,10.8,0.6,1.3]
for p, a, b, c in zip(periods, g26, g22, g18, strict=True):
    t(18, f"goal_timing_share_{p}", "percent", "of_goals", a, b, c)

# Page 19 - ball progressions in final third (take-ons + step-ins)
t(19, "final_third_progressions_take_ons", "count", "per_30min_in_possession", 11.9, 7.1, 8.6)
t(19, "final_third_progressions_step_ins", "count", "per_30min_in_possession", 1.5, 2.8, 2.9)
t(19, "final_third_progressions_total", "count", "per_30min_in_possession", 13.4, 9.9, 11.5)
prog = [("AUS",19.2,2.4,21.7),("FRA",18.2,3.2,21.4),("TUR",16.3,3.0,19.3),("CAN",16.3,2.0,18.4),
        ("GER",16.5,1.7,18.2),("JOR",16.3,1.7,18.0),("SEN",16.3,1.4,17.7),("CUW",15.9,1.6,17.5),
        ("BRA",15.7,1.2,16.9),("GHA",15.6,1.1,16.7),("HAI",15.2,1.3,16.5),("USA",14.4,1.9,16.4),
        ("ENG",14.8,1.5,16.3),("CPV",14.7,1.6,16.3),("URU",12.3,3.5,15.8),("ECU",13.6,1.8,15.4)]
k(19, "final_third_progressions_total", "count", "per_30min_in_possession", [(a,d) for a,b,c,d in prog])
k(19, "final_third_progressions_take_ons", "count", "per_30min_in_possession", [(a,b) for a,b,c,d in prog])
k(19, "final_third_progressions_step_ins", "count", "per_30min_in_possession", [(a,c) for a,b,c,d in prog])

# Page 20
t(20, "offers_per_possession", "count", "per_possession_sequence", 2.33, 3.42, 2.75)
t(20, "offers_in_behind_per_possession", "count", "per_possession_sequence", 0.65, 0.78, 0.67)

# Page 22
t(22, "direct_pressure_applied", "count", "per_30min_out_of_possession", 48, 54, 57)
k(22, "direct_pressure_applied", "count", "per_30min_out_of_possession", [
    ("ECU",71),("TUR",69),("MAR",65),("GER",65),("PAN",64),("CAN",64),("USA",62),("URU",58),
    ("PAR",56),("EGY",54),("HAI",53),("SUI",52),("ESP",52),("AUT",52),("ENG",51),("NZL",51)])

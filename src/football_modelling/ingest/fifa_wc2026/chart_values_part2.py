# ruff: noqa: E501, E741
"""Chart values, part 2 (pages 23-47). Imports and extends the lists from part 1."""

# K and T are re-exported: importing this module yields the complete lists
from football_modelling.ingest.fifa_wc2026.chart_values_part1 import K, T, k, t  # noqa: F401

# Page 23
t(23, "interceptions", "count", "per_30min_out_of_possession", 9.1, 8.4, 8.9)
k(23, "interceptions", "count", "per_30min_out_of_possession", [
    ("URU",14.2),("ESP",13.5),("ECU",13.4),("POR",13.4),("TUR",12.8),("GER",12.8),("USA",12.4),
    ("FRA",11.6),("RSA",11.0),("CAN",10.6),("CIV",10.4),("SEN",10.2),("SUI",10.1),("CUW",10.1),
    ("KOR",10.0),("BEL",9.9)])

# Page 24
t(24, "tackles", "count", "per_30min_out_of_possession", 35, 37, 43)
k(24, "tackles", "count", "per_30min_out_of_possession", [
    ("TUR",64),("GER",52),("ECU",51),("EGY",46),("PAN",46),("PAR",44),("CAN",43),("MAR",41),
    ("ESP",41),("USA",40),("URU",39),("IRN",39),("BRA",39),("UZB",38),("HAI",38),("CIV",38)])

# Pages 26-33 - set plays (normalisation as labelled on each chart)
t(26, "corners", "count", "per_team_per_match", 4.37, 4.41, 4.60)
t(26, "free_kicks", "count", "per_team_per_match", 12.96, 14.10, 14.48)
t(27, "inswinging_corners", "count", "per_match", 2.15, 1.67, 1.45)
t(27, "outswinging_corners", "count", "per_match", 1.13, 1.49, 1.81)
t(28, "short_corners", "count", "per_match", 0.79, 0.72, 0.90)
t(28, "corners_direct_into_box", "count", "per_match", 3.47, 3.66, 3.63)
t(29, "goals_from_set_play_delivery", "count", "per_match", 0.15, 0.09, 0.31)
t(29, "attempts_from_set_play_delivery", "count", "per_match", 2.44, 1.97, 2.98)
t(30, "corners_leading_directly_to_attempt", "count", "per_match", 1.64, 1.31, 1.86)
t(30, "goals_from_corner_delivery", "count", "per_match", 0.12, 0.03, 0.19)
t(31, "free_kicks_leading_directly_to_attempt", "count", "per_match", 0.68, 0.61, 0.92)
t(31, "goals_from_free_kick_delivery", "count", "per_match", 0.02, 0.06, 0.12)
t(32, "penalties_awarded", "count", "per_match", 0.21, 0.36, 0.45)
t(32, "penalties_scored", "count", "per_match", 0.15, 0.27, 0.34)
t(33, "throw_ins", "count", "per_team_per_match", 18.44, 20.58, 20.57)
t(33, "throw_ins_direct_into_box", "count", "per_team_per_match", 0.89, 0.62, 0.77)

# Pages 35-38 - physical
t(35, "total_distance", "km", "per_90min_playing_time", 98, 103, 101)
k(35, "total_distance", "km", "per_90min_playing_time", [
    ("CZE",104),("GER",103),("NZL",102),("SCO",102),("BEL",102),("USA",102),("AUS",101),
    ("JOR",101),("NOR",101),("TUR",101),("KOR",100),("CAN",100),("TUN",100),("IRN",100),
    ("PAN",100),("EGY",100)])
t(36, "zone5_distance", "m", "per_90min_playing_time", 1807, 1915, 1632)
k(36, "zone5_distance", "m", "per_90min_playing_time", [
    ("CAN",2278),("NZL",2203),("GER",2199),("MAR",2136),("CIV",2082),("URU",2064),("PAN",2045),
    ("CUW",2036),("ECU",2024),("CRO",1996),("TUR",1981),("NOR",1973),("HAI",1954),("SEN",1945),
    ("ENG",1936),("FRA",1934)])
t(37, "zone4_5_distance_share", "percent", "of_total_distance", 6.8, 7.1, 6.3)
k(37, "zone4_5_distance_share", "percent", "of_total_distance", [
    ("CAN",8.1),("NZL",7.9),("URU",7.6),("MAR",7.5),("ECU",7.5),("CRO",7.4),("KSA",7.4),
    ("GER",7.4),("HAI",7.3),("PAN",7.3),("RSA",7.3),("SEN",7.3),("CIV",7.2),("USA",7.1),
    ("CUW",7.1),("FRA",7.0)])
t(38, "sprints", "count", "per_90min_playing_time", 381, 412, 370)
k(38, "sprints", "count", "per_90min_playing_time", [
    ("CAN",451),("NZL",438),("KSA",426),("RSA",422),("USA",419),("URU",416),("BEL",415),
    ("CZE",413),("PAN",406),("GER",404),("HAI",404),("EGY",401),("CRO",398),("JOR",396),
    ("ECU",396),("MAR",396)])

# Page 47 - share of matches building with a back three (all listed teams, full names in source)
k(47, "back_three_build_up_match_share", "percent", "of_matches_played", [
    ("CZE",100),("GER",100),("JPN",100),("JOR",100),("KOR",100),("PAN",100),("TUN",100),
    ("UZB",100),("USA",80),("AUS",75),("SWE",75),("MAR",66.7),("SCO",66.7),("PAR",60),
    ("COD",50),("NED",50),("BRA",40),("ARG",37.5),("ENG",37.5),("CUW",33.3),("IRN",33.3),
    ("QAT",33.3),("BIH",25),("CRO",25),("ECU",25),("RSA",25),("EGY",20),("MEX",20),
    ("POR",20),("FRA",12.5)])

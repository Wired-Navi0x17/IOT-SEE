"""First-run data: the 10 IPL franchises with placeholder squads (real squads to be imported).

No fake fixtures or results are created."""
from __future__ import annotations

import random

from sqlmodel import select

from .db import log_activity, session
from .models import Player, Team

TEAMS = [   # the 10 IPL franchises (name, short, home city, head coach placeholder)
    ("Chennai Super Kings", "CSK", "Chennai", ""),
    ("Delhi Capitals", "DC", "Delhi", ""),
    ("Gujarat Titans", "GT", "Ahmedabad", ""),
    ("Kolkata Knight Riders", "KKR", "Kolkata", ""),
    ("Lucknow Super Giants", "LSG", "Lucknow", ""),
    ("Mumbai Indians", "MI", "Mumbai", ""),
    ("Punjab Kings", "PBKS", "Mullanpur", ""),
    ("Rajasthan Royals", "RR", "Jaipur", ""),
    ("Royal Challengers Bengaluru", "RCB", "Bengaluru", ""),
    ("Sunrisers Hyderabad", "SRH", "Hyderabad", ""),
]
FIRST = ["Aarav", "Vihaan", "Ishaan", "Kabir", "Reyansh", "Arjun", "Siddharth", "Omkar", "Pranav", "Tejas",
         "Yash", "Aditya", "Harsh", "Nikhil", "Rohit", "Saurabh", "Kunal", "Mihir", "Parth", "Chinmay", "Shreyas",
         "Atharva", "Varun", "Rahul", "Sahil", "Ninad", "Gaurav", "Akshay", "Devansh", "Ritesh", "Tanmay", "Abhay",
         "Swapnil", "Ketan", "Mandar", "Sarthak", "Hrishikesh", "Rushabh", "Jay", "Soham"]
LAST = ["Kulkarni", "Patil", "Deshmukh", "Joshi", "Gaikwad", "Shinde", "Pawar", "Jadhav", "Naik", "Kadam",
        "Salunkhe", "Mane", "Bhosale", "Chavan", "Sawant", "Rane", "Gokhale", "Apte", "Karve", "Thakur", "Dhumal",
        "Mohite", "Nikam", "Wagh", "More", "Kamble", "Londhe", "Phadke", "Ranade", "Sathe"]
STYLES = {"BOWL": ["RF", "RFM", "LFM", "OB", "LB", "SLA"], "AR": ["RM", "OB", "SLA", "LFM"], "BAT": [""], "WK": [""]}
ROLES = ["WK"] + ["BAT"] * 5 + ["AR"] * 3 + ["BOWL"] * 5


def seed_if_empty() -> None:
    with session() as s:
        if s.exec(select(Team)).first():
            return
    rng = random.Random(2026)
    used = set()
    team_ids = []
    with session() as s:
        for name, short, city, mgr in TEAMS:
            t = Team(name=name, short=short, city=city, manager=mgr)
            s.add(t)
            s.commit()
            s.refresh(t)
            team_ids.append(t.id)
            for role in ROLES:
                while True:
                    n = f"{rng.choice(FIRST)} {rng.choice(LAST)}"
                    if n not in used:
                        used.add(n)
                        break
                if role == "BAT":
                    bat, bowl = rng.randint(54, 86), rng.randint(5, 30)
                elif role == "WK":
                    bat, bowl = rng.randint(50, 78), rng.randint(2, 10)
                elif role == "AR":
                    bat, bowl = rng.randint(45, 72), rng.randint(45, 74)
                else:
                    bat, bowl = rng.randint(8, 35), rng.randint(56, 88)
                s.add(Player(team_id=t.id, name=n, role=role, bat=bat, bowl=bowl, style=rng.choice(STYLES[role])))
            s.commit()

    log_activity("team", f"{len(TEAMS)} IPL teams and {len(TEAMS) * len(ROLES)} players registered")

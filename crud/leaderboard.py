"""
===============================================================================
KAIZEN / MISSION AVINYA - Member Leaderboard & Gamification Services
===============================================================================
Module Purpose:
  Provides automated score computation, club session duration calculations,
  flight minutes tracking, and member ranking metrics with line-by-line comments.
===============================================================================
"""

# Import Python standard datetime & json utilities
from datetime import datetime
import json

# Import required database queries from submodules
from .base import _get_client
from .users import get_all_users_detailed
from .flights import get_all_flight_logs


def get_leaderboard_data():
    """
    Computes gamification scores and ranks all members based on:
      - Completed tasks (50 points each)
      - Total hours spent in club sessions (15 points per hour)
      - Flight log minutes (2 points per minute)
      - Attendance session check-ins (5 points each)
    """
    try:
        # Fetch all active profiles
        profiles = get_all_users_detailed()
        
        # Fetch all completed tasks
        tasks = _get_client().table("tasks").select("*").eq("status", "done").execute().data or []
        
        # Fetch all task assignee links
        task_assignees = _get_client().table("task_assignees").select("*").execute().data or []
        
        # Fetch all attendance records
        attendance = _get_client().table("attendance").select("*").execute().data or []
        
        # Fetch all flight logs
        flights = get_all_flight_logs()

        # Map completed tasks count per user
        completed_task_counts = {}
        for ta in task_assignees:
            tid = ta["task_id"]
            uid = ta["user_id"]
            if any(t["id"] == tid for t in tasks):
                completed_task_counts[uid] = completed_task_counts.get(uid, 0) + 1

        # Map attendance records & calculate total time spent in club (minutes)
        attendance_counts = {}
        club_minutes = {}
        for a in attendance:
            uid = a["user_id"]
            if a.get("status") == "present":
                attendance_counts[uid] = attendance_counts.get(uid, 0) + 1
                if a.get("notes"):
                    try:
                        notes = json.loads(a["notes"])
                        if "in" in notes and "out" in notes:
                            t_in = datetime.strptime(notes["in"], "%H:%M:%S")
                            t_out = datetime.strptime(notes["out"], "%H:%M:%S")
                            diff = (t_out - t_in).total_seconds() / 60
                            if diff > 0:
                                club_minutes[uid] = club_minutes.get(uid, 0) + int(diff)
                    except Exception:
                        pass

        # Map flight minutes per pilot
        flight_minutes = {}
        for f in flights:
            uid = f.get("pilot_id")
            if uid:
                flight_minutes[uid] = flight_minutes.get(uid, 0) + (f.get("duration_minutes") or 0)

        # Build final leaderboard list with weighted score calculations
        leaderboard = []
        for p in profiles:
            uid = p["id"]
            t_count = completed_task_counts.get(uid, 0)
            a_count = attendance_counts.get(uid, 0)
            c_mins = club_minutes.get(uid, 0)
            f_mins = flight_minutes.get(uid, 0)
            
            c_hours = round(c_mins / 60.0, 1)
            
            # Score formula: (Tasks * 50) + (Club Hours * 15) + (Flight Mins * 2) + (Attendance Count * 5)
            score = int((t_count * 50) + (c_hours * 15) + (f_mins * 2) + (a_count * 5))
            
            leaderboard.append({
                "profile": p,
                "tasks_completed": t_count,
                "attendance_events": a_count,
                "club_minutes": c_mins,
                "club_hours": c_hours,
                "flight_minutes": f_mins,
                "score": score
            })

        # Sort leaderboard descending by total score
        leaderboard.sort(key=lambda x: x["score"], reverse=True)
        return leaderboard
    except Exception as e:
        print(f"Error computing leaderboard: {e}")
        return []

import os
import json
import glob
import re
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

TZ = ZoneInfo("America/New_York")

# Explicit weekday-to-cycle-day lookup table
CYCLE_DAY_MAP = {
    0: "A",  # Monday
    1: "B",  # Tuesday
    2: "C",  # Wednesday
    3: "D",  # Thursday
    4: "A",  # Friday
}

# --- 1. Bell Schedule Templates ---
TEMPLATES = {
    "MHS": {
        "Monday": [
            {"id": "B1", "name": "Bell 1", "type": "instructional", "start": "07:45", "end": "08:31"},
            {"id": "B2", "name": "Bell 2", "type": "instructional", "start": "08:36", "end": "09:22"},
            {"id": "B3", "name": "Bell 3", "type": "instructional", "start": "09:27", "end": "10:13"},
            {"id": "B4", "name": "Bell 4", "type": "instructional", "start": "10:18", "end": "11:03"},
            {"id": "B5", "name": "Bell 5 & Lunches", "type": "instructional", "start": "11:08", "end": "12:48"},
            {"id": "B6", "name": "Bell 6", "type": "instructional", "start": "12:53", "end": "13:39"},
            {"id": "B7", "name": "Bell 7", "type": "instructional", "start": "13:44", "end": "14:30"},
        ],
        "Tuesday": [
            {"id": "B1", "name": "Bell 1", "type": "instructional", "start": "07:45", "end": "08:55"},
            {"id": "B2", "name": "Bell 2", "type": "instructional", "start": "09:00", "end": "10:10"},
            {"id": "B3", "name": "Bell 3", "type": "instructional", "start": "10:15", "end": "11:25"},
            {"id": "B5", "name": "Bell 5", "type": "instructional", "start": "11:30", "end": "13:15"},
            {"id": "B7", "name": "Bell 7", "type": "instructional", "start": "13:20", "end": "14:30"},
            {"id": "P8", "name": "Period 8", "type": "instructional", "start": "14:30", "end": "14:35"}
        ],
        "Wednesday": [
            {"id": "B2", "name": "Bell 2", "type": "instructional", "start": "07:45", "end": "08:55"},
            {"id": "B5", "name": "Bell 5", "type": "instructional", "start": "09:00", "end": "10:10"},
            {"id": "B3", "name": "Bell 3", "type": "instructional", "start": "10:15", "end": "12:00"},
            {"id": "CRW", "name": "Connect", "type": "advisory", "start": "12:05", "end": "13:15"},
            {"id": "B6", "name": "Bell 6", "type": "instructional", "start": "13:20", "end": "14:30"}
        ],
        "Thursday": [
            {"id": "B1", "name": "Bell 1", "type": "instructional", "start": "07:45", "end": "08:55"},
            {"id": "B4", "name": "Bell 4", "type": "instructional", "start": "09:00", "end": "10:10"},
            {"id": "B3", "name": "Bell 3", "type": "instructional", "start": "10:15", "end": "11:25"},
            {"id": "B5", "name": "Bell 5 & Lunches", "type": "instructional", "start": "11:30", "end": "13:15"},
            {"id": "B7", "name": "Bell 7", "type": "instructional", "start": "13:20", "end": "14:30"}
        ],
        "Friday": [
            {"id": "B1", "name": "Bell 1", "type": "instructional", "start": "07:45", "end": "08:30"},
            {"id": "B2", "name": "Bell 2", "type": "instructional", "start": "08:35", "end": "09:18"},
            {"id": "B3", "name": "Bell 3", "type": "instructional", "start": "09:23", "end": "10:16"},
            {"id": "B4", "name": "Bell 4", "type": "instructional", "start": "10:21", "end": "11:04"},
            {"id": "B5A", "name": "Lunch 5A", "type": "lunch", "start": "11:09", "end": "11:39"},
            {"id": "B5B", "name": "Lunch 5B", "type": "lunch", "start": "11:43", "end": "12:13"},
            {"id": "B5C", "name": "Lunch 5C", "type": "lunch", "start": "12:18", "end": "12:48"},
            {"id": "B6", "name": "Bell 6", "type": "instructional", "start": "12:59", "end": "13:42"},
            {"id": "B7", "name": "Bell 7", "type": "instructional", "start": "13:47", "end": "14:30"}
        ]
    },
    "MMS": {
        "Regular Day": [
            {"id": "CRW", "name": "CREW", "type": "instructional", "start": "07:40", "end": "08:10"},
            {"id": "P1", "name": "Period 1", "type": "instructional", "start": "08:14", "end": "09:04"},
            {"id": "P2", "name": "Period 2", "type": "instructional", "start": "09:08", "end": "09:58"},
            {"id": "P3", "name": "Period 3", "type": "instructional", "start": "10:02", "end": "10:52"},
            {"id": "P4", "name": "Period 4", "type": "instructional", "start": "10:56", "end": "12:34"},
            {"id": "LA", "name": "Lunch A", "type": "lunch", "start": "10:56", "end": "11:26"},
            {"id": "LB", "name": "Lunch B", "type": "lunch", "start": "11:30", "end": "12:00"},
            {"id": "LC", "name": "Lunch C", "type": "lunch", "start": "12:04", "end": "12:34"},
            {"id": "P5", "name": "Period 5", "type": "instructional", "start": "12:38", "end": "13:28"},
            {"id": "P6", "name": "Period 6", "type": "instructional", "start": "13:32", "end": "14:25"},
            {"id": "P7", "name": "Period 7", "type": "instructional", "start": "14:25", "end": "14:30"}
        ]
    }
}

# --- 2. Calendar Parser ---
def parse_calendar_files():
    schedule_map = {}
    csv_files = glob.glob("STAFF_Calendar_2026-2027_MHS_*.csv")
    
    for fpath in csv_files:
        with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                dates = re.findall(r"(\d{4}-\d{2}-\d{2})", line)
                if not dates:
                    continue
                date_str = dates[0]
                
                if "Monday Schedule" in line:
                    sched_type = "Monday"
                elif "Tuesday Schedule" in line:
                    sched_type = "Tuesday"
                elif "Wednesday Schedule" in line:
                    sched_type = "Wednesday"
                elif "Thursday Schedule" in line:
                    sched_type = "Thursday"
                elif "Friday Schedule" in line:
                    sched_type = "Friday"
                else:
                    sched_type = "No School"
                
                schedule_map[date_str] = sched_type
    return schedule_map

def build_day_json(date_str, mhs_sched_type):
    dt_base = datetime.strptime(date_str, "%Y-%m-%d")
    weekday_idx = dt_base.weekday()
    
    is_school_day = (mhs_sched_type != "No School") and (weekday_idx < 5)
    
    # Apply requested cycle_day rules: Mon=A, Tue=B, Wed=C, Thu=D, Fri=A
    cycle_day = CYCLE_DAY_MAP.get(weekday_idx, None) if is_school_day else None

    buildings = []

    # High School (MHS)
    mhs_periods = []
    if is_school_day:
        for p in TEMPLATES["MHS"].get(mhs_sched_type, []):
            s_dt = datetime.strptime(f"{date_str} {p['start']}", "%Y-%m-%d %H:%M").replace(tzinfo=TZ)
            e_dt = datetime.strptime(f"{date_str} {p['end']}", "%Y-%m-%d %H:%M").replace(tzinfo=TZ)
            mhs_periods.append({
                "period_id": p["id"],
                "name": p["name"],
                "type": p["type"],
                "start_time": p["start"],
                "end_time": p["end"],
                "start_iso": s_dt.isoformat(),
                "end_iso": e_dt.isoformat(),
                "start_epoch": int(s_dt.timestamp()),
                "end_epoch": int(e_dt.timestamp())
            })

    buildings.append({
        "building_id": "MHS",
        "building_name": "Mason High School",
        "schedule_type": mhs_sched_type if is_school_day else "No School",
        "cycle_day": cycle_day,
        "periods": mhs_periods
    })

    # Middle School (MMS)
    mms_periods = []
    if is_school_day:
        for p in TEMPLATES["MMS"]["Regular Day"]:
            s_dt = datetime.strptime(f"{date_str} {p['start']}", "%Y-%m-%d %H:%M").replace(tzinfo=TZ)
            e_dt = datetime.strptime(f"{date_str} {p['end']}", "%Y-%m-%d %H:%M").replace(tzinfo=TZ)
            mms_periods.append({
                "period_id": p["id"],
                "name": p["name"],
                "type": p["type"],
                "start_time": p["start"],
                "end_time": p["end"],
                "start_iso": s_dt.isoformat(),
                "end_iso": e_dt.isoformat(),
                "start_epoch": int(s_dt.timestamp()),
                "end_epoch": int(e_dt.timestamp())
            })

    buildings.append({
        "building_id": "MMS",
        "building_name": "Mason Middle School",
        "schedule_type": "Regular Day" if is_school_day else "No School",
        "cycle_day": cycle_day,
        "periods": mms_periods
    })

    return {
        "status": "success",
        "timezone": "America/New_York",
        "date": date_str,
        "is_school_day": is_school_day,
        "buildings": buildings
    }

def main():
    os.makedirs("schedules", exist_ok=True)
    cal_map = parse_calendar_files()
    
    start_date = datetime(2026, 8, 1)
    end_date = datetime(2027, 6, 30)
    curr = start_date

    while curr <= end_date:
        d_str = curr.strftime("%Y-%m-%d")
        sched_type = cal_map.get(d_str, curr.strftime("%A"))
        day_json = build_day_json(d_str, sched_type)
        
        with open(f"schedules/{d_str}.json", "w") as f:
            json.dump(day_json, f, indent=4)
        curr += timedelta(days=1)

    print("Successfully generated all schedules in /schedules directory!")

if __name__ == "__main__":
    main()
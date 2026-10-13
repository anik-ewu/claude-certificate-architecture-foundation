"""Made-up Nimbus Robotics fleet backends. Nothing to do here.

Three systems built by three different teams, so each returns a different format
(like three different MCP servers):

  fleet_status     last_seen = Unix epoch seconds,  state = numeric code
  maintenance_log  date = "Mar 4 2026",              cost_cents = integer cents
  incident_db      opened_at = ISO 8601 with a timezone offset (various offsets)

send_command() really "executes" and is recorded in COMMANDS.
"""

import json

# Only the fleet team's docs say what the codes mean:
STATE_CODES = {0: "idle", 1: "active", 2: "charging", 3: "fault", 4: "maintenance_due"}

FLEET = {
    "RTM-1": [
        {"robot_id": "ST-01", "state": 1, "last_seen": 1791850200},
        {"robot_id": "ST-03", "state": 3, "last_seen": 1791837300},
        {"robot_id": "ST-07", "state": 4, "last_seen": 1791849000},
        {"robot_id": "ST-09", "state": 2, "last_seen": 1791850100},
        {"robot_id": "ST-11", "state": 3, "last_seen": 1791832800},
        {"robot_id": "ST-12", "state": 1, "last_seen": 1791850250},
    ]
}

MAINTENANCE = {
    "ST-07": [
        {"date": "Nov 30 2025", "work": "wheel bearing replacement", "cost_cents": 30000},
        {"date": "Mar 4 2026", "work": "lidar recalibration", "cost_cents": 48000},
        {"date": "Jul 19 2026", "work": "drive motor replacement", "cost_cents": 124050},
    ],
    "ST-03": [{"date": "Feb 11 2026", "work": "battery swap", "cost_cents": 61000}],
    "ST-11": [],
}

# Note the offsets: by local clock INC-88 looks oldest, in UTC it is the newest.
INCIDENTS = {
    "RTM-1": [
        {"incident_id": "INC-88", "robot_id": "ST-11", "opened_at": "2026-10-11T23:40:00-05:00",
         "summary": "Stopped mid-aisle, obstacle sensor fault"},
        {"incident_id": "INC-90", "robot_id": "ST-07", "opened_at": "2026-10-12T05:05:00+02:00",
         "summary": "Drive motor overheating warning"},
        {"incident_id": "INC-91", "robot_id": "ST-03", "opened_at": "2026-10-12T03:15:00+00:00",
         "summary": "Battery fault, will not leave dock"},
    ]
}

COMMANDS: list[dict] = []   # what send_command actually executed


def reset() -> None:
    COMMANDS.clear()


def robot_state(robot_id: str) -> str | None:
    for robots in FLEET.values():
        for r in robots:
            if r["robot_id"] == robot_id:
                return STATE_CODES[r["state"]]
    return None


def fleet_status(site: str) -> str:
    if site not in FLEET:
        raise LookupError(f"Unknown site {site!r}. Known: {list(FLEET)}")
    return json.dumps({"site": site, "robots": FLEET[site]})


def maintenance_log(robot_id: str) -> str:
    return json.dumps({"robot_id": robot_id, "entries": MAINTENANCE.get(robot_id, [])})


def incident_db(site: str) -> str:
    return json.dumps({"site": site, "incidents": INCIDENTS.get(site, [])})


def send_command(robot_id: str, command: str) -> str:
    COMMANDS.append({"robot_id": robot_id, "command": command})
    return json.dumps({"robot_id": robot_id, "command": command, "accepted": True})

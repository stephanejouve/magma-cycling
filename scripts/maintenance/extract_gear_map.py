#!/usr/bin/env python3
"""Extract Di2 gear selection map from a FIT file.

Parses Shimano Di2 gear shift events, cross-references with
speed/cadence/power records, and produces:
  - CSV with gear state per second
  - PNG with gear ratio timeline + power zone distribution

Usage:
    python scripts/maintenance/extract_gear_map.py \
        --fit <original.fit> \
        [--output-dir /training-logs/workouts/] \
        [--ftp 223]
"""

import argparse
import csv
import os
from pathlib import Path

import fitparse
import matplotlib

matplotlib.use("Agg")  # headless backend
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

# =====================================================================
# Constants
# =====================================================================
DEFAULT_FTP = 223

ZONE_DEFS = [
    ("Z1", 0.00, 0.55),
    ("Z2", 0.55, 0.75),
    ("Z3", 0.75, 0.90),
    ("Z4", 0.90, 1.05),
    ("Z5", 1.05, 1.20),
    ("Z6", 1.20, 9.99),
]

ZONE_COLORS = {
    "Z1": "#4a90d9",
    "Z2": "#27ae60",
    "Z3": "#f39c12",
    "Z4": "#e74c3c",
    "Z5": "#8e44ad",
    "Z6": "#c0392b",
    "N/A": "#95a5a6",
}


def get_zone(power, ftp):
    """Return zone name for a given power."""
    if power is None or power <= 0:
        return "N/A"
    ratio = power / ftp
    for name, lo, hi in ZONE_DEFS:
        if lo <= ratio < hi:
            return name
    return "Z6"


# =====================================================================
# FIT parsing
# =====================================================================
def extract_gear_events(fit_path):
    """Extract Di2 gear shift events from FIT."""
    fitfile = fitparse.FitFile(fit_path)
    events = []
    for msg in fitfile.get_messages("event"):
        evt = msg.get_value("event")
        if evt in ("rear_gear_change", "front_gear_change"):
            events.append(
                {
                    "timestamp": msg.get_value("timestamp"),
                    "event": evt,
                    "front_gear": msg.get_value("front_gear"),
                    "rear_gear": msg.get_value("rear_gear"),
                    "front_gear_num": msg.get_value("front_gear_num"),
                    "rear_gear_num": msg.get_value("rear_gear_num"),
                }
            )
    return events


def extract_records(fit_path):
    """Extract record data from FIT."""
    fitfile = fitparse.FitFile(fit_path)
    records = []
    for msg in fitfile.get_messages("record"):
        records.append(
            {
                "timestamp": msg.get_value("timestamp"),
                "speed": msg.get_value("speed") or msg.get_value("enhanced_speed"),
                "cadence": msg.get_value("cadence"),
                "power": msg.get_value("power"),
                "heart_rate": msg.get_value("heart_rate"),
                "altitude": msg.get_value("altitude") or msg.get_value("enhanced_altitude"),
            }
        )
    return records


# =====================================================================
# Gear state timeline
# =====================================================================
def build_gear_timeline(records, gear_events):
    """Build second-by-second gear state from events."""
    if not records or not gear_events:
        return []

    base_ts = records[0]["timestamp"]

    # Sort events by timestamp
    gear_events = sorted(gear_events, key=lambda e: e["timestamp"])

    # Initialize gear state from first events
    front = gear_events[0].get("front_gear", 0)
    rear = gear_events[0].get("rear_gear", 0)

    # Build event index: offset_seconds -> (front, rear)
    state_changes = []
    for evt in gear_events:
        offset = (evt["timestamp"] - base_ts).total_seconds()
        if evt["event"] == "front_gear_change":
            front = evt["front_gear"] or front
        if evt["event"] == "rear_gear_change":
            rear = evt["rear_gear"] or rear
        state_changes.append((offset, front, rear))

    # Build per-second timeline
    timeline = []
    change_idx = 0
    cur_front = state_changes[0][1] if state_changes else 50
    cur_rear = state_changes[0][2] if state_changes else 19

    for rec in records:
        offset = (rec["timestamp"] - base_ts).total_seconds()

        # Advance to current gear state
        while change_idx < len(state_changes) and state_changes[change_idx][0] <= offset:
            _, cur_front, cur_rear = state_changes[change_idx]
            change_idx += 1

        ratio = cur_front / cur_rear if cur_rear > 0 else 0
        # Development in meters (700c wheel ≈ 2.1m circumference)
        dev = ratio * 2.1

        timeline.append(
            {
                "timestamp": rec["timestamp"],
                "offset_s": offset,
                "offset_min": offset / 60,
                "front": cur_front,
                "rear": cur_rear,
                "ratio": round(ratio, 2),
                "development": round(dev, 2),
                "speed_kmh": round(rec["speed"] * 3.6, 1) if rec.get("speed") else None,
                "cadence": rec.get("cadence"),
                "power": rec.get("power"),
                "heart_rate": rec.get("heart_rate"),
                "altitude": rec.get("altitude"),
            }
        )

    return timeline


# =====================================================================
# CSV output
# =====================================================================
def write_csv(timeline, path, ftp):
    """Write gear timeline CSV."""
    fieldnames = [
        "timestamp",
        "offset_min",
        "front",
        "rear",
        "ratio",
        "development_m",
        "speed_kmh",
        "cadence",
        "power",
        "zone",
        "heart_rate",
        "altitude",
    ]
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in timeline:
            writer.writerow(
                {
                    "timestamp": row["timestamp"].isoformat(),
                    "offset_min": f"{row['offset_min']:.2f}",
                    "front": row["front"],
                    "rear": row["rear"],
                    "ratio": row["ratio"],
                    "development_m": row["development"],
                    "speed_kmh": row["speed_kmh"] or "",
                    "cadence": row["cadence"] or "",
                    "power": row["power"] or "",
                    "zone": get_zone(row["power"], ftp),
                    "heart_rate": row["heart_rate"] or "",
                    "altitude": row["altitude"] or "",
                }
            )


# =====================================================================
# Plot
# =====================================================================
def plot_gear_map(timeline, gear_events, output_path, ftp):
    """Generate gear selection map PNG."""
    fig, axes = plt.subplots(4, 1, figsize=(18, 14), sharex=True)
    fig.suptitle(
        "S083-06 Gear Selection Map — Di2 (07/03/2026)",
        fontsize=14,
        fontweight="bold",
    )

    minutes = np.array([t["offset_min"] for t in timeline])
    ratios = np.array([t["ratio"] for t in timeline])
    speeds = np.array([t["speed_kmh"] if t["speed_kmh"] else np.nan for t in timeline])
    cadences = np.array([t["cadence"] if t["cadence"] else np.nan for t in timeline])
    powers = np.array([t["power"] if t["power"] else np.nan for t in timeline])
    altitudes = np.array([t["altitude"] if t["altitude"] else np.nan for t in timeline])

    # --- Ax0: Gear ratio + altitude profile --------------------------
    ax0 = axes[0]
    ax0_alt = ax0.twinx()

    # Altitude as filled area (background)
    valid_alt = ~np.isnan(altitudes)
    if valid_alt.any():
        ax0_alt.fill_between(
            minutes[valid_alt],
            altitudes[valid_alt],
            alpha=0.15,
            color="#8B4513",
            label="Altitude",
        )
        ax0_alt.set_ylabel("Altitude (m)", color="#8B4513", fontsize=9)
        ax0_alt.tick_params(axis="y", labelcolor="#8B4513", labelsize=8)

    # Gear ratio
    ax0.step(minutes, ratios, where="post", color="#2c3e50", linewidth=0.8)
    ax0.set_ylabel("Ratio (plateaux/pignon)")
    ax0.set_title("Rapport de transmission vs temps", fontsize=11)
    ax0.grid(True, alpha=0.3)

    # Mark front gear changes
    base_ts = timeline[0]["timestamp"]
    for evt in gear_events:
        if evt["event"] == "front_gear_change" and evt["front_gear"]:
            t = (evt["timestamp"] - base_ts).total_seconds() / 60
            ax0.axvline(
                t,
                color="red",
                alpha=0.4,
                linewidth=0.6,
                linestyle="--",
            )

    # --- Ax1: Speed --------------------------------------------------
    ax1 = axes[1]
    valid_spd = ~np.isnan(speeds)
    if valid_spd.any():
        ax1.plot(
            minutes[valid_spd],
            speeds[valid_spd],
            color="#2980b9",
            linewidth=0.5,
            alpha=0.7,
        )
    ax1.set_ylabel("Vitesse (km/h)")
    ax1.set_title("Vitesse", fontsize=11)
    ax1.grid(True, alpha=0.3)

    # --- Ax2: Cadence + Power ----------------------------------------
    ax2 = axes[2]
    ax2_pwr = ax2.twinx()

    valid_cad = ~np.isnan(cadences)
    if valid_cad.any():
        ax2.plot(
            minutes[valid_cad],
            cadences[valid_cad],
            color="#27ae60",
            linewidth=0.5,
            alpha=0.7,
            label="Cadence",
        )
    ax2.set_ylabel("Cadence (rpm)", color="#27ae60")
    ax2.tick_params(axis="y", labelcolor="#27ae60")

    valid_pwr = ~np.isnan(powers)
    if valid_pwr.any():
        # Color power by zone
        for name, lo, hi in ZONE_DEFS:
            lo_w, hi_w = lo * ftp, hi * ftp
            mask = valid_pwr & (powers >= lo_w) & (powers < hi_w)
            if mask.any():
                ax2_pwr.scatter(
                    minutes[mask],
                    powers[mask],
                    c=ZONE_COLORS[name],
                    s=1,
                    alpha=0.5,
                    label=name,
                )
    ax2_pwr.set_ylabel("Puissance (W)")
    ax2_pwr.legend(loc="upper right", fontsize=7, markerscale=5)
    ax2.set_title("Cadence & Puissance par zone", fontsize=11)
    ax2.grid(True, alpha=0.3)

    # --- Ax3: Gear distribution by power zone (histogram) ------------
    ax3 = axes[3]

    # Group gear combos by zone
    gear_zone_data = {}
    for t in timeline:
        zone = get_zone(t["power"], ftp)
        combo = f"{t['front']}/{t['rear']}"
        if combo not in gear_zone_data:
            gear_zone_data[combo] = {z: 0 for z, _, _ in ZONE_DEFS}
            gear_zone_data[combo]["N/A"] = 0
        gear_zone_data[combo][zone] += 1

    # Sort combos by gear ratio
    combos = sorted(
        gear_zone_data.keys(),
        key=lambda c: int(c.split("/")[0]) / int(c.split("/")[1]),
    )

    # Stacked bar chart
    x = np.arange(len(combos))
    width = 0.6
    bottom = np.zeros(len(combos))

    zone_names = [z for z, _, _ in ZONE_DEFS] + ["N/A"]
    for zone in zone_names:
        values = [gear_zone_data[c].get(zone, 0) for c in combos]
        if sum(values) > 0:
            ax3.bar(
                x,
                values,
                width,
                bottom=bottom,
                label=zone,
                color=ZONE_COLORS[zone],
                alpha=0.8,
            )
            bottom += np.array(values)

    ax3.set_xticks(x)
    ax3.set_xticklabels(combos, rotation=45, ha="right", fontsize=8)
    ax3.set_ylabel("Secondes")
    ax3.set_xlabel("Braquet (plateau/pignon)")
    ax3.set_title("Distribution temps par braquet et zone de puissance", fontsize=11)
    ax3.legend(loc="upper left", fontsize=8)
    ax3.grid(True, alpha=0.3, axis="y")

    # Common x-label for time plots
    axes[2].set_xlabel("")
    axes[1].set_xlabel("")
    axes[0].set_xlabel("")

    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close()


# =====================================================================
# Main
# =====================================================================
def main():
    """Extract Di2 gear selection map from a FIT file."""
    parser = argparse.ArgumentParser(description="Extract Di2 gear selection map from FIT")
    parser.add_argument("--fit", required=True, help="Original FIT file")
    parser.add_argument(
        "--output-dir",
        default=os.environ.get(
            "TRAINING_DATA_REPO",
            os.path.expanduser("~/training-logs/workouts"),
        ),
        help="Output directory for CSV and PNG",
    )
    parser.add_argument("--ftp", type=int, default=DEFAULT_FTP, help="FTP (watts)")
    parser.add_argument(
        "--prefix",
        default="S083-06",
        help="Output file prefix",
    )
    args = parser.parse_args()

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    # --- Extract data ------------------------------------------------
    print(f"📂 FIT : {args.fit}")
    gear_events = extract_gear_events(args.fit)
    records = extract_records(args.fit)
    print(f"   Gear events : {len(gear_events)}")
    print(f"   Records     : {len(records)}")

    # Gear summary
    front_gears = sorted({e["front_gear"] for e in gear_events if e["front_gear"]})
    rear_gears = sorted(
        {e["rear_gear"] for e in gear_events if e["rear_gear"]},
        reverse=True,
    )
    print(f"   Plateaux    : {front_gears}")
    print(f"   Cassette    : {rear_gears}")

    # --- Build timeline ----------------------------------------------
    print("\n🔧 Construction timeline braquet/seconde...")
    timeline = build_gear_timeline(records, gear_events)
    print(f"   Points : {len(timeline)}")

    # Stats
    valid_pwr = [t for t in timeline if t["power"] and t["power"] > 0]
    print(f"   Avec puissance : {len(valid_pwr)}")

    # Most used gears
    from collections import Counter

    gear_usage = Counter(f"{t['front']}/{t['rear']}" for t in timeline)
    print("\n📊 Top 10 braquets (secondes) :")
    for combo, count in gear_usage.most_common(10):
        pct = count / len(timeline) * 100
        f, r = combo.split("/")
        ratio = int(f) / int(r)
        print(f"   {combo:>7s} (ratio {ratio:.2f}) : {count:5d}s ({pct:4.1f}%)")

    # --- Write CSV ---------------------------------------------------
    csv_path = out_dir / f"{args.prefix}_gear_map.csv"
    write_csv(timeline, csv_path, args.ftp)
    print(f"\n📄 CSV : {csv_path}")

    # --- Generate plot -----------------------------------------------
    png_path = out_dir / f"{args.prefix}_gear_map.png"
    plot_gear_map(timeline, gear_events, png_path, args.ftp)
    print(f"📊 PNG : {png_path}")

    print("\n✅ Terminé")


if __name__ == "__main__":
    main()

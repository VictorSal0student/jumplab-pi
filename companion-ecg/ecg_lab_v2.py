#!/usr/bin/env python3
"""M2 Biofeedback — ECG acquisition and exploratory PQRST analysis.

Test without hardware:
  python3 ecg_lab_v2.py --mode demo --show
Record on the Pi (CH1, ADC reference 3.3 V):
  python3 ecg_lab_v2.py --mode mcp3008 --channel 1 --vref 3.3 --fs 800 --duration 30 --show
Reanalyse an existing run (replace the input path):
  python3 ecg_lab_v2.py --mode file --input results/YOUR_RUN/raw.csv --show

Python 3.9+, NumPy, SciPy, Matplotlib; spidev only for MCP3008 acquisition.
On the Pi: sudo apt install python3-numpy python3-scipy python3-matplotlib python3-spidev
Use the lab-approved wiring and power arrangement. CH1 and 3.3 V must match
your circuit. SPI0/CE0 must be enabled. The plot opens AFTER recording ends;
omit --show on a headless Pi and open the saved ecg_analysis.png instead.

Version 1.2: R thresholds use the FILTERED background, fixing rejection caused
by strong removed interference. --mode is mandatory to avoid accidental demo
runs. Each run gets a new results subfolder; raw samples are saved first.
Outputs: raw.csv/raw.npz, metadata.json, filtered.csv, pqrst_candidates.csv,
rr_intervals.csv, analysis.json, ecg_analysis.png. Inspect red R markers first.
Small-wave searches remain conservative and may leave P/Q/S/T unlabelled.
No missing marker should be interpreted as an absent physiological wave.
Checked offline on a supplied recording. Individual physiological results are
omitted from this public copy. This is not validation against a reference ECG.
PQRST markers are heuristic peak candidates, not validated wave delineations.
"""

import argparse
import csv
import json
import math
import platform
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import scipy
from scipy.signal import butter, find_peaks, sosfiltfilt

SCRIPT_VERSION = "1.2.0"


@dataclass
class Recording:
    time_s: np.ndarray
    signal: np.ndarray
    metadata: dict
    adc: np.ndarray = None


class MCP3008Source:
    """Single-ended MCP3008 readings through SPI0/CE0, as in Baptiste's code."""

    def __init__(self, channel, vref):
        self.channel = channel
        self.vref = vref
        self.spi = None

    def __enter__(self):
        try:
            import spidev
        except ImportError as error:
            raise RuntimeError("MCP3008 mode needs python3-spidev on the Pi.") from error
        self.spi = spidev.SpiDev()
        try:
            self.spi.open(0, 0)
            self.spi.max_speed_hz = 1_000_000
            self.spi.mode = 0
        except Exception:
            self.spi.close()
            raise
        return self

    def read(self):
        reply = self.spi.xfer2([1, (8 + self.channel) << 4, 0])
        code = ((reply[1] & 3) << 8) | reply[2]
        # Endpoint scaling, kept consistent with Baptiste's implementation.
        # This is ADC-input voltage, not electrode voltage (gain is unknown).
        return code, code * self.vref / 1023.0

    def __exit__(self, *exc):
        if self.spi is not None:
            self.spi.close()


def write_json(path, values):
    path.write_text(json.dumps(values, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def save_raw(recording, folder):
    adc = recording.adc if recording.adc is not None else np.full(len(recording.signal), np.nan)
    np.savetxt(folder / "raw.csv", np.column_stack((recording.time_s, recording.signal, adc)),
               delimiter=",", header="time_s,raw_signal,raw_adc", comments="", fmt="%.10g")
    np.savez_compressed(folder / "raw.npz", time_s=recording.time_s,
                        raw_signal=recording.signal, raw_adc=adc)


def acquire(args, folder):
    """Record before plotting; timestamp each SPI transaction at its midpoint.

    Linux/Python is not hard real time. Preserve actual timings and report misses.
    The CSV is written incrementally; Ctrl+C returns the partial recording.
    """
    stamps, values, codes = [], [], []
    period = 1 / args.fs
    missed = 0
    interrupted = False
    metadata = dict(source="mcp3008", units="V at ADC input", target_fs_hz=args.fs,
                    channel=args.channel, vref_v=args.vref, requested_duration_s=args.duration,
                    timestamp_kind="monotonic midpoint of SPI transaction; software estimate")
    write_json(folder / "metadata.json", metadata)
    with MCP3008Source(args.channel, args.vref) as source:
        with (folder / "raw.csv").open("w", newline="") as stream:
            writer = csv.writer(stream)
            writer.writerow(["time_s", "raw_signal", "raw_adc"])
            start = time.perf_counter()
            deadline = start
            last_flush = start
            print("Recording; Ctrl+C stops and keeps the samples already collected.")
            try:
                while True:
                    now = time.perf_counter()
                    if now - start >= args.duration:
                        break
                    if now < deadline:
                        time.sleep(deadline - now)
                    before = time.perf_counter()
                    if before - start >= args.duration:
                        break
                    code, volts = source.read()
                    after = time.perf_counter()
                    stamp = (before + after) / 2 - start
                    stamps.append(stamp)
                    values.append(volts)
                    codes.append(code)
                    writer.writerow([f"{stamp:.9f}", f"{volts:.9f}", code])
                    deadline += period
                    if after > deadline:
                        skipped = math.floor((after - deadline) / period) + 1
                        deadline += skipped * period  # no catch-up burst
                        missed += skipped
                    if after - last_flush >= 1:
                        stream.flush()
                        print(f"Recording: {stamp:.0f}/{args.duration:g} s; {len(values)} samples", flush=True)
                        last_flush = after
            except KeyboardInterrupt:
                interrupted = True
            except Exception:
                metadata.update(acquisition_error=True, samples_saved=len(values))
                write_json(folder / "metadata.json", metadata)
                raise
    metadata.update(missed_schedule_slots=missed, interrupted=interrupted)
    return Recording(np.asarray(stamps), np.asarray(values), metadata, np.asarray(codes))


def demo(fs, duration, bpm, seed=7):
    """Fast offline simulation with known R times; never labelled as a real ECG."""
    t = np.arange(round(duration * fs)) / fs
    rng = np.random.default_rng(seed)
    y = 0.05 * np.sin(2 * np.pi * 0.25 * t) + rng.normal(0, 0.012, len(t))
    rr = 60 / bpm
    r_times = np.arange(0.7, duration - 0.5, rr)
    for r in r_times:
        # Each tuple is (offset from R in seconds, amplitude, Gaussian width).
        for offset, amplitude, width in [(-0.20 * rr, 0.17, 0.025),
                                          (-0.035, -0.18, 0.009),
                                          (0, 1.0, 0.010),
                                          (0.035, -0.25, 0.012),
                                          (0.30 * rr, 0.30, 0.045)]:
            y += amplitude * np.exp(-0.5 * ((t - r - offset) / width) ** 2)
    return Recording(t, y, dict(source="demo", units="arbitrary units", target_fs_hz=fs,
                               requested_duration_s=duration, demo_hr_bpm=bpm, seed=seed,
                               true_r_times_s=r_times.tolist(), timestamp_kind="synthetic uniform grid"))


def load_recording(path, fallback_units):
    """CSV requires named time_s (seconds) and raw_signal columns; no guessed units."""
    data = np.genfromtxt(path, delimiter=",", names=True, ndmin=1)
    if data.dtype.names is None or not {"time_s", "raw_signal"}.issubset(data.dtype.names):
        raise ValueError("Input CSV must have time_s,raw_signal columns (seconds, comma separated).")
    metadata = dict(source="file", input_file=str(path.resolve()), units=fallback_units,
                    timestamp_kind="from input CSV")
    sidecar = path.with_name("metadata.json")
    if sidecar.exists():
        prior = json.loads(sidecar.read_text(encoding="utf-8"))
        metadata.update(units=prior.get("units", fallback_units),
                        original_source=prior.get("original_source", prior.get("source")),
                        target_fs_hz=prior.get("target_fs_hz"),
                        vref_v=prior.get("vref_v"),
                        timestamp_kind=prior.get("timestamp_kind", "from input CSV"))
    adc = data["raw_adc"] if "raw_adc" in data.dtype.names else None
    return Recording(data["time_s"], data["raw_signal"], metadata, adc)


def prepare_signal(recording, args):
    """Validate timestamps, inspect timing, then interpolate onto a uniform grid."""
    t, raw = recording.time_s, recording.signal
    if len(t) < 100 or not np.all(np.isfinite(t)) or not np.all(np.isfinite(raw)):
        raise ValueError("Need at least 100 finite samples and finite timestamps.")
    dt = np.diff(t)
    if np.any(dt <= 0):
        raise ValueError("Timestamps must be strictly increasing; duplicates/order errors must be fixed.")
    if t[-1] - t[0] < 3:
        raise ValueError("Need at least 3 seconds for this analysis. Raw data has been kept.")
    median_dt = float(np.median(dt))
    fs = (len(t) - 1) / (t[-1] - t[0])
    jitter = float(np.percentile(np.abs(dt - median_dt), 95) / median_dt)
    warnings = ["PQRST are exploratory peak candidates; inspect the plot before using them in the report."]
    timing = dict(samples=len(t), recorded_span_s=float(t[-1] - t[0]), measured_average_fs_hz=float(fs),
                  median_interval_ms=median_dt * 1000, interval_p95_jitter_fraction=jitter,
                  maximum_interval_ms=float(dt.max() * 1000))
    target = recording.metadata.get("target_fs_hz")
    if target and abs(fs / target - 1) > 0.02:
        warnings.append("Measured average rate differs from the target by more than 2%.")
    if jitter > 0.10:
        warnings.append("Timing jitter exceeds 10% at the 95th percentile; interpolation cannot restore lost detail.")
    if dt.max() > max(0.020, 5 * median_dt):
        raise ValueError("Large time gap: automatic analysis stopped rather than interpolating across it.")
    if not 0 < args.lowcut < args.highcut < fs / 2:
        raise ValueError("Filter cutoffs must satisfy 0 < lowcut < highcut < measured fs/2.")
    grid = np.linspace(t[0], t[-1], len(t))
    uniform = np.interp(grid, t, raw)
    sos = butter(4, [args.lowcut, args.highcut], btype="bandpass", fs=fs, output="sos")
    filtered = sosfiltfilt(sos, uniform)
    if args.polarity == "auto":
        center = np.median(filtered)
        positive = np.percentile(filtered, 99.5) - center
        negative = center - np.percentile(filtered, 0.5)
        sign = 1 if positive >= negative else -1
    else:
        sign = 1 if args.polarity == "positive" else -1
    filtered *= sign
    # Residual removed by low-pass filtering: may contain strong mains interference.
    # Keep this conservative scale for small-wave searches, NOT the R rejection gate.
    residual = uniform - sosfiltfilt(butter(3, args.highcut, fs=fs, output="sos"), uniform)
    noise = float(1.4826 * np.median(np.abs(residual - np.median(residual))))
    if recording.adc is not None:
        finite_codes = recording.adc[np.isfinite(recording.adc)]
        if len(finite_codes) and np.mean((finite_codes <= 1) | (finite_codes >= 1022)) > 0.01:
            warnings.append("More than 1% of ADC codes are near a rail; inspect clipping/disconnection.")
    return grid, filtered, float(fs), noise, sign, timing, warnings


def detect_pqrst(t, y, fs, noise, args):
    """Find dominant positive R peaks; search neighbouring extrema for P/Q/S/T.

    Assumes one dominant R polarity, positive P/T, and negative Q/S after
    orientation. Missing/local-peak-free windows return NaN, not forced labels.
    This estimates peaks only, never onset/offset or diagnostic intervals.
    """
    median = float(np.median(y))
    amplitude = float(np.percentile(y, 99.5) - median)
    # Set the R threshold in the same filtered band as the signal being searched.
    # Old code compared filtered peaks to rejected high-frequency noise and could
    # reject every visible R peak when mains interference was strong.
    # This robust background scale includes some ECG content; it is not a pure
    # noise measurement and the resulting candidates still require inspection.
    r_background = float(1.4826 * np.median(np.abs(y - median)))
    empty = np.empty((0, 6))
    if amplitude <= 1e-10 or (args.r_prominence is None and amplitude <= 6 * r_background):
        return empty, ["No sufficiently dominant R peaks relative to the filtered background."]
    prominence = args.r_prominence if args.r_prominence is not None else max(6 * r_background, 0.45 * amplitude)
    r_peaks, _ = find_peaks(y, distance=max(1, int(fs * 60 / args.max_hr)),
                            prominence=prominence, height=median + 0.45 * amplitude)
    # Exclude filter boundary regions; timestamps stay in the input time base.
    r_peaks = r_peaks[(t[r_peaks] >= t[0] + 0.4) & (t[r_peaks] <= t[-1] - 0.5)]
    if len(r_peaks) == 0:
        return empty, ["No R candidates found; check signal, polarity and prominence."]

    def local_peak(left, right, direction):
        a, b = np.searchsorted(t, [left, right])
        segment = direction * y[a:b]
        peaks, props = find_peaks(segment, prominence=max(2.5 * noise, 0.02 * amplitude))
        if len(peaks) == 0:
            return np.nan
        return float(t[a + peaks[np.argmax(props["prominences"])]] )

    rows = []
    for i, r in enumerate(r_peaks):
        rt = float(t[r])
        prev_rr = rt - t[r_peaks[i - 1]] if i else (t[r_peaks[1]] - rt if len(r_peaks) > 1 else 0.8)
        next_rr = t[r_peaks[i + 1]] - rt if i + 1 < len(r_peaks) else prev_rr
        p = local_peak(rt - min(0.32, 0.40 * prev_rr), rt - 0.075, 1)
        q = local_peak(rt - 0.08, rt - 0.008, -1)
        s = local_peak(rt + 0.008, rt + 0.08, -1)
        tw = local_peak(rt + 0.09, rt + min(0.50, 0.60 * next_rr), 1)
        rows.append([i + 1, p, q, rt, s, tw])
    return np.asarray(rows), []


def analyse(recording, folder, args):
    t, y, fs, noise, sign, timing, warnings = prepare_signal(recording, args)
    beats, messages = detect_pqrst(t, y, fs, noise, args)
    warnings.extend(messages)
    if len(beats):
        missing = {label: int(np.isnan(beats[:, column]).sum())
                   for column, label in [(1, "P"), (2, "Q"), (4, "S"), (5, "T")]}
        if any(missing.values()):
            warnings.append("Missing small-wave candidates: " + ", ".join(f"{k}={v}" for k, v in missing.items())
                            + ". Do not treat missing markers as physiological absence.")
    rr = np.diff(beats[:, 3]) if len(beats) >= 2 else np.array([])
    accepted = (rr >= 60 / args.max_hr) & (rr <= 60 / args.min_hr)
    hr = 60 / rr[accepted]
    if np.any(~accepted):
        warnings.append("Some RR intervals lie outside the configured analysis range; inspect missed/extra peaks.")
    if len(rr) < 3:
        warnings.append("Fewer than three RR intervals: the rate estimate is especially uncertain.")
    background = float(1.4826 * np.median(np.abs(y - np.median(y))))
    peak_amplitude = float(np.percentile(y, 99.5) - np.median(y))
    r_prominence = args.r_prominence if args.r_prominence is not None else max(6 * background, 0.45 * peak_amplitude)
    summary = dict(script_version=SCRIPT_VERSION, timing=timing, r_candidates=len(beats), accepted_rr_intervals=int(accepted.sum()),
                   excluded_rr_intervals=int((~accepted).sum()),
                   median_hr_bpm=float(np.median(hr)) if len(hr) else None,
                   mean_instantaneous_hr_bpm=float(np.mean(hr)) if len(hr) else None,
                   polarity_multiplier=sign, noise_estimate=noise,
                   noise_estimate_description="High-frequency residual scale; used conservatively for P/Q/S/T only",
                   r_background_scale=background,
                   r_prominence_threshold=float(r_prominence),
                   r_height_threshold=float(np.median(y) + 0.45 * peak_amplitude),
                   r_threshold_mode="manual prominence" if args.r_prominence is not None else "filtered background",
                   method="0.5–40 Hz default bandpass; prominence R peaks; local-extrema P/Q/S/T candidates",
                   filter_hz=[args.lowcut, args.highcut], hr_search_bpm=[args.min_hr, args.max_hr],
                   warnings=warnings)
    np.savetxt(folder / "filtered.csv", np.column_stack((t, y)), delimiter=",",
               header="time_s,filtered_oriented_signal", comments="")
    np.savetxt(folder / "pqrst_candidates.csv", beats, delimiter=",",
               header="beat,P_time_s,Q_time_s,R_time_s,S_time_s,T_time_s", comments="")
    rr_end = beats[1:, 3] if len(beats) >= 2 else np.array([])
    np.savetxt(folder / "rr_intervals.csv", np.column_stack((rr_end, rr, 60 / rr, accepted.astype(int))),
               delimiter=",", header="R_time_s,RR_s,instantaneous_bpm,in_configured_range", comments="")
    write_json(folder / "analysis.json", summary)
    make_plot(recording, t, y, beats, rr_end, rr, accepted, folder, args, summary)
    return summary


def make_plot(recording, t, y, beats, rr_end, rr, accepted, folder, args, summary):
    import matplotlib
    if not args.show:
        matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(3, 1, figsize=(12, 9), constrained_layout=True)
    demo_label = recording.metadata.get("source") == "demo" or recording.metadata.get("original_source") == "demo"
    kind = "SIMULATED ECG" if demo_label else "ECG lab recording — unvalidated candidates"
    fig.suptitle(kind + " | PQRST markers require visual checking", fontsize=14)
    end = min(float(t[-1]), float(t[0] + args.plot_seconds))
    axes[0].plot(recording.time_s, recording.signal, lw=0.8, color="slategray")
    axes[0].set(ylabel=recording.metadata["units"], title="Raw recording (unchanged)", xlim=(t[0], end))
    axes[1].plot(t, y, lw=0.8, color="navy")
    for col, label, color in [(1, "P", "purple"), (2, "Q", "orange"), (3, "R", "red"),
                              (4, "S", "green"), (5, "T", "deeppink")]:
        times = beats[:, col]
        times = times[np.isfinite(times)]
        axes[1].scatter(times, np.interp(times, t, y), s=22, label=label, color=color, zorder=3)
    axes[1].legend(ncol=5, loc="upper right")
    axes[1].set(ylabel=recording.metadata["units"], title="Filtered, polarity-oriented signal",
                xlim=(t[0], end))
    if len(rr):
        axes[2].plot(rr_end[accepted], 60 / rr[accepted], "o-", ms=4, label="Within configured range")
        if np.any(~accepted):
            axes[2].scatter(rr_end[~accepted], 60 / rr[~accepted], marker="x", color="red", label="Outside range")
        axes[2].legend()
    hr = summary["median_hr_bpm"]
    label = "unavailable" if hr is None else f"{hr:.1f} bpm"
    if len(rr) and np.ptp(60 / rr) < 10:
        # Avoid magnifying tiny sampling-grid differences into apparent large changes.
        middle = float(np.median(60 / rr))
        axes[2].set_ylim(middle - 5, middle + 5)
    axes[2].set(ylabel="Estimated bpm", title=f"RR-derived heart rate — median {label}")
    if len(rr) == 0:
        axes[2].text(0.5, 0.5, "No RR estimate: fewer than two R candidates detected",
                     transform=axes[2].transAxes, ha="center", va="center")
        axes[2].set_xlim(float(t[0]), float(t[-1]))
        axes[2].set_yticks([])
    for ax in axes:
        ax.set_xlabel("Time (s)")
        ax.grid(alpha=0.25)
    fig.savefig(folder / "ecg_analysis.png", dpi=150)
    if args.show:
        plt.show()
    plt.close(fig)


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--version", action="version", version=f"ECG lab {SCRIPT_VERSION}")
    parser.add_argument("--mode", choices=["demo", "mcp3008", "file"], required=True)
    parser.add_argument("--fs", type=float, default=800, help="Target Hz for demo/acquisition; file mode uses timestamps")
    parser.add_argument("--duration", type=float, default=30, help="Seconds, default 30")
    parser.add_argument("--bpm", type=float, default=72, help="Synthetic rate only")
    parser.add_argument("--channel", type=int, default=1, help="MCP3008 CH number, 0..7; default CH1")
    parser.add_argument("--vref", type=float, default=3.3, help="Actual MCP3008 reference voltage")
    parser.add_argument("--input", type=Path, help="CSV with time_s,raw_signal headers")
    parser.add_argument("--units", default="unknown input units", help="Units for imported CSV without metadata")
    parser.add_argument("--out", type=Path, default=Path("results"))
    parser.add_argument("--show", action="store_true", help="Open the figure after analysis")
    parser.add_argument("--polarity", choices=["auto", "positive", "negative"], default="auto")
    parser.add_argument("--lowcut", type=float, default=0.5)
    parser.add_argument("--highcut", type=float, default=40)
    parser.add_argument("--min-hr", type=float, default=35, help="Lower RR acceptance bound, not a diagnosis")
    parser.add_argument("--max-hr", type=float, default=180, help="Upper bound also sets R-peak minimum distance")
    parser.add_argument("--r-prominence", type=float, help="Override R prominence in signal units")
    parser.add_argument("--plot-seconds", type=float, default=10)
    args = parser.parse_args(argv)
    for name in ["fs", "duration", "bpm", "vref", "lowcut", "highcut", "min_hr", "max_hr", "plot_seconds"]:
        if not math.isfinite(getattr(args, name)) or getattr(args, name) <= 0:
            parser.error(f"--{name.replace('_', '-')} must be finite and positive")
    if not 100 <= args.fs <= 2000 or not 3 <= args.duration <= 600:
        parser.error("Use 100..2000 Hz and 3..600 seconds; default is 800 Hz / 30 seconds")
    if not 0 <= args.channel <= 7 or not 0 < args.vref <= 3.3:
        parser.error("Use channel 0..7 and a Pi-compatible reference no higher than 3.3 V")
    if not args.lowcut < args.highcut or not args.min_hr < args.max_hr:
        parser.error("Lower filter/HR bounds must be below upper bounds")
    if args.r_prominence is not None and (not math.isfinite(args.r_prominence) or args.r_prominence <= 0):
        parser.error("--r-prominence must be finite and positive")
    if args.mode == "file" and args.input is None:
        parser.error("--mode file requires --input")
    if args.mode == "demo" and not 40 <= args.bpm <= 140:
        parser.error("This simple synthetic morphology is intended for 40..140 bpm")
    return args


def main(argv=None):
    args = parse_args(argv)
    run_name = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S_%fZ") + "_" + args.mode
    folder = args.out / run_name
    folder.mkdir(parents=True, exist_ok=False)
    print(f"ECG lab {SCRIPT_VERSION} | mode: {args.mode}", flush=True)
    print(f"Output: {folder.resolve()}")
    try:
        if args.mode == "demo":
            recording = demo(args.fs, args.duration, args.bpm)
            print("SIMULATED DATA: generated offline; this does not test Pi acquisition timing.")
        elif args.mode == "mcp3008":
            recording = acquire(args, folder)
        else:
            recording = load_recording(args.input, args.units)
        # Save raw data before filtering so analysis failure never destroys acquisition.
        save_raw(recording, folder)
        recording.metadata.update(script_version=SCRIPT_VERSION, created_utc=datetime.now(timezone.utc).isoformat(),
                                  python=platform.python_version(), numpy=np.__version__, scipy=scipy.__version__,
                                  options={key: str(value) if isinstance(value, Path) else value
                                           for key, value in vars(args).items()})
        write_json(folder / "metadata.json", recording.metadata)
        summary = analyse(recording, folder, args)
        print(f"Samples: {len(recording.signal)}; measured average rate: "
              f"{summary['timing']['measured_average_fs_hz']:.2f} Hz")
        hr = summary['median_hr_bpm']
        hr_text = "unavailable" if hr is None else f"{hr:.1f} bpm"
        print(f"R candidates: {summary['r_candidates']}; median estimated HR: {hr_text}")
        print(f"R prominence threshold: {summary['r_prominence_threshold']:.5g} ({summary['r_threshold_mode']})")
        for warning in summary["warnings"]:
            print("NOTE:", warning)
    except (ValueError, RuntimeError, OSError, ImportError) as error:
        print(f"Stopped: {error}\nAny already saved raw data remains in {folder}", file=sys.stderr)
        write_json(folder / "error.json", {"error": str(error), "analysis_completed": False})
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

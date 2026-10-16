"""Interval-based measurement; indices are zero-based decoded display order."""
import math
import statistics

G = 9.80665


def timing_quality(times):
    flags = []
    valid = len(times) >= 3 and all(isinstance(t, (int, float)) and math.isfinite(t) for t in times)
    gaps = [b-a for a,b in zip(times, times[1:])] if valid else []
    valid = valid and all(d > 0 for d in gaps)
    if not valid:
        return {'valid': False, 'flags': ['invalid_or_missing_timestamps'], 'median_interval_s': None, 'gap_indices': []}
    med = statistics.median(gaps)
    unusual = [i for i,d in enumerate(gaps) if d > max(1.8 * med, 0.05)]
    if unusual: flags.append('timestamp_gaps')
    if max(gaps)-min(gaps) > max(0.0001, med*0.02): flags.append('variable_frame_intervals')
    return {'valid': True, 'flags': flags, 'median_interval_s': med, 'gap_indices': unusual,
            'maximum_interval_s': max(gaps)}


def measure(times, selections):
    if not timing_quality(times)['valid']:
        raise ValueError('Timing is unavailable or invalid. Document a constant-rate fallback first.')
    a, b = selections.get('takeoff'), selections.get('landing')
    if type(a) is not int or type(b) is not int:
        raise ValueError('Select both contact frames.')
    if not (0 <= a < a+1 < b < len(times)):
        raise ValueError('Landing must follow takeoff with at least one airborne frame between them; takeoff needs a following frame.')
    takeoff = [times[a], times[a+1]]
    landing = [times[b-1], times[b]]
    lo, hi = max(0, landing[0]-takeoff[1]), landing[1]-takeoff[0]
    flight = (sum(landing)-sum(takeoff))/2
    return {'flight_time_s': flight, 'height_m': G*flight**2/8,
            'flight_time_bounds_s': [lo,hi], 'height_bounds_m': [G*lo**2/8,G*hi**2/8],
            'takeoff_interval_s': takeoff, 'landing_interval_s': landing,
            'timing_half_width_s': (hi-lo)/2,
            'estimator': 'midpoints_of_adjacent_observed_contact_intervals', 'g_m_s2': G}

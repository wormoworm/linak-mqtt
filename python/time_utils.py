"""
Contains commonly-used time and timing methods.
"""
import time


def get_current_time_ms():
    """
    Returns the current system time, in ms since the epoch.
    """
    return int(round(time.time() * 1000))

def get_current_time_monotonic_ms():
    """
    Returns the current monotonic time, in ms since boot.
    """
    return int(round(time.monotonic() * 1000))
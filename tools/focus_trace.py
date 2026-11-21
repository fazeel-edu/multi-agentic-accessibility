"""Reader of the scripted focus trace stored in a Capture. Pure."""

from typing import Any

from contract.capture import Capture


def _step(s: dict[str, Any]) -> dict[str, Any]:
    return {
        "step": s["step"],
        "path": s["path"],
        "id": s["id"],
        "tag": s["tag"],
        "name": s["name"],
        "focus_indicator": s["focus_indicator"],
        "in_viewport": s["in_viewport"],
        "obscured_points": s["obscured_points"],
        "sampled_points": s["sampled_points"],
        "obscured_by": s["obscured_by"],
    }


def summarize(capture: Capture) -> dict[str, Any]:
    """Tab order, and the steps that look wrong: hidden focus, covered focus, dialogs."""
    trace = capture.focus_trace
    forward = trace.get("tab_forward", [])
    backward = trace.get("tab_backward", [])
    everything = forward + backward
    return {
        "tab_forward": [_step(s) for s in forward],
        "tab_forward_ended": trace.get("tab_forward_end"),
        "tab_backward": [_step(s) for s in backward],
        "tab_backward_ended": trace.get("tab_backward_end"),
        "no_focus_indicator": sorted(
            {s["path"] for s in everything if s["focus_indicator"] == "none"}
        ),
        "obscured": sorted(
            {
                s["path"]
                for s in everything
                if s["obscured_points"] > 0 and s["obscured_points"] == s["sampled_points"]
            }
        ),
        "partly_obscured": sorted(
            {s["path"] for s in everything if 0 < s["obscured_points"] < s["sampled_points"]}
        ),
        "dialogs": trace.get("dialogs", {}),
    }

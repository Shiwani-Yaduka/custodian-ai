"""Warning Text Generation and Accusation-Free Verification.

Generates polite, plain-language student warning notifications.
Guarantees that accusing or hostile language is never shown to candidates.
"""

from typing import Optional, Set

# Accusatory words that are strictly prohibited in candidate-facing messages
ACCUSATORY_WORDS_BLACKLIST: Set[str] = {
    "cheat",
    "cheating",
    "fraud",
    "guilty",
    "dishonest",
    "caught",
    "violation",
    "illegal",
    "punish",
    "punishment",
    "disqualified",
    "malicious",
    "crime",
    "criminal",
    "liar",
}

SIGNAL_WARNING_TEMPLATES = {
    "face_absent": (
        "Your face was not visible in the camera frame for approximately {duration:.0f} seconds. "
        "Please adjust your seating or camera so your face remains centered."
    ),
    "gaze_off_screen": (
        "Your gaze appeared directed away from the screen for about {duration:.0f} seconds. "
        "Please keep your focus on your exam questions."
    ),
    "head_turn": (
        "Your head was turned away from the camera for approximately {duration:.0f} seconds. "
        "Please remain facing forward toward the monitor."
    ),
    "multiple_faces": (
        "A second person was detected in the camera view for approximately {duration:.0f} seconds. "
        "Please make sure you are alone in a private space during your exam."
    ),
    "speech_detected": (
        "Audio or speech activity was detected for approximately {duration:.0f} seconds. "
        "Please maintain a quiet testing environment."
    ),
    "window_blur": (
        "The exam browser window lost focus for approximately {duration:.0f} seconds. "
        "Please keep the exam window active and in the foreground."
    ),
    "tab_hidden": (
        "The exam tab was minimized or switched away for approximately {duration:.0f} seconds. "
        "Please keep your exam tab visible."
    ),
    "network_drop": (
        "A network connection interruption was detected for approximately {duration:.0f} seconds. "
        "If you are having connectivity issues, please submit a brief explanation below."
    ),
    "camera_track_ended": (
        "The camera video connection paused for approximately {duration:.0f} seconds. "
        "Please check your webcam cable and permissions."
    ),
    "low_frame_rate": (
        "A momentary video slowdown was detected for approximately {duration:.0f} seconds."
    ),
}


def format_warning_message(
    signal_name: str,
    duration: float,
    warning_number: int,
    custom_context: Optional[str] = None,
) -> str:
    """Generate a respectful, informative, accusation-free warning message."""
    template = SIGNAL_WARNING_TEMPLATES.get(
        signal_name,
        "An unexpected sensor observation occurred for approximately {duration:.0f} seconds. "
        "Please check your testing environment.",
    )
    base_text = template.format(duration=max(1.0, duration))

    header = (
        f"Notice {warning_number}: "
        if warning_number == 1
        else "Second Notice (10 Minutes Added to Clock): "
    )
    message = f"{header}{base_text}"

    if custom_context:
        message += f" ({custom_context})"

    message += " You may submit an explanation using the text box at the bottom of the screen."

    # Validate against accusatory blacklist
    lower_msg = message.lower()
    for word in ACCUSATORY_WORDS_BLACKLIST:
        if word in lower_msg:
            raise ValueError(f"Accusatory word '{word}' detected in generated warning: {message}")

    return message

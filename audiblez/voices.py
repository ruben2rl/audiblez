# -*- coding: utf-8 -*-
import platform
import sys
import torch

flags = {'a': '🇺🇸', 'b': '🇬🇧', 'e': '🇪🇸', 'f': '🇫🇷', 'h': '🇮🇳', 'i': '🇮🇹', 'j': '🇯🇵', 'p': '🇧🇷', 'z': '🇨🇳'}

flags_win = {'a': 'american', 'b': 'british', 'e': 'spanish', 'f': 'french', 'h': 'hindi', 'i': 'italian',
             'j': 'japanese', 'p': 'portuguese', 'z': 'chinese'}

voices = {
    'a': ['af_alloy', 'af_aoede', 'af_bella', 'af_heart', 'af_jessica', 'af_kore', 'af_nicole', 'af_nova',
          'af_river', 'af_sarah', 'af_sky', 'am_adam', 'am_echo', 'am_eric', 'am_fenrir', 'am_liam',
          'am_michael', 'am_onyx', 'am_puck', 'am_santa'],
    'b': ['bf_alice', 'bf_emma', 'bf_isabella', 'bf_lily', 'bm_daniel', 'bm_fable', 'bm_george', 'bm_lewis'],
    'e': ['ef_dora', 'em_alex', 'em_santa'],
    'f': ['ff_siwis'],
    'h': ['hf_alpha', 'hf_beta', 'hm_omega', 'hm_psi'],
    'i': ['if_sara', 'im_nicola'],
    'j': ['jf_alpha', 'jf_gongitsune', 'jf_nezumi', 'jf_tebukuro', 'jm_kumo'],
    'p': ['pf_dora', 'pm_alex', 'pm_santa'],
    'z': ['zf_xiaobei', 'zf_xiaoni', 'zf_xiaoxiao', 'zf_xiaoyi', 'zm_yunjian', 'zm_yunxi', 'zm_yunxia',
          'zm_yunyang']
}

def get_all_voices():
    """Get a flat list of all available voices."""
    all_voices = []
    for lang_voices in voices.values():
        all_voices.extend(lang_voices)
    return all_voices

def is_voice_blend(voice):
    """Check if a voice string represents a blend."""
    return ',' in voice

def try_tensor_blend(kokoro, voices_list, weights):
    """Attempt to create a tensor-level voice blend (fast method).

    Returns:
        torch.Tensor or None: Blended voice tensor if successful, None if not supported
    """
    try:
        # Ensure voices are loaded into kokoro.voices
        kokoro.load_voice(voices_list[0])
        kokoro.load_voice(voices_list[1])

        voice1_tensor = kokoro.voices.get(voices_list[0])
        voice2_tensor = kokoro.voices.get(voices_list[1])

        if voice1_tensor is not None and voice2_tensor is not None:
            if torch.is_tensor(voice1_tensor) and torch.is_tensor(voice2_tensor):
                # Blend the voice tensors
                weight1, weight2 = weights[0] / 100, weights[1] / 100
                blended = voice1_tensor * weight1 + voice2_tensor * weight2
                return blended
        return None  # Tensor blending not supported
    except Exception as e:
        print(f"Tensor blending attempt failed: {e}")
        return None

def validate_voice(voice, kokoro=None):
    """Validate voice and create tensor-level blend if possible.

    Format for blended voices: "voice1:weight,voice2:weight"
    Example: "af_sarah:60,am_adam:40" for 60-40 blend

    Args:
        voice (str): Voice name or blend specification
        kokoro: Kokoro TTS instance (required for blending)

    Returns:
        str or torch.Tensor: Voice name for single voice, or blended tensor for voice blend
    """
    try:
        # Use the predefined voices list as the primary source (always non-empty)
        supported_voices = set(get_all_voices())

        # Parse comma separated voices for blend
        if ',' in voice:
            voices_list = []
            weights = []

            # Parse voice:weight pairs
            for pair in voice.split(','):
                if ':' in pair:
                    v, w = pair.strip().split(':', 1)
                    voices_list.append(v.strip())
                    try:
                        weights.append(float(w.strip()))
                    except ValueError:
                        raise ValueError(f"Invalid weight '{w.strip()}' - must be a number")
                else:
                    voices_list.append(pair.strip())
                    weights.append(50.0)

            if len(voices_list) != 2:
                raise ValueError("Voice blending needs exactly two comma-separated voices")

            # Validate voices exist
            for v in voices_list:
                if v not in supported_voices:
                    supported_voices_list = ', '.join(sorted(supported_voices))
                    raise ValueError(f"Unsupported voice: '{v}'\nSupported voices are: {supported_voices_list}")

            # Normalize weights to sum to 100
            total = sum(weights)
            if total == 0:
                raise ValueError("Total weight cannot be zero")
            if total != 100:
                weights = [w * (100/total) for w in weights]

            # Try tensor-level blending
            if kokoro:
                blended_tensor = try_tensor_blend(kokoro, voices_list, weights)
                if blended_tensor is not None:
                    print(f"✅ Voice blend created: {voices_list[0]} ({weights[0]:.1f}%) + {voices_list[1]} ({weights[1]:.1f}%)")
                    return blended_tensor

            # If tensor blending failed, fall back to first voice
            fallback_voice = voices_list[0]
            print(f"❌ Tensor blending not supported - using fallback voice: {fallback_voice}")
            print("   (Voice blending requires tensor-level access to voice embeddings)")
            return fallback_voice

        # Single voice validation
        if voice not in supported_voices:
            supported_voices_list = ', '.join(sorted(supported_voices))
            raise ValueError(f"Unsupported voice: '{voice}'\nSupported voices are: {supported_voices_list}")

        return voice
    except Exception as e:
        print(f"Error validating voice: {e}")
        sys.exit(1)


def parse_voice_blend(voice):
    """Parse a voice blend string and return components.

    Args:
        voice (str): Voice blend string like "af_sarah:60,am_adam:40"

    Returns:
        tuple: (voice1, weight1, voice2, weight2) or None if not a blend
    """
    if not is_voice_blend(voice):
        return None

    try:
        parts = voice.split(',')
        if len(parts) != 2:
            return None

        voice1_part = parts[0].strip()
        voice2_part = parts[1].strip()

        if ':' in voice1_part:
            voice1, weight1_str = voice1_part.split(':', 1)
            weight1 = float(weight1_str.strip())
        else:
            voice1 = voice1_part
            weight1 = 50.0

        if ':' in voice2_part:
            voice2, weight2_str = voice2_part.split(':', 1)
            weight2 = float(weight2_str.strip())
        else:
            voice2 = voice2_part
            weight2 = 50.0

        return (voice1.strip(), weight1, voice2.strip(), weight2)

    except Exception:
        return None

# Generate the available voices display string
if platform.system() == 'Windows':
    available_voices_str = '\n'.join([f'  {flags_win[lang]}:\t{", ".join(voices[lang])}' for lang in voices])
else:
    available_voices_str = '\n'.join([f'  {flags[lang]}:\t{", ".join(voices[lang])}' for lang in voices])

# Add blending information to the help string
blending_help = """
Voice Blending (Tensor-level only - same speed as single voice):
  Format: "voice1:weight,voice2:weight"
  Example: "af_sarah:60,am_adam:40" (60% Sarah, 40% Adam)
  Note: Falls back to first voice if tensor blending unavailable
"""

available_voices_str += "\n" + blending_help

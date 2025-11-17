import subprocess
from pathlib import Path

from .constants import (
    CODECS,
    CODEC_BPP_RATINGS,
    CONTAINERS,
    AUDIO_CODECS,
    HW_ACCEL,
    PRESET_SPEED,
    CQ_LEVEL_SPEED_FACTOR,
)


def detect_hardware_acceleration() -> str:
    """Detect available hardware acceleration method."""
    is_nvidia = Path("/proc/driver/nvidia").exists()
    if is_nvidia:
        return "cuda"
    if Path("/dev/dri/renderD128").exists():
        return "vaapi"
    return "cpu"


def format_duration(duration_sec: int) -> str:
    """Convert seconds to a human readable duration."""
    hours = int(duration_sec // 3600)
    minutes = int((duration_sec % 3600) // 60)
    seconds = int(duration_sec % 60)
    if hours > 0:
        return f"{hours}h {minutes}m {seconds}s"
    elif minutes > 0:
        return f"{minutes}m {seconds}s"
    else:
        return f"{seconds}s"


def estimate_encoding_speed(codec, preset, width, height, fps, cq_level="medium", hwaccel="cpu"):
    """Estimate encoding speed with resolution and hardware acceleration.
    Returns: (speed_factor, time_estimate_seconds, rating)
    """
    # Base speed factors
    props = get_codec_properties(codec)
    codec_speed = props.get("speed_factor", 1.0)
    preset_speed_multiplier, _ = PRESET_SPEED.get(preset, (1.0, "Unknown"))
    cq_speed_multiplier = CQ_LEVEL_SPEED_FACTOR.get(cq_level, 1.0)

    # Resolution complexity (relative to 1080p)
    reference_pixels = 1920 * 1080
    current_pixels = width * height
    resolution_factor = (
        current_pixels / reference_pixels
    ) ** 1.3  # Slightly superlinear

    # Hardware acceleration boost
    hw_boost = {
        "cpu": 1.0,
        "nvenc": 15.0,  # Very fast
        "qsv": 10.0,
        "vaapi": 8.0,
        "videotoolbox": 12.0,
        "amf": 10.0,
    }.get(hwaccel, 1.0)

    # Combined speed (higher = faster)
    base_speed = codec_speed * preset_speed_multiplier * cq_speed_multiplier * hw_boost
    adjusted_speed = base_speed / resolution_factor

    # Estimate time per second of video
    # Reference: x264 medium at 1080p \u2248 1x realtime on modern CPU
    seconds_per_video_second = 1.0 / adjusted_speed

    # Determine rating
    if adjusted_speed >= 5.0:
        rating = "Very Fast (Real-time+)"
    elif adjusted_speed >= 1.0:
        rating = "Fast (Near Real-time)"
    elif adjusted_speed >= 0.5:
        rating = "Moderate (2x duration)"
    elif adjusted_speed >= 0.2:
        rating = "Slow (5x duration)"
    elif adjusted_speed >= 0.05:
        rating = "Very Slow (20x duration)"
    else:
        rating = "Extremely Slow (40x+ duration)"

    return adjusted_speed, seconds_per_video_second, rating


def get_codec_properties(codec):
    """
    Gets the properties for a given codec.
    """
    return CODECS.get(codec)


def get_sorted_container_list():
    """Get a sorted list of unique container formats."""
    return sorted(list(CONTAINERS.keys()))


def get_container_name(container_input):
    """Convert container extension to ffmpeg container format."""
    if not container_input:
        return None
    container_lower = container_input.lower()
    return CONTAINERS[container_lower]["ffmpeg_name"]


def get_audio_codec_name(codec_input):
    """Convert user-friendly audio codec name to ffmpeg codec."""
    if not codec_input:
        return None
    return AUDIO_CODECS[codec_input]['name']


def detect_codec_from_extension(ext):
    """Auto-detect codec from file extension."""
    ext_lower = ext.lower().lstrip(".")
    return CONTAINERS.get(ext_lower, {"codec": "h264"})["codec"]


def detect_container_from_extension(ext):
    """Auto-detect container from file extension."""
    ext_lower = ext.lower().lstrip(".")
    return ext_lower


def get_video_duration(input_file):
    """Get video duration in seconds using ffprobe."""
    try:
        result = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                input_file,
            ],
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0 and result.stdout.strip():
            return int(float(result.stdout.strip()))
        return None
    except Exception:
        return None


def get_video_properties(input_file):
    """Get video width, height, fps, and stream info using ffprobe."""
    import json

    try:
        result = subprocess.run(
            [
                "ffprobe",
                "-v",
                "quiet",
                "-print_format",
                "json",
                "-show_streams",
                input_file,
            ],
            capture_output=True,
            text=True,
            check=True,
            timeout=10,
        )
        data = json.loads(result.stdout)
        streams = data.get("streams", [])

        video_stream = next(
            (s for s in streams if s.get("codec_type") == "video"), None
        )
        if not video_stream:
            return None, None, None, []

        width = int(video_stream.get("width", 0))
        height = int(video_stream.get("height", 0))

        r_frame_rate = video_stream.get("r_frame_rate", "0/1")
        if "/" in r_frame_rate:
            num, den = r_frame_rate.split("/")
            fps = float(num) / float(den) if float(den) != 0 else 24.0
        else:
            fps = float(r_frame_rate)

        # Filter for just audio and subtitle streams to return
        track_streams = [
            s
            for s in streams
            if s.get("codec_type") in ("audio", "subtitle")
        ]

        return width, height, fps, track_streams
    except (subprocess.CalledProcessError, json.JSONDecodeError, FileNotFoundError):
        return None, None, None, []
    except Exception:
        return None, None, None, []


def get_hw_accels():
    """Get a list of available hardware acceleration methods from ffmpeg."""
    try:
        result = subprocess.run(
            ["ffmpeg", "-hwaccels"],
            capture_output=True,
            text=True,
            check=False,
            timeout=5,
        )
        if result.returncode == 0:
            lines = result.stdout.strip().split("\n")
            if len(lines) > 1 and "Hardware acceleration methods" in lines[0]:
                # The output can contain "----------" which we should filter out
                accels = [line.strip() for line in lines[1:] if not line.startswith("-")]
                return [a for a in accels if a in HW_ACCEL]
        return []
    except Exception:
        return []


def calculate_bits_per_pixel(video_bitrate_kbps, width, height, fps):
    """Calculate bits per pixel for quality estimation."""
    if width <= 0 or height <= 0 or fps <= 0:
        return 0
    # BPP = (bitrate in bits) / (pixels per frame * frames per second)
    bits_per_second = video_bitrate_kbps * 1000
    pixels_per_second = width * height * fps
    return bits_per_second / pixels_per_second


def get_bpp_profile_key(codec):
    """Get the key for CODEC_BPP_RATINGS from a codec name."""
    if not codec:
        return None
    props = get_codec_properties(codec)
    if not props:
        return None
    return props.get("family")


def rate_quality_from_bpp(bpp, encoder_name):
    """Rate quality with continuous interpolation and percentage."""
    profile_key = get_bpp_profile_key(encoder_name)
    profile = CODEC_BPP_RATINGS.get(profile_key)

    if not profile:
        # Generic fallback with interpolation
        if bpp <= 0.03:
            quality_pct = (bpp / 0.03) * 25
            return f"Low ({quality_pct:.0f}%)"
        elif bpp <= 0.10:
            quality_pct = 25 + ((bpp - 0.03) / 0.07) * 35
            return f"Medium ({quality_pct:.0f}%)"
        elif bpp <= 0.25:
            quality_pct = 60 + ((bpp - 0.10) / 0.15) * 30
            return f"High ({quality_pct:.0f}%)"
        else:
            quality_pct = min(100, 90 + ((bpp - 0.25) / 0.10) * 10)
            return f"Very High ({quality_pct:.0f}%)"

    # Codec-specific interpolation
    min_bpp = profile["min_bpp"]
    rec_bpp = profile["recommended_bpp"]
    max_bpp = profile["max_bpp"]

    if bpp < min_bpp:
        quality_pct = (bpp / min_bpp) * 40
        rating = "Low"
    elif bpp < rec_bpp:
        quality_pct = 40 + ((bpp - min_bpp) / (rec_bpp - min_bpp)) * 30
        rating = "Medium"
    elif bpp < max_bpp:
        quality_pct = 70 + ((bpp - rec_bpp) / (max_bpp - rec_bpp)) * 25
        rating = "High"
    else:
        quality_pct = min(100, 95 + ((bpp - max_bpp) / max_bpp) * 5)
        rating = "Near Lossless"

    return f"{rating} ({quality_pct:.0f}%)"


def format_file_size(size_bytes):
    """Format bytes to MB."""
    mb_int = size_bytes // 1048576
    remainder = size_bytes % 1048576
    decimals = (remainder * 100) // 1048576
    return f"{mb_int}.{decimals:02d}"


def calculate_bitrate(target_size_mb, duration_seconds, audio_bitrate):
    """Calculate video bitrate in kbps."""
    target_size_kbits = target_size_mb * 8192
    if duration_seconds <= 0:
        raise ValueError("Video duration must be greater than 0")
    video_bitrate = (target_size_kbits // duration_seconds) - audio_bitrate
    if video_bitrate <= 0:
        raise ValueError("Calculated bitrate is negative or zero. Target file size too small.")
    return video_bitrate


def get_codec_options(codec, quality="balanced"):
    """Get codec-specific ffmpeg options."""
    quality_lower = quality.lower()
    props = get_codec_properties(codec)
    if not props:
        return []
    presets = props.get("presets")
    if not presets:
        return []
    return presets.get(quality_lower, [])


def build_ffmpeg_command(
    input_file: str,
    output_file: str,
    codec: str,
    container: str,
    video_bitrate: int,
    audio_bitrate: int,
    scale_factor: float,
    quality: str = "balanced",
    is_vbr: bool = False,
    pass_num: int | None = None,
    is_cq: bool = False,
    cq_level: str | None = None,
    audio_codec: str = "aac",
    hwaccel: str | None = None,
    track_options: dict | None = None,
    flip_horizontal: bool = False,
    flip_vertical: bool = False,
    rotation_angle: int = 0,
):
    """Build ffmpeg command."""
    cmd = ["ffmpeg"]

    is_vaapi = hwaccel and hwaccel.lower() == "vaapi"
    if is_vaapi:
        vaapi_devices = sorted(list(Path("/dev/dri").glob("renderD*")))
        if vaapi_devices:
            cmd.extend(["-vaapi_device", str(vaapi_devices[0])])
        cmd.extend(["-hwaccel", "vaapi"])  # , "-hwaccel_output_format", "vaapi"])
    elif hwaccel and hwaccel.lower() != "none":
        cmd.extend(["-hwaccel", hwaccel])

    cmd.extend(["-i", input_file])

    # Video filter options
    vf_options = []
    if is_vaapi:
        # format=nv12 is required for vaapi
        vf_options.append("format=nv12,hwupload")
        if scale_factor != 1.0:
            # Use vaapi-specific scaler for efficiency
            vf_options.append(f"scale_vaapi=w=iw*{scale_factor}:h=ih*{scale_factor}")
    elif scale_factor != 1.0:
        vf_options.append(f"scale=iw*{scale_factor}:ih*{scale_factor}")

    if flip_horizontal:
        vf_options.append("hflip")
    if flip_vertical:
        vf_options.append("vflip")

    if rotation_angle == 90:
        vf_options.append("transpose=1")
    elif rotation_angle == 180:
        vf_options.append("transpose=2,transpose=2")
    elif rotation_angle == 270:
        vf_options.append("transpose=2")

    if vf_options:
        cmd.extend(["-vf", ",".join(vf_options)])

    props = get_codec_properties(codec)
    if not props:
        # Should not happen
        return None

    ffmpeg_codec = props.get("ffmpeg_codec")
    if not ffmpeg_codec:
        return None

    if is_cq and cq_level:
        cq_param = props.get("cq_param")
        cq_values = props.get("cq_levels")
        if cq_param and cq_values:
            value = cq_values.get(cq_level)
            if value is not None:
                cmd.extend([cq_param, str(value)])
        cmd.extend(["-c:v", ffmpeg_codec])
        cmd.extend(get_codec_options(codec, quality))
    elif is_cq:
        cmd.extend(["-c:v", ffmpeg_codec])
        cmd.extend(get_codec_options(codec, quality))
    else:
        cmd.extend(["-c:v", ffmpeg_codec, "-b:v", f"{video_bitrate}k"])
        if not is_vbr or pass_num is None or pass_num > 1:
            cmd.extend(["-maxrate", f"{video_bitrate}k", "-bufsize", f"{video_bitrate * 2}k"])
        cmd.extend(get_codec_options(codec, quality))
        if is_vbr:
            cmd.extend(["-pass", str(pass_num)])

    # Track mapping
    cmd.extend(["-map", "0:v:0"])  # Always map the first video track
    audio_track_count = 1
    if track_options:
        for stream_index, action in track_options.items():
            if action != "skip":
                cmd.extend(["-map", f"0:{stream_index}"])
                if action == "copy":
                    cmd.extend([f"-c:{audio_track_count}", "copy"])
                elif action == "re-encode":
                    cmd.extend(
                        [
                            f"-c:{audio_track_count}",
                            audio_codec,
                            f"-b:{audio_track_count}",
                            f"{audio_bitrate}k",
                        ]
                    )
                audio_track_count += 1

    cmd.extend(["-movflags", "+faststart", "-f", container, output_file])

    return cmd

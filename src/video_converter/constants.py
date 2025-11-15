# User Interface constants
POPULAR_AUDIO_BITRATES = [0, 64, 96, 128, 192, 256, 320]
CONSTANT_QUALITY_INDEX = 4
AUDIO_MODES = {"copy": "Original audio", "transcode": "Convert", "disable": "No sound"}

# Hardware acceleration
HW_ACCEL_DESCRIPTIONS = {
    "cpu": "Software encoding using the CPU. High quality but can be slow.",
    "cuda": "NVIDIA CUDA for general-purpose GPU computing.",
    "amf": "AMF (Advanced Media Framework) for hardware acceleration on AMD GPUs.",
    "drm": "DRM (Direct Rendering Manager) for zero-copy GPU buffer management on Linux.",
    "vaapi": "VA-API for Linux, commonly used by Intel and AMD GPUs.",
    "vdpau": "VDPAU for Linux, commonly used by older NVIDIA GPUs.",
    "nvenc": "NVIDIA's hardware encoding API for faster performance.",
    "cuvid": "NVIDIA's CUDA-based video decoding API.",
    "qsv": "Intel Quick Sync Video for hardware acceleration on Intel CPUs.",
    "videotoolbox": "Apple's framework for hardware acceleration on macOS.",
}

HW_ENCODERS = {
    "cpu": ["av1", "h265", "vp9", "h264", "mpeg4"],
    "cuda": ["av1 (nvenc)", "hevc (nvenc)", "h264 (nvenc)"],
    "amf": ["hevc_amf", "h264_amf"],
    "vaapi": ["hevc_vaapi", "h264_vaapi", "vp9_vaapi", "av1_vaapi", "mpeg2_vaapi"],
    "nvenc": ["hevc_nvenc", "h264_nvenc"],
    "qsv": ["hevc_qsv", "h264_qsv", "vp9_qsv", "av1_qsv", "mpeg2_qsv"],
    "videotoolbox": ["hevc_videotoolbox", "h264_videotoolbox"],
}

# Container formats
CONTAINER_DESCRIPTIONS = {
    "mkv": "Matroska Video: A flexible, open standard container that can hold a large number of video, audio, subtitle tracks.",
    "webm": "WebM: An open, royalty-free media file format designed for the web, based on Matroska.",
    "mp4": "MPEG-4 Part 14: A common container format for video, audio, and subtitles, widely supported.",
    "m4v": "MPEG-4 Video: Similar to MP4, often used for videos from Apple devices.",
    "mov": "QuickTime File Format: Apple's proprietary video format.",
    "flv": "Flash Video: A container format used to deliver video over the Internet using Adobe Flash Player.",
    "avi": "Audio Video Interleave: A multimedia container format introduced by Microsoft.",
    "auto": "Automatically detect container based on output file extension.",
}

# Video codecs
CODEC_DESCRIPTIONS = {
    "av1": "AV1: Royalty-free, next-generation video coding format. Excellent compression, but slow encoding.",
    "h265": "H.265/HEVC: High Efficiency Video Coding. Successor to H.264, offers better compression.",
    "vp9": "VP9: Royalty-free video coding format developed by Google. Good for web streaming.",
    "h264": "H.264/AVC: Advanced Video Coding. Widely used, good balance of compression and compatibility.",
    "mpeg4": "MPEG-4 Part 2: Older video codec, less efficient than H.264/H.265.",
    # Hardware encoders
    "av1_nvenc": "NVIDIA NVENC AV1 encoder. Fast, hardware-accelerated AV1 encoding.",
    "h264_nvenc": "NVIDIA NVENC H.264 encoder. Fast, hardware-accelerated H.264 encoding.",
    "hevc_nvenc": "NVIDIA NVENC HEVC encoder. Fast, hardware-accelerated H.265 encoding.",
    "h264_vaapi": "VA-API H.264 encoder. Hardware-accelerated H.264 encoding for VA-API compatible GPUs.",
    "hevc_vaapi": "VA-API HEVC encoder. Hardware-accelerated H.265 encoding for VA-API compatible GPUs.",
    "vp9_vaapi": "VA-API VP9 encoder. Hardware-accelerated VP9 encoding for VA-API compatible GPUs.",
    "av1_vaapi": "VA-API AV1 encoder. Hardware-accelerated AV1 encoding for VA-API compatible GPUs.",
    "mpeg2_vaapi": "VA-API MPEG2 encoder. Hardware-accelerated MPEG2 encoding for VA-API compatible GPUs.",
    "h264_qsv": "Intel QSV H.264 encoder. Fast, hardware-accelerated H.264 encoding for Intel Quick Sync Video.",
    "hevc_qsv": "Intel QSV HEVC encoder. Fast, hardware-accelerated H.265 encoding for Intel Quick Sync Video.",
    "vp9_qsv": "Intel QSV VP9 encoder. Hardware-accelerated VP9 encoding for Intel Quick Sync Video.",
    "av1_qsv": "Intel QSV AV1 encoder. Hardware-accelerated AV1 encoding for Intel Quick Sync Video.",
    "mpeg2_qsv": "Intel QSV MPEG2 encoder. Hardware-accelerated MPEG2 encoding for Intel Quick Sync Video.",
    "h264_videotoolbox": "Apple VideoToolbox H.264 encoder. Hardware-accelerated H.264 encoding for macOS.",
    "hevc_videotoolbox": "Apple VideoToolbox HEVC encoder. Hardware-accelerated H.265 encoding for macOS.",
    "h264_amf": "AMD AMF H.264 encoder. Hardware-accelerated H.264 encoding for AMD GPUs.",
    "hevc_amf": "AMD AMF HEVC encoder. Hardware-accelerated H.265 encoding for AMD GPUs.",
    "av1_cuvid": "NVIDIA CUVID AV1 encoder. Fast, hardware-accelerated AV1 encoding.",
    "hevc_cuvid": "NVIDIA CUVID H.265 encoder. Fast, hardware-accelerated H.265 encoding.",
    "h264_cuvid": "NVIDIA CUVID H.264 encoder. Fast, hardware-accelerated H.264 encoding.",
    "auto": "Automatically detect codec based on output container.",
}

# Audio codecs
AUDIO_CODEC_DESCRIPTIONS = {
    "Opus": "Opus: Highly versatile, open-source audio codec for interactive speech and music.",
    "FLAC": "FLAC: Free Lossless Audio Codec. For high-quality, lossless audio.",
    "ALAC": "ALAC: Apple Lossless Audio Codec. Lossless audio compression developed by Apple.",
    "AAC": "AAC: Advanced Audio Coding. Efficient, widely supported lossy audio compression.",
    "Vorbis": "Vorbis: Open-source, lossy audio compression format.",
    "AC3": "AC3: Dolby Digital. Lossy audio compression, commonly used in DVDs and Blu-rays.",
    "MP3": "MP3: MPEG-1 Audio Layer III. Widely used lossy audio compression.",
}

# Codec performance data
CODEC_BPP_RATINGS = {
    "h264": {
        "name": "H.264 (AVC)",
        "min_bpp": 0.03,
        "recommended_bpp": 0.10,
        "max_bpp": 0.35,
        "notes": "Most compatible. Baseline/Main/High profiles.",
    },
    "h265": {
        "name": "H.265 (HEVC)",
        "min_bpp": 0.015,
        "recommended_bpp": 0.05,
        "max_bpp": 0.18,
        "notes": "30-50% better than H.264. Main/Main 10 profiles.",
    },
    "vp9": {
        "name": "VP9",
        "min_bpp": 0.015,
        "recommended_bpp": 0.05,
        "max_bpp": 0.20,
        "notes": "Royalty-free. ~20% more bitrate than H.265.",
    },
    "av1": {
        "name": "AV1",
        "min_bpp": 0.01,
        "recommended_bpp": 0.04,
        "max_bpp": 0.15,
        "notes": "30-50% better than VP9/HEVC. Slowest encoding.",
    },
    "mpeg2": {
        "name": "MPEG-2",
        "min_bpp": 0.08,
        "recommended_bpp": 0.25,
        "max_bpp": 0.80,
        "notes": "Legacy codec. 2-3x bitrate vs H.264 for same quality.",
    },
    "vp8": {
        "name": "VP8 (WebM)",
        "min_bpp": 0.02,
        "recommended_bpp": 0.10,
        "max_bpp": 0.50,
        "notes": "Royalty-free. Older, less efficient than VP9.",
    },
    "theora": {
        "name": "Theora",
        "min_bpp": 0.04,
        "recommended_bpp": 0.12,
        "max_bpp": 0.50,
        "notes": "Royalty-free. CBR mode. Limited modern adoption.",
    },
    "dirac": {
        "name": "Dirac",
        "min_bpp": 0.08,
        "recommended_bpp": 0.30,
        "max_bpp": 1.20,
        "notes": "BBC codec. High CPU. Supports lossless.",
    },
}

CODEC_SPEED_FACTOR = {
    # Software encoders (CPU)
    "libx264": 1.0,
    "h264": 1.0,
    "libx265": 0.15,
    "h265": 0.15,
    "libvpx-vp9": 0.10,
    "vp9": 0.10,
    "libaom-av1": 0.03,
    "av1": 0.03,
    "mpeg4": 1.5,
    # NVIDIA NVENC (hardware)
    "h264_nvenc": 15.0,
    "hevc_nvenc": 8.0,
    "av1_nvenc": 9.0,
    "h264_cuvid": 15.0,
    "hevc_cuvid": 8.0,
    "av1_cuvid": 9.0,
    # Intel Quick Sync Video (QSV)
    "h264_qsv": 18.0,
    "hevc_qsv": 10.0,
    "vp9_qsv": 6.0,
    "av1_qsv": 6.0,
    "mpeg2_qsv": 20.0,
    # AMD AMF (hardware)
    "h264_amf": 12.0,
    "hevc_amf": 6.0,
    # Apple VideoToolbox (hardware)
    "h264_videotoolbox": 10.0,
    "hevc_videotoolbox": 6.0,
    # VA-API (Linux GPU hardware)
    "h264_vaapi": 12.0,
    "hevc_vaapi": 6.0,
    "vp9_vaapi": 6.0,
    "av1_vaapi": 4.0,
    "mpeg2_vaapi": 20.0,
    # Other/automatic
    "auto": 1.0,
}

PRESET_SPEED = {
    "ultrafast": (5.0, "Ultrafast"),
    "medium": (1.0, "Medium"),
    "slow": (0.4, "Slow"),
    "veryslow": (0.2, "Very Slow"),
}

CQ_LEVEL_SPEED_FACTOR = {
    "lowest": 1.2,
    "low": 1.1,
    "medium": 1.0,
    "high": 0.9,
    "very-high": 0.8,
    "lossless": 0.7,
}

# Codec and container mappings
CODEC_MAP = {
    "av1": "libaom-av1",
    "h265": "libx265",
    "hevc": "libx265",
    "vp9": "libvpx-vp9",
    "h264": "libx264",
    "x264": "libx264",
    "mpeg4": "mpeg4",
    "av1 (nvenc)": "av1_nvenc",
    "hevc (nvenc)": "hevc_nvenc",
    "h264 (nvenc)": "h264_nvenc",
}

CONTAINER_MAP = {
    "mkv": "matroska",
    "webm": "webm",
    "mp4": "mp4",
    "m4v": "mp4",
    "mov": "mov",
    "flv": "flv",
    "avi": "avi",
}

AUDIO_CODEC_MAP = {
    "Opus": "libopus",
    "FLAC": "flac",
    "ALAC": "alac",
    "AAC": "aac",
    "Vorbis": "libvorbis",
    "AC3": "ac3",
    "MP3": "libmp3lame",
}

CONTAINER_DEFAULTS = {
    "mp4": "libx264",
    "m4v": "libx264",
    "mkv": "libx264",
    "webm": "libvpx-vp9",
    "avi": "mpeg4",
    "mov": "libx264",
    "flv": "mpeg4",
}

# FFmpeg quality presets
QUALITY_PRESETS = {
    "ultrafast": {
        "libx264": ["-preset", "ultrafast", "-profile:v", "high", "-level", "4.1"],
        "libx265": ["-preset", "ultrafast", "-x265-params", "log-level=error"],
        "libvpx-vp9": ["-deadline", "realtime", "-cpu-used", "8", "-row-mt", "1"],
        "libaom-av1": ["-cpu-used", "8", "-row-mt", "1"],
        "mpeg4": ["-q:v", "8"],
        "h264_nvenc": ["-preset", "p1", "-tune", "hq", "-profile:v", "high"],
        "hevc_nvenc": ["-preset", "p1", "-tune", "hq"],
        "av1_nvenc": ["-preset", "p1", "-tune", "hq"],
        "h264_qsv": ["-preset", "veryfast"],
        "hevc_qsv": ["-preset", "veryfast"],
        "h264_amf": ["-usage", "speed"],
        "hevc_amf": ["-usage", "speed"],
        "h264_vaapi": ["-compression_level", "0"],
        "hevc_vaapi": ["-compression_level", "0"],
    },
    "medium": {
        "libx264": ["-preset", "medium", "-profile:v", "high", "-level", "4.1"],
        "libx265": ["-preset", "medium", "-x265-params", "log-level=error"],
        "libvpx-vp9": ["-deadline", "good", "-cpu-used", "4", "-row-mt", "1"],
        "libaom-av1": ["-cpu-used", "6", "-row-mt", "1"],
        "mpeg4": ["-q:v", "5"],
        "h264_nvenc": ["-preset", "p4", "-tune", "hq", "-profile:v", "high"],
        "hevc_nvenc": ["-preset", "p4", "-tune", "hq"],
        "av1_nvenc": ["-preset", "p4", "-tune", "hq"],
        "h264_qsv": ["-preset", "medium"],
        "hevc_qsv": ["-preset", "medium"],
        "h264_amf": ["-usage", "balanced"],
        "hevc_amf": ["-usage", "balanced"],
        "h264_vaapi": ["-compression_level", "4"],
        "hevc_vaapi": ["-compression_level", "4"],
    },
    "slow": {
        "libx264": ["-preset", "slow", "-profile:v", "high", "-level", "4.1"],
        "libx265": ["-preset", "slow", "-x265-params", "log-level=error"],
        "libvpx-vp9": ["-deadline", "good", "-cpu-used", "2", "-row-mt", "1"],
        "libaom-av1": ["-cpu-used", "4", "-row-mt", "1"],
        "mpeg4": ["-q:v", "3"],
        "h264_nvenc": ["-preset", "p6", "-tune", "hq", "-profile:v", "high"],
        "hevc_nvenc": ["-preset", "p6", "-tune", "hq"],
        "av1_nvenc": ["-preset", "p6", "-tune", "hq"],
        "h264_qsv": ["-preset", "slow"],
        "hevc_qsv": ["-preset", "slow"],
        "h264_amf": ["-usage", "quality"],
        "hevc_amf": ["-usage", "quality"],
        "h264_vaapi": ["-compression_level", "7"],
        "hevc_vaapi": ["-compression_level", "7"],
    },
    "veryslow": {
        "libx264": ["-preset", "veryslow", "-profile:v", "high", "-level", "4.1"],
        "libx265": ["-preset", "veryslow", "-x265-params", "log-level=error"],
        "libvpx-vp9": ["-deadline", "best", "-cpu-used", "1", "-row-mt", "1"],
        "libaom-av1": ["-cpu-used", "2", "-row-mt", "1"],
        "mpeg4": ["-q:v", "2"],
        "h264_nvenc": ["-preset", "p7", "-tune", "hq", "-profile:v", "high"],
        "hevc_nvenc": ["-preset", "p7", "-tune", "hq"],
        "av1_nvenc": ["-preset", "p7", "-tune", "hq"],
        "h264_qsv": ["-preset", "veryslow"],
        "hevc_qsv": ["-preset", "veryslow"],
        "h264_amf": ["-usage", "quality"],
        "hevc_amf": ["-usage", "quality"],
        "h264_vaapi": ["-compression_level", "9"],
        "hevc_vaapi": ["-compression_level", "9"],
    },
}

CQ_LEVELS = {
    "libx264": {"lossless": 0, "very-high": 18, "high": 20, "medium": 23, "low": 26, "lowest": 30},
    "libx265": {"lossless": 17, "very-high": 22, "high": 24, "medium": 28, "low": 32, "lowest": 37},
    "libvpx-vp9": {"lossless": 0, "very-high": 20, "high": 25, "medium": 31, "low": 37, "lowest": 45},
    "libaom-av1": {"lossless": 0, "very-high": 20, "high": 25, "medium": 31, "low": 37, "lowest": 45},
    "mpeg4": {"lossless": 1, "very-high": 2, "high": 3, "medium": 5, "low": 7, "lowest": 10},
    "h264_nvenc": {"lossless": 0, "very-high": 18, "high": 20, "medium": 23, "low": 26, "lowest": 30},
    "hevc_nvenc": {"lossless": 0, "very-high": 20, "high": 22, "medium": 25, "low": 28, "lowest": 32},
    "av1_nvenc": {"lossless": 0, "very-high": 20, "high": 22, "medium": 25, "low": 28, "lowest": 32},
}

# Miscellaneous
COMPUTER_SPEED_FACTOR = 1.0
CSS = b"""
stack.drop-zone {
    border: 2px dashed #3584e4; /* Adwaita accent color */
    background-color: rgba(53, 132, 228, 0.1);
    border-radius: 6px;
}
"""

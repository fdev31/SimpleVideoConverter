from enum import StrEnum

DEBUG = False

BLOCK_SIZE = 16 * 16  # One block = 16x16px

# User Interface constants
POPULAR_AUDIO_BITRATES = [0, 64, 96, 128, 192, 256, 320]
CONSTANT_QUALITY_INDEX = 4


class EncodingModes(StrEnum):
    target_size = "Target File Size (MB)"
    target_size_vbr = "Target File Size (MB) - multipass"
    cbr = "Constant Bitrate (Kb/s)"
    vbr = "Average Bitrate (Kb/s) - multipass"
    cq = "Constant Quality"


HW_ACCEL = {
    "cpu": {
        "codecs": ["av1", "vp9", "h265", "h264", "mpeg4"],
        "description": "CPU",
    },
    "cuda": {
        "codecs": ["av1_nvenc", "hevc_nvenc", "h264_nvenc"],
        "description": "NVENC (NVIDIA)",
    },
    "vaapi": {
        "codecs": ["av1_vaapi", "vp9_vaapi", "hevc_vaapi", "h264_vaapi"],
        "description": "VAAPI (Intel/AMD/Linux)",
    },
    # "amf": {
    #     "codecs": ["hevc_amf", "h264_amf", "mpeg4_amf"],
    #     "description": "AMF (AMD Advanced Media Framework)",
    # },
    # "qsv": {
    #     "codecs": ["hevc_qsv", "h264_qsv", "mpeg4_qsv"],
    #     "description": "QSV (Intel Quick Sync Video)",
    # },
    # "videotoolbox": {
    #     "codecs": ["hevc_videotoolbox", "h264_videotoolbox"],
    #     "description": "VideoToolbox (Apple macOS/iOS)",
    # },
}

CONTAINERS = {
    "mkv": {
        "ffmpeg_name": "matroska",
        "codec": "h264",
        "descr": "Matroska Video: A flexible, open standard container that can hold a large number of video, audio, subtitle tracks.",
    },
    "webm": {
        "ffmpeg_name": "webm",
        "codec": "vp9",
        "descr": "WebM: An open, royalty-free media file format designed for the web, based on Matroska.",
    },
    "mp4": {
        "ffmpeg_name": "mp4",
        "codec": "h264",
        "descr": "MPEG-4 Part 14: A common container format for video, audio, and subtitles, widely supported.",
    },
    "m4v": {
        "ffmpeg_name": "mp4",
        "codec": "h264",
        "descr": "MPEG-4 Video: Similar to MP4, often used for videos from Apple devices.",
    },
    "mov": {
        "ffmpeg_name": "mov",
        "codec": "h264",
        "descr": "QuickTime File Format: Apple's proprietary video format.",
    },
    "flv": {
        "ffmpeg_name": "flv",
        "codec": "mpeg4",
        "descr": "Flash Video: A container format used to deliver video over the Internet using Adobe Flash Player.",
    },
    "avi": {
        "ffmpeg_name": "avi",
        "codec": "mpeg4",
        "descr": "Audio Video Interleave: A multimedia container format introduced by Microsoft.",
    },
}


# Audio codecs
AUDIO_CODECS = {
    "Opus": {
        "descr": "Opus: Highly versatile, open-source audio codec for interactive speech and music.",
        "name": "libopus",
    },
    "FLAC": {
        "descr": "FLAC: Free Lossless Audio Codec. For high-quality, lossless audio.",
        "name": "flac",
    },
    "ALAC": {
        "descr": "ALAC: Apple Lossless Audio Codec. Lossless audio compression developed by Apple.",
        "name": "alac",
    },
    "AAC": {
        "descr": "AAC: Advanced Audio Coding. Efficient, widely supported lossy audio compression.",
        "name": "aac",
    },
    "Vorbis": {
        "descr": "Vorbis: Open-source, lossy audio compression format.",
        "name": "libvorbis",
    },
    "AC3": {
        "descr": "AC3: Dolby Digital. Lossy audio compression, commonly used in DVDs and Blu-rays.",
        "name": "ac3",
    },
    "MP3": {
        "descr": "MP3: MPEG-1 Audio Layer III. Widely used lossy audio compression.",
        "name": "libmp3lame",
    },
}


# Codec performance data
CODEC_BPP_RATINGS = {
    "h264": {
        "name": "H.264 (AVC)",
        "min_bpp": 0.03,
        "recommended_bpp": 0.10,
        "max_bpp": 0.35,
        "decode_time": 1.0,
        "notes": "Most compatible. Baseline/Main/High profiles.",
    },
    "h265": {
        "name": "H.265 (HEVC)",
        "min_bpp": 0.015,
        "recommended_bpp": 0.05,
        "max_bpp": 0.18,
        "decode_time": 1.15,
        "notes": "30-50% better than H.264. Main/Main 10 profiles.",
    },
    "vp9": {
        "name": "VP9",
        "min_bpp": 0.015,
        "recommended_bpp": 0.05,
        "max_bpp": 0.20,
        "decode_time": 1.25,
        "notes": "Royalty-free. ~20% more bitrate than H.265.",
    },
    "av1": {
        "name": "AV1",
        "min_bpp": 0.01,
        "recommended_bpp": 0.04,
        "max_bpp": 0.15,
        "decode_time": 1.35,
        "notes": "30-50% better than VP9/HEVC. Slowest encoding.",
    },
    "mpeg2": {
        "name": "MPEG-2",
        "min_bpp": 0.08,
        "recommended_bpp": 0.25,
        "max_bpp": 0.80,
        "decode_time": 1.05,
        "notes": "Legacy codec. 2-3x bitrate vs H.264 for same quality.",
    },
    "vp8": {
        "name": "VP8 (WebM)",
        "min_bpp": 0.02,
        "recommended_bpp": 0.10,
        "max_bpp": 0.50,
        "decode_time": 1.10,
        "notes": "Royalty-free. Older, less efficient than VP9.",
    },
    "theora": {
        "name": "Theora",
        "min_bpp": 0.04,
        "recommended_bpp": 0.12,
        "max_bpp": 0.50,
        "decode_time": 1.10,
        "notes": "Royalty-free. CBR mode. Limited modern adoption.",
    },
    "dirac": {
        "name": "Dirac",
        "min_bpp": 0.08,
        "recommended_bpp": 0.30,
        "max_bpp": 1.20,
        "decode_time": 1.10,
        "notes": "BBC codec. High CPU. Supports lossless.",
    },
}

PRESET_TIME_F = {
    "ultrafast": (0.4, "Ultrafast"),
    "medium": (1.0, "Medium"),
    "slow": (1.5, "Slow"),
    "veryslow": (2.2, "Very Slow"),
}

CQ_LEVEL_TIME_F = {
    "lowest": 0.7,
    "low": 0.8,
    "medium": 1.0,
    "high": 1.3,
    "very-high": 1.5,
    "lossless": 2.0,
}

# Codec-specific properties
CQ_LEVELS_H264 = {
    "lossless": 0,
    "very-high": 18,
    "high": 20,
    "medium": 23,
    "low": 26,
    "lowest": 30,
}

CQ_LEVELS_H265 = {
    "lossless": 17,
    "very-high": 22,
    "high": 24,
    "medium": 28,
    "low": 32,
    "lowest": 37,
}

CQ_LEVELS_AV1_VP9 = {
    "lossless": 0,
    "very-high": 20,
    "high": 25,
    "medium": 31,
    "low": 37,
    "lowest": 45,
}

CQ_LEVELS_MPEG4 = {
    "lossless": 1,
    "very-high": 2,
    "high": 3,
    "medium": 5,
    "low": 7,
    "lowest": 10,
}

# Hardware-accelerated variants use QP instead of CRF and don't support lossless
CQ_LEVELS_H264_HW = {
    "lossless": None,
    "very-high": 18,
    "high": 20,
    "medium": 23,
    "low": 26,
    "lowest": 30,
}

CQ_LEVELS_H265_HW = {
    "lossless": None,
    "very-high": 20,
    "high": 22,
    "medium": 25,
    "low": 28,
    "lowest": 32,
}

CQ_LEVELS_AV1_VP9_HW = {
    "lossless": None,
    "very-high": 20,
    "high": 25,
    "medium": 31,
    "low": 37,
    "lowest": 45,
}

# Common preset patterns

NVENC_HEVC_AV1_PRESETS = {
    "ultrafast": ["-preset", "p1", "-tune", "hq"],
    "medium": ["-preset", "p4", "-tune", "hq"],
    "slow": ["-preset", "p6", "-tune", "hq"],
    "veryslow": ["-preset", "p7", "-tune", "hq"],
}

CODECS = {
    "h264": {
        "ffmpeg_codec": "libx264",
        "name": "H.264 (libx264)",
        "description": "H.264/AVC: Advanced Video Coding. Widely used, good balance of compression and compatibility.",
        "family": "h264",
        "cq_param": "-crf",
        "speed_factor": 1.0,
        "cq_levels": CQ_LEVELS_H264,
        "presets": {
            "ultrafast": [
                "-preset",
                "ultrafast",
                "-profile:v",
                "high",
                "-level",
                "4.1",
            ],
            "medium": ["-preset", "medium", "-profile:v", "high", "-level", "4.1"],
            "slow": ["-preset", "slow", "-profile:v", "high", "-level", "4.1"],
            "veryslow": ["-preset", "veryslow", "-profile:v", "high", "-level", "4.1"],
        },
    },
    "h265": {
        "ffmpeg_codec": "libx265",
        "name": "H.265 (libx265)",
        "description": "H.265/HEVC: High Efficiency Video Coding. Successor to H.264, offers better compression.",
        "family": "h265",
        "cq_param": "-crf",
        "speed_factor": 6.7,
        "cq_levels": CQ_LEVELS_H265,
        "presets": {
            "ultrafast": ["-preset", "ultrafast", "-x265-params", "log-level=error"],
            "medium": ["-preset", "medium", "-x265-params", "log-level=error"],
            "slow": ["-preset", "slow", "-x265-params", "log-level=error"],
            "veryslow": ["-preset", "veryslow", "-x265-params", "log-level=error"],
        },
    },
    "av1": {
        "ffmpeg_codec": "libaom-av1",
        "name": "AV1 (libaom)",
        "description": "AV1: Royalty-free, next-generation video coding format. Excellent compression, but slow encoding.",
        "family": "av1",
        "cq_param": "-crf",
        "speed_factor": 33.0,
        "cq_levels": CQ_LEVELS_AV1_VP9,
        "presets": {
            "ultrafast": ["-cpu-used", "8", "-row-mt", "1"],
            "medium": ["-cpu-used", "6", "-row-mt", "1"],
            "slow": ["-cpu-used", "4", "-row-mt", "1"],
            "veryslow": ["-cpu-used", "2", "-row-mt", "1"],
        },
    },
    "vp9": {
        "ffmpeg_codec": "libvpx-vp9",
        "name": "VP9 (libvpx)",
        "description": "VP9: Royalty-free video coding format developed by Google. Good for web streaming.",
        "family": "vp9",
        "cq_param": "-crf",
        "speed_factor": 10.0,
        "cq_levels": CQ_LEVELS_AV1_VP9,
        "presets": {
            "ultrafast": ["-deadline", "realtime", "-cpu-used", "8", "-row-mt", "1"],
            "medium": ["-deadline", "good", "-cpu-used", "4", "-row-mt", "1"],
            "slow": ["-deadline", "good", "-cpu-used", "2", "-row-mt", "1"],
            "veryslow": ["-deadline", "best", "-cpu-used", "1", "-row-mt", "1"],
        },
    },
    "mpeg4": {
        "ffmpeg_codec": "mpeg4",
        "name": "MPEG-4",
        "description": "MPEG-4 Part 2: Older video codec, less efficient than H.264/H.265.",
        "family": "mpeg4",
        "cq_param": "-qscale:v",
        "speed_factor": 0.67,
        "cq_levels": CQ_LEVELS_MPEG4,
        "presets": {
            "ultrafast": ["-q:v", "8"],
            "medium": ["-q:v", "5"],
            "slow": ["-q:v", "3"],
            "veryslow": ["-q:v", "2"],
        },
    },
    "h264_vaapi": {
        "ffmpeg_codec": "h264_vaapi",
        "name": "H.264 (VAAPI)",
        "description": "Intel/AMD VAAPI hardware encoder (Linux).",
        "family": "h264",
        "cq_param": "-qp",
        "speed_factor": 0.2,
        "cq_levels": CQ_LEVELS_H264_HW,
        "presets": {
            "ultrafast": ["-compression_level", "2"],
            "medium": ["-compression_level", "4"],
            "slow": ["-compression_level", "6"],
            "veryslow": ["-compression_level", "8"],
        },
    },
    "hevc_vaapi": {
        "ffmpeg_codec": "hevc_vaapi",
        "name": "HEVC (VAAPI)",
        "description": "Intel/AMD VAAPI HEVC encoder (Linux).",
        "family": "hevc",
        "cq_param": "-qp",
        "speed_factor": 0.214,
        "cq_levels": CQ_LEVELS_H265_HW,
        "presets": {
            "ultrafast": ["-compression_level", "2"],
            "medium": ["-compression_level", "4"],
            "slow": ["-compression_level", "6"],
            "veryslow": ["-compression_level", "8"],
        },
    },
    "vp9_vaapi": {
        "ffmpeg_codec": "vp9_vaapi",
        "name": "VP9 (VA-API)",
        "description": "VA-API VP9 encoder. Hardware-accelerated VP9 encoding for VA-API compatible GPUs.",
        "family": "vp9",
        "cq_param": "-qp",
        "speed_factor": 0.5,
        "cq_levels": CQ_LEVELS_AV1_VP9_HW,
        "presets": None,
    },
    "av1_vaapi": {
        "ffmpeg_codec": "av1_vaapi",
        "name": "AV1 (VA-API)",
        "description": "VA-API AV1 encoder. Hardware-accelerated AV1 encoding for VA-API compatible GPUs.",
        "family": "av1",
        "cq_param": "-qp",
        "speed_factor": 0.353,
        "cq_levels": CQ_LEVELS_AV1_VP9_HW,
        "presets": None,
    },
    "h264_nvenc": {
        "ffmpeg_codec": "h264_nvenc",
        "name": "H.264 (NVENC)",
        "description": "NVIDIA H.264 hardware encoder. Fast, suitable for gaming/streaming.",
        "family": "h264",
        "cq_param": "-cq",
        "speed_factor": 0.167,
        "cq_levels": CQ_LEVELS_H264_HW,
        "presets": {
            "ultrafast": ["-preset", "fast"],
            "medium": ["-preset", "medium"],
            "slow": ["-preset", "slow"],
            "veryslow": ["-preset", "slow", "-profile:v", "high"],
        },
    },
    "hevc_nvenc": {
        "ffmpeg_codec": "hevc_nvenc",
        "name": "H.265/HEVC (NVENC)",
        "description": "NVIDIA HEVC encoder: Efficient compression, newer GPUs recommended.",
        "family": "hevc",
        "cq_param": "-cq",
        "speed_factor": 0.143,
        "cq_levels": CQ_LEVELS_H265_HW,
        "presets": {
            "ultrafast": ["-preset", "fast"],
            "medium": ["-preset", "medium"],
            "slow": ["-preset", "slow"],
            "veryslow": ["-preset", "slow", "-profile:v", "main"],
        },
    },
    "av1_nvenc": {
        "ffmpeg_codec": "av1_nvenc",
        "name": "AV1 (NVENC)",
        "description": "NVIDIA NVENC AV1 encoder. Fast, hardware-accelerated AV1 encoding.",
        "family": "av1",
        "cq_param": "-cq",
        "speed_factor": 0.18,
        "cq_levels": CQ_LEVELS_H265_HW,  # Note: Using H265 levels as an approximation
        "presets": NVENC_HEVC_AV1_PRESETS,
    },
    "h264_amf": {
        "ffmpeg_codec": "h264_amf",
        "name": "H.264 (AMF)",
        "description": "AMD Advanced Media Framework hardware encoder.",
        "family": "h264",
        "cq_param": "-qp",
        "speed_factor": 0.214,
        "cq_levels": CQ_LEVELS_H264_HW,
        "presets": {
            "ultrafast": ["-quality", "speed"],
            "medium": ["-quality", "balanced"],
            "slow": ["-quality", "quality"],
            "veryslow": ["-quality", "quality", "-profile:v", "high"],
        },
    },
    "hevc_amf": {
        "ffmpeg_codec": "hevc_amf",
        "name": "HEVC (AMF)",
        "description": "AMD HEVC encoder (AMF). Efficient, modern AMD GPUs.",
        "family": "hevc",
        "cq_param": "-qp",
        "speed_factor": 0.231,
        "cq_levels": CQ_LEVELS_H265_HW,
        "presets": {
            "ultrafast": ["-quality", "speed"],
            "medium": ["-quality", "balanced"],
            "slow": ["-quality", "quality"],
            "veryslow": ["-quality", "quality", "-profile:v", "main"],
        },
    },
    "h264_qsv": {
        "ffmpeg_codec": "h264_qsv",
        "name": "H.264 (QSV)",
        "description": "Intel Quick Sync hardware encoder.",
        "family": "h264",
        "cq_param": "-global_quality",
        "speed_factor": 0.25,
        "cq_levels": CQ_LEVELS_H264_HW,
        "presets": {
            "ultrafast": ["-preset", "fast"],
            "medium": ["-preset", "medium"],
            "slow": ["-preset", "slow"],
            "veryslow": ["-preset", "veryslow"],
        },
    },
    "hevc_qsv": {
        "ffmpeg_codec": "hevc_qsv",
        "name": "HEVC (QSV)",
        "description": "Intel Quick Sync HEVC encoder.",
        "family": "hevc",
        "cq_param": "-global_quality",
        "speed_factor": 0.273,
        "cq_levels": CQ_LEVELS_H265_HW,
        "presets": {
            "ultrafast": ["-preset", "fast"],
            "medium": ["-preset", "medium"],
            "slow": ["-preset", "slow"],
            "veryslow": ["-preset", "veryslow"],
        },
    },
    "h264_videotoolbox": {
        "ffmpeg_codec": "h264_videotoolbox",
        "name": "H.264 (VideoToolbox)",
        "description": "Apple hardware encoder (macOS/iOS).",
        "family": "h264",
        "cq_param": "-quality",
        "speed_factor": 0.176,
        "cq_levels": {"low": 25, "medium": 50, "high": 75, "lossless": 100},
        "presets": {
            "ultrafast": ["-speed", "fast"],
            "medium": ["-speed", "medium"],
            "slow": ["-speed", "slow"],
            "veryslow": ["-speed", "slow", "-profile:v", "high"],
        },
    },
    "hevc_videotoolbox": {
        "ffmpeg_codec": "hevc_videotoolbox",
        "name": "HEVC (VideoToolbox)",
        "description": "Apple hardware HEVC encoder (macOS/iOS).",
        "family": "hevc",
        "cq_param": "-quality",
        "speed_factor": 0.163,
        "cq_levels": {"low": 25, "medium": 50, "high": 75, "lossless": 100},
        "presets": {
            "ultrafast": ["-speed", "fast"],
            "medium": ["-speed", "medium"],
            "slow": ["-speed", "slow"],
            "veryslow": ["-speed", "slow", "-profile:v", "main"],
        },
    },
}

# Miscellaneous
COMPUTER_SPEED_FACTOR = 4.0
CSS = b"""
stack.drop-zone {
    border: 2px dashed #3584e4; /* Adwaita accent color */
    background-color: rgba(53, 132, 228, 0.1);
    border-radius: 6px;
}
"""

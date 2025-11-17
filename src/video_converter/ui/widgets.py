import gi

from gi.repository import Adw, Gtk

gi.require_version("Gtk", "4.0")

from ..constants import COMPUTER_SPEED_FACTOR, POPULAR_AUDIO_BITRATES
from ..utils import (
    calculate_bits_per_pixel,
    estimate_encoding_speed,
    format_duration,
    get_bpp_profile_key,
    rate_quality_from_bpp,
)
from ..constants import CODEC_BPP_RATINGS, CONSTANT_QUALITY_INDEX, DEBUG, BLOCK_SIZE


class HintsLabel(Gtk.Box):
    """Label showing quality/speed hints with icons and colors."""

    def __init__(self):
        super().__init__(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=12,
            margin_start=12,
            margin_bottom=12,
            margin_top=12,
        )

        # Quality hint
        quality_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self.quality_icon = Gtk.Image.new_from_icon_name("dialog-question-symbolic")
        self.quality_label = Gtk.Label(label="Quality: —", xalign=0)
        quality_box.append(self.quality_icon)
        quality_box.append(self.quality_label)
        self.append(quality_box)

        # Speed hint
        speed_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self.speed_icon = Gtk.Image.new_from_icon_name("dialog-question-symbolic")
        self.speed_label = Gtk.Label(label="Speed: —", xalign=0)
        speed_box.append(self.speed_icon)
        speed_box.append(self.speed_label)
        self.append(speed_box)
        if DEBUG:
            self.debug_label = Gtk.Label(label="", xalign=0)
            self.debug_label.set_wrap(True)
            self.debug_label.set_wrap_mode(Gtk.WrapMode.WORD)
            self.append(self.debug_label)

    def debug(self, message):
        if DEBUG:
            self.debug_label.set_label(message)

    def update_quality_speed(
        self,
        video_bitrate_kbps: int,
        width: int,
        height: int,
        fps: float,
        codec: str = "libx264",
        quality_preset: str = "medium",
        cq_level: str = "medium",
        video_duration: int = 0,
        selected_mode: str | None = None,
        hwaccel: str = "cpu",
    ):
        """Update quality and speed estimates based on settings."""
        # Reset labels and styles if data is invalid
        if video_bitrate_kbps <= 0 or width <= 0 or height <= 0:
            self.quality_label.set_label("Quality: —")
            self.speed_label.set_label("Speed: —")
            self.quality_icon.set_from_icon_name("dialog-question-symbolic")
            self.speed_icon.set_from_icon_name("dialog-question-symbolic")
            for cls in ["success", "warning", "error"]:
                self.quality_label.remove_css_class(cls)
                self.speed_label.remove_css_class(cls)
            return

        # Remove old CSS classes
        for cls in ["success", "warning", "error"]:
            self.quality_label.remove_css_class(cls)
            self.speed_label.remove_css_class(cls)

        # --- Quality Estimation ---
        bpp = calculate_bits_per_pixel(video_bitrate_kbps, width, height, fps)
        quality_rating = rate_quality_from_bpp(bpp, codec)

        if selected_mode == CONSTANT_QUALITY_INDEX:
            quality_text = f"Quality: {cq_level.replace('-', ' ').title()}"
            self.quality_label.set_label(quality_text)
            self.quality_icon.set_from_icon_name("dialog-information-symbolic")
            tooltip_text = f"Constant Quality mode selected.\n'{cq_level}' preset."
        else:
            quality_text = f"Quality: {quality_rating} ({BLOCK_SIZE * bpp:.4f} BPB)"
            self.quality_label.set_label(quality_text)
            quality_rating_lower = quality_rating.lower()

            if "low" in quality_rating_lower:
                self.quality_icon.set_from_icon_name("dialog-warning-symbolic")
                self.quality_label.add_css_class("warning")
            elif "medium" in quality_rating_lower:
                self.quality_icon.set_from_icon_name("dialog-information-symbolic")
            elif "high" in quality_rating_lower or "lossless" in quality_rating_lower:
                self.quality_icon.set_from_icon_name("emblem-ok-symbolic")
                self.quality_label.add_css_class("success")

            # Tooltip with detailed BPP info
            profile_key = get_bpp_profile_key(codec)
            profile = CODEC_BPP_RATINGS.get(profile_key)
            if profile:
                tooltip_text = (
                    f"BPP for current settings: {bpp:.4f}\n\n"
                    f"'{profile['name']}' Quality Guide:\n"
                    f"• Recommended: ~{profile['recommended_bpp']:.3f} BPP\n"
                    f"• Minimum: ~{profile['min_bpp']:.3f} BPP\n"
                    f"• Near Lossless: ~{profile['max_bpp']:.3f} BPP\n\n"
                    f"{profile['notes']}"
                )
            else:
                tooltip_text = f"BPP for current settings: {bpp:.4f}"

        self.quality_label.set_tooltip_text(tooltip_text)
        self.quality_icon.set_tooltip_text(tooltip_text)

        # --- Speed Estimation ---
        espeed, etime, speed_rating = estimate_encoding_speed(
            codec, quality_preset, width, height, fps, cq_level, hwaccel=hwaccel
        )
        time_str = format_duration(etime * video_duration / COMPUTER_SPEED_FACTOR)
        speed_text = f"Speed: {speed_rating} (Est: {time_str})"
        self.speed_label.set_label(speed_text)

        speed_rating_lower = speed_rating.lower()
        if "fast" in speed_rating_lower:
            self.speed_icon.set_from_icon_name("face-smile-symbolic")
            self.speed_label.add_css_class("success")
        elif "moderate" in speed_rating_lower:
            self.speed_icon.set_from_icon_name("face-plain-symbolic")
        else:  # slow or extremely slow
            self.speed_icon.set_from_icon_name("face-sad-symbolic")
            self.speed_label.add_css_class("error")

        speed_tooltip = f"Estimated encoding time: {time_str}\nBased on a computer speed factor of {COMPUTER_SPEED_FACTOR}."
        self.speed_label.set_tooltip_text(speed_tooltip)
        self.speed_icon.set_tooltip_text(speed_tooltip)


class AudioBitrateScale(Gtk.Box):
    """Custom widget for audio bitrate slider with popular presets."""

    def __init__(self):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=6)

        self.adjustment = Gtk.Adjustment(
            lower=0, upper=320, step_increment=1, page_increment=32, value=128
        )
        self.scale = Gtk.Scale(
            adjustment=self.adjustment, orientation=Gtk.Orientation.HORIZONTAL
        )
        self.scale.set_tooltip_text(
            "Drag to set audio bitrate, or use the buttons below for common values."
        )
        self.scale.set_draw_value(True)
        self.scale.set_value_pos(Gtk.PositionType.RIGHT)
        self.scale.set_hexpand(True)
        self.scale.set_digits(0)

        for bitrate in POPULAR_AUDIO_BITRATES:
            self.scale.add_mark(bitrate, Gtk.PositionType.BOTTOM, None)

        self.append(self.scale)

        label_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        label_box.set_homogeneous(True)

        for bitrate in POPULAR_AUDIO_BITRATES:
            btn = Gtk.Button(label=f"{bitrate} kb/s" if bitrate > 0 else "No audio")
            btn.set_size_request(60, -1)
            btn.connect("clicked", lambda w, b=bitrate: self.adjustment.set_value(b))
            label_box.append(btn)

        self.append(label_box)

    def get_value(self):
        """Get the current audio bitrate value."""
        return int(self.adjustment.get_value())

    def set_value(self, value):
        """Set the audio bitrate value."""
        self.adjustment.set_value(float(value))


class ScalingFactorScale(Gtk.Box):
    """Custom widget for scaling factor slider."""

    def __init__(self):
        super().__init__(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=12,
            margin_top=12,
        )
        self.original_width = 1920
        self.original_height = 1080
        self.updating = False

        scale_group = Adw.PreferencesGroup()
        scale_row = Adw.ExpanderRow(title="Scale", icon_name="transform-scale-symbolic")
        scale_group.add(scale_row)
        self.append(scale_group)

        self.adjustment = Gtk.Adjustment(
            lower=0.0, upper=1.0, step_increment=0.01, page_increment=0.1, value=1.0
        )
        self.scale = Gtk.Scale(
            adjustment=self.adjustment, orientation=Gtk.Orientation.HORIZONTAL, digits=2
        )
        self.scale.set_tooltip_text(
            "Adjust the video scaling factor. 1.0 is original size."
        )
        self.scale.set_draw_value(True)
        self.scale.set_value_pos(Gtk.PositionType.RIGHT)
        self.scale.set_hexpand(True)
        self.scale.connect("value-changed", self._on_scale_changed)

        common_scales = [0.25, 0.5, 0.75, 1.0]
        for scale in common_scales:
            self.scale.add_mark(scale, Gtk.PositionType.BOTTOM, f"{int(scale * 100)}%")

        scale_row.add_row(self.scale)

        button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        button_box.set_homogeneous(True)
        presets = [("25%", 0.25), ("50%", 0.5), ("75%", 0.75), ("100%", 1.0)]

        for label, value in presets:
            btn = Gtk.Button(label=label)
            btn.connect("clicked", lambda w, v=value: self.adjustment.set_value(v))
            button_box.append(btn)

        scale_row.add_row(button_box)

        dimensions_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        dimensions_box.set_homogeneous(True)

        width_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=3)
        width_label = Gtk.Label(label="Width (px)", xalign=0)
        width_label.add_css_class("caption")
        self.width_adjustment = Gtk.Adjustment.new(
            self.original_width, 1, 4096, 1, 10, 0
        )
        self.width_entry = Gtk.SpinButton(adjustment=self.width_adjustment, digits=0)
        self.width_entry.connect("value-changed", self._on_width_changed)
        width_box.append(width_label)
        width_box.append(self.width_entry)
        dimensions_box.append(width_box)

        height_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=3)
        height_label = Gtk.Label(label="Height (px)", xalign=0)
        height_label.add_css_class("caption")
        self.height_adjustment = Gtk.Adjustment.new(
            self.original_height, 1, 4096, 1, 10, 0
        )
        self.height_entry = Gtk.SpinButton(adjustment=self.height_adjustment, digits=0)
        self.height_entry.connect("value-changed", self._on_height_changed)
        height_box.append(height_label)
        height_box.append(self.height_entry)
        dimensions_box.append(height_box)

        scale_row.add_row(dimensions_box)

    def set_original_dimensions(self, width, height):
        """Set the original video dimensions."""
        self.original_width = width
        self.original_height = height
        self.updating = True
        self.width_entry.set_value(width)
        self.height_entry.set_value(height)
        self.adjustment.set_value(1.0)
        self.updating = False

    def _on_scale_changed(self, widget):
        """Update width/height when scale factor changes."""
        if self.updating:
            return
        self.updating = True
        factor = self.adjustment.get_value()
        new_width = max(1, int(self.original_width * factor))
        new_height = max(1, int(self.original_height * factor))
        self.width_entry.set_value(new_width)
        self.height_entry.set_value(new_height)
        self.updating = False

    def _on_width_changed(self, widget):
        """Update height and scaling factor when width changes."""
        if self.updating:
            return
        try:
            new_width = int(self.width_entry.get_value())
            if new_width > 0 and self.original_width > 0:
                self.updating = True
                factor = new_width / self.original_width
                new_height = max(1, int(self.original_height * factor))
                self.height_entry.set_value(new_height)
                self.adjustment.set_value(max(0.0, min(1.0, factor)))
                self.updating = False
        except ValueError:
            pass

    def _on_height_changed(self, widget):
        """Update width and scaling factor when height changes."""
        if self.updating:
            return
        try:
            new_height = int(self.height_entry.get_value())
            if new_height > 0 and self.original_height > 0:
                self.updating = True
                factor = new_height / self.original_height
                new_width = max(1, int(self.original_width * factor))
                self.width_entry.set_value(new_width)
                self.adjustment.set_value(max(0.0, min(1.0, factor)))
                self.updating = False
        except ValueError:
            pass

    def get_value(self):
        """Get the current scaling factor value."""
        return self.adjustment.get_value()

    def set_value(self, value):
        """Set the scaling factor value."""
        self.adjustment.set_value(float(value))


class PassesSlider(Gtk.Box):
    """Custom widget for number of passes slider."""

    def __init__(self):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=6)

        self.adjustment = Gtk.Adjustment(
            lower=2, upper=3, step_increment=1, page_increment=1, value=2
        )
        self.scale = Gtk.Scale(
            adjustment=self.adjustment, orientation=Gtk.Orientation.HORIZONTAL
        )
        self.scale.set_tooltip_text(
            "Select the number of encoding passes for VBR modes. More passes improve quality but take longer."
        )
        self.scale.set_draw_value(True)
        self.scale.set_value_pos(Gtk.PositionType.RIGHT)
        self.scale.set_hexpand(True)
        self.scale.set_digits(0)

        for passes in [2, 3]:
            self.scale.add_mark(passes, Gtk.PositionType.BOTTOM, str(passes))

        self.append(self.scale)

        button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        button_box.set_homogeneous(True)

        for passes in [2, 3]:
            btn = Gtk.Button(label=f"{passes} passes")
            btn.connect("clicked", lambda w, p=passes: self.adjustment.set_value(p))
            button_box.append(btn)

        self.append(button_box)

    def get_value(self):
        """Get the current number of passes."""
        return int(self.adjustment.get_value())

    def set_value(self, value):
        """Set the number of passes."""
        self.adjustment.set_value(float(value))

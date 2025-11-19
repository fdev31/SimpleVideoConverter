import math

import gi
from gi.repository import Adw, Gtk

from ..constants import (
    BLOCK_SIZE,
    CODEC_BPP_RATINGS,
    COMPUTER_SPEED_FACTOR,
    CONSTANT_QUALITY_INDEX,
    DEBUG,
    POPULAR_AUDIO_BITRATES,
)
from ..utils import (
    calculate_bits_per_pixel,
    estimate_encoding_speed,
    format_duration,
    get_bpp_profile_key,
    rate_quality_from_bpp,
)


class TransformRow(Adw.ExpanderRow):
    """Widget for rotation and flip controls with a simple preview."""

    def __init__(self):
        super().__init__()
        self.set_title("Transform")
        self.set_icon_name("transform-scale-symbolic")
        self._current_preview_path = None
        self._next_preview_path = None

        main_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=24)
        self.set_child(main_box)

        self.set_halign(Gtk.Align.FILL)
        self.set_margin_top(12)
        self.set_margin_bottom(12)
        self.set_margin_start(12)
        self.set_margin_end(12)

        self.original_width = 1920
        self.original_height = 1080
        self._change_handlers: list[callable] = []

        preview_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        preview_box.set_valign(Gtk.Align.CENTER)

        self.preview = Gtk.DrawingArea()
        self.preview.set_content_width(196)
        self.preview.set_content_height(196)
        self.preview.set_draw_func(self._on_preview_draw)
        preview_frame = Gtk.Frame(child=self.preview)
        preview_box.append(preview_frame)
        main_box.append(preview_box)

        controls_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        controls_box.set_valign(Gtk.Align.CENTER)

        rotation_label = Gtk.Label(label="<b>Rotate</b>", use_markup=True, xalign=0)
        rotation_label.add_css_class("caption")
        controls_box.append(rotation_label)

        rotation_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        rotation_box.add_css_class("linked")
        self.rotation_none_button = Gtk.ToggleButton(label="0°", active=True)
        self.rotation_none_button.set_tooltip_text("No rotation")
        self.rotation_left_button = Gtk.ToggleButton(
            icon_name="object-rotate-left-symbolic", group=self.rotation_none_button
        )
        self.rotation_left_button.set_tooltip_text("Rotate 90° counter-clockwise")
        self.rotation_right_button = Gtk.ToggleButton(
            icon_name="object-rotate-right-symbolic", group=self.rotation_none_button
        )
        self.rotation_right_button.set_tooltip_text("Rotate 90° clockwise")
        self.rotation_180_button = Gtk.ToggleButton(
            label="180°", group=self.rotation_none_button
        )
        self.rotation_180_button.set_tooltip_text("Rotate 180°")
        rotation_box.append(self.rotation_none_button)
        rotation_box.append(self.rotation_left_button)
        rotation_box.append(self.rotation_right_button)
        rotation_box.append(self.rotation_180_button)
        controls_box.append(rotation_box)

        controls_box.append(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL))

        flip_label = Gtk.Label(label="<b>Flip</b>", xalign=0, use_markup=True)
        flip_label.add_css_class("caption")
        controls_box.append(flip_label)

        flip_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        flip_box.add_css_class("linked")
        self.flip_horizontal_button = Gtk.ToggleButton(
            icon_name="object-flip-horizontal-symbolic"
        )
        self.flip_horizontal_button.set_tooltip_text("Flip horizontally")
        self.flip_vertical_button = Gtk.ToggleButton(
            icon_name="object-flip-vertical-symbolic"
        )
        self.flip_vertical_button.set_tooltip_text("Flip vertically")
        flip_box.append(self.flip_horizontal_button)
        flip_box.append(self.flip_vertical_button)
        controls_box.append(flip_box)

        main_box.append(controls_box)

        main_box.append(Gtk.Separator(orientation=Gtk.Orientation.VERTICAL))

        self.scale_widget = ScalingFactorScale()
        main_box.append(self.scale_widget)

        for button in (
            self.rotation_none_button,
            self.rotation_left_button,
            self.rotation_right_button,
            self.rotation_180_button,
        ):
            button.connect("toggled", self._on_rotation_button_toggled)
        self.flip_horizontal_button.connect("toggled", self._on_flip_button_toggled)
        self.flip_vertical_button.connect("toggled", self._on_flip_button_toggled)

        self._update_preview()

    def connect_changed(self, callback):
        """Register a callback invoked when any transform option changes."""
        if callable(callback):
            self._change_handlers.append(callback)
            self.scale_widget.scale.connect("value-changed", callback)

    def _notify_changed(self):
        for handler in self._change_handlers:
            handler()

    def _on_rotation_button_toggled(self, button: Gtk.ToggleButton) -> None:
        if not button.get_active():
            return
        self._update_preview()
        self._notify_changed()

    def _on_flip_button_toggled(self, button: Gtk.ToggleButton) -> None:
        self._update_preview()
        self._notify_changed()

    def _update_preview(self) -> None:
        if self.preview is not None:
            self.preview.queue_draw()

    def get_rotation(self) -> int:
        """Get the selected rotation angle."""
        if self.rotation_left_button.get_active():
            return 270
        if self.rotation_right_button.get_active():
            return 90
        if self.rotation_180_button.get_active():
            return 180
        return 0

    def get_flip_horizontal(self) -> bool:
        return self.flip_horizontal_button.get_active()

    def get_flip_vertical(self) -> bool:
        return self.flip_vertical_button.get_active()

    def reset(self) -> None:
        self.rotation_none_button.set_active(True)
        self.flip_horizontal_button.set_active(False)
        self.flip_vertical_button.set_active(False)
        self._update_preview()
        self._notify_changed()

    def set_original_dimensions(self, width: int, height: int) -> None:
        self.original_width = max(1, int(width))
        self.original_height = max(1, int(height))
        self.scale_widget.set_original_dimensions(width, height)
        self._update_preview()

    def set_preview_image(self, image_path):
        if image_path != self._current_preview_path:
            self._next_preview_path = image_path

    def _on_preview_draw(self, area, ctx, width, height) -> None:
        from gi.repository import Gdk, GdkPixbuf

        ctx.save()

        try:
            if self._current_preview_path != self._next_preview_path:
                self._preview_pixbuf = GdkPixbuf.Pixbuf.new_from_file(
                    self._next_preview_path
                )
                self._current_preview_path = self._next_preview_path = None
        except Exception:
            ctx.restore()
            return

        pixbuf = getattr(self, "_preview_pixbuf", None)
        if not pixbuf:
            return

        image_width = pixbuf.get_width()
        image_height = pixbuf.get_height()
        if not image_width or not image_height:
            ctx.restore()
            return

        available_width = max(width - 1.0, 1.0)
        available_height = max(height - 1.0, 1.0)

        rotation = self.get_rotation() % 360
        angle = math.radians(rotation)
        abs_cos = abs(math.cos(angle))
        abs_sin = abs(math.sin(angle))

        denom_width = abs_cos * image_width + abs_sin * image_height
        denom_height = abs_sin * image_width + abs_cos * image_height
        if not denom_width or not denom_height:
            ctx.restore()
            return

        scale = min(available_width / denom_width, available_height / denom_height)
        if scale <= 0:
            ctx.restore()
            return

        ctx.save()
        ctx.translate(width / 2, height / 2)
        ctx.rotate(angle)

        flip_x = -1 if self.get_flip_horizontal() else 1
        flip_y = -1 if self.get_flip_vertical() else 1
        ctx.scale(scale * flip_x, scale * flip_y)

        Gdk.cairo_set_source_pixbuf(ctx, pixbuf, -image_width / 2, -image_height / 2)
        ctx.paint()
        ctx.restore()
        ctx.restore()


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
        self.estimated_compression_time = 60

        hints_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)

        # Quality hint (left aligned)
        quality_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self.quality_icon = Gtk.Image.new_from_icon_name("dialog-question-symbolic")
        self.quality_label = Gtk.Label(label="Quality: —", xalign=0)
        quality_box.append(self.quality_icon)
        quality_box.append(self.quality_label)
        quality_box.set_halign(Gtk.Align.START)

        # Speed hint (right aligned)
        speed_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self.speed_icon = Gtk.Image.new_from_icon_name("dialog-question-symbolic")
        self.speed_label = Gtk.Label(label="Speed: —", xalign=0)
        speed_box.append(self.speed_icon)
        speed_box.append(self.speed_label)
        speed_box.set_margin_end(12)
        speed_box.set_halign(Gtk.Align.END)
        speed_box.set_hexpand(True)

        hints_box.append(quality_box)
        hints_box.append(speed_box)
        self.append(hints_box)
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
        input_codec: str = "libx264",
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

        if selected_mode == CONSTANT_QUALITY_INDEX:
            quality_text = f"Quality: {cq_level.replace('-', ' ').title()}"
            tooltip_text = f"Constant Quality mode selected.\n'{cq_level.replace('-', ' ').title()}' preset."
            self.quality_label.set_label(quality_text)
            self.quality_icon.set_from_icon_name("dialog-information-symbolic")
        else:
            cq_level = "medium"  # forces 1.0
            bpp = calculate_bits_per_pixel(video_bitrate_kbps, width, height, fps)
            quality_rating = rate_quality_from_bpp(bpp, codec)

            quality_text = f"Quality: {quality_rating} ({BLOCK_SIZE * bpp:.2f} BPB)"
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
        _, etime, speed_rating = estimate_encoding_speed(
            codec,
            quality_preset,
            width,
            height,
            fps,
            cq_level,
            hwaccel=hwaccel,
            video_duration=video_duration,
        )
        self.estimated_compression_time = (
            etime * video_duration
        ) / COMPUTER_SPEED_FACTOR
        time_str = format_duration(self.estimated_compression_time)
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
    """Custom widget for scaling factor slider and dimension controls."""

    def __init__(self):
        super().__init__(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=12,
        )
        self.original_width = 1920
        self.original_height = 1080
        self.updating = False

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

        for mark in [0.25, 0.5, 0.75, 1.0]:
            self.scale.add_mark(mark, Gtk.PositionType.BOTTOM, f"{int(mark * 100)}%")

        self.width_adjustment = Gtk.Adjustment.new(
            self.original_width, 1, self.original_width, 1, 10, 0
        )
        self.height_adjustment = Gtk.Adjustment.new(
            self.original_height, 1, self.original_height, 1, 10, 0
        )
        self.width_entry = Gtk.SpinButton(adjustment=self.width_adjustment, digits=0)
        self.width_entry.connect("value-changed", self._on_width_changed)
        self.height_entry = Gtk.SpinButton(adjustment=self.height_adjustment, digits=0)
        self.height_entry.connect("value-changed", self._on_height_changed)

        content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        scale_title = Gtk.Label(label="<b>Shrinking</b>", xalign=0, use_markup=True)
        content_box.append(scale_title)

        dimensions_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        dimensions_box.set_homogeneous(True)

        width_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=3)
        width_label = Gtk.Label(label="Width (px)", xalign=0)
        width_label.add_css_class("caption")
        width_box.append(width_label)
        width_box.append(self.width_entry)
        dimensions_box.append(width_box)

        height_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=3)
        height_label = Gtk.Label(label="Height (px)", xalign=0)
        height_label.add_css_class("caption")
        height_box.append(height_label)
        height_box.append(self.height_entry)
        dimensions_box.append(height_box)

        content_box.append(dimensions_box)
        content_box.append(self.scale)

        scale_button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        scale_button_box.set_homogeneous(True)
        presets = [
            ("10%", 0.1),
            ("25%", 0.25),
            ("33%", 0.33),
            ("50%", 0.5),
            ("66%", 0.66),
            ("75%", 0.75),
            ("100%", 1.0),
        ]
        for label, value in presets:
            btn = Gtk.Button(label=label)
            btn.connect("clicked", lambda w, v=value: self.adjustment.set_value(v))
            scale_button_box.append(btn)
        content_box.append(scale_button_box)
        self.append(content_box)

    def set_original_dimensions(self, width, height):
        """Set the original video dimensions."""
        self.original_width = max(1, int(width))
        self.original_height = max(1, int(height))

        self.updating = True
        self.width_adjustment.set_upper(self.original_width)
        self.height_adjustment.set_upper(self.original_height)
        self.width_entry.set_value(self.original_width)
        self.height_entry.set_value(self.original_height)
        self.adjustment.set_value(1.0)
        self.updating = False

    def _on_scale_changed(self, widget):
        """Update width/height when scale factor changes."""
        if self.updating:
            return
        factor = max(
            self.adjustment.get_lower(),
            min(self.adjustment.get_upper(), self.adjustment.get_value()),
        )
        new_width = max(1, int(self.original_width * factor))
        new_height = max(1, int(self.original_height * factor))
        self.updating = True
        self.width_entry.set_value(new_width)
        self.height_entry.set_value(new_height)
        self.updating = False

    def _on_width_changed(self, widget):
        """Update height and scaling factor when width changes."""
        if self.updating or self.original_width <= 0:
            return
        new_width = max(1, int(self.width_entry.get_value()))
        new_width = min(new_width, self.original_width)
        factor = new_width / self.original_width
        new_height = max(1, int(self.original_height * factor))
        self.updating = True
        self.height_entry.set_value(new_height)
        self.adjustment.set_value(
            max(self.adjustment.get_lower(), min(self.adjustment.get_upper(), factor))
        )
        self.updating = False

    def _on_height_changed(self, widget):
        """Update width and scaling factor when height changes."""
        if self.updating or self.original_height <= 0:
            return
        new_height = max(1, int(self.height_entry.get_value()))
        new_height = min(new_height, self.original_height)
        factor = new_height / self.original_height
        new_width = max(1, int(self.original_width * factor))
        self.updating = True
        self.width_entry.set_value(new_width)
        self.adjustment.set_value(
            max(self.adjustment.get_lower(), min(self.adjustment.get_upper(), factor))
        )
        self.updating = False

    def get_value(self):
        """Get the current scaling factor value."""
        return self.adjustment.get_value()

    def set_value(self, value):
        """Set the scaling factor value."""
        self.adjustment.set_value(float(value))


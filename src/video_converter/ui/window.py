import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

import subprocess
import sys
import threading
import time
from pathlib import Path

from gi.repository import Adw, Gdk, GLib, Gtk

from .widgets import (
    AudioBitrateScale,
    HintsLabel,
    PassesSlider,
    ScalingFactorScale,
)
from ..constants import (
    AUDIO_CODEC_DESCRIPTIONS,
    AUDIO_CODEC_MAP,
    CODEC_DESCRIPTIONS,
    CONSTANT_QUALITY_INDEX,
    CONTAINER_DESCRIPTIONS,
    HW_ACCEL_DESCRIPTIONS,
    HW_ENCODERS,
)
from ..utils import (
    build_ffmpeg_command,
    calculate_bitrate,
    detect_container_from_extension,
    detect_hardware_acceleration,
    format_file_size,
    get_audio_codec_name,
    get_codec_name,
    get_container_name,
    get_hw_accels,
    get_sorted_container_list,
    get_video_duration,
    get_video_properties,
)


class VideoConverterWindow(Adw.ApplicationWindow):
    def __init__(self, app):
        super().__init__(application=app)
        self.set_resizable(True)
        self.set_title("Video Converter")
        self.set_default_size(900, 1100)
        self.is_encoding = False
        self.encoding_thread = None
        self.encoding_process = None
        self.progress_updater = None
        self.estimated_size_bytes = 0
        self.mode_keys = ["target-size", "target-size-vbr", "cbr", "vbr", "cq"]
        self.updating_ui = False

        # Store video properties for calculations
        self.video_width = 1920
        self.video_height = 1080
        self.video_fps = 24.0
        self.video_duration = 30.0

        # Main container
        main_container = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)

        # ViewStack and ViewSwitcher
        # ViewStack and ViewSwitcher
        self.view_stack = Adw.ViewStack()
        self.view_stack.set_vexpand(True)
        view_switcher = Adw.ViewSwitcher.new()
        view_switcher.set_stack(self.view_stack)

        # Header bar with progress and action buttons
        header_bar = Adw.HeaderBar()
        header_bar.set_title_widget(view_switcher)

        # Progress bar in header (center-left area)
        self.progress_bar = Gtk.ProgressBar()
        self.progress_bar.set_show_text(True)
        self.progress_bar.set_size_request(200, -1)
        self.progress_bar.set_visible(False)
        header_bar.pack_start(self.progress_bar)

        # Action buttons on the right side of header
        self.action_button = Gtk.Button()
        self.action_button.connect("clicked", self.on_action_clicked)
        self.set_action_mode(True)
        header_bar.pack_end(self.action_button)

        main_container.append(header_bar)

        # Settings content
        settings_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        settings_box.set_margin_top(12)
        settings_box.set_margin_bottom(12)
        settings_box.set_margin_start(12)
        settings_box.set_margin_end(12)

        # Files section
        files_group = Adw.PreferencesGroup(title="Files")
        settings_box.append(files_group)

        self.input_row = Adw.ActionRow(title="Input Video", subtitle="No file selected")
        self.input_row.add_prefix(
            Gtk.Image.new_from_icon_name("video-x-generic-symbolic")
        )
        self.input_row.set_tooltip_text("Select the video file to convert.")
        input_browse_button = Gtk.Button(label="Browse…")
        input_browse_button.set_icon_name("document-open-symbolic")
        input_browse_button.set_valign(Gtk.Align.CENTER)
        input_browse_button.connect("clicked", self.on_input_browse)
        self.input_row.add_suffix(input_browse_button)
        self.input_row.set_activatable_widget(input_browse_button)
        files_group.add(self.input_row)

        self.output_row = Adw.ActionRow(
            title="Output Video", subtitle="No file selected"
        )
        self.output_row.add_prefix(
            Gtk.Image.new_from_icon_name("media-floppy-symbolic")
        )
        self.output_row.set_tooltip_text(
            "Select the destination for the converted video file."
        )
        output_browse_button = Gtk.Button(label="Browse…")
        output_browse_button.set_icon_name("document-save-as-symbolic")
        output_browse_button.set_valign(Gtk.Align.CENTER)
        output_browse_button.connect("clicked", self.on_output_browse)
        self.output_row.add_suffix(output_browse_button)
        self.output_row.set_activatable_widget(output_browse_button)
        files_group.add(self.output_row)

        # Hints label (quality/speed)
        self.hints_label = HintsLabel()
        hints_row = Adw.PreferencesRow()
        hints_row.set_child(self.hints_label)
        files_group.add(hints_row)

        # Format & Quality section
        format_group = Adw.PreferencesGroup()
        format_expander = Adw.ExpanderRow(
            title="Encoder: Format and Codec",
            expanded=True,
            icon_name="video-x-generic-symbolic",
        )
        format_group.add(format_expander)
        settings_box.append(format_group)

        self.hwaccels = ["cpu"] + get_hw_accels()
        hwaccel_model = Gtk.StringList.new(self.hwaccels)
        self.hwaccel_combo = Adw.ComboRow(model=hwaccel_model, title="Hardware")
        self.hwaccel_combo.set_subtitle(HW_ACCEL_DESCRIPTIONS.get("cpu"))
        self.hwaccel_combo.set_tooltip_text(
            "Select a hardware acceleration method for video encoding and decoding."
        )
        hw_index = self.hwaccels.index(detect_hardware_acceleration())
        GLib.timeout_add(200, self.hwaccel_combo.set_selected, hw_index)
        self.hwaccel_combo.connect("notify::selected-item", self.on_hwaccel_selected)
        format_expander.add_row(self.hwaccel_combo)

        container_model = Gtk.StringList.new(["auto"] + get_sorted_container_list())
        self.container_combo = Adw.ComboRow(
            model=container_model, title="Container Format"
        )
        self.container_combo.set_subtitle(CONTAINER_DESCRIPTIONS.get("auto"))
        self.container_combo.set_tooltip_text(
            "Choose the container format for the output file. 'auto' selects a suitable container based on the output file extension."
        )
        self.container_combo.set_selected(0)
        self.container_combo.connect(
            "notify::selected-item", self.on_container_selected
        )
        format_expander.add_row(self.container_combo)

        codec_model = Gtk.StringList.new(HW_ENCODERS["cpu"])
        self.codec_combo = Adw.ComboRow(model=codec_model, title="Video Codec")
        self.codec_combo.set_subtitle(CODEC_DESCRIPTIONS.get(HW_ENCODERS["cpu"][0]))
        self.codec_combo.set_tooltip_text("Choose the video codec for encoding.")
        self.codec_combo.set_selected(0)
        self.codec_combo.connect("notify::selected-item", self.on_codec_selected)
        self.codec_combo.connect(
            "notify::selected", self._on_settings_changed
        )  # Keep this for hints
        format_expander.add_row(self.codec_combo)

        quality_model = Gtk.StringList.new(["ultrafast", "medium", "slow", "veryslow"])
        self.quality_combo = Adw.ComboRow(
            model=quality_model, title="Encoding Speed / Quality Preset"
        )
        self.quality_combo.set_subtitle("Affects encoding time and efficiency")
        self.quality_combo.set_tooltip_text(
            "Select the encoding speed vs. quality trade-off. 'ultrafast' is quickest but least efficient, 'veryslow' is most efficient but takes much longer."
        )
        self.quality_combo.set_selected(1)
        self.quality_combo.connect("notify::selected", self._on_settings_changed)
        format_expander.add_row(self.quality_combo)

        # Encoding section
        encoding_group = Adw.PreferencesGroup()
        encoding_expander = Adw.ExpanderRow(
            title="Encoding strategy",
            expanded=True,
            icon_name="preferences-system-symbolic",
        )
        encoding_group.add(encoding_expander)
        settings_box.append(encoding_group)

        mode_model = Gtk.StringList.new(
            [
                "Target File Size",
                "Target File Size (VBR)",
                "Fixed Bitrate (CBR)",
                "Average Bitrate (VBR)",
                "Constant Quality",
            ]
        )
        self.mode_combo = Adw.ComboRow(model=mode_model, title="Mode")
        self.mode_combo.set_tooltip_text(
            "Select the encoding mode. This determines how the bitrate is controlled."
        )
        self.mode_combo.set_selected(CONSTANT_QUALITY_INDEX)
        self.mode_combo.connect("notify::selected", self.on_mode_changed)
        encoding_expander.add_row(self.mode_combo)

        self.target_size_entry = Adw.EntryRow(title="Target Size (MB)")
        self.target_size_entry.set_tooltip_text(
            "Set the desired output file size in megabytes (MB). The video bitrate will be calculated automatically."
        )
        self.target_size_entry.set_text("50")
        self.target_size_entry.connect("changed", self._on_settings_changed)
        encoding_expander.add_row(self.target_size_entry)

        self.bitrate_entry = Adw.EntryRow(title="Video Bitrate (kbps)")
        self.bitrate_entry.set_tooltip_text(
            "Set a fixed or average video bitrate in kilobits per second (kbps)."
        )
        self.bitrate_entry.set_text("1000")
        self.bitrate_entry.connect("changed", self._on_settings_changed)
        encoding_expander.add_row(self.bitrate_entry)

        cq_model = Gtk.StringList.new(
            ["lowest", "low", "medium", "high", "very-high", "lossless"]
        )
        self.cq_combo = Adw.ComboRow(model=cq_model, title="Quality Level")
        self.cq_combo.set_tooltip_text(
            "Constant Quality (CRF/QP). Lower values mean higher quality and larger file size. 'medium' is a good starting point."
        )
        self.cq_combo.set_selected(2)
        self.cq_combo.connect("notify::selected", self._on_settings_changed)
        encoding_expander.add_row(self.cq_combo)

        # Advanced settings
        advanced_group = Adw.PreferencesGroup()
        advanced_expander = Adw.ExpanderRow(
            title="Advanced Settings",
            expanded=True,
            icon_name="preferences-other-symbolic",
        )
        advanced_group.add(advanced_expander)
        settings_box.append(advanced_group)
        advanced_expander.set_expanded(False)

        scaling_expander = Adw.ExpanderRow(title="Video Scaling")
        scaling_expander.set_tooltip_text(
            "Resize the video. 1.0 is original size, 0.5 is half size."
        )
        self.scale_factor_scale = ScalingFactorScale()
        self.scale_factor_scale.scale.connect("value-changed", self._on_settings_changed)
        scaling_expander.add_row(self.scale_factor_scale)
        advanced_expander.add_row(scaling_expander)

        passes_expander = Adw.ExpanderRow(title="Number of Passes")
        passes_expander.set_tooltip_text(
            "For VBR modes, use multiple passes for better quality and bitrate accuracy. More passes take longer."
        )
        self.passes_slider = PassesSlider()
        passes_expander.add_row(self.passes_slider)
        self.passes_expander = passes_expander
        advanced_expander.add_row(passes_expander)

        audio_mode_model = Gtk.StringList.new(
            ["Re-encode", "Copy Original", "Disable Audio"]
        )
        self.audio_mode_combo = Adw.ComboRow(model=audio_mode_model, title="Audio Mode")
        self.audio_mode_combo.set_tooltip_text(
            "Choose how to handle the audio track. 'Re-encode' re-encodes the audio, 'Copy Original' copies it without changes, and 'Disable Audio' removes it."
        )
        self.audio_mode_combo.set_selected(1)
        self.audio_mode_combo.connect("notify::selected", self.on_audio_mode_changed)
        advanced_expander.add_row(self.audio_mode_combo)

        audio_codec_model = Gtk.StringList.new(list(AUDIO_CODEC_MAP.keys()))
        self.audio_codec_combo = Adw.ComboRow(
            model=audio_codec_model, title="Audio Codec"
        )
        self.audio_codec_combo.set_subtitle(
            AUDIO_CODEC_DESCRIPTIONS.get(list(AUDIO_CODEC_MAP.keys())[0])
        )
        self.audio_codec_combo.set_selected(0)
        self.audio_codec_combo.connect(
            "notify::selected-item", self.on_audio_codec_selected
        )
        advanced_expander.add_row(self.audio_codec_combo)

        audio_expander = Adw.ExpanderRow(title="Audio Bitrate")
        audio_expander.set_tooltip_text(
            "Set the bitrate for transcoded audio. Higher values mean better quality and larger file size."
        )
        self.audio_scale = AudioBitrateScale()
        audio_expander.add_row(self.audio_scale)
        self.audio_expander = audio_expander
        advanced_expander.add_row(audio_expander)

        # Scrollable settings
        self.scrolled_settings = Gtk.ScrolledWindow()
        self.scrolled_settings.set_child(settings_box)
        self.scrolled_settings.set_vexpand(True)
        self.scrolled_settings.set_hexpand(True)

        # Output log section
        output_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        output_box.set_margin_top(6)
        output_box.set_margin_bottom(6)
        output_box.set_margin_start(12)
        output_box.set_margin_end(12)

        output_label = Gtk.Label(xalign=0)
        output_label.set_markup("<b>Conversion Output</b>")
        output_box.append(output_label)

        scrolled_output = Gtk.ScrolledWindow()
        scrolled_output.set_min_content_width(100)
        scrolled_output.set_vexpand(True)
        scrolled_output.set_hexpand(False)
        scrolled_output.set_min_content_height(80)

        self.output_text = Gtk.TextView()
        self.output_text.set_editable(False)
        self.output_text.set_cursor_visible(False)
        self.output_text.set_monospace(True)
        scrolled_output.set_child(self.output_text)

        output_box.append(scrolled_output)

        self.view_stack.add_titled_with_icon(
            self.scrolled_settings, "settings", "Settings", "preferences-system-symbolic"
        )
        self.view_stack.add_titled_with_icon(
            output_box, "output", "Output", "utilities-terminal-symbolic"
        )

        main_container.append(self.view_stack)

        drop_target = Gtk.DropTarget.new(Gdk.FileList, Gdk.DragAction.COPY)
        drop_target.connect("drop", self._on_drop)
        drop_target.connect("enter", self._on_drag_enter)
        drop_target.connect("leave", self._on_drag_leave)
        main_container.add_controller(drop_target)

        self.set_content(main_container)

        self.on_mode_changed(None, None)
        self.on_audio_mode_changed(None, None)

    def _handle_new_input_file(self, path):
        """Handles all the logic for when a new input file is selected,
        either by browsing or drag-and-drop.
        """
        try:
            self.input_file = Path(path)
            self.input_row.set_subtitle(Path(path).name)

            # Reset output file when input changes
            self.output_row.set_subtitle("No file selected")
            if hasattr(self, "outputfile"):
                self.outputfile = None

            # Get video properties
            try:
                width, height, fps = get_video_properties(path)
                if width and height and fps:
                    self.video_width = width
                    self.video_height = height
                    self.video_fps = fps
                    self.scale_factor_scale.set_original_dimensions(width, height)

                duration = get_video_duration(path)
                if duration and duration > 0:
                    self.video_duration = duration

                self._on_settings_changed()
            except Exception as e:
                print(f"Could not read video properties: {e}", file=sys.stderr)

            # Get audio bitrate
            try:
                proc_result = subprocess.run(
                    [
                        "ffprobe",
                        "-v",
                        "error",
                        "-select_streams",
                        "a:0",
                        "-show_entries",
                        "stream=bit_rate",
                        "-of",
                        "csv=p=0",
                        path,
                    ],
                    capture_output=True,
                    text=True,
                    check=True,
                    timeout=10,
                )
                audio_bitrate = proc_result.stdout.strip()
                if audio_bitrate and audio_bitrate.isdigit():
                    bitrate_kbps = int(audio_bitrate) // 1000
                    self.audioscale.set_value(bitrate_kbps)
            except subprocess.CalledProcessError:
                # This is not an error, the video may not have an audio track.
                pass
            except Exception as e:
                print(f"Could not read audio bitrate: {e}", file=sys.stderr)
        except Exception as e:
            print(f"Error processing input file: {e}", file=sys.stderr)

    def _on_drag_enter(self, drop_target, x, y):
        self.view_stack.add_css_class("drop-zone")
        # Return the action we want to perform
        print("plop")
        return Gdk.DragAction.COPY

    def _on_drag_leave(self, drop_target):
        self.view_stack.remove_css_class("drop-zone")

    def _on_drop(self, drop_target, value, x, y):
        self.view_stack.remove_css_class("drop-zone")
        if isinstance(value, Gdk.FileList):
            files = value.get_files()
            if files:
                # We only handle the first dropped file
                file_path = files[0].get_path()
                self._handle_new_input_file(file_path)
        return True  # Indicate that the drop was successfully handled

    def _on_settings_changed(self, *args):
        """Update quality/speed hints when settings change."""
        if not hasattr(self, "hints_label"):
            return

        try:
            # Get current bitrate from selected mode
            selected_index = self.mode_combo.get_selected()
            mode = self.mode_keys[selected_index]

            if "target-size" in mode:
                target_size = float(self.target_size_entry.get_text())
                video_bitrate = (
                    int(
                        (target_size * 8192 / self.video_duration)
                        - self.audio_scale.get_value()
                    )
                    if self.video_duration > 0
                    else 0
                )
            elif mode == "cq":
                # For CQ mode, use a standard reference bitrate (varies by codec)
                codec_str = (
                    self.codec_combo.get_selected_item().get_string()
                    if self.codec_combo.get_selected_item()
                    else "h264"
                )
                codec = get_codec_name(codec_str)
                # Reference bitrates for different codecs at "balanced" quality
                ref_bitrates = {
                    "libx264": 2000,
                    "libx265": 1500,
                    "libvpx-vp9": 1500,
                    "libaom-av1": 1200,
                    "mpeg4": 2500,
                }
                video_bitrate = ref_bitrates.get(codec, 2000)
            else:
                video_bitrate = (
                    int(self.bitrate_entry.get_text())
                    if self.bitrate_entry.get_text()
                    else 1000
                )

            # Get codec and preset
            codec_str = (
                self.codec_combo.get_selected_item().get_string()
                if self.codec_combo.get_selected_item()
                else "h264"
            )
            codec = get_codec_name(codec_str)
            preset = (
                self.quality_combo.get_selected_item().get_string()
                if self.quality_combo.get_selected_item()
                else "balanced"
            )
            cq_level = (
                self.cq_combo.get_selected_item().get_string()
                if self.cq_combo.get_selected_item()
                else "medium"
            )
            hwaccel = (
                self.hwaccel_combo.get_selected_item().get_string()
                if self.hwaccel_combo.get_selected_item()
                else "cpu"
            )

            # Update hints
            scale_factor = self.scale_factor_scale.get_value()
            self.hints_label.update_quality_speed(
                video_bitrate,
                self.video_width * scale_factor,
                self.video_height * scale_factor,
                self.video_fps,
                codec,
                preset,
                cq_level,
                self.video_duration,
                self.mode_combo.get_selected(),
                hwaccel,
            )
        except (ValueError, AttributeError):
            pass

    def on_audio_mode_changed(self, widget, _):
        """Handle audio mode changes."""
        if not hasattr(self, "audio_mode_combo"):
            return

        selected_index = self.audio_mode_combo.get_selected()
        is_transcode = selected_index == 0

        self.audio_expander.set_sensitive(is_transcode)
        self.audio_expander.set_enable_expansion(is_transcode)
        self.audio_codec_combo.set_sensitive(is_transcode)

    def on_mode_changed(self, widget, _):
        if not hasattr(self, "mode_combo"):
            return

        selected_index = self.mode_combo.get_selected()
        active_mode = self.mode_keys[selected_index]

        is_cq = active_mode == "cq"
        is_vbr = "vbr" in active_mode
        is_target_size = "target-size" in active_mode

        self.target_size_entry.set_visible(is_target_size)
        self.bitrate_entry.set_visible(not is_target_size and not is_cq)
        self.cq_combo.set_visible(is_cq)

        self.passes_expander.set_visible(is_vbr)

        self._on_settings_changed()

    def on_input_browse(self, widget):
        """Browse for input file."""
        dialog = Gtk.FileDialog.new()
        dialog.set_title("Select Video File")

        def on_response(dialog, result):
            try:
                file = dialog.open_finish(result)
                if file:
                    path = file.get_path()
                    self._handle_new_input_file(path)
            except GLib.Error as e:
                # Gtk.DialogError.DISMISSED is raised when the user cancels the dialog
                if not e.matches(Gtk.DialogError, Gtk.DialogError.DISMISSED):
                    # Re-raise other dialog errors
                    raise
            except Exception:
                # Handle other exceptions if necessary, or pass
                pass

        dialog.open(self, None, on_response)

    def on_output_browse(self, widget):
        """Browse for output file."""
        dialog = Gtk.FileDialog.new()  # ✅ Modern API
        dialog.set_title("Select Output Video")
        dialog.set_initial_name("output.mp4")

        def on_response(dialog, result):
            try:
                file = dialog.save_finish(result)
                if file:
                    path = Path(file.get_path())
                    self.output_row.set_subtitle(path.name)
                    self.output_file = path
            except Exception:
                pass  # User cancelled

        dialog.save(self, None, on_response)

    def log_output(self, message):
        """Add message to output log."""
        buffer = self.output_text.get_buffer()
        buffer.insert(buffer.get_end_iter(), message + "\n")
        mark = buffer.create_mark("end", buffer.get_end_iter(), False)
        self.output_text.scroll_mark_onscreen(mark)

    def set_action_mode(self, convert=True):
        if convert:
            self.action_button.set_label("Start conversion")
            self.action_button.set_icon_name("media-playback-start-symbolic")
            self.action_button.set_tooltip_text("Start the video conversion process.")
            self.action_button.add_css_class("suggested-action")
        else:
            self.action_button.set_label("Cancel")
            self.action_button.set_icon_name("process-stop-symbolic")
            self.action_button.set_tooltip_text("Cancel the ongoing conversion.")

    def on_action_clicked(self, widget):
        handler = self.on_cancel_clicked if self.is_encoding else self.on_convert_clicked
        return handler(widget)

    def on_convert_clicked(self, widget):
        """Start conversion."""
        if not hasattr(self, "input_file") or not hasattr(self, "output_file"):
            dialog = Adw.AlertDialog.new(
                "Error", "Please select input and output files"
            )
            dialog.add_response("ok", "OK")
            dialog.set_default_response("ok")
            dialog.present(self)
            return

        self.view_stack.set_visible_child_name("output")
        self.scrolled_settings.set_sensitive(False)
        self.set_action_mode(False)
        self.output_text.get_buffer().set_text("")

        self.progress_bar.set_visible(True)
        self.progress_bar.set_fraction(0)
        self.progress_bar.set_text("Preparing...")
        if self.progress_updater:
            GLib.source_remove(self.progress_updater)
        self.progress_updater = GLib.timeout_add(500, self.update_progress)

        self.encoding_thread = threading.Thread(target=self.run_conversion)
        self.encoding_thread.daemon = True
        self.encoding_thread.start()

    def on_cancel_clicked(self, widget):
        """Cancel conversion."""
        self.is_encoding = False
        self.progress_bar.set_text("Cancelling...")

    def on_hwaccel_selected(self, combo, _):
        """Handle hardware acceleration selection changes."""
        selected_item = combo.get_selected_item()
        if not selected_item:
            return

        hwaccel_name = selected_item.get_string().lower()
        if hwaccel_name == "none":
            hwaccel_name = "cpu"
        self._hw_accel = hwaccel_name

        # Update description
        description = HW_ACCEL_DESCRIPTIONS.get(
            hwaccel_name, f"Hardware acceleration method: {hwaccel_name.upper()}"
        )
        combo.set_subtitle(description)

        # Update codec list
        codec_list = HW_ENCODERS.get(hwaccel_name, HW_ENCODERS["cpu"])
        self.codec_combo.set_model(Gtk.StringList.new(codec_list))
        self.codec_combo.set_selected(0)
        self.codec_combo.set_subtitle(CODEC_DESCRIPTIONS.get(codec_list[0].lower(), ""))

        # Quality and CQ presets are available for most encoders.
        is_cpu = hwaccel_name == "cpu"
        self.quality_combo.set_sensitive(not is_cpu)
        self.cq_combo.set_sensitive(not is_cpu)
        self._on_settings_changed()

    def on_container_selected(self, combo, _):
        """Handle container selection changes and update subtitle."""
        selected_item = combo.get_selected_item()
        if not selected_item:
            return
        container_name = selected_item.get_string().lower()
        description = CONTAINER_DESCRIPTIONS.get(container_name, "")
        combo.set_subtitle(description)

    def on_codec_selected(self, combo, _):
        """Handle video codec selection changes and update subtitle."""
        selected_item = combo.get_selected_item()
        if not selected_item:
            return
        codec_name = selected_item.get_string().lower()
        description = CODEC_DESCRIPTIONS.get(codec_name, "")
        combo.set_subtitle(description)

    def on_audio_codec_selected(self, combo, _):
        """Handle audio codec selection changes and update subtitle."""
        selected_item = combo.get_selected_item()
        if not selected_item:
            return
        audio_codec_name = selected_item.get_string()
        description = AUDIO_CODEC_DESCRIPTIONS.get(audio_codec_name, "")
        combo.set_subtitle(description)

    def update_progress(self):
        """Enhanced progress tracking with time-based estimation."""
        if not self.is_encoding:
            return False

        mode = self.mode_keys[self.mode_combo.get_selected()]

        # For CQ mode, try to parse ffmpeg output for time progress
        # This requires capturing ffmpeg output progressively
        if mode == "cq":
            # Parse stderr for time= progress
            # This requires capturing ffmpeg output progressively
            self.progress_bar.pulse()
            return True

        if not hasattr(self, "output_file") or self.estimated_size_bytes <= 0:
            return True

        if not self.output_file.is_file():
            return True

        current_size = self.output_file.stat().st_size

        # Use sigmoid curve for more realistic progress
        # Early encoding: faster growth
        # Late encoding: slower growth (finalization)
        if self.estimated_size_bytes > 0:
            raw_fraction = current_size / self.estimated_size_bytes
            # Apply sigmoid smoothing
            # progress = 1 / (1 + e^(-10*(x - 0.5)))
            import math

            if raw_fraction < 0.95:  # Don't smooth the final approach
                smoothed = 1 / (1 + math.exp(-10 * (raw_fraction - 0.5)))
                fraction = min(0.95, smoothed)
            else:
                fraction = raw_fraction

            self.progress_bar.set_fraction(min(1.0, fraction))

            # Estimate time remaining
            if hasattr(self, "encoding_start_time"):
                elapsed = time.time() - self.encoding_start_time
                if fraction > 0.05:  # Wait for meaningful data
                    estimated_total = elapsed / fraction
                    remaining = estimated_total - elapsed
                    self.progress_bar.set_text(
                        f"{fraction:.0%} - {int(remaining // 60)}m {int(remaining % 60)}s remaining"
                    )
            else:
                self.progress_bar.set_text(f"{fraction:.0%}")

        return True

    def run_conversion(self):
        """Run the conversion."""
        try:
            self.is_encoding = True
            input_file = self.input_file
            output_file = self.output_file

            GLib.idle_add(self.log_output, "=== Video Converter Started ===")

            if not input_file.is_file():
                GLib.idle_add(
                    self.log_output, f"Error: Input file not found: {input_file}"
                )
                return

            output_ext = output_file.suffix.lower().lstrip(".")

            # Determine hwaccel and codec based on UI
            hwaccel = self.hwaccel_combo.get_selected_item().get_string().lower()
            if hwaccel == "cpu":
                hwaccel = "None"  # Pass "None" for decoding

            codec_str = self.codec_combo.get_selected_item().get_string()
            codec = get_codec_name(codec_str)

            container_str = (
                self.container_combo.get_selected_item().get_string()
                if self.container_combo.get_selected_item()
                else "auto"
            )

            if container_str == "auto":
                container = detect_container_from_extension(output_ext)
            else:
                container = get_container_name(container_str)

            try:
                subprocess.run(
                    ["ffmpeg", "-version"], check=False, capture_output=True, timeout=5
                )
            except FileNotFoundError:
                GLib.idle_add(self.log_output, "Error: ffmpeg is not installed")
                return

            duration = get_video_duration(input_file.absolute())

            if duration is None:
                GLib.idle_add(
                    self.log_output, "Error: Could not determine video duration"
                )
                return

            try:
                audio_bitrate = self.audio_scale.get_value()
                scale_factor = self.scale_factor_scale.get_value()
                quality = (
                    self.quality_combo.get_selected_item().get_string()
                    if self.quality_combo.get_selected_item()
                    else "balanced"
                )
                passes = self.passes_slider.get_value()

                audio_mode_index = self.audio_mode_combo.get_selected()
                audio_mode_map = ["transcode", "copy", "disable"]
                audio_mode = audio_mode_map[audio_mode_index]

                audio_codec_str = (
                    self.audio_codec_combo.get_selected_item().get_string()
                    if self.audio_codec_combo.get_selected_item()
                    else "AAC"
                )
                audio_codec = get_audio_codec_name(audio_codec_str)

            except ValueError as e:
                GLib.idle_add(self.log_output, f"Error: Invalid input - {e}")
                return

            selected_index = self.mode_combo.get_selected()
            mode = self.mode_keys[selected_index]

            GLib.idle_add(self.log_output, f"Input: {input_file}")
            GLib.idle_add(self.log_output, f"Output: {output_file}")
            GLib.idle_add(self.log_output, f"Codec: {codec}")
            GLib.idle_add(self.log_output, f"Container: {container}")
            GLib.idle_add(self.log_output, f"Quality: {quality}")
            GLib.idle_add(self.log_output, f"Scale factor: {scale_factor:.2f}")
            GLib.idle_add(self.log_output, f"Audio mode: {audio_mode}")

            if audio_mode == "transcode":
                GLib.idle_add(self.log_output, f"Audio codec: {audio_codec}")
                GLib.idle_add(self.log_output, f"Audio bitrate: {audio_bitrate}kbps")

            GLib.idle_add(self.log_output, f"Video duration: {duration}s\n")

            video_bitrate = 0
            cq_level = None
            is_cq = mode == "cq"

            if is_cq:
                cq_level = (
                    self.cq_combo.get_selected_item().get_string()
                    if self.cq_combo.get_selected_item()
                    else "medium"
                )
                GLib.idle_add(self.log_output, f"Constant Quality level: {cq_level}")

            elif "target-size" in mode:
                try:
                    target_size = float(self.target_size_entry.get_text())
                    video_bitrate = calculate_bitrate(
                        target_size, duration, audio_bitrate
                    )
                    GLib.idle_add(self.log_output, f"Target size: {target_size}MB")
                    GLib.idle_add(
                        self.log_output,
                        f"Calculated video bitrate: {video_bitrate}kbps\n",
                    )
                except ValueError as e:
                    GLib.idle_add(self.log_output, f"Error: {e}")
                    return

            else:
                try:
                    video_bitrate = int(self.bitrate_entry.get_text())
                    GLib.idle_add(
                        self.log_output, f"Video bitrate: {video_bitrate}kbps\n"
                    )
                except ValueError:
                    GLib.idle_add(self.log_output, "Error: Invalid bitrate")
                    return

            # Estimate final size for progress bar
            self.estimated_size_bytes = 0
            if "target-size" in mode:
                target_size = float(self.target_size_entry.get_text())
                self.estimated_size_bytes = target_size * 1024 * 1024
            elif "cq" not in mode:  # CBR or VBR bitrate modes
                effective_audio_bitrate = 0
                if audio_mode == "transcode":
                    effective_audio_bitrate = audio_bitrate
                elif audio_mode == "copy":
                    effective_audio_bitrate = (
                        self.audio_scale.get_value()
                    )  # Approximation

                total_bitrate_kbps = video_bitrate + effective_audio_bitrate
                self.estimated_size_bytes = (
                    total_bitrate_kbps * 1000 / 8
                ) * duration

            GLib.idle_add(self.log_output, "Starting encoding...\n")

            is_vbr = "vbr" in mode
            actual_passes = passes if is_vbr else 1

            def run_ffmpeg_process(cmd):
                GLib.idle_add(self.log_output, f"Running {' '.join(cmd)}")
                process = subprocess.Popen(
                    cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
                )
                self.encoding_process = process

                while process.poll() is None:
                    if not self.is_encoding:
                        process.terminate()
                        break
                    time.sleep(0.2)

                self.encoding_process = None
                try:
                    stdout, stderr = process.communicate(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    stdout, stderr = process.communicate()

                return process.returncode, stdout, stderr

            if output_file.is_file():
                output_file.unlink()

            if is_vbr and actual_passes > 1:
                GLib.idle_add(
                    self.log_output,
                    f"Multi-pass VBR Encoding ({actual_passes} passes)\n",
                )

                for pass_num in range(1, actual_passes + 1):
                    if not self.is_encoding:
                        break

                    GLib.idle_add(
                        self.log_output, f"--- Pass {pass_num} of {actual_passes} ---"
                    )

                    cmd = build_ffmpeg_command(
                        str(input_file.absolute()),
                        str(output_file.absolute()),
                        codec,
                        container,
                        video_bitrate,
                        audio_bitrate,
                        scale_factor,
                        quality=quality,
                        is_vbr=True,
                        pass_num=pass_num,
                        is_cq=is_cq,
                        cq_level=cq_level,
                        audio_mode=audio_mode,
                        audio_codec=audio_codec,
                        hwaccel=hwaccel,
                    )

                    if pass_num < actual_passes:
                        cmd[-1] = "/dev/null"
                        cmd.insert(-1, "-y")

                    return_code, _, stderr = run_ffmpeg_process(cmd)

                    if return_code != 0:
                        if self.is_encoding:  # Don't show error if cancelled
                            GLib.idle_add(
                                self.log_output, f"Error at pass {pass_num}: {stderr}"
                            )
                        return

            else:
                cmd = build_ffmpeg_command(
                    str(input_file.absolute()),
                    str(output_file.absolute()),
                    codec,
                    container,
                    video_bitrate,
                    audio_bitrate,
                    scale_factor,
                    quality=quality,
                    is_vbr=is_vbr,
                    is_cq=is_cq,
                    cq_level=cq_level,
                    audio_mode=audio_mode,
                    audio_codec=audio_codec,
                    hwaccel=hwaccel,
                )

                return_code, _, stderr = run_ffmpeg_process(cmd)

                if return_code != 0:
                    if self.is_encoding:
                        GLib.idle_add(self.log_output, f"Error: {stderr}")
                    return

            if not self.is_encoding:
                GLib.idle_add(self.log_output, "\nEncoding cancelled by user.")
                return

            if output_file.is_file():
                output_size = output_file.stat().st_size
                output_size_mb = format_file_size(output_size)

                GLib.idle_add(self.log_output, "\n=== Conversion Complete ===")
                GLib.idle_add(self.log_output, f"Output file: {output_file}")
                GLib.idle_add(self.log_output, f"Output size: {output_size_mb}MB")

                def show_success():
                    self.progress_bar.set_fraction(1.0)
                    self.progress_bar.set_text("Complete")
                    dialog = Adw.AlertDialog.new(
                        "Conversion Complete",
                        f"Output: {output_file}\nSize: {output_size_mb}MB",
                    )
                    dialog.add_response("ok", "OK")
                    dialog.set_default_response("ok")
                    dialog.present(self)

                GLib.idle_add(show_success)

            else:
                GLib.idle_add(self.log_output, "Error: Output file was not created")

                def set_progress_error():
                    self.progress_bar.set_text("Error")

                GLib.idle_add(set_progress_error)

        except Exception as e:
            GLib.idle_add(self.log_output, f"Exception: {e}")

            def set_progress_exception():
                self.progress_bar.set_text("Error")

            GLib.idle_add(set_progress_exception)

        finally:
            self.is_encoding = False
            self.encoding_process = None

            def restore_ui():
                self.set_action_mode(True)
                self.scrolled_settings.set_sensitive(True)
                if self.progress_updater:
                    GLib.source_remove(self.progress_updater)
                    self.progress_updater = None

                self.progress_bar.set_visible(False)
                self.progress_bar.set_fraction(0)
                self.progress_bar.set_text("")

            GLib.idle_add(restore_ui)

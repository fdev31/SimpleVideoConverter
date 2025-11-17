import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

import subprocess
import sys
import threading
import time
from functools import partial
from pathlib import Path

from gi.repository import Adw, Gdk, GLib, GObject, Gtk

from ..constants import (
    AUDIO_CODECS,
    CODECS,
    CONSTANT_QUALITY_INDEX,
    CONTAINERS,
    HW_ACCEL,
    EncodingModes,
)
from ..models import ListItem, get_ItemList
from ..utils import (
    build_ffmpeg_command,
    calculate_bitrate,
    detect_codec_from_extension,
    detect_container_from_extension,
    detect_hardware_acceleration,
    format_file_size,
    get_audio_codec_name,
    get_codec_properties,
    get_container_name,
    get_hw_accels,
    get_sorted_container_list,
    get_video_duration,
    get_video_properties,
)
from .widgets import AudioBitrateScale, HintsLabel, ScalingFactorScale, TransformRow


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
        self.mode_keys = list([e.name for e in EncodingModes])
        self.updating_ui = False

        # Store video properties for calculations
        self.video_width = 1920
        self.video_height = 1080
        self.video_fps = 24.0
        self.video_duration = 30.0

        self.input_file = Path("./Input.mp4")
        self.output_file = Path("./output.mp4")

        # Main container
        main_container = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)

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

        # # Files section
        files_group = Adw.PreferencesGroup(title="General")
        settings_box.append(files_group)

        self.input_row = Adw.ActionRow(
            title="Video to convert", subtitle="No file selected"
        )
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
            title="Output File", subtitle="No file selected"
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

        # Encoding section
        encoding_mode_action_row = Adw.ActionRow(title="Encoding Mode")
        encoding_mode_action_row.add_prefix(
            Gtk.Image.new_from_icon_name("applications-science-symbolic")
        )
        files_group.add(encoding_mode_action_row)

        self.scale_factor_scale = ScalingFactorScale()
        self.scale_factor_scale.scale.connect(
            "value-changed", self._on_settings_changed
        )
        files_group.add(self.scale_factor_scale)

        # Hints label (quality/speed)
        self.hints_label = HintsLabel()
        debug_hints = Adw.PreferencesRow()
        debug_hints.set_child(self.hints_label)
        files_group.add(debug_hints)
        encoding_mode_action_row.set_subtitle("Fixed file size or Quality driven")

        controls_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        encoding_mode_action_row.add_suffix(controls_box)

        mode_model = Gtk.StringList.new([e.value for e in EncodingModes])
        self.mode_combo = Gtk.DropDown.new(mode_model, None)
        self.mode_combo.set_tooltip_text(
            "Select the encoding mode. This determines how the bitrate is controlled."
        )
        self.mode_combo.set_selected(CONSTANT_QUALITY_INDEX)
        self.mode_combo.connect("notify::selected-item", self.on_mode_changed)
        controls_box.append(self.mode_combo)

        self.mode_settings_stack = Gtk.Stack()
        self.mode_settings_stack.set_hexpand(True)
        controls_box.append(self.mode_settings_stack)

        self.target_size_adjustment = Gtk.Adjustment.new(50, 1, 100000, 1, 10, 0)
        self.target_size_entry = Gtk.SpinButton(
            adjustment=self.target_size_adjustment, digits=0
        )
        self.target_size_entry.set_tooltip_text(
            "Set the desired output file size in megabytes (MB). The video bitrate will be calculated automatically."
        )
        self.target_size_entry.connect("value-changed", self._on_settings_changed)
        self.mode_settings_stack.add_titled(
            self.target_size_entry, "target_size", "Target Size"
        )

        self.bitrate_adjustment = Gtk.Adjustment.new(1000, 1, 500000, 1, 100, 0)
        self.bitrate_entry = Gtk.SpinButton(
            adjustment=self.bitrate_adjustment, digits=0
        )
        self.bitrate_entry.set_tooltip_text(
            "Set a fixed or average video bitrate in kilobits per second (kbps)."
        )
        self.bitrate_entry.connect("value-changed", self._on_settings_changed)
        self.mode_settings_stack.add_titled(self.bitrate_entry, "bitrate", "Bitrate")

        cq_model = Gtk.StringList.new(
            ["lowest", "low", "medium", "high", "very-high", "lossless"]
        )
        self.cq_combo = Gtk.DropDown.new(cq_model, None)
        self.cq_combo.set_tooltip_text(
            "Constant Quality (CRF/QP). Lower values mean higher quality and larger file size. 'medium' is a good starting point."
        )
        self.cq_combo.set_selected(1)
        self.cq_combo.connect("notify::selected-item", self._on_settings_changed)
        self.mode_settings_stack.add_titled(self.cq_combo, "cq", "Quality Level")

        # Format & Quality section
        format_group = Adw.PreferencesGroup()
        format_expander = Adw.ExpanderRow(
            title="Encoder",
            expanded=True,
            icon_name="video-x-generic-symbolic",
        )
        format_expander.set_expanded(False)
        format_group.add(format_expander)
        settings_box.append(format_group)

        self.hwaccels = ["cpu"] + get_hw_accels()
        hwaccel_model = Gtk.StringList.new(self.hwaccels)
        self.hwaccel_combo = Adw.ComboRow(model=hwaccel_model, title="Hardware")
        self.hwaccel_combo.set_subtitle(HW_ACCEL["cpu"]["description"])
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
        self.container_combo.set_subtitle("")
        self.container_combo.set_tooltip_text(
            "Choose the container format for the output file. 'auto' selects a suitable container based on the output file extension."
        )
        self.container_combo.connect(
            "notify::selected-item", self.on_container_selected
        )
        format_expander.add_row(self.container_combo)

        codec_list = HW_ACCEL["cpu"]["codecs"]
        codec_model = self._get_codec_list(codec_list)
        self.codec_combo = Adw.ComboRow(model=codec_model, title="Video Codec")
        expression = Gtk.PropertyExpression.new(ListItem, None, "display")
        self.codec_combo.set_expression(expression)
        initial_props = get_codec_properties(codec_list[0])
        if initial_props:
            self.codec_combo.set_subtitle(initial_props.get("description", ""))
        self.codec_combo.set_tooltip_text("Choose the video codec for encoding.")
        self.codec_combo.set_selected(0)
        self.codec_combo.connect("notify::selected-item", self.on_codec_selected)
        self.codec_combo.connect(
            "notify::selected", self._on_settings_changed
        )  # Keep this for hints
        format_expander.add_row(self.codec_combo)

        quality_model = Gtk.StringList.new(["ultrafast", "medium", "slow", "veryslow"])
        self.quality_combo = Adw.ComboRow(
            model=quality_model, title="Encoding Quality Preset"
        )
        self.quality_combo.set_subtitle("Affects encoding time and efficiency")
        self.quality_combo.set_tooltip_text(
            "Select the encoding speed vs. quality trade-off. 'ultrafast' is quickest but least efficient, 'veryslow' is most efficient but takes much longer."
        )
        self.quality_combo.set_selected(1)
        self.quality_combo.connect("notify::selected", self._on_settings_changed)
        format_expander.add_row(self.quality_combo)

        # Advanced settings
        advanced_group = Adw.PreferencesGroup()
        advanced_expander = Adw.ExpanderRow(
            title="Advanced",
            expanded=True,
            icon_name="preferences-other-symbolic",
        )
        advanced_group.add(advanced_expander)
        settings_box.append(advanced_group)
        advanced_expander.set_expanded(False)

        # Rotation and Flip
        self.transform_row = TransformRow()
        advanced_expander.add_row(self.transform_row)

        passes_expander = Adw.SpinRow(title="Number of Passes")
        passes_expander.set_adjustment(Gtk.Adjustment.new(2, 2, 3, 1, 1, 0))
        passes_expander.set_digits(0)
        # passes_expander = Adw.ExpanderRow(title="Number of Passes")
        passes_expander.set_tooltip_text(
            "For VBR modes, use multiple passes for better quality and bitrate accuracy. More passes take longer."
        )
        self.passes_expander = passes_expander
        advanced_expander.add_row(passes_expander)

        # Track selection
        self.tracks_expander = Adw.ExpanderRow(title="Audio tracks &amp; Subtitles")
        self.tracks_expander.set_tooltip_text(
            "Select which audio and subtitle tracks to include in the output."
        )
        self.track_widgets = []
        self.no_tracks_row = Adw.ActionRow(
            title="Load a video to see available tracks."
        )
        self.tracks_expander.add_row(self.no_tracks_row)
        advanced_expander.add_row(self.tracks_expander)

        audio_codec_model = Gtk.StringList.new(list(AUDIO_CODECS.keys()))
        self.audio_codec_combo = Adw.ComboRow(
            model=audio_codec_model, title="Audio Codec"
        )
        self.audio_codec_combo.set_subtitle(list(AUDIO_CODECS.values())[0]["descr"])
        self.audio_codec_combo.set_selected(0)
        self.audio_codec_combo.connect(
            "notify::selected-item", self.on_audio_codec_selected
        )
        self.audio_codec_combo.set_selected(0)
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
            self.scrolled_settings,
            "settings",
            "Settings",
            "preferences-system-symbolic",
        )
        self.view_stack.add_titled_with_icon(
            output_box, "output", "Output", "utilities-terminal-symbolic"
        )

        main_container.append(self.view_stack)

        self.set_content(main_container)

        drop_target = Gtk.DropTarget.new(
            type=GObject.TYPE_NONE, actions=Gdk.DragAction.COPY
        )
        drop_target.set_gtypes([Gdk.FileList, str])
        drop_target.connect("drop", self._on_drop)
        drop_target.connect("enter", self._on_enter)
        drop_target.connect("motion", self._on_drag_motion)  # Use 'motion' not 'enter'
        drop_target.connect("leave", self._on_drag_leave)
        self.add_controller(drop_target)  # Add to window, not container

        self.on_mode_changed(None, None)

    def _handle_new_input_file(self, path):
        """Handles all the logic for when a new input file is selected,
        either by browsing or drag-and-drop.
        """
        try:
            self.input_file = Path(path)
            self.input_row.set_subtitle(Path(path).name)

            # Reset output file when input changes
            self.output_row.set_subtitle("No file selected")

            # Clear existing track widgets
            if hasattr(self, "no_tracks_row") and self.no_tracks_row:
                self.tracks_expander.remove(self.no_tracks_row)
                self.no_tracks_row = None
            for track_info in self.track_widgets:
                self.tracks_expander.remove(track_info["widget"])
            self.track_widgets = []

            # Get video properties
            try:
                width, height, fps, streams = get_video_properties(path)
                if width and height and fps:
                    self.video_width = width
                    self.video_height = height
                    self.video_fps = fps
                    self.scale_factor_scale.set_original_dimensions(width, height)

                duration = get_video_duration(path)
                if duration and duration > 0:
                    self.video_duration = duration

                # Populate track selection UI
                if not streams:
                    self.no_tracks_row = Adw.ActionRow(
                        title="No audio or subtitle tracks found."
                    )
                    self.tracks_expander.add_row(self.no_tracks_row)
                else:
                    for stream in streams:
                        stream_index = stream.get("index", "N/A")
                        codec_type = stream.get("codec_type", "unknown")
                        codec_name = stream.get("codec_name", "unknown")
                        lang = stream.get("tags", {}).get("language", "und")

                        label = f"{codec_type.title()} #{stream_index} ({lang}, {codec_name})"

                        if codec_type == "audio":
                            model = Gtk.StringList.new(["Copy", "Re-encode", "Skip"])
                        else:
                            model = Gtk.StringList.new(["Copy", "Skip"])

                        combo = Adw.ComboRow(title=label, model=model)
                        combo.set_selected(0)  # Default to "Copy"
                        combo.connect(
                            "notify::selected-item", self._on_settings_changed
                        )

                        self.tracks_expander.add_row(combo)
                        self.track_widgets.append(
                            {
                                "widget": combo,
                                "stream_index": stream_index,
                                "codec_type": codec_type,
                            }
                        )

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
        self._on_settings_changed()

    def _on_drag_motion(self, drop_target, x, y):
        """Handle drag motion to show drop zone and enable cursor change."""
        self.view_stack.add_css_class("drop-zone")
        return Gdk.DragAction.COPY  # This enables the cursor change

    # Keep your _on_drag_leave as is (or improve it):
    def _on_drag_leave(self, drop_target):
        """Remove drop zone styling when drag leaves."""
        self.view_stack.remove_css_class("drop-zone")

    def _on_enter(self, drop_target, x, y):
        # Add visual feedback, e.g., change the widget's appearance
        return Gdk.DragAction.COPY  # Accept the drop

    # Fix the _on_drop method:
    def _on_drop(self, drop_target, value, x, y):
        """Handle the actual drop event."""
        self.view_stack.remove_css_class("drop-zone")
        print(value)

        if isinstance(value, Gdk.FileList):
            files = value.get_files()
            if files and len(files) > 0:
                first_file = files[0]
                if first_file:
                    file_path = first_file.get_path()
                    if file_path:  # Verify path is valid
                        self._handle_new_input_file(file_path)
                        return True

        return False

    def _on_settings_changed(self, *args):
        """Update quality/speed hints when settings change."""
        if not hasattr(self, "hints_label"):
            return

        try:
            # Get current bitrate from selected mode
            selected_index = self.mode_combo.get_selected()
            mode = self.mode_keys[selected_index]

            if "size" in mode:
                target_size = self.target_size_entry.get_value()
                video_bitrate = (
                    int(
                        (target_size * 8192 / self.video_duration)
                        - self.audio_scale.get_value()
                    )
                    if self.video_duration > 0
                    else 0
                )
            elif EncodingModes.cq.name == mode:
                # For CQ mode, use a standard reference bitrate (varies by codec)
                codec = (
                    self.codec_combo.get_selected_item().value
                    if self.codec_combo.get_selected_item()
                    else "h264"
                )
                props = get_codec_properties(codec)
                # Reference bitrates for different codecs at "balanced" quality
                ref_bitrates = {
                    "h264": 2000,
                    "h265": 1500,
                    "vp9": 1500,
                    "av1": 1200,
                    "mpeg4": 2500,
                }
                video_bitrate = ref_bitrates.get(props.get("family"), 2000)
            else:
                video_bitrate = int(self.bitrate_entry.get_value())

            # Get codec and preset
            codec = (
                self.codec_combo.get_selected_item().value
                if self.codec_combo.get_selected_item()
                else "h264"
            )
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
            # show ffmpeg command
            self.hints_label.debug(" ".join(self.get_ffmpeg_command()))

            # Update sensitivity of audio codec and bitrate based on track selections
            has_audio_reencode = False
            for track_info in self.track_widgets:
                if track_info["codec_type"] == "audio":
                    selected_action = (
                        track_info["widget"].get_selected_item().get_string().lower()
                    )
                    if selected_action == "re-encode":
                        has_audio_reencode = True
                        break

            self.audio_codec_combo.set_sensitive(has_audio_reencode)
            self.audio_expander.set_sensitive(has_audio_reencode)
            self.audio_expander.set_enable_expansion(has_audio_reencode)

        except (ValueError, AttributeError) as e:
            print(e)
            pass

    def on_mode_changed(self, widget, _):
        if not hasattr(self, "mode_combo"):
            return

        selected_index = self.mode_combo.get_selected()
        active_mode = self.mode_keys[selected_index]

        is_cq = EncodingModes.cq.name == active_mode
        is_vbr = "vbr" in active_mode
        is_target_size = "size" in active_mode

        if is_target_size:
            self.mode_settings_stack.set_visible_child_name("target_size")
        elif is_cq:
            self.mode_settings_stack.set_visible_child_name("cq")
        else:  # cbr or vbr
            self.mode_settings_stack.set_visible_child_name("bitrate")

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
                    self._on_settings_changed()
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
        handler = (
            self.on_cancel_clicked if self.is_encoding else self.on_convert_clicked
        )
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
        self.view_stack.set_visible_child_name("settings")

    def on_hwaccel_selected(self, combo, _):
        """Handle hardware acceleration selection changes."""
        selected_item = combo.get_selected_item()
        if not selected_item:
            return

        hwaccel_name = selected_item.get_string().lower()

        # Update description
        description = HW_ACCEL.get(hwaccel_name, HW_ACCEL["cpu"])["description"]
        combo.set_subtitle(description)

        current_codec = self.codec_combo.get_selected_item().value
        codec_family = CODECS[current_codec]["family"]

        # Update codec list
        codec_list = HW_ACCEL.get(hwaccel_name, HW_ACCEL["cpu"])["codecs"]
        store = self._get_codec_list(codec_list)
        self.codec_combo.set_model(store)
        for i, codec in enumerate(codec_list):
            if CODECS[codec]["family"] == codec_family:
                self.codec_combo.set_selected(i)
                break
        self.on_codec_selected(self.codec_combo, None)
        self._on_settings_changed()

    def _get_codec_list(self, orig):
        return get_ItemList(orig, lambda codec: CODECS[codec]["name"])

    def on_container_selected(self, combo, _):
        """Handle container selection changes and update subtitle."""
        selected_item = combo.get_selected_item()
        if not selected_item:
            return
        container_name = selected_item.get_string().lower()
        if container_name == "auto":
            description = "Automatically detect from output file extension"
        else:
            description = CONTAINERS[container_name]["descr"]
        combo.set_subtitle(description)

    def on_codec_selected(self, combo, _):
        """Handle video codec selection changes and update subtitle."""
        selected_item = combo.get_selected_item()
        if not selected_item:
            return
        codec = selected_item.value
        props = get_codec_properties(codec)
        if not props:
            return

        combo.set_subtitle(props.get("description", ""))

        # Update quality presets
        presets = props.get("presets")
        if presets:
            self.quality_combo.set_model(Gtk.StringList.new(list(presets.keys())))
            self.quality_combo.set_sensitive(True)
            self.quality_combo.set_selected(1)
        else:
            self.quality_combo.set_model(Gtk.StringList.new([]))
            self.quality_combo.set_sensitive(False)

        # Update CQ levels
        cq_levels = props.get("cq_levels")
        if cq_levels:
            self.cq_combo.set_model(Gtk.StringList.new(list(cq_levels.keys())))
            self.cq_combo.set_sensitive(True)
            self.cq_combo.set_selected(3)  # medium
        else:
            self.cq_combo.set_model(Gtk.StringList.new([]))
            self.cq_combo.set_sensitive(False)

    def on_audio_codec_selected(self, combo, _):
        """Handle audio codec selection changes and update subtitle."""
        selected_item = combo.get_selected_item()
        if not selected_item:
            return
        audio_codec_name = selected_item.get_string()
        description = AUDIO_CODECS[audio_codec_name]["descr"]
        combo.set_subtitle(description)

    def update_progress(self):
        """Enhanced progress tracking with time-based estimation."""
        if not self.is_encoding:
            return False

        mode = self.mode_keys[self.mode_combo.get_selected()]

        # For CQ mode, try to parse ffmpeg output for time progress
        # This requires capturing ffmpeg output progressively
        if mode == EncodingModes.cq.name:
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

    def get_conversion_parameters(self):
        """Extract and validate conversion parameters from UI.

        Returns:
            dict: Dictionary containing all conversion parameters

        Raises:
            ValueError: If parameters are invalid
        """
        input_file = self.input_file
        output_file = self.output_file

        if not input_file.is_file():
            raise ValueError(f"Input file not found: {input_file}")

        try:
            output_ext = output_file.suffix.lower().lstrip(".")
        except AttributeError:
            output_ext = "mp4"

        # Determine hwaccel and codec based on UI
        hwaccel = self.hwaccel_combo.get_selected_item().get_string().lower()
        if hwaccel == "cpu":
            hwaccel = "None"  # Pass "None" for decoding

        codec = self.codec_combo.get_selected_item().value

        container_str = (
            self.container_combo.get_selected_item().get_string()
            if self.container_combo.get_selected_item()
            else "auto"
        )

        if container_str == "auto":
            container = detect_container_from_extension(output_ext)
        else:
            container = get_container_name(container_str)

        if codec == "auto":
            codec = detect_codec_from_extension(output_ext)

        duration = get_video_duration(input_file.absolute())
        if duration is None:
            raise ValueError("Could not determine video duration")

        audio_bitrate = self.audio_scale.get_value()
        scale_factor = self.scale_factor_scale.get_value()
        quality = (
            self.quality_combo.get_selected_item().get_string()
            if self.quality_combo.get_selected_item()
            else "balanced"
        )
        passes = int(self.passes_expander.get_value())

        audio_codec_str = (
            self.audio_codec_combo.get_selected_item().get_string()
            if self.audio_codec_combo.get_selected_item()
            else "AAC"
        )
        audio_codec = get_audio_codec_name(audio_codec_str)

        selected_index = self.mode_combo.get_selected()
        mode = self.mode_keys[selected_index]

        video_bitrate = 0
        cq_level = None
        is_cq = mode == EncodingModes.cq.name

        if is_cq:
            cq_level = (
                self.cq_combo.get_selected_item().get_string()
                if self.cq_combo.get_selected_item()
                else "medium"
            )
        elif "size" in mode:
            target_size = self.target_size_entry.get_value()
            video_bitrate = calculate_bitrate(target_size, duration, audio_bitrate)
        else:
            video_bitrate = int(self.bitrate_entry.get_value())

        is_vbr = "vbr" in mode
        actual_passes = passes if is_vbr else 1

        track_options = {}
        for track_info in self.track_widgets:
            widget = track_info["widget"]
            stream_index = track_info["stream_index"]
            selected = widget.get_selected_item().get_string().lower()
            track_options[stream_index] = selected

        flip_horizontal = self.transform_row.get_flip_vertical()
        flip_vertical = self.transform_row.get_flip_vertical()

        rotation_angle = self.transform_row.get_rotation()

        return {
            "input_file": input_file,
            "output_file": output_file,
            "codec": codec,
            "container": container,
            "hwaccel": hwaccel,
            "video_bitrate": video_bitrate,
            "audio_bitrate": audio_bitrate,
            "scale_factor": scale_factor,
            "quality": quality,
            "audio_codec": audio_codec,
            "is_cq": is_cq,
            "cq_level": cq_level,
            "is_vbr": is_vbr,
            "actual_passes": actual_passes,
            "duration": duration,
            "mode": mode,
            "track_options": track_options,
            "flip_horizontal": flip_horizontal,
            "flip_vertical": flip_vertical,
            "rotation_angle": rotation_angle,
        }

    def get_ffmpeg_command(self, pass_num=None):
        """Get the ffmpeg command that would be executed.

        Args:
            pass_num (int, optional): Pass number for multi-pass encoding.
                                     None for single-pass.

        Returns:
            list: The ffmpeg command as a list of arguments

        Raises:
            ValueError: If parameters are invalid
        """
        try:
            params = self.get_conversion_parameters()
        except ValueError:
            return []

        actual_pass_num = (
            pass_num if pass_num is not None else (1 if params["is_vbr"] else None)
        )

        cmd = build_ffmpeg_command(
            "IN",
            "OUT",
            params["codec"],
            params["container"],
            params["video_bitrate"],
            params["audio_bitrate"],
            params["scale_factor"],
            quality=params["quality"],
            is_vbr=params["is_vbr"],
            pass_num=actual_pass_num,
            is_cq=params["is_cq"],
            cq_level=params["cq_level"],
            audio_codec=params["audio_codec"],
            hwaccel=params["hwaccel"],
            track_options=params["track_options"],
            flip_horizontal=params["flip_horizontal"],
            flip_vertical=params["flip_vertical"],
            rotation_angle=params["rotation_angle"],
        )

        return cmd

    def run_conversion(self):
        """Run the conversion."""
        try:
            self.is_encoding = True

            GLib.idle_add(self.log_output, "=== Video Converter Started ===")

            try:
                subprocess.run(
                    ["ffmpeg", "-version"], check=False, capture_output=True, timeout=5
                )
            except FileNotFoundError:
                GLib.idle_add(self.log_output, "Error: ffmpeg is not installed")
                return

            try:
                params = self.get_conversion_parameters()
            except ValueError as e:
                GLib.idle_add(self.log_output, f"Error: {e}")
                return

            input_file = params["input_file"]
            output_file = params["output_file"]
            codec = params["codec"]
            container = params["container"]
            quality = params["quality"]
            scale_factor = params["scale_factor"]
            audio_codec = params["audio_codec"]
            audio_bitrate = params["audio_bitrate"]
            video_bitrate = params["video_bitrate"]
            duration = params["duration"]
            mode = params["mode"]
            is_cq = params["is_cq"]
            cq_level = params["cq_level"]
            is_vbr = params["is_vbr"]
            actual_passes = params["actual_passes"]

            GLib.idle_add(self.log_output, f"Input: {input_file}")
            GLib.idle_add(self.log_output, f"Output: {output_file}")
            GLib.idle_add(self.log_output, f"Codec: {codec}")
            GLib.idle_add(self.log_output, f"Container: {container}")
            GLib.idle_add(self.log_output, f"Quality: {quality}")
            GLib.idle_add(self.log_output, f"Scale factor: {scale_factor:.2f}")

            if "re-encode" in [
                track["widget"].get_selected_item().get_string().lower()
                for track in self.track_widgets
                if track["codec_type"] == "audio"
            ]:
                GLib.idle_add(self.log_output, f"Audio codec: {audio_codec}")
                GLib.idle_add(self.log_output, f"Audio bitrate: {audio_bitrate}kbps")

            GLib.idle_add(self.log_output, f"Video duration: {duration}s\n")

            if is_cq:
                GLib.idle_add(self.log_output, f"Constant Quality level: {cq_level}")
            elif "size" in mode:
                target_size = float(self.target_size_entry.get_text())
                GLib.idle_add(self.log_output, f"Target size: {target_size}MB")
                GLib.idle_add(
                    self.log_output,
                    f"Calculated video bitrate: {video_bitrate}kbps\n",
                )
            else:
                GLib.idle_add(self.log_output, f"Video bitrate: {video_bitrate}kbps\n")
            # Estimate final size for progress bar
            self.estimated_size_bytes = 0
            if "size" in mode:
                target_size = float(self.target_size_entry.get_text())
                self.estimated_size_bytes = target_size * 1024 * 1024
            elif (
                mode != EncodingModes.cq.name
            ):  # Constant Bitrate or Variable Bitrate modes
                effective_audio_bitrate = 0
                for track in self.track_widgets:
                    if track["codec_type"] == "audio":
                        action = (
                            track["widget"].get_selected_item().get_string().lower()
                        )
                        if action == "re-encode":
                            effective_audio_bitrate += audio_bitrate
                        elif action == "copy":
                            effective_audio_bitrate += (
                                self.audio_scale.get_value()
                            )  # Approximation

                total_bitrate_kbps = video_bitrate + effective_audio_bitrate
                self.estimated_size_bytes = (total_bitrate_kbps * 1000 / 8) * duration

            GLib.idle_add(self.log_output, "Starting encoding...\n")

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

                GLib.idle_add(self.view_stack.set_visible_child_name, "settings")
                return process.returncode, stdout, stderr

            if output_file.is_file():
                output_file.unlink()

            ffmpeg_command = partial(
                build_ffmpeg_command,
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
                audio_codec=audio_codec,
                hwaccel=params["hwaccel"],
                track_options=params["track_options"],
                flip_horizontal=params["flip_horizontal"],
                flip_vertical=params["flip_vertical"],
                rotation_angle=params["rotation_angle"],
            )
            if is_vbr and actual_passes > 1:
                pass_list = range(1, actual_passes + 1)
            else:
                pass_list = [None]

            for pass_num in pass_list:
                if not self.is_encoding:
                    break

                GLib.idle_add(
                    self.log_output, f"--- Pass {pass_num} of {actual_passes} ---"
                )

                cmd = ffmpeg_command(pass_num=pass_num)

                if pass_num is not None and pass_num < actual_passes:
                    cmd[-1] = "/dev/null"
                    cmd.insert(-1, "-y")

                return_code, _, stderr = run_ffmpeg_process(cmd)

                if return_code != 0:
                    if self.is_encoding:  # Don't show error if canceled
                        GLib.idle_add(
                            self.log_output, f"Error at pass {pass_num}: {stderr}"
                        )
                    return

            if not self.is_encoding:
                GLib.idle_add(self.log_output, "\nEncoding canceled by user.")
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

import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gtk

from video_converter.app import VideoConverterApp
from video_converter.ui.window import VideoConverterWindow


class TestFfmpegCommands(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = VideoConverterApp()
        cls.app.register(None)
        with patch("gi.repository.GLib.timeout_add"):
            cls.app.do_startup()
        cls.window = cls.app.win

    @classmethod
    def tearDownClass(cls):
        cls.app.quit()

    @patch("pathlib.Path.is_file", return_value=True)
    @patch("video_converter.ui.window.get_video_duration", return_value=30)
    def test_default_command(self, mock_get_video_duration, mock_is_file):
        command = self.window.get_ffmpeg_command()
        self.assertIsInstance(command, list)
        self.assertIn("ffmpeg", command)

    @patch("pathlib.Path.is_file", return_value=True)
    @patch("video_converter.ui.window.get_video_duration", return_value=30)
    def test_all_setting_combinations_produce_unique_commands(
        self, mock_get_video_duration, mock_is_file
    ):
        generated_commands = {}

        hwaccel_model = self.window.hwaccel_combo.get_model()
        container_model = self.window.container_combo.get_model()
        mode_model = self.window.mode_combo.get_model()

        for h in range(hwaccel_model.get_n_items()):
            self.window.hwaccel_combo.set_selected(h)
            hwaccel_name = hwaccel_model.get_item(h).get_string()

            codec_model = self.window.codec_combo.get_model()
            for i in range(codec_model.get_n_items()):
                self.window.codec_combo.set_selected(i)
                codec_name = codec_model.get_item(i).value

                quality_model = self.window.quality_combo.get_model()
                cq_model = self.window.cq_combo.get_model()

                for j in range(container_model.get_n_items()):
                    self.window.container_combo.set_selected(j)
                    container_name = container_model.get_item(j).get_string()

                    for l in range(quality_model.get_n_items()):
                        self.window.quality_combo.set_selected(l)
                        quality_name = quality_model.get_item(l).get_string()

                        for k in range(mode_model.get_n_items()):
                            self.window.mode_combo.set_selected(k)
                            mode_name = mode_model.get_item(k).get_string()
                            mode_key = self.window.mode_keys[k]

                            def check_command(sub_setting_name, sub_setting_value):
                                current_settings = {
                                    "hw": hwaccel_name,
                                    "codec": codec_name,
                                    "container": container_name,
                                    "quality_preset": quality_name,
                                    "mode": mode_name,
                                    "sub_setting_name": sub_setting_name,
                                    "sub_setting_value": sub_setting_value,
                                }
                                current_settings_string = (
                                    f"HW: '{hwaccel_name}', Codec: '{codec_name}', Container: '{container_name}', "
                                    f"Quality: '{quality_name}', Mode: '{mode_name}', "
                                    f"{sub_setting_name}: '{sub_setting_value}'"
                                )

                                mock_output_file = MagicMock(spec=Path)
                                mock_output_file.is_file.return_value = True
                                if container_name == "auto":
                                    mock_output_file.suffix = ".mkv"
                                else:
                                    mock_output_file.suffix = f".{container_name}"

                                with patch.object(
                                    self.window, "output_file", mock_output_file
                                ):
                                    command = " ".join(self.window.get_ffmpeg_command())

                                if command in generated_commands:
                                    conflicting_settings = generated_commands[command]

                                    # Symmetrically check for m4v/mp4 alias
                                    is_alias = {
                                        current_settings["container"],
                                        conflicting_settings["container"],
                                    } == {"mp4", "m4v"}

                                    # Check if all other settings are identical
                                    other_settings_match = all(
                                        current_settings[key] == conflicting_settings[key]
                                        for key in current_settings
                                        if key != "container"
                                    )

                                    if is_alias and other_settings_match:
                                        return  # Expected alias, do not fail

                                    conflicting_settings_string = (
                                        f"HW: '{conflicting_settings['hw']}', Codec: '{conflicting_settings['codec']}', Container: '{conflicting_settings['container']}', "
                                        f"Quality: '{conflicting_settings['quality_preset']}', Mode: '{conflicting_settings['mode']}', "
                                        f"{conflicting_settings['sub_setting_name']}: '{conflicting_settings['sub_setting_value']}'"
                                    )
                                    self.fail(
                                        f'"{current_settings_string}" produces the same ffmpeg command as "{conflicting_settings_string}"\n=> {command}'
                                    )
                                generated_commands[command] = current_settings

                            if mode_key == "cq":
                                if cq_model and cq_model.get_n_items() > 0:
                                    for m in range(cq_model.get_n_items()):
                                        self.window.cq_combo.set_selected(m)
                                        cq_name = cq_model.get_item(m).get_string()
                                        check_command("CQ Level", cq_name)
                                else:
                                    check_command("CQ Level", "N/A")
                            elif "size" in mode_key:
                                for size in ["10", "50"]:
                                    self.window.target_size_entry.set_value(int(size))
                                    check_command("Target Size", size)
                            else:  # cbr/vbr
                                for bitrate in ["800", "1200"]:
                                    self.window.bitrate_entry.set_value(int(bitrate))
                                    check_command("Bitrate", bitrate)



if __name__ == "__main__":
    unittest.main()

# Simple Video Converter

A modern video conversion application built with Python, GTK4, and Adwaita. This application provides an intuitive interface for converting videos between different formats, with support for various codecs, hardware acceleration, and advanced encoding options.

Linux only.

Folded (as on startup):
![shot1](https://github.com/fdev31/SimpleVideoConverter/blob/main/shots/window_folded.png?raw=true)

Everything expanded:
![shot2](https://github.com/fdev31/SimpleVideoConverter/blob/main/shots/window_expanded.png?raw=true)

## Features

- **User-friendly Interface**: Clean, modern interface built with GTK4 and Adwaita
- **Multiple Encoding Modes**:
  - Constant Quality (CRF/QP)
  - Constant Bitrate (CBR)
  - Variable Bitrate (VBR)
  - Target File Size (VBR or CBR)
- **Wide Format Support**: Support for various video containers and codecs
- **Hardware Acceleration**: Utilize GPU acceleration for faster encoding (when available)
- **Audio Processing**: Options to re-encode, copy, or disable audio tracks
- **Multi-pass Encoding**: Support for multi-pass encoding for improved quality
- **Progress Tracking**: Real-time progress updates during conversion
- **Quality Presets**: Choose between encoding speed and efficiency
- **Transformations**: Rotate or flip the video, select which tracks to keep, skip or re-encode

  <!--- **Drag and Drop**: Conveniently drag video files into the application -->

## Requirements

- Python 3.8 or higher
  - PyGObject
- FFmpeg
- ffmpegthumbnailer
- [Adwaita](https://gnome.pages.gitlab.gnome.org/libadwaita/) / Gtk4

## Installation

### From Source

1. Clone the repository:
   ```bash
   git clone https://github.com/fdev31/SimpleVideoConverter.git
   cd video-converter
   ```

2. Install the required Python packages:
   ```bash
   pip install .
   ```

3. Install FFmpeg:
   - On Ubuntu/Debian:
     ```bash
     sudo apt update
     sudo apt install ffmpeg
     ```
   - On Fedora:
     ```bash
     sudo dnf install ffmpeg
     ```
   - On macOS (using Homebrew):
     ```bash
     brew install ffmpeg
     ```

4. Run the application:
   ```bash
   video-converter
   ```

## Usage

1. **Select Input File**: Click "Browse…" next to "Video to convert" or drag and drop a video file onto the application
2. **Select Output File**: Click "Browse…" next to "Output File" to choose where to save the converted video
3. **Configure Encoding Settings**:
   - Choose an encoding mode from the dropdown
   - Adjust quality, bitrate, or target size based on the selected mode
   - Select video codec and container format
   - Configure hardware acceleration if available
4. **Advanced Settings** (optional):
   - Adjust number of passes for VBR encoding
   - Configure audio settings (codec, bitrate)
5. **Start Conversion**: Click "Start conversion" to begin the process
6. **Monitor Progress**: View the conversion progress and output log in the "Output" tab

## Configuration

The application supports various configuration options:

- **Encoding Modes**:
  - *Constant Quality*: Use a quality parameter (CRF/QP) to control output quality
  - *Bitrate*: Set a specific bitrate for the output
  - *Target Size*: Specify a target file size and let the application calculate the appropriate bitrate

- **Video Settings**:
  - Codec selection (H.264, H.265, VP9, AV1, etc.)
  - Quality preset (ultrafast, medium, slow, veryslow)
  - Scaling factor for resolution adjustment

- **Audio Settings**:
  - Audio mode (Re-encode, Copy Original, Disable Audio)
  - Audio codec selection
  - Audio bitrate adjustment

## Troubleshooting

- **FFmpeg not found**: Ensure FFmpeg is installed and accessible in your system's PATH
- **Conversion fails**: Check the output log for error messages
- **Hardware acceleration not working**: Verify that your system supports the selected hardware acceleration method

## Contributing

Contributions are welcome! Please feel free to submit pull requests or open issues for bugs and feature requests.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- FFmpeg for the powerful video processing capabilities
- GTK and Adwaita for the modern UI framework
- The Python community for the excellent libraries used in this project

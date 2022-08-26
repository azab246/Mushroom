<p align="center">
  <img src="https://raw.githubusercontent.com/azab246/Mushroom/Main/src/res/Mushroom.svg" height="250px" vspace="20px" alt="Mushroom logo">
</p>
 
# Mushroom 
An elegant youtube video downloader based on [pytube](https://github.com/pytube/pytube) and built with [GTK4](https://github.com/GNOME/pygobject) & [libadwaita](https://gitlab.gnome.org/GNOME/libadwaita)

## Features
<img src="https://raw.githubusercontent.com/azab246/Mushroom/Main/Screenshots/01-dark-prealpha.png" height="350px" align="right" alt="Main menu screenshot">

- Download __videos__ with __up to 8K resolution__
- Download __playlists__ with just one click
- Download only audio for videos/playlists! Great for music videos
- Support for more than 8 different formats
- And more!

## Notes
A FFMPEG static build will be downloaded at the first app launch.

The app uses [FFMPEG](https://ffmpeg.org/) to handle youtube DASH streams (the method used for all downloads).

## Usage
1. Install flatpak via [these instructions](https://flatpak.org/setup/)
2. Download the release, then locate the `.flatpak` file and run `sudo flatpak install com.github.azab246.mushroom.flatpak` within the same directory
3. Run `flatpak run com.github.azab246.mushroom`

## Disclaimer
This app was made for the [CS50x 2022 final project](https://cs50.harvard.edu/x/2022/).
This app is developed by a beginner programmer with no previous experience. The developer makes no guarantees on the reliability or performance of this application. For more information, see the license.

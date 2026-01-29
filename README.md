# Space-Watcher (portable)

This project opens an X (Twitter) Space in a mobile-like browser window and plays the audio.

## Requirements (first time only)

1) Python 3.10+ installed.
2) Install dependencies:

```
python -m pip install -r requirements.txt
```

3) Download binaries (mpv, ffmpeg, yt-dlp):

```
powershell -ExecutionPolicy Bypass -File .\tools\fetch_bins.ps1
```

This creates the `bin` folder with:

- `mpv.exe`
- `ffmpeg.exe`
- `yt-dlp.exe`

## Normal use (each time)

1) Run:

```
python -m space_watcher.main
```

2) Paste the Space link and press Enter.

3) If you want to record, enable the checkbox.

## Mute shortcut

- Press **Ctrl+M** to mute/unmute audio (mpv).

## Audio device (optional)

If you do not hear audio, you can force an output device:

1) List devices:

```
.\bin\mpv.exe --audio-device=help
```

2) Set the device in an environment variable:

```
setx SPACE_WATCHER_AUDIO_DEVICE "wasapi/DEVICE_ID"
```

Reopen the terminal and run the app again.

## Cookies audio (recommended)

If `yt-dlp` fails to read Edge cookies, use a `cookies.txt` file:

1) Export X cookies from your browser (for example with a "cookies.txt" extension).
2) Save it as `cookies.txt` in one of these locations:
   - `space-watcher\cookies.txt`
   - `space-watcher\bin\cookies.txt`
   - next to the portable `.exe`
3) Optional: set the exact path with:

```
setx SPACE_WATCHER_COOKIES_PATH "C:\path\cookies.txt"
```

Then run the app normally.

## If something fails

Errors are saved with this format:

```
space_watcher_errors_YYYYMMDD_HHMMSS.json
```

They are saved at the same level as the `space-watcher` folder.

## Notes

- The browser opens in dark mode with a mobile-like size.
- To change the size, edit `space_watcher/presentation/gui.py`.


```
.\.venv\Scripts\Activate.ps1
```
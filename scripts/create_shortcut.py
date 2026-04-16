"""Створення ярлика VoiceType.lnk у кореневій папці проєкту."""

from pathlib import Path
import win32com.client


def main():
    root = Path(__file__).parent.parent
    dist_exe = root / "dist" / "VoiceType" / "VoiceType.exe"
    icon = root / "voicetype.ico"
    shortcut_path = root / "VoiceType.lnk"

    if not dist_exe.exists():
        print(f"EXE not found: {dist_exe}")
        return

    shell = win32com.client.Dispatch("WScript.Shell")
    s = shell.CreateShortCut(str(shortcut_path))
    s.TargetPath = str(dist_exe)
    s.WorkingDirectory = str(dist_exe.parent)
    s.IconLocation = str(icon) if icon.exists() else str(dist_exe)
    s.Description = "VoiceType"
    s.WindowStyle = 7  # minimized
    s.Save()
    print(f"Shortcut created: {shortcut_path}")


if __name__ == "__main__":
    main()

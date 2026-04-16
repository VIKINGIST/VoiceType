[Setup]
AppName=VoiceType
AppVersion=1.0.0
AppPublisher=Viktor Korol
AppPublisherURL=https://github.com/VIKINGIST/VoiceType
DefaultDirName={autopf}\VoiceType
DefaultGroupName=VoiceType
UninstallDisplayIcon={app}\VoiceType.exe
OutputDir=installer_output
OutputBaseFilename=VoiceType-Setup
SetupIconFile=voicetype.ico
Compression=lzma2/ultra64
SolidCompression=yes
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
WizardStyle=modern
DisableProgramGroupPage=yes

[Languages]
Name: "ukrainian"; MessagesFile: "compiler:Languages\Ukrainian.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Desktop shortcut"; GroupDescription: "Shortcuts:"
Name: "startmenu"; Description: "Start Menu shortcut"; GroupDescription: "Shortcuts:"
Name: "autostart"; Description: "Run at Windows startup"; GroupDescription: "Options:"; Flags: unchecked

[Files]
Source: "dist\VoiceType\*"; DestDir: "{app}"; Excludes: "*.lock"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "voicetype.ico"; DestDir: "{app}"; Flags: ignoreversion

[Dirs]
Name: "{app}\logs"

[Icons]
Name: "{autodesktop}\VoiceType"; Filename: "{app}\VoiceType.exe"; IconFilename: "{app}\voicetype.ico"; Tasks: desktopicon
Name: "{group}\VoiceType"; Filename: "{app}\VoiceType.exe"; IconFilename: "{app}\voicetype.ico"; Tasks: startmenu
Name: "{group}\Uninstall VoiceType"; Filename: "{uninstallexe}"; Tasks: startmenu
Name: "{userstartup}\VoiceType"; Filename: "{app}\VoiceType.exe"; IconFilename: "{app}\voicetype.ico"; Tasks: autostart

[Run]
Filename: "{app}\VoiceType.exe"; Description: "Launch VoiceType"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{app}\logs"
Type: files; Name: "{app}\config.yaml"

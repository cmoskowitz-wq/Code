; ThreatScope Inno Setup Script
; Builds a standalone Windows installer from the PyInstaller --onedir output.
;
; Prerequisites:
;   1. Build the app first:
;        pyinstaller --onedir --windowed --name ThreatScope threatscope.py
;   2. Install Inno Setup 6: https://jrsoftware.org/isdl.php
;   3. Open this file in Inno Setup and click Build > Compile (or press F9)
;
; Output: installer\Output\ThreatScopeSetup.exe

#define AppName      "ThreatScope"
#define AppVersion   "4.5"
#define AppPublisher "Christopher Moskowitz"
#define AppURL       "https://github.com/cmoskowitz-wq/Code"
#define AppExe       "ThreatScope.exe"
; Path to the PyInstaller output folder — adjust if your layout differs
#define SourceDir    "..\dist\ThreatScope"

[Setup]
AppId={{A1B2C3D4-E5F6-7890-ABCD-EF1234567890}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} v{#AppVersion}
AppPublisher={#AppPublisher}
AppPublisherURL={#AppURL}
AppSupportURL={#AppURL}
AppUpdatesURL={#AppURL}

; Install to Program Files\ThreatScope
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
AllowNoIcons=yes

; Single-file installer output
OutputDir=Output
OutputBaseFilename=ThreatScopeSetup
SetupIconFile=

; Compression
Compression=lzma2/ultra64
SolidCompression=yes
LZMAUseSeparateProcess=yes

; Require admin rights so it installs to Program Files properly
PrivilegesRequired=admin

; Minimum Windows version: Windows 10
MinVersion=10.0

; Show wizard in modern style
WizardStyle=modern
WizardSizePercent=120

; Uninstall information shown in Add/Remove Programs
UninstallDisplayName={#AppName}
UninstallDisplayIcon={app}\{#AppExe}

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon";   Description: "Create a &desktop shortcut";    GroupDescription: "Additional icons:"; Flags: unchecked
Name: "startmenuicon"; Description: "Create a &Start Menu shortcut"; GroupDescription: "Additional icons:"

[Files]
; Copy every file from the PyInstaller onedir output recursively
Source: "{#SourceDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
; Start Menu shortcut (always created)
Name: "{group}\{#AppName}";           Filename: "{app}\{#AppExe}"
Name: "{group}\Uninstall {#AppName}"; Filename: "{uninstallexe}"

; Desktop shortcut (only if the user ticked the task above)
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExe}"; Tasks: desktopicon

[Run]
; Offer to launch the app immediately after install
Filename: "{app}\{#AppExe}"; \
    Description: "Launch {#AppName} now"; \
    Flags: nowait postinstall skipifsilent

[UninstallDelete]
; Remove the CVE cache that the app writes at runtime
Type: filesandordirs; Name: "{userappdata}\.threatscope"

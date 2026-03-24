; TradeMe — Inno Setup Installer Script
; Run with:  iscc TradeMe.iss
; Or let build.py call it automatically.
;
; Prerequisites:
;   Inno Setup 6  https://jrsoftware.org/isdownload.php
;   PyInstaller bundle already built in  dist\TradeMe\

#define AppName      "TradeMe"
#define AppVersion   "1.0.0"
#define AppPublisher "TradeMe"
#define AppExeName   "TradeMe.exe"
#define SourceDir    "dist\TradeMe"

[Setup]
AppId={{A3F2B1C4-7E5D-4A9F-8C6B-2D0E1F3A5B7C}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher={#AppPublisher}
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
AllowNoIcons=yes
; Single output installer exe
OutputDir=dist
OutputBaseFilename=TradeMe-Setup
; Compression
Compression=lzma2/ultra64
SolidCompression=yes
; Require Windows 10 or later
MinVersion=10.0
; 64-bit only (matches Python 3 default)
ArchitecturesInstallIn64BitMode=x64
ArchitecturesAllowed=x64
; Appearance
WizardStyle=modern
; Uninstall info shown in Add/Remove Programs
UninstallDisplayName={#AppName}

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop shortcut"; GroupDescription: "Additional icons:"; Flags: unchecked

[Files]
; Include the entire PyInstaller output folder
Source: "{#SourceDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
; Start Menu
Name: "{group}\{#AppName}";          Filename: "{app}\{#AppExeName}"
Name: "{group}\Uninstall {#AppName}"; Filename: "{uninstallexe}"
; Desktop (optional)
Name: "{autodesktop}\{#AppName}";    Filename: "{app}\{#AppExeName}"; Tasks: desktopicon

[Run]
; Offer to launch immediately after install
Filename: "{app}\{#AppExeName}"; Description: "Launch {#AppName}"; \
  Flags: nowait postinstall skipifsilent

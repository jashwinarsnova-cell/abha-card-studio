; ============================================================
;  ABHA Card Studio v5.2 — Inno Setup Script
;  Supports: Windows 10/11 x64
; ============================================================

#define AppName      "ABHA Card Studio"
#define AppVersion   "5.2"
#define AppExeName   "abha_card_studio.exe"
#define AppFolder    "abha_card_studio"
#define AppDataDir   "ABHA_Studio"

[Setup]
AppId={{B7E2F1A3-4C8D-4E9F-A012-3B4C5D6E7F89}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} v{#AppVersion}
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
AllowNoIcons=yes
OutputDir=installer_output
OutputBaseFilename=ABHA_Card_Studio_v{#AppVersion}_Setup
SetupIconFile=abha_studio.ico
Compression=lzma2/ultra64
SolidCompression=yes
LZMAUseSeparateProcess=yes
LZMANumBlockThreads=4
WizardStyle=modern
; NOTE: WizardSmallImageFile MUST be exactly 55x58 px PNG.
; If your logo.png is a different size, comment this line out to avoid
; the "bitmap is not valid" error when launching the installer.
; WizardSmallImageFile=logo.png
ShowLanguageDialog=no
PrivilegesRequired=admin
PrivilegesRequiredOverridesAllowed=dialog
ArchitecturesAllowed=x64
ArchitecturesInstallIn64BitMode=x64
MinVersion=10.0.17763
UninstallDisplayIcon={app}\abha_studio.ico
UninstallDisplayName={#AppName} v{#AppVersion}
CreateUninstallRegKey=yes
RestartIfNeededByRun=no

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Files]
; ── Main application bundle ──
Source: "dist\{#AppFolder}\*"; \
    DestDir: "{app}"; \
    Flags: ignoreversion recursesubdirs createallsubdirs

; ── Tesseract OCR engine ──
Source: "dist\{#AppFolder}\tesseract\tesseract.exe"; \
    DestDir: "{app}\tesseract"; \
    Flags: ignoreversion

; ── Tamil font ──
Source: "dist\{#AppFolder}\NotoSansTamil-Bold.ttf"; \
    DestDir: "{app}"; \
    Flags: ignoreversion

Source: "dist\{#AppFolder}\NotoSansTamil-Bold.ttf"; \
    DestDir: "{fonts}"; \
    FontInstall: "Noto Sans Tamil Bold"; \
    Flags: onlyifdoesntexist uninsneveruninstall

; ── Malayalam font ──
Source: "dist\{#AppFolder}\NotoSansMalayalam-Bold.ttf"; \
    DestDir: "{app}"; \
    Flags: ignoreversion

Source: "dist\{#AppFolder}\NotoSansMalayalam-Bold.ttf"; \
    DestDir: "{fonts}"; \
    FontInstall: "Noto Sans Malayalam Bold"; \
    Flags: onlyifdoesntexist uninsneveruninstall

; ── Devanagari font ──
Source: "dist\{#AppFolder}\NotoSansDevanagari-Bold.ttf"; \
    DestDir: "{app}"; \
    Flags: ignoreversion

Source: "dist\{#AppFolder}\NotoSansDevanagari-Bold.ttf"; \
    DestDir: "{fonts}"; \
    FontInstall: "Noto Sans Devanagari Bold"; \
    Flags: onlyifdoesntexist uninsneveruninstall

; ── Logo PNG ──
Source: "dist\{#AppFolder}\logo.png"; \
    DestDir: "{app}"; \
    Flags: ignoreversion

; ── Logo ICO ──
Source: "dist\{#AppFolder}\logo.ico"; \
    DestDir: "{app}"; \
    Flags: ignoreversion

; ── App ICO (used for shortcuts and taskbar) ──
Source: "abha_studio.ico"; \
    DestDir: "{app}"; \
    Flags: ignoreversion

; ── Background images ──
Source: "dist\{#AppFolder}\background.jpg"; \
    DestDir: "{app}"; \
    Flags: ignoreversion

Source: "dist\{#AppFolder}\background2.jpg"; \
    DestDir: "{app}"; \
    Flags: ignoreversion

[Dirs]
Name: "{commonappdata}\{#AppDataDir}"; \
    Permissions: users-full admins-full system-full

[Icons]
; FIX: IconFilename points to abha_studio.ico copied into {app}
Name: "{group}\{#AppName}"; \
    Filename: "{app}\{#AppExeName}"; \
    IconFilename: "{app}\abha_studio.ico"; \
    Tasks: startmenuicon

Name: "{group}\Uninstall {#AppName}"; \
    Filename: "{uninstallexe}"; \
    Tasks: startmenuicon

Name: "{autodesktop}\{#AppName}"; \
    Filename: "{app}\{#AppExeName}"; \
    IconFilename: "{app}\abha_studio.ico"; \
    Tasks: desktopicon

[Tasks]
Name: "desktopicon";   Description: "Create a &desktop shortcut";    GroupDescription: "Shortcuts:"; Flags: checkedonce
Name: "startmenuicon"; Description: "Create a &Start Menu shortcut"; GroupDescription: "Shortcuts:"; Flags: checkedonce

[Registry]
Root: HKLM; \
    Subkey: "Software\{#AppName}"; \
    ValueType: string; ValueName: "InstallPath"; \
    ValueData: "{app}"; \
    Flags: uninsdeletekey createvalueifdoesntexist

Root: HKLM; \
    Subkey: "Software\{#AppName}"; \
    ValueType: string; ValueName: "Version"; \
    ValueData: "{#AppVersion}"; \
    Flags: createvalueifdoesntexist

[Run]
Filename: "{app}\{#AppExeName}"; \
    Description: "Launch {#AppName} now"; \
    Flags: nowait postinstall skipifsilent unchecked

[UninstallDelete]
Type: files;      Name: "{commonappdata}\{#AppDataDir}\license.key"
Type: files;      Name: "{tmp}\abha_studio_icon.ico"
Type: dirifempty; Name: "{commonappdata}\{#AppDataDir}"

[Code]
function InitializeSetup(): Boolean;
begin
  if not Is64BitInstallMode then
  begin
    MsgBox(
      '{#AppName} requires a 64-bit version of Windows 10 or later.' + #13#10 +
      'Setup will now exit.',
      mbError, MB_OK);
    Result := False;
    Exit;
  end;
  Result := True;
end;

function GetUninstallString(): String;
var
  sKey: String;
  sVal: String;
begin
  sKey := 'Software\Microsoft\Windows\CurrentVersion\Uninstall\{B7E2F1A3-4C8D-4E9F-A012-3B4C5D6E7F89}_is1';
  sVal := '';
  if not RegQueryStringValue(HKLM, sKey, 'UninstallString', sVal) then
    RegQueryStringValue(HKCU, sKey, 'UninstallString', sVal);
  Result := sVal;
end;

function IsUpgrade(): Boolean;
begin
  Result := GetUninstallString() <> '';
end;

procedure RemovePreviousVersion();
var
  sUninstall: String;
  iCode:      Integer;
begin
  sUninstall := GetUninstallString();
  if sUninstall = '' then Exit;
  sUninstall := RemoveQuotes(sUninstall);
  Exec(sUninstall, '/SILENT /NORESTART /SUPPRESSMSGBOXES',
       '', SW_HIDE, ewWaitUntilTerminated, iCode);
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssInstall then
  begin
    if IsUpgrade() then
    begin
      Log('Upgrade detected — removing previous version.');
      RemovePreviousVersion();
    end;
  end;
end;

procedure CurPageChanged(CurPageID: Integer);
var
  sExe:     String;
  sTess:    String;
  sMissing: String;
begin
  if CurPageID <> wpFinished then Exit;

  sExe     := ExpandConstant('{app}\{#AppExeName}');
  sTess    := ExpandConstant('{app}\tesseract\tesseract.exe');
  sMissing := '';

  if not FileExists(sExe)  then
    sMissing := sMissing + #13#10 + '  • abha_card_studio.exe';
  if not FileExists(sTess) then
    sMissing := sMissing + #13#10 + '  • tesseract\tesseract.exe';

  if not FileExists(ExpandConstant('{app}\NotoSansTamil-Bold.ttf')) then
    Log('WARNING: NotoSansTamil-Bold.ttf not in {app} — will try system fonts.');
  if not FileExists(ExpandConstant('{app}\NotoSansMalayalam-Bold.ttf')) then
    Log('WARNING: NotoSansMalayalam-Bold.ttf not in {app} — will try system fonts.');
  if not FileExists(ExpandConstant('{app}\NotoSansDevanagari-Bold.ttf')) then
    Log('WARNING: NotoSansDevanagari-Bold.ttf not in {app} — will try system fonts.');
  if not FileExists(ExpandConstant('{app}\logo.png')) then
    Log('WARNING: logo.png not in {app} — app will use fallback icon.');
  if not FileExists(ExpandConstant('{app}\logo.ico')) then
    Log('WARNING: logo.ico not in {app} — app will use fallback icon.');
  if not FileExists(ExpandConstant('{app}\abha_studio.ico')) then
    Log('WARNING: abha_studio.ico not in {app} — shortcut may show blank icon.');
  if not FileExists(ExpandConstant('{app}\background.jpg')) then
    Log('WARNING: background.jpg not in {app} — app will use fallback background.');
  if not FileExists(ExpandConstant('{app}\background2.jpg')) then
    Log('WARNING: background2.jpg not in {app} — app will use fallback background.');

  if sMissing <> '' then
    MsgBox(
      'Installation is incomplete. The following critical files were not found:' +
      sMissing + #13#10 + #13#10 +
      'Please reinstall or contact support.',
      mbError, MB_OK);
end;

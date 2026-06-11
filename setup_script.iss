; 物联网多源传感器数据分析系统 V1.0 — Inno Setup 安装脚本
#define MyAppName "物联网多源传感器数据分析系统"
#define MyAppShortName "物联网传感器分析"
#define MyAppVersion "1.1.0"
#define MyAppPublisher "xxu"
#define MyAppExeName "物联网传感器分析系统.exe"

[Setup]
AppId={{B8F3A2E1-4C7D-4A9E-8F2B-1D6C5A3E7F90}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\{#MyAppShortName}
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
OutputDir=installer
OutputBaseFilename=物联网传感器分析系统_V1.1_Setup
SetupIconFile=app_icon.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
WizardStyle=modern
Compression=lzma2/max
SolidCompression=yes
DiskSpanning=no
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
CloseApplications=no
DisableProgramGroupPage=yes
DisableWelcomePage=no
ShowLanguageDialog=no

[Languages]
Name: "en"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional shortcuts:"

[Files]
Source: "dist\物联网传感器分析系统\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "samples\*"; DestDir: "{app}\samples"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"
Name: "{group}\示例数据"; Filename: "{app}\samples"; WorkingDir: "{app}"
Name: "{group}\卸载 {#MyAppShortName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppShortName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "启动 {#MyAppShortName}"; Flags: postinstall nowait skipifsilent unchecked shellexec

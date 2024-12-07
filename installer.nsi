!include "MUI2.nsh"

Name "LocalMediaSearch"
OutFile "dist\LocalMediaSearch-Setup.exe"
InstallDir "$PROGRAMFILES\LocalMediaSearch"

!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

!insertmacro MUI_LANGUAGE "SimpChinese"

Section "MainSection" SEC01
    SetOutPath "$INSTDIR"
    File /r "dist\windows\LocalMediaSearch\*.*"
    
    CreateDirectory "$SMPROGRAMS\LocalMediaSearch"
    CreateShortCut "$SMPROGRAMS\LocalMediaSearch\LocalMediaSearch.lnk" "$INSTDIR\LocalMediaSearch.exe"
    CreateShortCut "$DESKTOP\LocalMediaSearch.lnk" "$INSTDIR\LocalMediaSearch.exe"
    
    WriteUninstaller "$INSTDIR\uninstall.exe"
SectionEnd

Section "Uninstall"
    Delete "$INSTDIR\uninstall.exe"
    RMDir /r "$INSTDIR"
    Delete "$SMPROGRAMS\LocalMediaSearch\LocalMediaSearch.lnk"
    Delete "$DESKTOP\LocalMediaSearch.lnk"
    RMDir "$SMPROGRAMS\LocalMediaSearch"
SectionEnd 
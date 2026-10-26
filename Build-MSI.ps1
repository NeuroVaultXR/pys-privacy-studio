$ErrorActionPreference='Stop'
Set-Location -LiteralPath $PSScriptRoot
New-Item -ItemType Directory -Force tools,outputs | Out-Null
Invoke-WebRequest 'https://api.nuget.org/v3-flatcontainer/wix/4.0.6/wix.4.0.6.nupkg' -OutFile tools/wix.zip
Expand-Archive -LiteralPath tools/wix.zip -DestinationPath tools/wix -Force
Invoke-WebRequest 'https://api.nuget.org/v3-flatcontainer/wixtoolset.ui.wixext/4.0.6/wixtoolset.ui.wixext.4.0.6.nupkg' -OutFile tools/ui.zip
Expand-Archive -LiteralPath tools/ui.zip -DestinationPath tools/ui -Force
dotnet tools/wix/tools/net6.0/any/wix.dll build work/PyS.wxs -arch x64 -ext tools/ui/wixext4/WixToolset.UI.wixext.dll -out outputs/PyS-PrivacyStudio.msi
if($LASTEXITCODE -ne 0){throw 'Compilazione MSI non riuscita'}

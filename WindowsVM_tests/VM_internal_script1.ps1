##Assuming the path to pacakges will have vf driver & pf driver (zipped) , ffmpeg installer.msi & vf driver .pdb for tracelogs
$parent_dir = $args[0]

cd "$parent_dir"
ls
$packages_path="$parent_dir\\packages"
$tracelogs_path="$parent_dir\\windows_dmesg"
$tests_path="$parent_dir\\teams_use_case_12_density_windows"
$input_path="$parent_dir\\Marathon_360p30_2M_2b_8bit_60K_fr_0A1V_ffmpeg6_h264.mp4"

#Write-Host "~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~DEBUG"
#Write-Host $packages_path
#Write-Host $tracelogs_path
#Write-Host $tests_path
#Write-Host $input_path
#Write-Host "~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~"

$vf_driver_path = Get-Item "$packages_path\\MA35-MCDM-VF*win64" 
$trace_log_vf_pdb_path="$pacakges_path\\ma35vfdrv.pdb"

#
# vf uninstall and  install
#

# remove existing drivers
  $all_drivers_list= pnputil /enum-drivers
echo "`[INFO`]Existing Drivers..."
echo $all_drivers_list
$existing_ma35_drivers= $all_drivers_list -join "\n" -split "\n\n" | Select-String -Pattern "Published Name:\s+(oem\d+\.inf).*?Original Name:\s+(ma35\w*)" -AllMatches | ForEach-Object { $_.Matches.Groups[1].Value }

foreach ($driver in $existing_ma35_drivers) {
    Write-Host "`[INFO`]Uninstalling driver: $driver"
    pnputil /delete-driver $driver /uninstall
	Start-Sleep -Seconds 5
}
# Install #302 DAB vf driver
echo "`[INFO`]Installing vf driver..."

Test-Path -Path $vf_driver_path\driver\ma35vfdrv\ma35vfdrv.inf

#pnputil /add-driver $vf_driver_path\driver\ma35vfdrv\ma35vfdrv.inf /install
pnputil /add-driver $vf_driver_path\driver\ma35vfdrv\ma35vfdrv.inf /install /force
# verify after installation  list of current drivers
pnputil /enum-drivers




#
#
# ffmpeg uninstall and installation 
#
#
Test-Path -Path $packages_path\\ma35-ffmpeg-installer.msi
$App = Get-WmiObject -Class Win32_Product | Where-Object{$_.Name -eq "MA35 FFMPEG"}
Write-Host "`[INFO`]ffmpeg details before installation"
Get-WmiObject -Class Win32_Product | Where-Object{$_.Name -eq "MA35 FFMPEG"} | Select-Object Name, InstallDate,IdentifyingNumber

if ($App) {
    Write-Host "`[INFO`]Uninstalling $ProgramName..."
    $App.Uninstall()
} else {
    Write-Host "`[INFO`]ffmpeg not found! Skipping ffmpeg uninstall step"
} 

#Start-Process msiexec "/i $packages_path\\ma35-ffmpeg-installer.msi /qn " #This exact cmd works directly, but doesnt show results after installation
$logPath = "$parent_dir\\install_log.txt"
Start-Process -FilePath "msiexec.exe" -ArgumentList "/i `"$packages_path\ma35-ffmpeg-installer.msi`" /qn /L*v `"$logPath`"" -Wait -NoNewWindow
Write-Host "Installation log saved at: $logPath"
Write-Host "`[INFO`]Installing Done..."
Write-Host "`[INFO`]ffmpeg details after installation"
Get-WmiObject -Class Win32_Product | Where-Object{$_.Name -eq "MA35 FFMPEG"} | Select-Object Name, InstallDate,IdentifyingNumber


#clear previous logs in test folder(everything except .bat
Write-Host "`[INFO`] clearing previous logs from test folder if any"
cd $tests_path
    Get-ChildItem -Path . | Where-Object { $_.Extension -ne ".bat" } | Remove-Item -Force -Recurse
$env:MA35_IGNORE_FPS_VERSION = 'true'
#
#Tracelogs
#
Test-Path -Path "$tracelogs_path\\trace_collection.bat"
cd $tracelogs_path
Remove-Item -Path "$tracelogs_path\dmesg.log*" -Force

#.\trace_collection.bat -start $trace_log_vf_pdb_path dmesg
#Start-Process -NoNewWindow -FilePath "$tracelogs_path\\trace_collection.bat -start $trace_log_vf_pdb_path dmesg" -Wait
#.\trace_collection.bat -start $trace_log_vf_pdb_path dmesg
#cd $tests_path
Test-Path -Path "$tests_path\\teamshw_nfr_nl_360p30_nondual_60Kfr_8bit_h264_h264_12den_1devs_12nondual.bat"
#Start-Process -NoNewWindow -FilePath "$tests_path\\teamshw_nfr_nl_360p30_nondual_60Kfr_8bit_h264_h264_12den_1devs_12nondual.bat"  #script terminates midway???
#Start-Process -NoNewWindow -FilePath "$tests_path\\windows_run_check_density.bat"
#& .\teamshw_nfr_nl_360p30_nondual_60Kfr_8bit_h264_h264_12den_1devs_12nondual.bat   #script terminates midway???
#cmd /c start "" ".\teamshw_nfr_nl_360p30_nondual_60Kfr_8bit_h264_h264_12den_1devs_12nondual.bat"


#& .\windows_run_check_density.bat
#Start-Process -FilePath "$tests_path\\windows_run_check_density.bat" -NoNewWindow
#Start-Sleep -Seconds 2

#Not triggered now , will be triggered by a second helper script that will do this 
#trace_collection.bat -stop trace_log_vf_pdb_path dmesg
#trace_collection.bat -parse trace_log_vf_pdb_path dmesg please use thie above and follow the steps
Write-host "Complete..."
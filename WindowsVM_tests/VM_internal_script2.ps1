##Assuming the path to pacakges will have vf driver & pf driver (zipped) , ffmpeg installer.msi & vf driver .pdb for tracelogs
$parent_dir = $args[0]

cd "$parent_dir"
ls
$packages_path="$parent_dir\\packages"
$tracelogs_path="$parent_dir\\windows_dmesg"
$tests_path="$parent_dir\\teams_use_case_12_density_windows"
$input_path="$parent_dir\\Marathon_360p30_2M_2b_8bit_60K_fr_0A1V_ffmpeg6_h264.mp4"

Write-Host "~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~DEBUG"
Write-Host $parent_dir
Write-Host $packages_path
Write-Host $tracelogs_path
Write-Host $tests_path
Write-Host $input_path
Write-Host "~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~"
$trace_log_vf_pdb_path="$packages_path\\ma35vfdrv.pdb"

#Stop tracelogs
#
cd $tracelogs_path
ls
Write-Host "`[INFO`] stop and parse trace logs "

#Start-Process -NoNewWindow -FilePath ".\\trace_collection.bat -stop $trace_log_vf_pdb_path dmesg" -Wait
#Start-Process -NoNewWindow -FilePath ".\\trace_collection.bat -parse $trace_log_vf_pdb_path dmesg please use thie above and follow the steps" -Wait
#Get-Process ffmpeg -ErrorAction SilentlyContinue | Stop-Process -Force
#Write-Host "`[INFO`] copy trace logs to run folder "
#Copy-Item -Path ".\\dmesg.log*" -Destination $tests_path -Force

.\trace_collection.bat -stop $trace_log_vf_pdb_path dmesg
.\trace_collection.bat -parse $trace_log_vf_pdb_path dmesg please use thie above and follow the steps
Get-Process ffmpeg -ErrorAction SilentlyContinue | Stop-Process -Force
Write-Host "`[INFO`] copy trace logs to run folder "
Copy-Item -Path ".\\dmesg.log*" -Destination $tests_path -Force
Write-host "Complete..."
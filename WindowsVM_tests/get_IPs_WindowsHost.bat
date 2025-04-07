# List of VM Names
$vmNames = @("vm21-COPY_xco2398-winDC-1vf","vm22-xco2398-winDC-1vf", "vm23-xco2398-winDC-1vf", "vm24-xco2398-winDC-1vf","vm25-xco2398-winDC-1vf", "vm26-xco2398-winDC-1vf", "vm27-xco2398-winDC-1vf","vm28-xco2398-winDC-1vf", "vm29-xco2398-winDC-1vf", "vm30-xco2398-winDC-1vf","vm31-xco2398-winDC-1vf", "vm32-xco2398-winDC-1vf", "vm33-xco2398-winDC-1vf","vm34-xco2398-winDC-1vf", "vm36-xco2398-winDC-1vf", "vm37-xco2398-winDC-1vf","vm38-xco2398-winDC-1vf", "vm39-xco2398-winDC-1vf", "vm40-xco2398-winDC-1vf","vm41-xco2398-winDC-1vf")  
#$vmNames = @("vm1-xhd140-windcfw-1vf","vm2-xhd140-windc-1vf","WindowsVM") 

#"" | Set-Content -Path ip_list.txt #causes spacing issues
#"" | Out-File -FilePath log.txt #same spacing issues here as well , 1 7 2 . 2 0 . 1 6 6 . 5 6  for example
Remove-Item -Path ip_list.txt -Force -ErrorAction SilentlyContinue

# Loop through each VM name and get its IP
foreach ($vm in $vmNames) {
    $vmInfo = Get-VM -Name $vm | Get-VMNetworkAdapter | Select-Object -ExpandProperty IPAddresses

    # Ensure it's an array and filter only IPv4 addresses
    $ipv4_vmInfo = $vmInfo | Where-Object { $_ -match "^\d+\.\d+\.\d+\.\d+$" }

    # Print only IPv4 addresses (one per line)
    if ($ipv4_vmInfo) {
	    #Write-Host $vm
        $ipv4_vmInfo | ForEach-Object { Write-Host $_ }
        $ipv4_vmInfo | Out-File -Append -FilePath ip_list.txt
    }
    else{
    Write-Host "No IP assigned for $vm  or The VM might be in shutdown state"
    $vm | Out-File -Append -FilePath ip_list.txt
    }
}

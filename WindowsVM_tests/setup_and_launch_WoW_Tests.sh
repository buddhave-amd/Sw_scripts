#!/bin/bash


if [ "$#" -ne 4 ]; then
    echo "Error: Expected 3 arguments, but received $#."
    echo "Usage: $0 <script_path> <package_path> <intermediate_package_folder_name> <dependancy_check> "
	echo "script_path : script path containing commands to be run inside Vms "
	echo "package_path : path to pacakges- Must contain vf driver zip file, ffmpeg installation msi , vf driver pdb"
    echo "intermediate_package_folder_name : name for intermediate pacakges folder "
    echo "dependancy_check: checks for dependency files in remte & adds them if not present [0 or 1], 1 for performing dependency steps, 0 for Only executing script in all Ips(no dependancy steps)"
    exit 1
fi
LocalScript=$1 #This has commands to be run inside VM
host_pacakges_folder_ori=$2
test_folder_name=$3
dependancy_check_flag=$4
script_base_name=$(basename "$LocalScript")

echo $LocalScript
echo $host_pacakges_folder_ori
echo $test_folder_name
echo $dependancy_check_flag
#CONFIGURABLE VARS
Username=""
Password=""
RemoteBaseDir='C:\\Users\\videobuild\\xlnx_test' # Path where the script will be copied & executed
RemoteScriptPath="C:\\Users\\videobuild\\xlnx_test\\$script_base_name"
IP_LIST="ip_list.txt"          # File containing list of IPs 
dependencies_path="/proj/dcgss/users/buddhave/VM_crash_exp/TO_COPY" #Accessible from xhdswlabcompute04
DEPENDENCIES_TO_CHECK=("Marathon_360p30_2M_2b_8bit_60K_fr_0A1V_ffmpeg6_h264.mp4" "windows_dmesg" "teams_use_case_12_density_windows")



set -x


### TBD ? (currently manual step) - DO PF INSTALLATION, get IPs of VMs, reboot of host & start of all Vms followed by get IPs from this script ?

# Check if the IP list file exists
if [[ ! -f "$IP_LIST" ]]; then
    echo "Error: IP list file '$IP_LIST' not found in current directory. Exiting...!"
    exit 1
fi

dos2unix $IP_LIST

	if [[ "$dependancy_check_flag" -eq 1 ]]; then
	    echo "##########copy dependency files/folders if not existing"
	    
	    host_current_dir=$(pwd)
        host_package_path=${host_current_dir}/${test_folder_name}_package
        vf_driver=$(ls ${host_pacakges_folder_ori}/MA35-MCDM-VF*win64.zip | grep -v Baremetal)
        
        #copy packages 
	    echo "#copying required files from given packages"
        mkdir -p $host_package_path
		unzip -o $vf_driver -d $host_package_path/
        #unzip -o $host_pacakges_folder_ori/MA35-MCDM-PF*win64-driver.zip -d $host_package_path #PF driver not required inside VM , if needed to be done in host then use
        cp $host_pacakges_folder_ori/ma35-ffmpeg-installer.msi $host_package_path
        cp $host_pacakges_folder_ori/ma35vfdrv.pdb $host_package_path
        #echo $(basename $(ls $host_package_path/*VF*)) > $host_package_path/vf_driver_name.txt
    fi
# Loop through each IP in the list
while IFS= read -r IP; do
    echo -e "\nProcessing: $IP"
    
	# Ensure the remote parent test directory exists , create if not
	echo "##########check & create Test dir in remote"
	
	    CREATE_DIR_CMD="powershell -c \"if (!(Test-Path -Path '${RemoteBaseDir}')) { mkdir '${RemoteBaseDir}'/  }\""
	#echo "sshpass -p \"$Password\" ssh \"${Username}@${IP}" "${CREATE_DIR_CMD}\""
    sshpass -p "$Password" ssh "${Username}@${IP}" "${CREATE_DIR_CMD}" < /dev/null
	
    #CREATE_DIR_CMD="powershell -c \"if (!(Test-Path -Path '${RemoteBaseDir}')) { New-Item -Path '${RemoteBaseDir}' -ItemType Directory }\""
	##echo "sshpass -p \"$Password\" ssh \"${Username}@${IP}" "${CREATE_DIR_CMD}\""
    #sshpass -p "$Password" ssh "${Username}@${IP}" "${CREATE_DIR_CMD}" < /dev/null
	

    # Dependancy checks & setup
    if [[ "$dependancy_check_flag" -eq 1 ]]; then
	    
	    echo "#copy pacakges to remote"
	    sshpass -p "$Password" ssh -o StrictHostKeyChecking=no "${Username}@${IP}" "powershell -Command \"if (Test-Path '${RemoteBaseDir}/packages') { Remove-Item '${RemoteBaseDir}/packages/*' -Recurse -Force }\"" < /dev/null

		sshpass -p "$Password" ssh -o StrictHostKeyChecking=no ${Username}@${IP} "powershell -Command \"if (!(Test-Path -Path '${RemoteBaseDir}/packages')) { mkdir ${RemoteBaseDir}/packages}\"" < /dev/null
	    sshpass -p "$Password" ssh -o StrictHostKeyChecking=no ${Username}@${IP} "powershell -Command \"if (!(Test-Path -Path '${RemoteBaseDir}/packages')) { New-Item -Path '${RemoteBaseDir}/packages' -ItemType Directory }\"" < /dev/null
	    sshpass -p "$Password" scp -o StrictHostKeyChecking=no -r ${host_package_path}/* ${Username}@${IP}:${RemoteBaseDir}/packages/ < /dev/null
	    
        
        # Loop through files and copy only if missing
	    echo "copy dependencies to remote (if not existing)"
        for file in "${DEPENDENCIES_TO_CHECK[@]}"; do
            #if ! sshpass -p "$Password" ssh -o StrictHostKeyChecking=no "${Username}@${IP}" "powershell -Command \"Test-Path '${RemoteBaseDir}\\$file'\"" | grep -q "True" < /dev/null; then
                #scp -r"$file" "$IP:${RemoteBaseDir}/"
	    		sshpass -p "$Password" scp -r -o StrictHostKeyChecking=no  "$dependencies_path/${file}" ${Username}@${IP}:${RemoteBaseDir}/ < /dev/null
                echo "#Copied $file to $IP"
            #fi
        done
    else
	    echo "##########skipping dependency files/folders check"
	fi	
    
	# Copy the script to the remote machine
	echo "##########copy script to remote"
    sshpass -p "$Password" scp -o StrictHostKeyChecking=no  ${LocalScript} ${Username}@${IP}:${RemoteBaseDir} < /dev/null
	


    # Execute the script on the remote machine
	echo "##########execute script in remote"
    #EXEC_CMD="powershell -ExecutionPolicy Bypass -File ${RemoteScriptPath} -ArgumentList '${RemoteBaseDir}'"
	EXEC_CMD="powershell -ExecutionPolicy Bypass -File ${RemoteScriptPath}  ${RemoteBaseDir}"
    sshpass -p "$Password" ssh "$Username@$IP" "$EXEC_CMD" < /dev/null

    ## Remove the script after execution
	#echo "##########remove script"
    #DELETE_CMD="powershell -c \"Remove-Item -Path '$RemoteScriptPath' -Force\""
    #sshpass -p "$Password" ssh "$Username@$IP" "$DELETE_CMD" < /dev/null
done < "$IP_LIST"

##WAIT FOR 30 mins , launch a second template script /directly run tracelog stop & parse and then scp the Logs back to the host (folder names as IPs/ VM names?)

echo -e "\nAll remote executions completed!"

set +x

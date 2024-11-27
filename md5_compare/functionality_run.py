#!/usr/bin/env python3

import psutil
import signal
import subprocess
import sys
import time
import os
import re
import hashlib
import shutil
import platform
from datetime import datetime

linux_path="/proj/video_qa/MA35_QA"
windows_mapped_drive_path="T:"
linux_path_fmg="/opt/amd/ama/ma35/bin/ffmpeg"
windows_path_fmg="ffmpeg"
TC_output_Destination_folder='TC_outputs'
md5empty="d41d8cd98f00b204e9800998ecf8427e"
prev_fname="NULL"
device=0
timeout_value = 600
av1_ama = "-c:v av1_ama -type 2"
file_pattern="_out_file.txt"
op_file_name="results.csv"
header = ["TC id","Execution_Result","MD5 golden","MD5 sum","CR number","Error","Executed Command"]
retain = 0
LAST_N_LINES = 8

def time_stamp():
    current_timestamp = datetime.now()
    return current_timestamp.strftime("%Y-%m-%d_%H-%M-%S")

def Get_OS_kernal(tag):
    # Get the operating system version like U20,U22
    OS_ID = subprocess.check_output("cat /etc/os-release | grep ^ID=", shell=True).decode(
        'utf8').strip().split('=')[1].strip('"')[0].lower()
    OS_Version_ID = subprocess.check_output("cat /etc/os-release | grep ^VERSION_ID=", shell=True).decode(
        'utf8').strip().split('=')[1].split('.')[0].strip('\"')
    os_version = OS_ID + OS_Version_ID
    # Get the kernel version
    kernel_version = platform.release().split('-')[0].replace('.','')
    return tag + '_' + os_version + '_' + kernel_version

if "win" in sys.platform:
    cur_platform = 'windows'
else:
    cur_platform = 'linux'

if cur_platform == 'windows':
    exclude_folders = ["\\v0\\", "\\v1\\", "\\v2\\", "\\v3\\"]
else:
    exclude_folders = ["/v0/", "/v1/", "/v2/", "/v3/"]

def killfunc(application):
    for i in range(10):
        print(f"Killing {application}")
        subprocess.Popen(f"pkill -u $USER -SIGINT {application}", shell=True)
        time.sleep(1)
        try:
            process_remaining = int(subprocess.check_output(f"ps aux | grep -w '{application} ' | grep -w $USER | grep -v grep -c", shell=True))
            if process_remaining == 0:
                return
        except subprocess.CalledProcessError as e:
            return

    while True:
        print(f"Killing {application} with SIGKILL")
        subprocess.Popen(f"pkill -u $USER -SIGKILL {application}", shell=True)
        time.sleep(1)
        try:
            process_remaining = int(subprocess.check_output(f"ps aux | grep -w '{application} ' | grep -w $USER | grep -v grep -c", shell=True))
            if process_remaining == 0:
                return
        except subprocess.CalledProcessError as e:
            return

def killfunc_win(process_name):
    while True:
        try:
            subprocess.run(["taskkill", "/F", "/IM", process_name], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            print(f"Successfully killed {process_name}")
        except subprocess.CalledProcessError as e:
            stderr_output = e.stderr.decode('utf-8')
            if "not found" in stderr_output.lower():
                print(f"No {process_name} found. Exiting...")
                break
            else:
                print(f"Error: Unable to kill {process_name}. Retrying...")
        time.sleep(1)

def create_device(device_num):
    dev_str =  " -hwaccel ama -hwaccel_device /dev/ama_transcoder" + str(device_num) + " "
    return dev_str

def add_at_pos(command,addpos,param_to_add):
    splitcmd = command.split()
    splitcmd.insert(addpos,param_to_add)
    return (' '.join(splitcmd))

def remove_device(command):
    command_out = remove_param(command,"-init_hw_device")
    command_out = remove_param(command_out,"-hwaccel")
    command_out = remove_param(command_out,"-hwaccel_device")
    return command_out

def remove_param(command,param_to_remove):
    splitcmd = command.split()
    temp_command = []
    removed = 0
    length = len(splitcmd)
    for i in range(length):
        if splitcmd[i] == param_to_remove:
            removed = 1
            if param_to_remove == "-y" or param_to_remove == "-n":
                removed = 0
        else:
            if removed == 1:
                removed = 0
                if splitcmd[i][0] == "-" and splitcmd[i][0].isdigit():
                    temp_command.append(splitcmd[i])
            else:
                temp_command.append(splitcmd[i])
                removed = 0

    return (' '.join(temp_command))

def change_cmd_md5sum(command):
    splitcmd = command.split()
    for i in range(len(splitcmd)):
        if splitcmd[i] == "-i":
           break
    start=i
    num_op = 0
    for i in range(start,len(splitcmd)):
        if splitcmd[i] == "-f":
            splitcmd[i+1] = "md5"
            num_op = num_op + 1
        elif splitcmd[i] == "-y":
            name="-"
            splitcmd[i] = name
            splitcmd[i+1] = ''
    ret_cmd = " ".join(splitcmd)
    if cur_platform == 'windows':
        ret_cmd=ret_cmd.replace(linux_path,windows_mapped_drive_path)
        ret_cmd=re_cmd.replace(linux_path_fmg,windows_path_fmg)
    ret_cmd=ret_cmd.replace("'","\"")
    return ret_cmd,num_op

def initial_cleanup(basepath):
    print(f"Initial cleanup of all files with name {file_pattern} in it")
    if os.path.isdir(basepath):
        for root,d_names,f_names in os.walk(basepath):
            for f in f_names:
                if file_pattern in f:
                    filepath=os.path.join(root, f)
                    try:
                        os.remove(filepath)
                    except FileNotFoundError:
                        continue
    else:
        f=basepath
        if file_pattern in f:
            try:
                os.remove(f)
            except FileNotFoundError:
                return


def write_file(test_id,density,fps,md5val,command,filename):
    outfilename = filename.replace(".txt",file_pattern)
    with open(outfilename, 'a+') as f:
        f.write(",".join([test_id,density,fps,md5val,command])+"\n")

def file_overwrite(basepath):
    if os.path.isdir(basepath):
        for root,d_names,f_names in os.walk(basepath):
            for f in f_names:
                filepath=os.path.join(root, f)
                if file_pattern in f and all(x not in filepath for x in exclude_folders):
                    try:
                        newfilepath=filepath.replace(file_pattern,".txt")
                        os.remove(newfilepath)
                    except FileExistsError as e:
                        pass
                    os.rename(filepath,newfilepath)
    else:
        print(f"Overwriting {basepath}")
        f=basepath
        newfilepath=f.replace(".txt",file_pattern)
        try:
            os.remove(f)
        except FileNotFoundError as e:
            pass
        os.rename(newfilepath,f)

def extract_md5sum_from_file(log_name,log_out_name):
    md5_arr=[]
    num_md5 = 0
    global cur_platform
    try:
        with open(log_name ,'r') as log:
            if cur_platform != 'windows':
                log_out=open(log_out_name ,'w')
            for line in log:
                if "md5=" in line.lower():
                    line_split = line.strip().split('=')
                    md5sum_val = line_split[1].strip()
                    if md5empty == md5sum_val:
                        md5sum_val = "NULL"
                    else:
                        num_md5 = num_md5 + 1
                    md5_arr.append(md5sum_val)
            if cur_platform != 'windows':
                line = line.replace('\r','\n')
                log_out.write(line)
        if cur_platform != 'windows':
           log_out.close()
    except (IOError, OSError, UnicodeError) as e:
        print(f"Unable to open file : {log_name} or {log_out_name}")
        return "NULL",0
    return md5_arr,num_md5

def md5sum(filename):
    hasher = hashlib.md5()
    with open(filename, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b''):
            hasher.update(chunk)
    return hasher.hexdigest()

def generate_md5sum_using_tc_outputs(out_name):
    global TC_output_Destination_folder
    global retain
    md5_arr=[]
    num_md5 = 0
    global cur_platform
    for op in range(len(out_name)):
        if os.path.exists(out_name[op]):
            md5sum_val = md5sum(out_name[op])
            if retain == 1:
                try:
                    shutil.move(out_name[op], TC_output_Destination_folder)
                except shutil.Error:
                    try:
                        shutil.copy2(out_name[op], TC_output_Destination_folder)
                        os.remove(out_name[op])
                    except Exception as e:
                        print(f"ERROR: Failed to copy TC output file {out_name[op]} to {TC_output_Destination_folder} because of error {e}")
            else:
                os.remove(out_name[op])
                print(f"TC output {out_name[op]} deleted")

            if md5empty == md5sum_val:
                md5sum_val = "NULL"
            else:
                num_md5 = num_md5 + 1
        elif any(out_name[op].split('.')[-1] == ext for ext in ['jpg', 'jpeg', 'avif']):
            md5sum_val = 'NULL'
            if retain == 1:
                try:
                    for filename in os.listdir(os.getcwd()):
                        if any(ex in filename for ex in ['.jpg', '.jpeg', '.avif']):
                            shutil.move(filename, TC_output_Destination_folder)
                except:
                    for filename in os.listdir(os.getcwd()):
                        if any(ex in filename for ex in ['.jpg', '.jpeg', '.avif']):
                            shutil.copy2(filename, TC_output_Destination_folder)
                            os.remove(filename)
            else:
                for filename in os.listdir(os.getcwd()):
                    if any(ex in filename for ex in ['.jpg', '.jpeg', '.avif']):
                        os.remove(filename)
                        print(f"TC output {filename} deleted")

        else:
            print(f"file not exist: {out_name[op]}")
            # return "NULL", 0
            md5sum_val = 'NULL'
        md5_arr.append(md5sum_val)
    return md5_arr, num_md5

def find_error_code(file_name):
    if os.path.exists(file_name):
        f = open(file_name)
        error_arr=[]
        for line in f:
            # Feed the file text into findall(); it returns a list of all the found strings
            r = re.compile(r'ERROR | \bUnable\b | \bUndefined\b | \bFail\b | \bSegmentation\b | \babort | \bCore\sdump\b | \bInvalid\b | Conversion failed! | \bSIGSEGV\b', flags=re.I | re.X)
            if r.search(line) and 'error: 0' not in line:
                error_arr.append(line.strip())
        return (';'.join(error_arr)).replace(","," ")

def set_output_filenames_gst(command,tc_num,out_tag):
    splitcmd = command.split()
    out_num=1
    out_file_names=[]
    for i in range(len(splitcmd)):
        if out_tag in splitcmd[i]:
            tc_name_ext = ''
            if 'location=' in splitcmd[i+1]:
                tc_name = splitcmd[i+1].strip().split('=')[1].split('.')
                if len(tc_name) == 2:
                    if '%03d' in tc_name[0]:
                        tc_name_ext = '_%03d' + '.' + tc_name[1]
                    else:
                        tc_name_ext =  '.' + tc_name[1]
            else:
                return out_file_names, command

            name="TC_op_" + str(tc_num) + "_" + str(out_num) + tc_name_ext
            splitcmd[i+1] = 'location=' + name + (splitcmd[i+1][-1] if (not tc_name_ext) and (splitcmd[i+1][-1] == "'" or splitcmd[i+1][-1] == '"') else '')
            out_file_names.append(name.strip('"'))
            out_num = out_num + 1

    ret_cmd = " ".join(splitcmd)
    if cur_platform == 'windows':
        ret_cmd=ret_cmd.replace(linux_path,windows_mapped_drive_path)
        ret_cmd=ret_cmd.replace(linux_path_fmg,windows_path_fmg)
        # if not CheckDoubleQuoteInsideSingleQuote(ret_cmd):
        ret_cmd = ret_cmd.replace("'", "\"")
    return out_file_names,ret_cmd

def set_output_filenames(command,tc_num,out_tag):
    splitcmd = command.split()
    for i in range(len(splitcmd)):
        if splitcmd[i] == "-i":
           break
    start=i
    out_num=1
    out_file_names=[]
    for i in range(start,len(splitcmd)):
        if splitcmd[i] == out_tag:
            if '-' in splitcmd[i+1][0]:
                return out_file_names,command
            tc_name_ext = ''
            if splitcmd[i+1] != '/dev/null':
                tc_name = splitcmd[i+1].strip().split('.')
                if len(tc_name) == 2:
                    if '%03d' in tc_name[0]:
                        tc_name_ext = '_%03d' + '.' + tc_name[1]
                    else:
                        tc_name_ext =  '.' + tc_name[1]


            name="TC_op_" + str(tc_num) + "_" + str(out_num) + tc_name_ext
            splitcmd[i+1] = name
            out_file_names.append(name)
            out_num = out_num + 1

    ret_cmd = " ".join(splitcmd)
    if cur_platform == 'windows':
        ret_cmd=ret_cmd.replace(linux_path,windows_mapped_drive_path)
        ret_cmd=ret_cmd.replace(linux_path_fmg,windows_path_fmg)
        if not CheckDoubleQuoteInsideSingleQuote(ret_cmd):
            ret_cmd = ret_cmd.replace("'", "\"")
    return out_file_names,ret_cmd

def validate_console_log(log_file_name,app):
    try:
        with open(log_file_name, 'r') as sf:
            sf.seek(0, 2)
            end_position = sf.tell()
            line_count = 0
            position = end_position
            while position >= 0:
                sf.seek(position)
                current_char = sf.read(1)
                if current_char == '\n':
                    line_count += 1
                    if line_count == LAST_N_LINES:
                        break
                position -= 1
            sf.seek(position + 1)
            for log_data in sf:
                #below condition for checking logs ffmpeg ,gst,xma
                if app == 'ffmpeg':
                    if all(sub_str in log_data for sub_str in ['video:','audio:','subtitle:']) or any(sub_str in log_data for sub_str in [' PSNR ',' SSIM ']) or re.search(r']\s+V:\s+\d+',log_data):
                        return True
                elif app == 'gst-launch-1.0':
                    if 'Execution ended after' in log_data:
                        for log_data_1 in sf:
                            r = re.compile(r'Caught SIG\w+')
                            if r.search(log_data_1):
                                return False
                        else:
                            return True
                elif 'ma35' in app:
                    if 'Total FPS: ' in log_data:
                        return True
            else:
                return False
    except (IOError, OSError, UnicodeError, IndexError) as e:
        print(f"Unable to open file : {log_file}, ERROR:{e}")
        return False

def log_file(log_name,log_out_name):
    if cur_platform == 'windows':
        file_name = log_name
    else:
        try:
            with open(log_name,'r') as sf:
                file_data = sf.read()
                file_data = file_data.replace('\r', '\n')
                with open(log_out_name,'w') as df:
                    df.write(file_data)
        except (IOError, OSError, UnicodeError) as e:
            print(f"Unable to open file : {log_name} or {log_out_name}")
        file_name = log_out_name
    return file_name

def check_param_in(cmd,param):
    cmdffmpeg_list = cmd.strip().split()
    try:
        i_index = cmdffmpeg_list.index('-i')
        if '-' == cmdffmpeg_list[i_index + 1][0]:
            print(f'ERROR: Inputvector is missing in Command \n=====================:{cmd}\n=========================')
            return False
    except ValueError:
        print(f'ERROR: Input vector is missing in Command \n=====================:{cmd}\n=========================')
        return False
    if param in cmdffmpeg_list[i_index]:
        return True
    return False

def check_param_out(cmd,param):
    cmdffmpeg_list = cmd.strip().split()
    try:
        i_index = cmdffmpeg_list.index('-i')
        if '-' == cmdffmpeg_list[i_index + 1][0]:
            print(f'ERROR: Inputvector is missing in Command \n=====================:{cmd}\n=========================')
            return False
    except ValueError:
        print(f'ERROR: -i is missing in Command \n=====================:{cmd}\n=========================')
        return False
    if param in cmdffmpeg_list[i_index+1:]:
        return True
    return False

def get_param(command,param_to_search):
    param_val = "NULL"
    splitcmd = command.split()
    for i in range(len(splitcmd)):
        if splitcmd[i] == param_to_search:
            param_val = splitcmd[i+1]
            break
    return param_val
def CheckDoubleQuoteInsideSingleQuote(command):
    # Define the regular expression to match single quotes inside double quotes
    stack = []
    for i in command:
        if i == '"':
            if not stack:
                stack.append(i)
            else:
                stack.pop()
        if i == "'":
            if stack:
                return True
    return False

def Kill_application(process_name):
    # Iterate over all running processes
    for proc in psutil.process_iter(['pid', 'name']):
        if process_name == proc.info['name']:  # Check if the process name matches
            try:
                print(f"Found process: {proc.info['name']} with PID: {proc.info['pid']}")
                proc.terminate()  # Attempt to terminate the process
                proc.wait(timeout=5)  # Wait for the process to terminate
                print(f"Terminated process: {proc.info['name']} with PID: {proc.info['pid']}")
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.TimeoutExpired) as e:
                print(f"Could not terminate process {proc.info['pid']}: {e}")
                raise SystemExit(f'ERROR: Unable to terminate process, Exception: {e}')
                
def run_func_test(tc_num,dev,cmd,md5val,cr_num,app):
    global timeout_value
    #killing the application before executing the command
    if cur_platform == 'windows':
        Kill_application(app + '.exe')
    else:
        Kill_application(app)
    subp_arr=[]
    j=0
    cmd = cmd.strip()
    if 'ffmpeg' == app and check_param_out(cmd,'-y'):
        out_tag = '-y'
    elif 'gst-launch-1.0' == app and  'filesink location' in cmd:
        out_tag = 'filesink'
    elif 'ma35' in app and check_param_out(cmd,'-o'):
        out_tag = '-o'
    else:
        print(f"Command executed : {cmd}")
        print(f"Wrong format of command. output missing!!")
        return 'FAIL',md5val,'NULL',cr_num,"Wrong format of command output or -i missing",cmd

    if app == 'ffmpeg':
        cmdlineread = remove_device(cmd)
        cmdlineread = add_at_pos(cmdlineread,1,create_device(dev))
        cmdlineread = add_before(cmdlineread, "-i", "-nostdin")
    elif 'gst-launch-1.0' == app:
        cmdlineread = re.sub(r'\bdevice\s*=\s*\S+', f'device={dev}', cmd)
    elif 'ma35' in app:
        cmdlineread = re.sub(r'-d\s+\S+', f'-d {dev}', cmd)

    if 'gst-launch-1.0' == app:
        tc_out_names, new_cmd = set_output_filenames_gst(cmdlineread, tc_num, out_tag)
    else:
        tc_out_names,new_cmd = set_output_filenames(cmdlineread,tc_num,out_tag)

    if not tc_out_names:
        return 'FAIL', md5val, 'NULL', cr_num, "Output is missing in command", cmd

    if 'gst-launch-1.0' == app:
        try:
            input_file = re.findall(r'filesrc location=([^\s]+)',new_cmd)[0]
        except:
            print(f"InputVector not found in  command ==> {new_cmd}")
            return 'FAIL', md5val, 'NULL', cr_num, "InputVector not found", cmd
    else:
        input_file = get_param(new_cmd, "-i")
        
    if not os.path.isfile(input_file) and '%' not in input_file:
        print(f"InputVector not exist:==>{input_file}")
        return 'FAIL',md5val,'NULL',cr_num,"InputVector not exist",cmd

    log_app = app.split('-')[0].split('_')[0]
    log_name=f'log_{log_app}_run_functest.txt'
    log_out_name = f'log_{log_app}_run_functest_out.txt'
    command_exec = new_cmd + " > " + log_name + " 2>&1"
    print(f"Command executed : {command_exec}")

    try:
        subp  = subprocess.Popen(command_exec,shell=True)
        return_code = subp.wait(timeout=timeout_value)
    except subprocess.TimeoutExpired:
        print("Command execution timed out")
        try:
            process = psutil.Process(subp.pid)
            for proc in process.children(recursive=True):
                proc.terminate()
                proc.wait(timeout=10)
            process.terminate()
            proc.wait(timeout=10)
            md5_arr, num_md5 = generate_md5sum_using_tc_outputs(tc_out_names)
            return 'FAIL',md5val,'NULL',cr_num,"Command execution timed out",new_cmd
        except Exception as e:
            raise SystemExit(f'ERROR: Unable to terminate process, Exception: {e}')

    except Exception as e:
        raise SystemExit(f'An unexpected error occurred: {e}')

    error_code = "NA"
    execution_result = "PASS"
    md5_arr,num_md5 = generate_md5sum_using_tc_outputs(tc_out_names)
    file_name = log_file(log_name, log_out_name)
    if not return_code:
        #'Execution ended after' -->for gst
        #'Total FPS:' -->for xma
        log_status = validate_console_log(file_name,app)
    else:
        log_status = False

    md5valout=md5val
    if len(tc_out_names) != num_md5 and not any(re.search(r'%0[0-9]d', tc_name) for tc_name in tc_out_names):
        execution_result = "FAIL"
    md5sum_op = ';'.join(md5_arr)
    if execution_result != "FAIL":
        if md5val != md5sum_op:
            if md5val != str(0):
                execution_result = "FAIL"
                error_code = "md5sum mismatch"
            if log_status:
                md5valout = md5sum_op

    if execution_result == "FAIL":
        cr_num_local = cr_num
    else:
        cr_num_local = "NA"
    if execution_result == "FAIL" or not log_status:
        if not (error_code == "md5sum mismatch" and log_status):
            execution_result = "FAIL"
            error_code= find_error_code(file_name)
            if not error_code:
                error_code = f"{app} command terminated without error"
                md5sum_op = 'NA'

    new_log_name=file_name.replace(".txt","_"+tc_num+".txt")
    try:
        os.remove(new_log_name)
    except FileNotFoundError:
        pass

    try:
        os.rename(file_name,execution_result+'_'+new_log_name)
    except FileExistsError:
        os.remove(execution_result+'_'+new_log_name)
        os.rename(file_name,execution_result+'_'+new_log_name)

    #print(",".join(header))
    #printval = [str(tc_num),execution_result,md5val,md5sum_op,cr_num_local,error_code]
    #print(",".join(printval))
    print(f"Result : {str(tc_num)},execution_status:{execution_result},md5sum:{md5sum_op}, Err_code:{error_code}\n")
    return execution_result,md5valout,md5sum_op,cr_num_local,error_code,new_cmd

def prepare_cr_table(cr_file_path):
    cr_list={}
    #prepare CR table
    try:
        with open(cr_file_path,'r') as crfile:
            for crentry in crfile:
                crentry_tmp = crentry.strip()
                if not crentry_tmp:
                    continue
                crentry_list=crentry_tmp.split(',')
                if((crentry_list[0].strip())[0] == '#'):
                    continue
                cr_list[crentry_list[0].strip()] = crentry_list[1].strip()

    except (IOError, OSError):
        pass
    return cr_list

def remove_command_out(command,param_to_remove):
    splitcmd = command.split()
    temp_command = []
    removed = 0
    length = len(splitcmd)

    for j in range(length):
        if splitcmd[j] == "-i":
            break
        else:
            temp_command.append(splitcmd[j])

    for i in range(j,length):
        if splitcmd[i] == param_to_remove:
            removed = 1
            if param_to_remove == "-y" or param_to_remove == "-n":
                removed = 0
        else:
            if removed == 1:
                removed = 0
                if splitcmd[i][0] == "-" and splitcmd[i][0].isdigit():
                    temp_command.append(splitcmd[i])
            else:
                temp_command.append(splitcmd[i])
                removed = 0

    return (' '.join(temp_command))

def remove_command_in(command,param_to_remove):
    splitcmd = command.split()
    temp_command = []
    removed = 0
    length = len(splitcmd)
    for i in range(length):
        if splitcmd[i] == param_to_remove:
            removed = 1
            if param_to_remove == "-y" or param_to_remove == "-n":
                removed = 0
        else:
            if removed == 1:
                removed = 0
                if splitcmd[i][0] == "-" and splitcmd[i][0].isdigit():
                    temp_command.append(splitcmd[i])
            elif splitcmd[i] == "-i":
                temp_command.extend(splitcmd[i:])
                break
            else:
                temp_command.append(splitcmd[i])
                removed = 0

    return (' '.join(temp_command))

def add_before(command,param_before,param_to_add):
    splitcmd = command.split()
    temp_command = []
    for i in range(len(splitcmd)):
        if splitcmd[i] == param_before:
            temp_command.append(str(param_to_add))
        temp_command.append(splitcmd[i])
    return (' '.join(temp_command))

def add_before_opside(command,param_before,param_to_add):
    command = command.strip().split(' -i ')
    splitcmd = command[1].split()
    temp_command = []
    for i in range(len(splitcmd)):
        if splitcmd[i] == param_before:
            temp_command.append(str(param_to_add))
        temp_command.append(splitcmd[i])
    return (command[0]+' -i '+' '.join(temp_command))

def add_in_params(command,in_args):
    in_args_arr = in_args.split(',')
    new_cmd = command
    for num in range(0,len(in_args_arr),2):
        new_cmd = remove_command_in(new_cmd,in_args_arr[num])
        if in_args_arr[num+1].lower() == "na":
            new_cmd = add_before(new_cmd,"-i",in_args_arr[num])
        else:
            new_cmd = add_before(new_cmd,"-i",f"{in_args_arr[num]} {in_args_arr[num+1]}")
    return new_cmd

def add_out_params(command,out_args):
    out_args_arr = out_args.split(',')
    new_cmd = command
    for num in range(0,len(out_args_arr),2):
        new_cmd = remove_command_out(new_cmd,out_args_arr[num])
        if out_args_arr[num+1].lower() == "na":
            new_cmd = add_before_opside(new_cmd,"-y",out_args_arr[num])
        else:
            new_cmd = add_before_opside(new_cmd,"-y",f"{out_args_arr[num]} {out_args_arr[num+1]}")
    return new_cmd

if cur_platform == 'windows':
    exclude_folders = ["\\v0\\", "\\v1\\", "\\v2\\", "\\v3\\"]
else:
    exclude_folders = ["/v0/", "/v1/", "/v2/", "/v3/"]

def script_usage():
    global timeout_value
    global device
    global prev_fname
    print(f"Usage : python3 {sys.argv[0]} -p <path of command_files> -K <lvol or lvow or wvow or wvol or bare> [Optional arguments]")
    print(f'Please provide host and guest os tag using -K: Example ==> -K lvol, -K lvow, -K wvow, -K wvol -K bare')
    print("Optional arguments  :")
    print(" -f :Forcefully overwrite input files. This can be used to create golden md5sum")
    print(" -r :Retain the TC outputs in ./TC_output folder. This can be used to Visually check the TC Outputs")
    print(f" -t : Timeout for command. default timeout is {timeout_value} sec ")
    print(f" -d : Device number to be used to execute the commands. default is {device}")
    print(" -cr <cr_file> :Give the path of the files with CRs. The file should have data in the format ")
    print("tc_id,CR number (for each tc name)")
    print('*The directory path should be git path at or above \"[testware,testware_v2]\" folder')
    print('eg: This will work testware|testware_v2/commands_files/abr_scale/')
    print('This will not work commands_files/abr_scale/abr_nfr_nl/, If you want to make this work use \"-standalone\" option')
    print('In this case Generated result file should not be use to generate the report ')
    print("*Optional parameter -in '<parameter1,value1,parameter2,value2...(no spaces)>' Adds")
    print("parameters on the input side. If a parameter does not have a value then keep it as NA")
    print("example -in '-re,NA,-stream_loop,3'")
    print("*Optional parameter -out '<parameter1,value1,parameter2,value2...(no spaces)>' Adds")
    print("parameters on the output side. If a parameter does not have a value then keep it as NA")
    print("example -out '-bf,3,-b:v,1M'")

def main_wrapper():
    global timeout_value
    global device
    global prev_fname
    if '-h' in sys.argv or '--help' in sys.argv:
        script_usage()
        exit(0)
    try:
        base_index = sys.argv.index('-p') + 1
        if '-' not in sys.argv[base_index][0]:
            basepath = sys.argv[base_index]
        else:
            print('ERROR: invalid command line arguments')
            script_usage()
            exit(0)
    except (ValueError,IndexError) as ve:
        print(f'ERROR: {ve}')
        script_usage()
        exit(0)
    tc_num = 1

    try:
        tag = sys.argv.index("-K") + 1
        if '-' not in sys.argv[tag][0]:
            tag = sys.argv[tag]
            try:
                if cur_platform == 'linux':
                    tag = Get_OS_kernal(tag)
                op_file_name = 'Report_' + tag + '_' + time_stamp() + '.csv'
            except Exception as e:
                print(f'op_file_name fine name creation failed Error: {e}')
                exit(0)
        else:
            print('ERROR: invalid command line arguments')
            script_usage()
            exit(0)
    except (ValueError, IndexError) as ve:
        print(f'Please provide host and guest os tag using -K: Example ==> -K lvol, -K lvow, -K wvow, -K wvol -K bare')
        exit(0)
    
    try:
        timeout_value_index = sys.argv.index("-t") + 1
        timeout_value = int(sys.argv[timeout_value_index])
    except (ValueError,IndexError) as ve:
        print(f'The specified -t was not found, default -t is {timeout_value} sec')
    try:
        standalone_index = sys.argv.index("-standalone")
    except:
        standalone_index = 0

    try:
        dev_index = sys.argv.index("-d") + 1
        device = int(sys.argv[dev_index])
    except (ValueError,IndexError) as ve:
        print(f'The specified -d was not found, default device is {device}')

    try:
        force_write = int(sys.argv.index("-f")!=0)
        print("Force write (-f) enabled !! Will overwrite command files ")
    except (ValueError,IndexError) as ve:
        force_write = 0
    global retain
    try:
        retain = int(sys.argv.index("-r")!=0)
        print("Retain the TC outputs (-r) should be enabled if not default disabled")
    except (ValueError,IndexError) as ve:
        print("No -r option given, outputs will be deleted")
        retain = 0
    try:
        cr_arg = sys.argv.index("-cr") + 1
        cr_file_name=sys.argv[cr_arg]
        cr_list = prepare_cr_table(cr_file_name)
    except (ValueError,IndexError) as ve:
        cr_file_name="NULL"
    try:
        in_arg_idx = sys.argv.index("-in")
        in_args = (sys.argv[in_arg_idx +1])
        if len(in_args.split(','))%2 !=0:
            print("Input parameter value or parameter missing.\nUse NA for parameters that don't take value.See detailed usage below")
            script_usage()
            exit(0)
        else:
            print("Input side arguments: " + in_args)
    except (ValueError,IndexError) as err:
        in_arg_idx = 0
    try:
        out_arg_idx = sys.argv.index("-out")
        out_args = (sys.argv[out_arg_idx +1])
        if len(out_args.split(','))%2 !=0:
            print("Output parameter value or parameter missing. .\nUse NA for parameters that don't take value. See detailed usage below")
            script_usage()
            exit(0)
        else:
            print("Ouput side arguments " + out_args)
    except (ValueError,IndexError) as err:
        out_arg_idx = 0

    total_cases=0
    passed_cases=0
    initial_cleanup(basepath)
    op_file = open(op_file_name,'w')
    op_file.close()
    if retain == 1:
        os.makedirs(TC_output_Destination_folder, exist_ok=True)
    standlone = ''
    if os.path.isdir(basepath):
        for root,d_names,f_names in os.walk(basepath):
            dyn_file_list = []
            for dyn_f in f_names:
                if '.dyn' in dyn_f:
                    dyn_filepath = os.path.join(root, dyn_f)
                    try:
                        shutil.copy2(dyn_filepath,os.curdir)
                        dyn_file_list.append(dyn_f)
                    except shutil.SameFileError:
                        pass

            for f in f_names:
                #********** extracting folder structure ***************
                folder_path = os.path.dirname(os.path.abspath(f))
                folder_path = os.path.join(folder_path,root)
                folder_path = folder_path.replace('\\','/')
                for testware_p in ['/testware_v2/','/testware/']:
                    if testware_p in folder_path:
                        # folder_path = folder_path.split('/ffmpeg/')[1].replace('/','_')
                        folder_path = folder_path.split(testware_p)[1].replace('/','_')
                        break
                else:
                    if standalone_index:
                        folder_path = 'standalone'
                    else:
                        print('ERROR: The directory path should be git path at or above "[/testware/,/testware_v2/]" folder')
                        print('eg: This will work testware|testware_2|/commands_files/abr_scale/',
                        'This will not work commands_files/abr_scale/abr_nfr_nl/',
                        'If you want to make this work use \"-standalone\" option',
                        'In this case Generated result file should not be use to generate the report',sep='\n')
                        exit(0)
                #************************************************************
                filepath=os.path.join(root, f)
                fname = os.path.basename(filepath).split('.')[0]
                file_extn = os.path.splitext(filepath)[1]
                if file_extn == ".txt" and any(fname.startswith(st) for st in ['fmg','gst','xma']) and file_pattern not in f and all(x not in filepath for x in exclude_folders):
                    with open(filepath) as csvf:
                        if fname != prev_fname:
                            tc_num = 1
                            outfilename = filepath.replace(".txt",file_pattern)
                            ftemp=open(outfilename, 'w')
                            ftemp.close()
                            print(f"File : {filepath}")
                            with open(op_file_name,'a') as op_file:
                                # op_file.write(f"File : {filepath}"+'\n')
                                #print(",".join(header))
                                op_file.write(",".join(header)+'\n')
                        file_cases = 0
                        file_passed_cases = 0
                        for row in csvf:
                            data = row.strip().split(',')
                            for app in ['ffmpeg','gst-launch-1.0','ma35_decoder_app','ma35_encoder_app','ma35_ml_app',
                                        'ma35_scaler_app','ma35_transcoder_app','ma35_roi_transcoder_app']:
                                if len(data) >= 5 and app in data[4].split(' ')[0]:
                                    test_id,density,fps,md5val,command = data[0],data[1],data[2],data[3],data[4].strip().split(' > ')[0]
                                    if len(data) > 5:
                                        command = ','.join(data[4:])
                                    break
                                elif app in data[0].split(' ')[0]:
                                    command = row.strip().split(' > ')[0]
                                    if not command or command[0] == '#':
                                        continue
                                    test_id = fname + "_" + str(tc_num)
                                    fps="NA"
                                    density="NA"
                                    prev_fname = fname
                                    md5val = str(0)
                                    break
                            else :
                                print(f"Wrong command format in {csvf}")
                                continue
                            try:
                                if cr_file_name != "NULL":
                                    cr_num=cr_list[test_id]
                                else:
                                    cr_num="No CR found"
                            except KeyError:
                                cr_num="No CR found"

                            tc_num = tc_num + 1
                            if in_arg_idx:
                                if app in ['gst-launch-1.0','ma35_decoder_app','ma35_encoder_app','ma35_ml_app',
                                           'ma35_scaler_app','ma35_transcoder_app','ma35_roi_transcoder_app']:
                                    print(f"ERROR:Currently {in_args} feature not support for 'gst-launch-1.0'|'ma35'")
                                    exit(0)
                                command = add_in_params(command, in_args)
                            if out_arg_idx:
                                if app in ['gst-launch-1.0','ma35_decoder_app','ma35_encoder_app','ma35_ml_app',
                                           'ma35_scaler_app','ma35_transcoder_app','ma35_roi_transcoder_app']:
                                    print(f"ERROR:Currently {out_args} feature not support for 'gst-launch-1.0'|'ma35'")
                                    exit(0)
                                command = add_out_params(command, out_args)
                            execution_result,md5val_ret,md5sum_op,cr_num_ret,error_code,new_cmd =run_func_test(test_id,device,command,md5val,cr_num,app)
                            write_file(test_id,density,fps,md5val_ret,command,filepath)
                            tag_test_id = tag+'-'+folder_path+'-'+test_id
                            out=[tag_test_id,execution_result,md5val,md5sum_op,cr_num_ret,error_code,new_cmd]
                            with open(op_file_name,'a') as op_file:
                                op_file.write(','.join(out)+'\n')
                            total_cases = total_cases + 1
                            file_cases +=1
                            if execution_result == "PASS":
                                passed_cases = passed_cases + 1
                                file_passed_cases+=1
                        print(f"File Cases Finished :{file_cases} Passed :{file_passed_cases} Failed :{file_cases - file_passed_cases}\n")
                        with open(op_file_name, 'a') as op_file:
                            op_file.write(f"File Cases :{file_cases} Passed :{file_passed_cases} Failed :{file_cases - file_passed_cases}\n")
            for dyn_f in dyn_file_list:
                os.remove(dyn_f)
    else:
        filepath=basepath
        fname = os.path.basename(filepath).split('.')[0]
        file_extn = os.path.splitext(filepath)[1]
        # ********** extracting folder structure ***************
        folder_path = os.path.dirname(os.path.abspath(filepath))
        folder_path = folder_path.replace('\\', '/')
        for testware_p in ['/testware_v2/','/testware/']:
            if testware_p in folder_path:
                # folder_path = folder_path.split('/ffmpeg/')[1].replace('/','_')
                folder_path = folder_path.split(testware_p)[1].replace('/', '_')
                break
        else:
            if standalone_index:
                folder_path = 'standalone'
            else:
                print('ERROR: The directory path should be git path at or above "[/testware/,/testware_v2/]" folder')
                print('eg: This will work testware|testware_v2/commands_files/abr_scale/',
                      'This will not work commands_files/abr_scale/abr_nfr_nl/',
                      'If you want to make this work use \"-standalone\" option',
                      'In this case Generated result file should not be use to generate the report', sep='\n')
                exit(0)
        # ************************************************************
        if os.path.isfile(filepath):
            with open(filepath) as csvf:
                tc_num = 1
                outfilename = filepath.replace(".txt",file_pattern)
                ftemp=open(outfilename, 'w')
                ftemp.close()
                print(f"File : {filepath}")
                with open(op_file_name,'a') as op_file:
                    # op_file.write(f"File : {filepath}"+'\n')
                    print(",".join(header))
                    op_file.write(",".join(header)+'\n')
                file_cases = 0
                file_passed_cases = 0
                for row in csvf:
                    data = row.strip().split(',')
                    for app in ['ffmpeg', 'gst-launch-1.0', 'ma35_decoder_app', 'ma35_encoder_app', 'ma35_ml_app',
                                'ma35_scaler_app', 'ma35_transcoder_app','ma35_roi_transcoder_app']:
                        if len(data) >= 5 and app in data[4].split(' ')[0]:
                            test_id, density, fps, md5val, command = data[0], data[1], data[2], data[3], data[4].strip().split(' > ')[0]
                            if len(data) > 5:
                                command = ','.join(data[4:])
                            break
                        elif app in data[0].split(' ')[0]:
                            command = row.strip().split(' > ')[0]
                            if not command or command[0] == '#':
                                continue
                            test_id = fname + "_" + str(tc_num)
                            fps = "NA"
                            density = "NA"
                            prev_fname = fname
                            md5val = str(0)
                            break
                    else:
                        print(f"Wrong command format in {csvf}")
                        continue
                    try:
                        if cr_file_name != "NULL":
                            cr_num=cr_list[test_id]
                        else:
                            cr_num="No CR found"
                    except KeyError:
                        cr_num="No CR found"

                    tc_num = tc_num + 1
                    if in_arg_idx:
                        if app in ['gst-launch-1.0', 'ma35_decoder_app', 'ma35_encoder_app', 'ma35_ml_app',
                                   'ma35_scaler_app', 'ma35_transcoder_app','ma35_roi_transcoder_app']:
                            print(f"ERROR:Currently {in_args} feature not support for 'gst-launch-1.0'|'ma35'")
                            exit(0)
                        command = add_in_params(command, in_args)
                    if out_arg_idx:
                        if app in ['gst-launch-1.0', 'ma35_decoder_app', 'ma35_encoder_app', 'ma35_ml_app',
                                   'ma35_scaler_app', 'ma35_transcoder_app','ma35_roi_transcoder_app']:
                            print(f"ERROR:Currently {out_args} feature not support for 'gst-launch-1.0'|'ma35'")
                            exit(0)
                        command = add_out_params(command, out_args)
                    execution_result,md5val_ret,md5sum_op,cr_num_ret,error_code,new_cmd =run_func_test(test_id,device,command,md5val,cr_num,app)
                    write_file(test_id,density,fps,md5val_ret,command,filepath)
                    tag_test_id = tag + '-' + folder_path + '-' + test_id
                    out=[tag_test_id,execution_result,md5val,md5sum_op,cr_num_ret,error_code,new_cmd]
                    with open(op_file_name,'a') as op_file:
                        op_file.write(','.join(out)+'\n')
                    total_cases = total_cases + 1
                    file_cases +=1
                    if execution_result == "PASS":
                        passed_cases = passed_cases + 1
                        file_passed_cases+=1
                print(f"File Cases Finished :{file_cases} ;Passed :{file_passed_cases} ;Failed :{file_cases - file_passed_cases}\n")
                with open(op_file_name, 'a') as op_file:
                    op_file.write(f"File Cases :{file_cases} ;Passed :{file_passed_cases} ;Failed :{file_cases - file_passed_cases}\n")

    if force_write == 1:
        file_overwrite(basepath)
    print(f"Finished running, Total cases :{total_cases} ;Passed :{passed_cases} ;Failed :{total_cases - passed_cases}")
    print(f"For detailed results check {op_file_name}")
    with open(op_file_name, 'a') as op_file:
        op_file.write(f"Total :{total_cases} ;Passed :{passed_cases} ;Failed :{total_cases - passed_cases}\n")

if __name__ == "__main__":
    main_wrapper()


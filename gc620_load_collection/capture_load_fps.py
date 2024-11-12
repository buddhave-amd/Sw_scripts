###Script description


####To be done
'''
1. Done :All cli used should goto cmd.txt
2. Done :if folder exists then remove the old folder and create a fresh one 
3. TBD: take fps sepeartely(i.e if user gives 15 fps then add -re -r 15 in CLI)--currently not there
4. Done : add 10 bit inputs and densities and pix formats #inputs are added, densities same as 8bit densities, pix_fmts can be anything according to script
5. Done : push min max avg values of core0 and core1 & avg fps to result.csv
6. TBD : if we give dual core --> core0& core1 commands todgether come up in ffmpeg_log_x.txt --> that needs to be split into ffmpeg_log_core0_x.txt and ffmpeg_log_core1_x.txt & also if its single core change the name to ffmpeg_log_core0_x.txt instead of ffmpeg_log_x.txt
7. TBD : Add a option to give cumulative csv file --if that is given in addition to the single_test/result.csv the csv given by user will also be populated- This will make it easier to collect logs without any postprocessing
8. TBD : Instead of single test , the user should be able to pass options as tuples, And if the tuple is passed the default options(which run all important cases) will be overwritten, else all the pre defined test cases will be run by default
'''
#print("python3 gc620_collect_load_fps.py <options>")

###
from optparse import OptionParser
import datetime, sys, os, subprocess, re, glob
from pathlib import Path
import time
import concurrent.futures

###
parser=OptionParser()
timestr = time.strftime("_%Y%m%d_%H%M%S")



#cli_options.add_option("-f", "--file", dest="filename", help="Name of the file to process")
parser.add_option("-d", "--dev", dest="device_id", action="store", help="Specify which device to use[DEFAULT = 0]",type="int", default=0 )
parser.add_option("-f", "--pix_fmt", dest="pix_fmt", action="store", help="Specify which pixel format to use[DEFAULT = \"\"]",type="string", default="" )
parser.add_option("-b", "--bit_depth", dest="bit_depth", action="store", help="Specify bit depth to use, 10BIT:TOBEDONE [DEFAULT = 8]",type="int", default=8 ) # Remove  10BIT:TOBEDONE comment after implementing
parser.add_option("-r", "--resolution_fps", dest="resolution_fps", action="store", help="Specify resolution & fps to use[DEFAULT = 2160p60]",type="string", default="2160p60" )
#parser.add_option("-f", "--fps", dest="input_fps", action="store", help="Specify input fps[DEFAULT = 60]",type="string", default="60" )
parser.add_option("-s", "--scaler_on", dest="scaler_on_flag", action="store_true", help="Specify if CLi needs scaler [DEFAULT = False]", default=False )
parser.add_option("-i", "--input_path", dest="input_path", action="store", help="Specify input path to use[DEFAULT = if not specified will be picked based on resolution/fps]", default="" )
parser.add_option("--density", dest="density", action="store", help="Specify density [DEFAULT = -1(Will be picked based on resolution/fps)]",type="int", default=-1 )
parser.add_option("--filter", dest="filter", action="store", help="select filter to test [DEFAULT = drawbox)]",type="string", default="drawbox" )
parser.add_option("-o","--out_folder", dest="out_folder", action="store", help="output folder name for results [DEFAULT = <filtername>_<timestamp>]",type="string", default="" )
parser.add_option("--preset", dest="preset", action="store", help="Select preset=fast/medium to decie density [DEFAULT = medium]",type="string", default="medium" )
parser.add_option("--dual_core", dest="dual_core", action="store_true", help="Set to true if both cores to be used [DEFAULT = False]", default=False )
parser.add_option("--out_csv", dest="out_csv", action="store", help="Set out_csv filename to get cumulative data of multiple tests", default="" )

(cli_options,cli_args)=parser.parse_args()
 

######Verify #TBD : Add relatable data in this and print only if verbose flag is used
print("####################################")
print(f"device_id : {cli_options.device_id}")
print(f"pix_fmt : {cli_options.pix_fmt}")
print(f"bit_depth : {cli_options.bit_depth}")
print(f"resolution : {cli_options.resolution_fps}")
#print(f"input_fps : {cli_options.input_fps}")
print(f"scaler_on_flag : {cli_options.scaler_on_flag}")
print(f"input_path : {cli_options.input_path}")
print(f"density : {cli_options.density}")
print(f"filter : {cli_options.filter}")
print(f"out_folder : {cli_options.out_folder}")

print("####################################")
### Functions 
def calculate_stats(filename):
    with open(filename, 'r') as file:
        values = [int(line.strip()) for line in file]
    #if len(values) <= 10:
    #    raise ValueError("Not enough values to skip the first and last 5")

    central_values = values[5:-5]
    filtered_central_values = [v for v in central_values if v != 0]

    if( len(filtered_central_values) == 0):
        return 0,0,0
    min_value = min(filtered_central_values)
    max_value = max(filtered_central_values)
    avg_value = sum(filtered_central_values) / len(filtered_central_values)

    return min_value, max_value, avg_value

def killfunc():
    print("Killing ffmpeg using SIGINT")
    subprocess.Popen("pkill -u $USER -SIGINT ffmpeg", shell=True)

def extract_last_fps_and_average(log_pattern):
    fps_values = []

    for log_file in glob.glob(log_pattern):
        with open(log_file, 'r') as file:
            lines = file.readlines()

        last_fps_line = None
        for line in lines:
            if 'fps=' in line:
                last_fps_line = line

        if last_fps_line:
            match = re.search(r'fps=\s*(\d+)', last_fps_line)
            if match:
                fps_values.append(int(match.group(1)))
            else:
                print(f"No FPS value found in line: {last_fps_line} in file: {log_file}")
        else:
            print(f"No 'fps=' line found in file: {log_file}")

    # Calculate the average FPS if any values were found
    if fps_values:
        avg_fps = sum(fps_values) / len(fps_values)
        return avg_fps, fps_values
    else:
        return None, fps_values

### Defaults 
in_file_dirname="/proj/video_qa/MA35_QA/InputVectors_TypicalBitrate/MRD_Corrected/NFR/Normal/nfr_normal_mp4_0a1v/vector_30K_frames/"
csv_header_string="test,Resolution,Pix_fmt,Bit_depth,Avg_fps,Core0_Min_load,Core0_Max_load,Core0_Avg_load,Core1_Min_load,Core1_Max_load,Core1_Avg_load,Density,CLI"

in_8bit_file_name_dict={
    "4320p30": "Marathon_8Kp30_26M_2b_8bit_30K_fr_0A1V_ffmpeg6_h264.mp4" ,
    "2160p60": "Marathon_2160p60_30M_2b_8bit_30K_fr_0A1V_ffmpeg6_h264.mp4" ,
    "2160p30": "Marathon_2160p30_20M_2b_8bit_30K_fr_0A1V_ffmpeg6_h264.mp4" ,
    "1440p60": "Marathon_1440p60_18M_2b_8bit_30K_fr_0A1V_ffmpeg6_h264.mp4" ,
    "1440p30": "Marathon_1440p30_14M_2b_8bit_30K_fr_0A1V_ffmpeg6_h264.mp4" ,
    "1080p60": "Marathon_1080p60_12M_2b_8bit_30K_fr_0A1V_ffmpeg6_h264.mp4" ,
    "1080p30": "Marathon_1080p30_6M_2b_8bit_30K_fr_0A1V_ffmpeg6_h264.mp4" ,
    "720p60" : "Marathon_720p60_5M_2b_8bit_30K_fr_0A1V_ffmpeg6_h264.mp4" ,
    "720p30" : "Marathon_720p30_4M_2b_8bit_30K_fr_0A1V_ffmpeg6_h264.mp4" ,
    "540p60" : "Marathon_540p60_6M_2b_8bit_30K_fr_0A1V_ffmpeg6_h264.mp4" ,
    "540p30" : "Marathon_540p30_3M_2b_8bit_30K_fr_0A1V_ffmpeg6_h264.mp4"
}

in_10bit_file_name_dict={
    "4320p30": "Marathon_8Kp30_26M_2b_10bit_30K_fr_0A1V_ffmpeg6_h264.mp4" ,
    "2160p60": "Marathon_2160p60_33M_2b_10bit_30K_fr_0A1V_ffmpeg6_h264.mp4" ,
    "2160p30": "Marathon_2160p30_22M_2b_10bit_30K_fr_0A1V_ffmpeg6_h264.mp4" ,
    "1440p60": "Marathon_1440p60_19800K_2b_10bit_30K_fr_0A1V_ffmpeg6_h264.mp4" ,
    "1440p30": "Marathon_1440p30_15400K_2b_10bit_30K_fr_0A1V_ffmpeg6_h264.mp4" ,
    "1080p60": "Marathon_1080p60_13200K_2b_10bit_30K_fr_0A1V_ffmpeg6_h264.mp4" ,
    "1080p30": "Marathon_1080p30_6600K_2b_10bit_30K_fr_0A1V_ffmpeg6_h264.mp4" ,
    "720p60" : "Marathon_720p60_5500K_2b_10bit_30K_fr_0A1V_ffmpeg6_h264.mp4" ,
    "720p30" : "Marathon_720p30_4400K_2b_10bit_30K_fr_0A1V_ffmpeg6_h264.mp4" ,
    "540p60" : "Marathon_540p60_6600K_2b_10bit_30K_fr_0A1V_ffmpeg6_h264.mp4" ,
    "540p30" : "Marathon_540p30_3300K_2b_10bit_30K_fr_0A1V_ffmpeg6_h264.mp4"
}

in_file_name_dict = {"8": in_8bit_file_name_dict , "10": in_10bit_file_name_dict }

FAST_PRESET_FACTOR=1.25

density_medium_preset_dict={
    "4320p30": 1 ,
    "2160p60": 2 ,
    "2160p30": 4 ,
    "1440p60": 4 ,
    "1440p30": 8 ,
    "1080p60": 8 ,
    "1080p30": 16 ,
    "720p60" : 18 ,
    "720p30" : 36 ,
    "540p60" : 32 ,
    "540p30" : 64    
}

in_resolution_dict={
    "4320p30": "7680×4320" ,
    "2160p60": "3840x2160" ,
    "2160p30": "3840x2160" ,
    "1440p60": "2560x1440" ,
    "1440p30": "2560x1440" ,
    "1080p60": "1920x1080" ,
    "1080p30": "1920x1080" ,
    "720p60" : "1280x720" ,
    "720p30" : "1280x720" ,
    "540p60" : "960x540" ,
    "540p30" : "960x540"
}

#dual/single
if (cli_options.dual_core == True ):
    dual_single_str="dualCore"
else:
    dual_single_str = "singleCore0"    

#input
default_input_folder="/proj/video_qa/MA35_QA/InputVectors_TypicalBitrate/MRD_Corrected/NFR/Normal/nfr_normal_mp4_0a1v/vector_30K_frames/"
if (cli_options.input_path == ""):
    input = default_input_folder + in_file_name_dict[str(cli_options.bit_depth)][cli_options.resolution_fps]
else :
    input = cli_options.input_path    

#vframes -- for 40 seconds
framerate=int(cli_options.resolution_fps.split("p")[-1])
vframes_count= framerate * 40

#target density
if (cli_options.density == -1 ):
    target_density = int(density_medium_preset_dict[cli_options.resolution_fps])
    if(cli_options.preset == "fast"):
        target_density = int(target_density*FAST_PRESET_FACTOR)
else :
    target_density =   cli_options.density 

print("target density=" ,target_density )

#outFolderName
if (cli_options.scaler_on_flag == True):
    scaler_flag_str="with"
else :
    scaler_flag_str="wo"    
if(cli_options.out_folder == ""):
    #out_folder=cli_options.filter+timestr
    out_folder=f"{cli_options.filter}_{target_density}x_{dual_single_str}_{cli_options.resolution_fps}_{cli_options.bit_depth}bit_{cli_options.pix_fmt}PixFmt_{cli_options.preset}Preset_{scaler_flag_str}ABRScaler"
else :
    out_folder= cli_options.out_folder  

###env
current_directory = os.getcwd()
result_dir=current_directory+"/"+out_folder
if( os.path.exists(result_dir)):
    print(f"Result folder {result_dir} exists...removing existing folder")
    os.system("rm -rf "+ result_dir )
Path(result_dir).mkdir(parents=True, exist_ok=True)
print(current_directory, result_dir)
result_csv_file = result_dir + "/result.csv"
commands_file = result_dir + "/cmds.txt"

core0_temp_load_file=result_dir + "/temp_out_load_core0" + ".txt"
core1_temp_load_file=result_dir + "/temp_out_load_core1" + ".txt"


core0_main_load_file=result_dir + "/temp_out_load_core0" + ".txt"
core1_main_load_file=result_dir + "/temp_out_load_core1" + ".txt"

load_file_core0=f"/sys/class/misc/ama_transcoder{cli_options.device_id}/perf/gc620/load0"
load_file_core1=f"/sys/class/misc/ama_transcoder{cli_options.device_id}/perf/gc620/load1"



###Checks
#check if input path exists
#check if device exists
#if resolution is not in the standard resolutions above , check if density and input are given or not --else error out

#drawbox CLI strings
if (cli_options.pix_fmt != ""  and cli_options.scaler_on_flag == False ) :
    dec_out_fmt_option="-out_fmt"
    dec_out_fmt_str= dec_out_fmt_option + " " +   cli_options.pix_fmt
else :
    dec_out_fmt_str= ""



if (cli_options.scaler_on_flag == True) :
    if ( cli_options.pix_fmt != ""):
        scaler_str=f"scaler_ama=outputs=1:out_res=({in_resolution_dict[cli_options.resolution_fps]}|{cli_options.pix_fmt})[a];[a]"
    else :
        scaler_str=f"scaler_ama=outputs=1:out_res=({in_resolution_dict[cli_options.resolution_fps]})[a];[a]"    
else:                                                                                                          
     scaler_str=""  
###

#derive 
drawbox_width=600
drawbox_height=600
print(int(cli_options.resolution_fps.split("p")[0]))
if(int(cli_options.resolution_fps.split("p")[0]) == 540 ):
    drawbox_height=500
    drawbox_width=500

drawbox_CLI=f"ffmpeg -nostdin  -y -hwaccel ama -hwaccel_device /dev/ama_transcoder{cli_options.device_id} -stream_loop -1 -xerror -re -c:v h264_ama {dec_out_fmt_str} -i {input} -filter_complex \"{scaler_str}drawbox_ama=thickness=16:color=red:x=0:y=0:w={drawbox_width}:h={drawbox_height}\" -vframes {vframes_count} -f NULL -"     


print(f"#########CLI : {drawbox_CLI}")

killfunc()


#execution
cmds_list=[]
for density in range(target_density):

    log_str= f" >> {result_dir}/ffmpeg_log_{density}.txt 2>&1 & "
    cmd_CLI=drawbox_CLI 
    cmd= cmd_CLI + log_str
    print(cmd)
    cmds_list.append(cmd)
    os.system(cmd)
    cmd_coreid1=""
    cmd_coreid1_CLI=""
    if (cli_options.dual_core == True ):
        #cmd_coreid1 = cmd.replace("x=0:y=0:w=600:h=600","x=0:y=0:w=600:h=600:core_id=1") ## quick workaround for drawbox dual core , need to fix for generalising and other filter dual cores
        #cmd_coreid1 = cmd.replace("x=0:y=0:w=500:h=500","x=0:y=0:w=500:h=500:core_id=1") ## quick workaround for drawbox dual core , need to fix for generalising and other filter dual cores
        #cmd_coreid1 = cmd.replace("\" vframes",":core_id=1\" vframes") ## quick workaround for drawbox dual core , need to fix for generalising and other filter dual cores
        cmd_coreid1 = re.sub(r'h=(\d+)"', r'h=\1:core_id=1"', cmd)
        cmd_coreid1_CLI= re.sub(r'h=(\d+)"', r'h=\1:core_id=1"', cmd_CLI)
        os.system(cmd_coreid1)
        print("$$$$$$$$$$$$$$"+cmd_coreid1)
        cmds_list.append(cmd_coreid1)

#load collection    
while True:
    result = subprocess.run("ps aux | grep '[f]fmpeg' | grep -v grep ", shell=True, stdout=subprocess.PIPE, text=True)
    if result.stdout.strip():  
        core0_load = os.system("cat  " + load_file_core0 + " | cut -d ' ' -f1   >> " + core0_temp_load_file )
        core1_load = os.system("cat  " + load_file_core1 + " | cut -d ' ' -f1   >> " + core1_temp_load_file)
    else:
        print("Exceution completed. Preparing logs...")
        break 

    time.sleep(1)  # Check every second

#write commands into file
test_commands_str = "\n".join(cmds_list) + "\n"

with open(commands_file, 'a') as file:
    file.write(test_commands_str) 


 ### calculate min , max avg loads on core 0 and core 1 & avg Fps
core0_min_load,core0_max_load, core0_avg_load = calculate_stats(core0_temp_load_file)
if(cli_options.dual_core):
    core1_min_load,core1_max_load, core1_avg_load =calculate_stats(core1_temp_load_file)
else:  
    core1_min_load,core1_max_load, core1_avg_load =0,0,0  

#print("Loads :", core0_min_load,core0_max_load, core0_avg_load ,core1_min_load,core1_max_load, core1_avg_load )
###avg fps 
#      
avg_fps, fps_values= extract_last_fps_and_average(result_dir+"/ffmpeg_log*.txt") 

#print("avg fps= ",avg_fps)

#write results
with open(result_csv_file, 'w') as file:
    # Convert dictionary to string and write it 
    file.write(csv_header_string + "\n") 
    file.write(f"{out_folder},{cli_options.resolution_fps},{cli_options.pix_fmt}{cli_options.bit_depth},{avg_fps},{core0_min_load},{core0_max_load},{core0_avg_load:.5f},{core1_min_load},{core1_max_load},{core1_avg_load:.5f},{target_density},{cmd_CLI} & {cmd_coreid1_CLI}\n")
    #TBD : Instead of writing like this, load all var names into a list and map header names to that list and use a loop to populate to avoid misalignment
if (cli_options.out_csv == ""):
    print(f"Results can be found in {result_csv_file}")
#sv_header_string="test,Resolution,Pix_fmt,Bit_depth,Avg_fps,Core0_Min_load,Core0_Max_load,Core0_Avg_load,Core1_Min_load,Core1_Max_load,Core1_Avg_load,Density,CLI"
else :
    csv_file_path = Path(cli_options.out_csv)
    if not csv_file_path.is_file():
        consolidated_results_file = open(csv_file_path, 'w')
        consolidated_results_file.write(csv_header_string + "\n")
    else:
        consolidated_results_file = open(csv_file_path, 'a')
    
    consolidated_results_file.write(f"{out_folder},{cli_options.resolution_fps},{cli_options.pix_fmt}{cli_options.bit_depth},{avg_fps},{core0_min_load},{core0_max_load},{core0_avg_load:.5f},{core1_min_load},{core1_max_load},{core1_avg_load:.5f},{target_density},{cmd_CLI} & {cmd_coreid1_CLI}\n")
    print(f"Results can be found in {result_csv_file} and {cli_options.out_csv}")
    consolidated_results_file.close()




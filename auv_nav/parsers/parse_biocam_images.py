# parse_acfr_images

# Scripts to parse acfr image acquisition data

# Author: Blair Thornton
# Date: 31/08/2017

import os
import glob
from pathlib import Path
# from datetime import datetime

# sys.path.append("..")
from auv_nav.tools.time_conversions import date_time_to_epoch
from auv_nav.tools.folder_structure import get_raw_folder
from auv_nav.tools.console import Console

stamp_pc1 = []
stamp_pc2 = []
stamp_cam1 = []
stamp_cam2 = []
values = []
data_list = []
tolerance = 0.05  # 0.01 # stereo pair must be within 10ms of each other

# http://www.json.org/


def parse_biocam_images(mission,
                        vehicle,
                        category,
                        ftype,
                        outpath,
                        fileoutname):
    # parser meta data
    class_string = 'measurement'
    frame_string = 'body'
    category = 'image'
    sensor_string = 'biocam'

    timezone = mission.image.timezone
    timezone_offset = 0
    timeoffset = mission.image.timeoffset
    filepath = mission.image.cameras[0].path
    camera1_label = mission.image.cameras[0].name
    camera2_label = mission.image.cameras[1].name

    # read in timezone
    if isinstance(timezone, str):
        if timezone == 'utc' or timezone == 'UTC':
            timezone_offset = 0
        elif timezone == 'jst' or timezone == 'JST':
            timezone_offset = 9
        else:
            try:
                timezone_offset = float(timezone)
            except ValueError:
                print('Error: timezone', timezone,
                      'in mission.cfg not recognised, please enter value from UTC in hours')
                return

    # convert to seconds from utc
    # timeoffset = -timezone_offset*60*60 + timeoffset

    Console.info('Parsing ' + sensor_string + ' images')

    # determine file paths

    filepath1 = get_raw_folder(outpath / '..' / filepath / str(camera1_label + '_*/*.*'))
    filepath2 = get_raw_folder(outpath / '..' / filepath / str(camera2_label + '_*/*.*'))

    camera1_list = glob.glob(str(filepath1))
    camera2_list = glob.glob(str(filepath2))

    camera1_filename = [
        line for line in camera1_list if '.txt' not in line and '._' not in line]
    camera2_filename = [
        line for line in camera2_list if '.txt' not in line and '._' not in line]

    print(filepath1)
    print(filepath2)
    print(camera1_list[0])
    print(camera1_list[1])
    print('Found ' + str(len(camera2_filename) + len(camera1_filename)) + ' images!')

    data_list = []
    if ftype == 'acfr':
        data_list = ''

    def timestamp_from_filename(filename, timezone_offset, timeoffset):
        filename_split = filename.strip().split('_')

        date_string = filename_split[0]
        time_string = filename_split[1]
        ms_time_string = filename_split[2]

        cam_date_string = filename_split[3]
        cam_time_string = filename_split[4]
        cam_ms_time_string = filename_split[5]

        def time_from_string(date_string, time_string, ms_time_string,
                             timezone_offset, timeoffset):
            # read in date
            yyyy = int(date_string[0:4])
            mm = int(date_string[4:6])
            dd = int(date_string[6:8])

            # read in time
            hour = int(time_string[0:2])
            mins = int(time_string[2:4])
            secs = int(time_string[4:6])
            usec = int(ms_time_string[0:6])

            if yyyy < 2000:
                return 0
            epoch_time = date_time_to_epoch(
                yyyy, mm, dd, hour, mins, secs, timezone_offset)
            # dt_obj = datetime(yyyy,mm,dd,hour,mins,secs)
            # time_tuple = dt_obj.timetuple()
            # epoch_time = time.mktime(time_tuple)
            epoch_timestamp = float(epoch_time+usec/1e6+timeoffset)
            return epoch_timestamp
        epoch_timestamp = time_from_string(date_string,
                                           time_string,
                                           ms_time_string,
                                           timezone_offset,
                                           timeoffset)
        cam_epoch_timestamp = time_from_string(cam_date_string,
                                               cam_time_string,
                                               cam_ms_time_string,
                                               timezone_offset,
                                               timeoffset)
        return epoch_timestamp, cam_epoch_timestamp

    for i in range(len(camera1_filename)):
        t1, tc1 = timestamp_from_filename(Path(camera1_filename[i]).name,
                                          timezone_offset,
                                          timeoffset)
        stamp_pc1.append(str(t1))
        stamp_cam1.append(str(tc1))
    for i in range(len(camera2_filename)):
        t2, tc2 = timestamp_from_filename(Path(camera2_filename[i]).name,
                                          timezone_offset,
                                          timeoffset)
        stamp_pc2.append(str(t2))
        stamp_cam2.append(str(tc2))

    for i in range(len(camera1_filename)):
        values = []
        for j in range(len(camera2_filename)):
            values.append(
                abs(float(stamp_pc1[i])-float(stamp_pc2[j])))

        (sync_difference, sync_pair) = min((v, k)
                                           for k, v in enumerate(values))

        if sync_difference < tolerance:
            if ftype == 'oplab':
                data = {
                    'epoch_timestamp': float(stamp_pc1[i]),
                    'class': class_string,
                    'sensor': sensor_string,
                    'frame': frame_string,
                    'category': category,
                    'camera1': [{
                        'epoch_timestamp': float(stamp_pc1[i]),
                        'epoch_timestamp_cam': float(stamp_cam1[i]),
                        'filename': str(camera1_filename[i])
                    }],
                    'camera2':  [{
                        'epoch_timestamp': float(stamp_pc2[sync_pair]),
                        'epoch_timestamp_cam': float(stamp_cam2[sync_pair]),
                        'filename': str(camera2_filename[sync_pair])
                    }]
                }
                data_list.append(data)
            if ftype == 'acfr':
                data = 'VIS: ' + str(float(stamp_pc1[i])) + ' [' + str(float(
                    stamp_pc1[i])) + '] ' + str(camera1_filename[i]) + ' exp: 0\n'
                # fileout.write(data)
                data_list += data
                data = 'VIS: ' + str(float(stamp_pc2[sync_pair])) + ' [' + str(float(
                    stamp_pc2[sync_pair])) + '] ' + str(camera2_filename[sync_pair]) + ' exp: 0\n'
                # fileout.write(data)
                data_list += data

    return data_list

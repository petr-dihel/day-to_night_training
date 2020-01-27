try:
    from PIL import Image
except ImportError:
    import Image
from threading import Lock
import cv2, imutils, re, os, time, sys, hashlib, fnmatch
import numpy as np
import pytesseract
import threading
from threading import Lock

MAX_THREADS = 14


def get_cropped_image(img, start_x, start_y, end_x=0, end_y=0):
    width, height, channels = img.shape
    if end_x == 0:
        end_x = width
    if end_y == 0:
        end_y = height
    crop = img[start_y:end_y, start_x:end_x, :]
    return crop


def get_mapped_string(string, map):
    for toReplace, replacement in map:
        string = string.replace(toReplace, replacement)
    return string


def get_black_and_white_image(image):
    gray_image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    (thresh, black_and_white_image) = cv2.threshold(gray_image, 210, 255, cv2.THRESH_BINARY)
    return black_and_white_image

def remove_artifacts(gps_location_string):
    if gps_location_string[0] == 'E':
        gps_location_string = gps_location_string[1:]
    index = len(gps_location_string) -1
    if gps_location_string[index] == "7":
        gps_location_string = gps_location_string[:-1]
    if "N499" in gps_location_string:
        gps_location_string = gps_location_string.replace("N499", "N49")
    return gps_location_string


def get_gps_location(img, is_front_view):
    start_x = 800
    end_x = 1400
    if is_front_view == False:
        start_x = 785
        end_x = 1350
    cropped_frame = get_cropped_image(img, start_x, 1010, end_x, 1060)
    black_and_white_image = get_black_and_white_image(cropped_frame)
    mapping = [('\"', '”'), ('/', ''), ('H', ''), (",", "."), (" ", ""), ("I", "1"), ("L", "1"), ("l", "1"), ("O", "0"),
               ("£", "1")]
    gps_location_string = pytesseract.image_to_string(black_and_white_image, lang='eng', config='--psm 7 --oem 3')
    gps_location_string = get_mapped_string(gps_location_string, mapping)
    return gps_location_string


def is_day_from_image(image):
    cropped_image = get_cropped_image(image, 235, 1020, 345, 1060)
    black_and_white_image = get_black_and_white_image(cropped_image)
    time_string = pytesseract.image_to_string(black_and_white_image, lang='eng', config='--psm 7 --oem 3 -c tessedit_char_whitelist=0123456789:')
    hours, minutes = time_string.split(':')
    hours = int(hours)
    minutes = int(minutes)
    #CASE january
    if (hours > 7 and hours < 15) or (hours == 6 and minutes < 30) or (hours == 15 and minutes < 30):
        return True
    return False


def get_blended_image(images):
    main_image = images[0]
    for img in images:
        main_image = main_image * 0.5 + img * 0.5
    return main_image


class PrepareTrainingData:

    def __init__(self, absolute_path, pytesseract_path, output_videos_path):
        self.absolute_path = absolute_path
        self.lock = Lock()
        self.directories_with_videos = []
        self.current_directory = False
        self.current_video_all_frame_count = 0
        self.current_video_count = 0
        self.gps_log_file = open(absolute_path + "/output/log_gps.txt", "w")
        self.log_file = open(absolute_path + "/output/log_info.txt", "w+")
        self.count_of_videos = 0
        self.pytesseract_path = pytesseract_path
        self.saved_videos = 0
        self.saved_videos = 0
        self.current_video_stream = False
        self.current_frame_count = 0
        self.success_count = 0
        self.failed_count = 0
        self.failed_strings = []
        self.done_videos = []
        self.last_video_file_name = ''
        self.path_to_video = ''
        self.output_videos_path = output_videos_path

    def load_saved_data(self):
        lines = self.log_file.readlines()
        for line in lines:
            if "Last_video" in line:
                current_video_count = line.split(":")[1]
                self.current_video_count = current_video_count
                print('Loaded current_video_count:{}'.format(current_video_count))

    def log_stats(self):
        if (self.failed_count + self.success_count) == 0:
            return
        self.log_info("success_count:{0}".format(self.success_count))
        self.log_info("Failed:{0}".format(self.failed_count))
        ratio = (self.success_count * 100) / (self.failed_count + self.success_count)
        self.log_info("Ratio:{0}".format(ratio))
        self.log_info("Failed_strings:{0}".format(';'.join(self.failed_strings)))
        self.log_info("Last_video_iterator:{0}".format(self.current_video_count))
        self.log_info("Last_video_name:{0}".format(self.last_video_file_name))
        self.log_info("done_videos:{0}".format(','.join(self.done_videos)))

    def log_info(self, message):
        try:
            self.log_file.write(message + "\n")
        except Exception as ex:
            print('Error - log_info - probably failed strings... clearing')
            self.failed_strings = []

    def init_video_dictionaries(self, path_to_videos, dictionary_limit = ''):
        self.path_to_video = path_to_videos
        files_at_directory = os.listdir(self.path_to_video + "/")
        for file in files_at_directory:
            if os.path.isdir(self.path_to_video + "/" + file):
                self.directories_with_videos.append(file)
        for dict in self.directories_with_videos:
            print(dict)
            if dictionary_limit != '' and dictionary_limit != dict:
                continue
            videos = fnmatch.filter(os.listdir(self.path_to_video + "/" + dict), '*.mp4')
            self.count_of_videos += len(videos)

    def blend_and_save_images(self, images, gps_location):
        main_image = images[0] * (1 / len(images)) * 2
        file_name = hashlib.md5(gps_location.encode('utf-8')).hexdigest()
        print(file_name)
        print(len(images))
        print(1 / len(images))
        for image in images:
            main_image = main_image * (1 - (1 / len(images))) + image * (1 / len(images))
        cv2.imwrite("output/" + file_name + ".png", main_image)

    def get_degree_from_gps_string(self, gps_string):
        parts = re.findall(r"[0-9]*\.?[0-9]*", gps_string)
        parts = list(filter(None, parts))
        n_degree = float(parts[0]) + float(parts[1]) / 60 + float(parts[2]) / 3600
        e_degree = float(parts[3]) + float(parts[4]) / 60 + float(parts[5]) / 3600
        return str(n_degree) + ":" + str(e_degree)

    def update_progress(self, progress, time_remaining, over_all_remaining_frames, over_all_time_remaining):
        bar_length = 10
        status = ""
        if progress < 0:
            progress = 0
            status = "Pause...\r\n"
        if progress >= 1:
            progress = 1
            status = "Done...\r\n"
        block = int(round(bar_length * progress))
        block2 = int(round(bar_length * over_all_remaining_frames))
        time_text = time.strftime('%H:%M:%S', time.gmtime(time_remaining))
        #time_text2 = time.strftime('%H:%M:%S', time.gmtime(over_all_time_remaining))
        days = (over_all_time_remaining/(3600*24))
        remainder = (over_all_time_remaining%(3600*24))
        hours = (remainder/3600)
        remainder = (remainder%3600)
        minutes = (remainder/60)
        remainder = (minutes % 60)
        time_text2 = "DAYS:{0:02.0f} {1:02.0f}:{2:02.0f}:{3:02.0f}".format(days, hours, minutes, remainder)
        text = "\rPercent: [{0}] {1:.5f}% (All: [{2}] {3:.5f}%) {4} - Estimated : {5} (All: {6})".format(
            "#" * block + "-" * (bar_length - block),
            progress * 100,
            "#" * block2 + "-" * (bar_length - block2),
            over_all_remaining_frames * 100,
            status,
            time_text,
            time_text2
        )
        sys.stdout.write(text)
        sys.stdout.flush()

    def run(self, dictionary_limit = ''):
        print("count of videos {0}".format(self.count_of_videos))
        print("Path to videos {0}".format(self.path_to_video))
        for directory in self.directories_with_videos:
            videos_at_dictionary = fnmatch.filter(os.listdir(self.path_to_video + '/' + directory), '*.mp4')
            if dictionary_limit != '' and dictionary_limit != directory:
                continue
            for video in videos_at_dictionary:
                is_front_view = True
                is_day_inited = False
                #fourcc = cv2.VideoWriter_fourcc(*'mp4v')
                #file_name = "project{0}.mp4".format(self.current_video_count)
                file_name = video
                #out = cv2.VideoWriter(self.output_videos_path + "/" + file_name, fourcc, 20.0, (1920, 1080))
                self.current_video_count += 1
                self.current_frame_count = 0
                self.current_video_stream = cv2.VideoCapture(self.path_to_video + '/' + directory + '/' + video)
                self.current_video_all_frame_count = int(self.current_video_stream.get(cv2.CAP_PROP_FRAME_COUNT))
                start_time = time.time()
                day_time_string = "N"
                if 'r.mp4' in video.lower():
                    is_front_view = False
                threads = []
                dic_of_gps = {}
                while True:
                    frame = self.current_video_stream.read()
                    frame = frame[1]
                    if frame is None:
                        break
                    frame_copy = frame.copy()
                    self.current_frame_count += 1
                    if is_day_inited == False:
                        try:
                            is_day = is_day_from_image(frame_copy)
                            if is_day:
                                day_time_string = "D"
                            is_day_inited = True
                        except ValueError:
                            print("Error isDay")
                            continue

                    new_thread = threading.Thread(target=self.thread_process,
                                                  args=(frame_copy, dic_of_gps, is_front_view, self.current_frame_count))
                    threads.append(new_thread)
                    new_thread.start()
                    if len(threads) > MAX_THREADS:
                        for thread in threads:
                            thread.join()
                        threads = []

                        for gps_location, images_by_location in dic_of_gps.items():
                            index_at_one_gps = 0
                            for frame_index, image in images_by_location.items():
                                print("Dasda")
                                log_message = day_time_string + ":" + str(is_front_view) + ":" + gps_location \
                                              + ":" + str(index_at_one_gps) + ":" + file_name + ":" + str(frame_index)
                                unique_key = hashlib.md5((str(day_time_string) + ":" + str(is_front_view) + ":" + str(
                                    gps_location) + ":" + str(index_at_one_gps)).encode('utf-8')).hexdigest()
                                self.gps_log_file.write(unique_key + ":" + log_message + "\n")
                                #out.write(image.astype('uint8'))
                                self.success_count += 1
                                index_at_one_gps += 1

                        current_time = time.time() - start_time
                        remaining_frames = self.current_frame_count / self.current_video_all_frame_count
                        estimated_time_for_video = ((self.current_video_all_frame_count / self.current_frame_count)
                                                    * current_time)
                        time_remaining = estimated_time_for_video - current_time
                        over_all_remaining_frames = (self.current_frame_count + self.current_video_all_frame_count
                                                     * (self.current_video_count - 1)) \
                                                    / (self.current_video_all_frame_count * self.count_of_videos)
                        over_all_time_remaining = estimated_time_for_video * self.count_of_videos - (
                                (self.current_video_count - 1) * estimated_time_for_video) - current_time
                        self.update_progress(remaining_frames, time_remaining, over_all_remaining_frames, over_all_time_remaining)
                        threads = []
                        blended_images_by_location = {}
                        dic_of_gps = {}
                self.done_videos.append(video)
                self.log_stats()

    def thread_process(self, frame_copy, dic_of_gps, is_front_view, frame_index):

        new_gps_location_string = get_gps_location(frame_copy, is_front_view)
        regular = r"N?[0-9]*\.?[0-9]*°[0-9]*\.?[0-9]*[’|”][0-9]*\.?[0-9]*”E[0-9]*\.?[0-9]*°[0-9]*\.?[0-9]*[’|”][" \
                  r"0-9]*\.?[0-9]*”"
        print(new_gps_location_string)
        if re.search(regular, new_gps_location_string):
            gps_degree = self.get_degree_from_gps_string(new_gps_location_string)
            self.lock.acquire()
            if gps_degree in dic_of_gps:
                img_list = dic_of_gps[gps_degree]
                img_list[frame_index] = frame_copy
                dic_of_gps[gps_degree] = img_list
            else:
                img_list = {}
                img_list[frame_index] = frame_copy
                dic_of_gps[gps_degree] = img_list
            self.lock.release()
        else:
            print('ADFasasd')
            self.lock.acquire()
            self.failed_count += 1
            self.failed_strings.append(new_gps_location_string)
            self.lock.release()

    def thread_process_blending(self, frames, gps_location, blended_images_by_location):
        blended_images_by_location[gps_location] = get_blended_image(frames)


#prepareTrainingData = PrepareTrainingData("D:/car_videos/", r"C:\Program Files\Tesseract-OCR\tesseract.exe")
#prepareTrainingData.init_video_dictionaries("D:/car_videos/")
if len(sys.argv) < 3:
    print("Arguments missing : input_videos_path, output_logs_file_path, tesseract_cmd=C:\Program Files\Tesseract-OCR\tesseract.exe")
    sys.exit()

#r"G:\car_videos\"
input_videos_path = sys.argv[1]
#r"C:\Users\Petr\Desktop\prepare_training_data"
output_logs_file_path = sys.argv[2]

output_video_path = sys.argv[3]
if len(sys.argv) > 4:
    tesseract_cmd = sys.argv[3]
else:
    tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
pytesseract.pytesseract.tesseract_cmd = tesseract_cmd
prepareTrainingData = PrepareTrainingData(output_logs_file_path, tesseract_cmd, output_video_path)
prepareTrainingData.init_video_dictionaries(input_videos_path, "CARDV_20181212")
try:
    prepareTrainingData.run("CARDV_20181212")

except Exception as ex:
    print('Exception {0}'.format(ex))
    print('Line {0}'.format(ex.with_traceback()))
finally:
    prepareTrainingData.log_stats()




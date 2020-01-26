try:
    from PIL import Image
except ImportError:
    import Image
from threading import Lock
import cv2, imutils, re, os, time, sys, hashlib, fnmatch
import pytesseract
import threading
from threading import Lock

MAX_THREADS = 10


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
    (thresh, black_and_white_image) = cv2.threshold(gray_image, 200, 255, cv2.THRESH_BINARY)
    return black_and_white_image


def get_gps_location(img, is_front_view):
    start_x = 800
    end_x = 1400
    if is_front_view == False:
        start_x = 785
        end_x = 1350
    cropped_frame = get_cropped_image(img, start_x, 1010, end_x, 1060)
    black_and_white_image = get_black_and_white_image(cropped_frame)
    mapping = [('\"', '”'), (",", "."), (" ", ""), ("I", "1"), ("L", "1"), ("l", "1"), ("O", "0"), ("£", "1")]
    gps_location_string = pytesseract.image_to_string(black_and_white_image, lang='eng', config='--psm 7 --oem 3')
    return get_mapped_string(gps_location_string, mapping)


def is_day_from_image(image):
    cropped_image = get_cropped_image(image, 240, 1010, 280, 1060)
    black_and_white_image = get_black_and_white_image(cropped_image)
    time_string = pytesseract.image_to_string(black_and_white_image, lang='eng', config='--psm 7 --oem 3')
    hours = int(time_string)
    return 7 < hours < 19


def get_blended_image(images):
    main_image = images[0]
    for img in images:
        main_image = main_image * 0.5 + img * 0.5
    return main_image


class PrepareTrainingData:

    def __init__(self, absolute_path, pytesseract_path):
        self.absolute_path = absolute_path
        self.lock = Lock()
        self.directories_with_videos = []
        self.current_directory = False
        self.current_video_all_frame_count = 0
        self.current_video_count = 0
        self.gps_log_file = open(absolute_path + "/output/log_gps.txt", "w")
        self.log_file = open(absolute_path + "/output/log_info.txt", "w")
        self.count_of_videos = 0
        self.pytesseract_path = pytesseract_path
        self.saved_videos = 0
        self.saved_videos = 0
        self.current_video_stream = False
        self.current_frame_count = 0
        self.success_count = 0
        self.failed_count = 0
        self.failed_strings = []

    def init_video_dictionaries(self, path_to_videos):
        #self.directories_with_videos = path_to_videos
        self.directories_with_videos = os.listdir(path_to_videos)
        print(self.directories_with_videos)
        dictionary_files = fnmatch.filter(os.listdir(path_to_videos), '*.mp4')
        self.count_of_videos = len(dictionary_files)
        print(dictionary_files)

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
        n_degree = float(parts[0]) + float(parts[1]) * 60 + float(parts[2]) * 3600
        e_degree = float(parts[3]) + float(parts[4]) * 60 + float(parts[5]) * 3600
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
        time_text2 = time.strftime('%H:%M:%S', time.gmtime(over_all_time_remaining))

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

    def run(self):
        print("count of videos {0}".format(self.count_of_videos))
        print("Path to videos {0}".format(self.absolute_path))
        for directory in self.directories_with_videos:
            videos_at_dictionary = fnmatch.filter(os.listdir(self.absolute_path + directory), '*.mp4')

            for video in videos_at_dictionary:
                is_front_view = True
                is_day_inited = False
                fourcc = cv2.VideoWriter_fourcc(*'mp4v')
                file_name = "project{0}.mp4".format(self.current_video_count)
                out = cv2.VideoWriter(self.absolute_path + "output/" + file_name, fourcc, 20.0, (1920, 1080))
                self.current_video_count += 1
                self.current_frame_count = 0
                self.current_video_stream = cv2.VideoCapture(self.absolute_path + directory + video)
                self.current_video_all_frame_count = int(self.current_video_stream.get(cv2.CAP_PROP_FRAME_COUNT))
                start_time = time.time()
                day_time_string = "N"
                if 'R.mp4' in video:
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
                    new_thread = threading.Thread(target=self.thread_process,
                                                  args=(frame_copy, dic_of_gps, is_front_view))
                    threads.append(new_thread)
                    new_thread.start()
                    if len(threads) > MAX_THREADS:
                        for thread in threads:
                            thread.join()
                        threads = []

                        for gps_location, images_by_location in dic_of_gps.items():
                            index_at_one_gps = 0
                            for image in images_by_location:
                                log_message = day_time_string + ":" + str(is_front_view) + ":" + gps_location \
                                              + ":" + str(index_at_one_gps) + ":" + file_name + ":" + str()
                                unique_key = hashlib.md5((str(day_time_string) + ":" + str(is_front_view) + ":" + str(
                                    gps_location) + ":" + str(index_at_one_gps)).encode('utf-8')).hexdigest()
                                self.gps_log_file.write(unique_key + ":" + log_message + "\n")
                                out.write(image.astype('uint8'))
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
                        self.update_progress(remaining_frames, time_remaining, over_all_remaining_frames,
                                             over_all_time_remaining)
                        threads = []
                        blended_images_by_location = {}
                        dic_of_gps = {}

    def thread_process(self, frame_copy, dic_of_gps, is_front_view):
        new_gps_location_string = get_gps_location(frame_copy, is_front_view)
        regular = r"N?[0-9]*\.?[0-9]*°[0-9]*\.?[0-9]*[’|”][0-9]*\.?[0-9]*”E[0-9]*\.?[0-9]*°[0-9]*\.?[0-9]*[’|”][" \
                  r"0-9]*\.?[0-9]*” "
        if re.search(regular, new_gps_location_string):
            gps_degree = self.get_degree_from_gps_string(new_gps_location_string)
            self.lock.acquire()
            if gps_degree in dic_of_gps:
                img_list = dic_of_gps[gps_degree]
                img_list.append(frame_copy)
            else:
                img_list = []
                img_list.append(frame_copy)
                dic_of_gps[gps_degree] = img_list
            self.lock.release()
        else:
            self.lock.acquire()
            self.failed_count += 1
            self.failed_strings.append(new_gps_location_string)
            self.lock.release()

    def thread_process_blending(self, frames, gps_location, blended_images_by_location):
        blended_images_by_location[gps_location] = get_blended_image(frames)


#prepareTrainingData = PrepareTrainingData("D:/car_videos/", r"C:\Program Files\Tesseract-OCR\tesseract.exe")
#prepareTrainingData.init_video_dictionaries("D:/car_videos/")

prepareTrainingData = PrepareTrainingData(r"c:\Users\Petr\Desktop\py\detection\project", r"C:\Program Files\Tesseract-OCR\tesseract.exe")
prepareTrainingData.init_video_dictionaries(r"c:\Users\Petr\Desktop\py\detection\project")
prepareTrainingData.run()

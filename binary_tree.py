import hashlib, sys, cv2
from functools import reduce


def get_degree_from_gps_string(self, gps_string):
    parts = re.findall(r"[0-9]*\.?[0-9]*", gps_string)
    parts = list(filter(None, parts))
    n_degree = float(parts[0]) + float(parts[1]) / 60 + float(parts[2]) / 3600
    e_degree = float(parts[3]) + float(parts[4]) / 60 + float(parts[5]) / 3600
    return str(n_degree) + ":" + str(e_degree)


def load_saved_data():
    log_file = open(r"C:\Users\Petr\Desktop\prepare_training_data\output\test\\log_info.txt", "r")
    lines = log_file.readlines()
    video_files_name = {}
    for line in lines:
        if "done_videos" in line:
            videosString = line.split(":")[1]
            videos = videosString.split(',')
            index = 0
            for video in videos:
                video_files_name[index] = video
                index += 1
    return video_files_name


def get_input_video_file_name(video_files_name, file_name):
    s = file_name[7:]
    s = s[:-4]
    index = int(s)
    return video_files_name[index]


def update_progress(total_count, current_count):
    bar_length = 10
    status = ""
    progress = current_count/total_count
    if progress < 0:
        progress = 0
        status = "Pause...\r\n"
    if progress >= 1:
        progress = 1
        status = "Done...\r\n"
    block = int(round(bar_length * progress))
    text = "\rPercent: [{0}] {1:.5f}% ".format(
        "#" * block + "-" * (bar_length - block),
        progress * 100,
    )
    sys.stdout.write(text)
    sys.stdout.flush()

class PairedImage:

    def __init__(self):
        self.node_day = False
        self.node_night = False

    def set_day(self, node_day):
        self.node_day = node_day

    def set_night(self, node_night):
        self.node_night = node_night


class TreeNode:

    def __init__(self, hash_value, is_day, north, east, gps_index, video_file_name, is_front_view, video_frame_index):
        self.hashValue = hash_value
        self.isDay = is_day
        self.north = north
        self.east = east
        self.gps_index = gps_index
        self.videoFileName = video_file_name
        self.right = False
        self.left = False
        self.isFrontView = is_front_view
        self.video_frame_index = video_frame_index

    def get_opposite_hash_value(self):
        gps_string = str(self.north) + ":" + str(self.east)
        if self.isDay:
            is_day = "N"
        else:
            is_day = "D"
        hash = hashlib.md5((str(is_day) + ":" + str(self.isFrontView) + ":" + gps_string + ":"
                            + str(self.gps_index)).encode('utf-8')).hexdigest()
        hash_value = int(hash, 16)
        return hash_value


class BinaryTree:

    def __init__(self):
        self.nodes = []
        self.root = False

    def insertNode(self, node):
        if self.root == False:
            self.root = node
            self.nodes.append(node)
        else:
            self.internalInsertNode(self.root, node)

    def internalInsertNode(self, current, newNode):
        if current.hashValue < newNode.hashValue:
            if current.right == False:
                self.nodes.append(newNode)
                current.right = newNode
            else:
                self.internalInsertNode(current.right, newNode)
        else:
            if current.left == False:
                self.nodes.append(newNode)
                current.left = newNode
            else:
                self.internalInsertNode(current.left, newNode)

    def load_from_file(self, file_name):
        with open(file_name, "r") as file:
            lines = file.readlines()
            count_total = len(lines)
            current_count = 0
            for line in lines:
                current_count += 1
                hash_value, is_day, is_front, north, east, gps_index, video_file_name, frame_index = line.split(":")
                # hash_value to number
                hash_value = int(hash_value, 16)
                is_day = (is_day == 'D')
                north = float(north)
                east = float(east)
                video_file_name = str(video_file_name)
                video_frame_index = int(frame_index)
                # line do nothing just to debug
                new_node = TreeNode(hash_value, is_day, north, east, gps_index, video_file_name, is_front, video_frame_index)
                self.insertNode(new_node)
                update_progress(count_total, current_count)

    def getNodeByHashValue(self, hash_value):
        return self.internalgetNodeByHashValue(self.root, hash_value)

    def internalgetNodeByHashValue(self, current_node, hash_value):
        if current_node.hashValue == hash_value:
            return current_node
        if current_node.hashValue < hash_value:
            if current_node.right == False:
                return False
            else:
                return self.internalgetNodeByHashValue(current_node.right, hash_value)
        else:
            if current_node.left == False:
                return False
            else:
                return self.internalgetNodeByHashValue(current_node.left, hash_value)

    def printTree(self):
        tabs = 3
        self.internal_print(self.root, tabs, True)

    def internal_print(self, node, tabs, new_line=False):
        if tabs < 1 or tabs > 6:
            return
        for x in range(0, tabs):
            print("\t", end='')
        if new_line:
            print(node.hashValue, end='\n\n')
        else:
            print(node.hashValue, end='')
        if node.left != False:
            print(str(tabs) + "-L-", end='')
            if node.right == False:
                self.internal_print(node.left, tabs - 1, True)
            else:
                self.internal_print(node.left, tabs - 1, True)
        if node.right != False:
            print(str(tabs) + "-R-", end='')
            self.internal_print(node.right, tabs + 1, True)

video_files_name = load_saved_data()
a = get_input_video_file_name(video_files_name, "project0.mp4")
print(a)
binary_tree = BinaryTree()
file = r"C:\Users\Petr\Desktop\prepare_training_data\output\test\log_gps.txt"
print("Loading from file {0}".format(file))
binary_tree.load_from_file(file)
print("\nDone loading\n")

currentNode = binary_tree.root
# calculated hash of opposite time for the same location

pairedImages = []

#binary_tree.printTree()
# self gonna be really tons of data should split somehow to parts or just it will return part of paired images than another part
current_count = 0
for node in binary_tree.nodes:
    if float(node.east) < 10 or float(node.north) < 10:
        continue
    #print(node.hashValue)
    current_count += 1
    searchedHashValue = node.get_opposite_hash_value()
    #print(searchedHashValue)
    ##print(hex(searchedHashValue))
    opossiteNode = binary_tree.getNodeByHashValue(searchedHashValue)
    if opossiteNode != False:
        newPairedImage = PairedImage()
        if node.isDay:
            newPairedImage.node_day = node
            newPairedImage.node_night = opossiteNode
        else:
            newPairedImage.node_day = opossiteNode
            newPairedImage.node_night = node
        pairedImages.append(newPairedImage)
        #break
    update_progress(len(binary_tree.nodes), current_count)
print("Prepared paired images to training : " + str(len(pairedImages)))


def hconcat_resize_min(im_list, interpolation=cv2.INTER_CUBIC):
    h_min = min(im.shape[0] for im in im_list)
    im_list_resize = [cv2.resize(im, (int(im.shape[1] * h_min / im.shape[0]), h_min), interpolation=interpolation)
                      for im in im_list]
    return cv2.hconcat(im_list_resize)


test = pairedImages[0]
index = 1
saved = 0
failedGps = 0
frameNoneError = 0

while saved < 20:
    test = pairedImages[index]
    while float(test.node_day.east) < 10 or float(test.node_day.north) < 10:
        index += 1
        if len(pairedImages[index]) -1 < index:
            break
        test = pairedImages[index]
        failedGps += 1
        continue
    path_to_video = r"G:\car_videos\output"
    path_to_video = r"G:\car_videos\input\CARDV_20181212"

    video_file_name_1 = get_input_video_file_name(video_files_name, test.node_day.videoFileName)
    current_video_stream = cv2.VideoCapture(path_to_video + '/' + video_file_name_1)
    current_video_stream.set(1, test.node_day.video_frame_index)
    frame = current_video_stream.read()
    if frame[1] is None:
        index += 1
        frameNoneError += 1
        continue
    img1 = frame[1].copy()

    # cv2.imshow("Test1", frame[1])

    video_file_name_2 = get_input_video_file_name(video_files_name, test.node_night.videoFileName)
    current_video_stream = cv2.VideoCapture(path_to_video + '/' + video_file_name_2)
    current_video_stream.set(1, test.node_night.video_frame_index)
    frame2 = current_video_stream.read()
    if frame2[1] is None:
        index += 1
        frameNoneError += 1
        continue
    img2 = frame2[1].copy()
    result_im = hconcat_resize_min([img1, img2])
    # cv2.imshow("Test2", frame2[1])
    img_path = r"C:\Users\Petr\Desktop\prepare_training_data\output\\"
    image_name = "test{0}.jpg".format(saved)
    cv2.imwrite(img_path + image_name, result_im)
    #cv2.imwrite(img_path + "Test2.png", frame2[1])

    print("Day : Is day {0} is Front : {1} videoFileName {2} real {3}".format(test.node_day.isDay, test.node_day.isFrontView, test.node_day.videoFileName, video_file_name_1))
    print("Night : Is day {0} is Front : {1} videoFileName {2} real {3}".format(test.node_night.isDay, test.node_night.isFrontView, test.node_night.videoFileName, video_file_name_2))
    print(index)
    index += int(len(pairedImages)/50)
    saved += 1
print("failedGps{0}".format(failedGps))
print("frameNoneError{0}".format(frameNoneError))


"""
print(test.node_day.videoFileName)
print(test.node_day.north)
print(test.node_day.east)
print(test.node_day.isFrontView)
print(test.node_night.videoFileName)
print(test.node_night.north)
print(test.node_night.east)
print(test.node_night.isFrontView)
print("Day: hash {0} opposite {1}".format(test.node_day.hashValue, test.node_day.get_opposite_hash_value()))
print("Day: hash {0} opposite {1}".format(test.node_night.hashValue, test.node_night.get_opposite_hash_value()))
"""


# for newPairedImage in pairedImages:
# todo preapre datasets and save

""""
def load_images(path, size=(256,256)):
	data_list = list()
	# enumerate filenames in directory, assume all are images
	for filename in listdir(path):
		# load and resize the image
		pixels = load_img(path + filename, target_size=size)
		# convert to numpy array
		pixels = img_to_array(pixels)
		# store
		data_list.append(pixels)
	return asarray(data_list)

# load dataset A
dataA1 = load_images(path + 'trainA/')
dataAB = load_images(path + 'testA/')
dataA = vstack((dataA1, dataAB))
print('Loaded dataA: ', dataA.shape)
# load dataset B
dataB1 = load_images(path + 'trainB/')
dataB2 = load_images(path + 'testB/')
dataB = vstack((dataB1, dataB2))
print('Loaded dataB: ', dataB.shape)
# save as compressed numpy array
filename = 'horse2zebra_256.npz'
savez_compressed(filename, dataA, dataB)
print('Saved dataset: ', filename)""""

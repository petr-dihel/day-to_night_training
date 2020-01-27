# day_to_night_prepare
Script preapres pairs day-night from videos by location

## prepare_training_data.py
- reads video files, read gps location, saves the information
- 92% ratio of succesfully readed gps

### Parameters
- input video path
- output log path

### log_gps.txt
- each row is one image and his location unique key:message
- unique_key -  md5(N/D(DAY/Night) : True/False (is_front) : east_cord :  norh_cord : index_at_one_gps
- log_message = md5(N/D(DAY/Night) : True/False (is_front) : east_cord :  norh_cord : index_at_one_gps : frame
- ef19617ef5e3ffea14985c61c3ffbdaf:N:True:49.86012777777778:18.294175000000003:1:project0.mp4:3

### log_info.txt
failed_strings, list of done video_filenames, count of successful frames and failed

## binary_tree.py
- create a b-tree from file
- than creates a list of paires 
- find oppoiste pair by calculated opposity unique_key
- todo preapre data set from each pair for learning


## Results

                               

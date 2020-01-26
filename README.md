# day-to_night_training
Script preapres pairs day-night from videos by location

## Parameters
- input video path
- output log path

## log_gps.txt
- each row is one image and his location unique key:message
- unique_key -  md5(N/D(DAY/Night) : True/False (is_front) : east_cord :  norh_cord : index_at_one_gps
- log_message = md5(N/D(DAY/Night) : True/False (is_front) : east_cord :  norh_cord : index_at_one_gps : frame

## log_info.txt
failed_strings, list of done video_filenames, count of successful frames and failed

## binary_tree.py
- create a b-tree from file
- than creates a list of paires 
- find oppoiste pair by calculated opposity unique_key

## Results
- 


                               

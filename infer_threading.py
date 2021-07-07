from gxipy.gxiapi import Timeout
from camera import GxCamera
from utils import unpack_results
from typing import Mapping
from numpy.lib.utils import source
import paddlex as pdx
import os
import time
import deploy
import cv2
from paddlex.det import transforms
import numpy as np
from utils import unpack_results, parse_args, watcher_alert_areas
from GMM import GMM_mask
# from SORT import SORT_Tracker
# from RM_radar_communicate.transmit import referee_transmit
import config
import sys
import gxipy as gx
import threading
import queue

device_manager = gx.DeviceManager()

path = "./imgs"
font = cv2.FONT_HERSHEY_SIMPLEX


# digit_model=digit_detector('RM-resnet18/',use_static=False,use_dynamic_input=True,precision_mode="FP16")
# if config.communite == 'enable':
#     referee_transmit_h = referee_transmit(config.color)


eval_transforms = transforms.Compose([
    transforms.Resize(target_size=416, interp='CUBIC'),
    transforms.Normalize(),
])

detect_model = deploy.Predictor('yolov3-inference-416', use_gpu=True, use_trt=True, use_static=True,
                                use_dynamic_input=False, precision_mode="FP16", use_glog=False,
                                memory_optimize=True, use_calib_mode=False)
# use imgs for testing
mask = GMM_mask()
# tracker=SORT_Tracker()


def test_images(path):
    pass


info_dict1 = config.cams_dict['cam_wide']
info_dict2 = config.cams_dict['cam_left']

device_manager = gx.DeviceManager()

class camera_thread(threading.Thread):
    def __init__(self,camera_info_dict,device_manager):
        threading.Thread.__init__(self)
        self.cam=GxCamera(info_dict=camera_info_dict, device_manager=device_manager)
        self.cam.cam_start()
        self.img_queue = queue.Queue(2)

    def run(self):
        while True:
            img=self.cam.read_image()
            self.img_queue.put(img)
            
    def get_image(self):
        return self.img_queue.get(timeout=1)

    def kill_thread(self):
        self.cam.cam_release()

cv2.namedWindow("wide_camera", cv2.WINDOW_AUTOSIZE)  # 创建一个名为video的窗口
# cv2.setWindowProperty("wide_camera", cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
cv2.resizeWindow("wide_camera",1920//2-50,1080//2-50)
cv2.moveWindow("wide_camera",-200,-100)

# dev_num, dev_info_list = device_manager.update_device_list() 
def test_video(video_path):
    if video_path == "cam":
        cap = cv2.VideoCapture(0)
    elif video_path == "daheng":
        camera_wide=camera_thread(info_dict1,device_manager)
        camera_wide.start()

    else:
        cap = cv2.VideoCapture(video_path)
    size = None

    fps = 25

    best_target = None
    count=0
    start_all =time.time()
    while True:
        if count <2000:
            count+=1
        else:
            print("avg fps:",2000/(time.time()-start_all))
            break
        start = time.time()
        if video_path == "daheng":
            img_wide = camera_wide.get_image()
            if img_wide is not None:
                img_wide = cv2.cvtColor(img_wide, cv2.COLOR_RGB2BGR)
            
            else:
                camera_wide.kill_thread()

                dev_num, dev_info_list = device_manager.update_device_list()
                while dev_num != 4:
                    dev_num, dev_info_list = device_manager.update_device_list()
                camera_wide=camera_thread(info_dict1,device_manager)
                camera_wide.start()
                # cap = GxCamera(1)
                # cap.cam_start()
                print("restarting camera!!!!!!!!!!!!!!!!!")
                continue
        else:
            _, img = cap.read()
            if img is None:
                break

        result = detect_model.predict(img_wide, eval_transforms)
        fgmask = mask.get_mask(img_wide)  # GMM get fmask for moving objects
        # end=time.time()
        img_wide=unpack_results(result,img_wide,mask,WITH_GMM=True)
        # cv2.rectangle(img, (642, 819), (711, 860),
        #               (0, 255, 0), 2)  # calibrate point

        # img=watcher_alert_areas(img)

        # img = cv2.resize(img, (1920//2, 1080//2))
        cv2.putText(img_wide, 'img_wide',
                    (50,50), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), thickness=2)

        img_wide=cv2.resize(img_wide,(1920//2,1080//2))

        cv2.imshow("wide_camera",img_wide)

        if size is None:
            size = (img_wide.shape[1], img_wide.shape[0])
            fourcc = cv2.VideoWriter_fourcc(
                'm', 'p', '4', 'v')  # opencv3.0
            videoWriter = cv2.VideoWriter(
                './videos/wide-result{}.mp4'.format(round(time.time()*1000)), fourcc, fps, size)
        videoWriter.write(img_wide)

        if cv2.waitKey(1) & 0xFF == 27:
            sys.exit(1)
        end = time.time()
        print(1/(end-start))
    # if video_path == "daheng":
    #     cap.cam_release()
    cv2.destroyAllWindows()
    sys.exit(1)


def main():
    args = parse_args()
    if args.video:
        if args.source == "cam":
            test_video("cam")
        elif args.source == "daheng":
            test_video("daheng")
        else:
            test_video(args.source)
    else:
        test_images(path)


main()

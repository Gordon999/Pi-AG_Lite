#!/usr/bin/env python3
import cv2
import time
import math
import numpy as np
import pygame
from pygame.locals import *
import os
from picamera2 import Picamera2
from libcamera import controls

# v0.03

# set default parameters
Pi_Cam       = 0       # 1 = use Pi Camera, 0 = use USB camera
crop         = 60      # size of detection window *
threshold    = 0       # 0 = auto *
scale        = 100     # mS/pixel *
fps          = 25      # set camera fps              (Pi camera only) *
mode         = 0       # set camera mode             (Pi camera only) *
speed        = 80000   # mS x 1000                   (Pi camera only) *
Again        = 0       # 0 = auto (Pi camera only) *
ev           = 0       # Auto Exposure Bias          (Pi camera only) *
brightness   = 3       # set camera brightness *
contrast     = 20      # set camera contrast *
Auto_G       = 0       # Auto Guide 0 = off, 1 = ON *
min_corr     = 100     # mS, no guiding correction applied below this *
interval     = 10      # Interval between corrections in Frames *
InvRA        = 1       # set to 1 to invert RA comands eg E<>W *
InvDEC       = 1       # set to 1 to invert DEC comands eg N<>S *
preview      = 0       # show detected star pixels *
c_mask       = 1       # set to 1 for circular window
fullscreen   = 1       # fullscreen = 1 give no border to window
noise        = 0       # noise reduction *
binn         = 0       # binning, 0 = none, 1 = 2x2, 2 = 3x3 etc *
conl         = 90      # Contrast Limit, determines minimum contrast that a star will be detected *
focus_fitted = 0       # 1 = enabled if focusser fitted eg Meade #1209

# USB Webcam presets
#===================================================================================
Auto_Gain    = 1      # Switch Automatic Gain , 1 = ON, 0 = OFF *
exposure     = 255    # USB camera initial exposure *
gain         = 35     # sets USB camera initial gain *
gamma        = 31     # sets USB camera initial gamma *
red_balance  = 66     # sets USB camera initial red balance
blue_balance = 48     # sets USB camera initial blue balance
auto_contour = 0      # 0 switches it to manual, range 0-1
contour      = 0      # set to min, range 0-63
dnr          = 0      # set to min, range 0-3 
backlight    = 0      # sets it OFF 0-1

# * user adjustable within script whilst running

# check PiAGconfig.txt exists, if not then write default values
if not os.path.exists('PiAGLconfig.txt'):
    points = [crop,threshold,scale,fps,mode,speed,Again,brightness,contrast,Auto_G,min_corr,interval,InvRA,InvDEC,preview,c_mask,fullscreen,ev,noise,binn,
              Auto_Gain,exposure,gain,gamma,red_balance,blue_balance,auto_contour,contour,dnr,backlight,conl]
    with open('PiAGLconfig.txt', 'w') as f:
        for item in points:
            f.write("%s\n" % item)

# read PiAGconfig.txt
config = []
with open("PiAGLconfig.txt", "r") as file:
   line = file.readline()
   while line:
      config.append(line.strip())
      line = file.readline()
config = list(map(int,config))

crop        = config[0]
threshold   = config[1]
scale       = config[2]
fps         = config[3]
mode        = config[4]
speed       = config[5]
ISO         = config[6]
brightness  = config[7]
contrast    = config[8]
Auto_G      = config[9]
min_corr    = config[10]
interval    = config[11]
InvRA       = config[12]
InvDEC      = config[13]
preview     = config[14]
c_mask      = config[15]
fullscreen  = config[16]
ev          = config[17]
noise       = config[18]
binn        = config[19]
Auto_Gain   = config[20]
exposure    = config[21]
gain        = config[22]
gamma       = config[23]
red_balance = config[24]
blue_balance= config[25]
auto_contour= config[26]
contour     = config[27]
dnr         = config[28]
backlight   = config[29]
conl        = config[30]

# set variables
if Pi_Cam == 1:
    width = 1920
    height = 1088
else:
    width = 640
    height = 480
    mode = 0

a = 320
b = 181
br = 50
co = 0
w = 960
h = 544
xo = 0
yo = 0
zoom = 2
frames = 0
Bits = 0
correct = ":Mgn0000:Mge0000"
RAstr =""
DECstr=""
RAon = 1
DECon = 1
ser_connected = 0
ser2_connected = 0
ISO2 = ISO
focus_speed = 2

import serial
if os.path.exists('/dev/ttyACM0') == True:
    import serial
    ser = serial.Serial('/dev/ttyACM0', 9600)
    ser_connected = 1
elif os.path.exists('/dev/ttyACM1') == True:
    import serial
    ser = serial.Serial('/dev/ttyACM1', 9600)
    ser_connected = 1
elif os.path.exists('/dev/ttyACM2') == True:
    import serial
    ser = serial.Serial('/dev/ttyACM2', 9600)
    ser_connected = 1
elif os.path.exists('/dev/ttyACM3') == True:
    import serial
    ser = serial.Serial('/dev/ttyACM3', 9600)
    ser_connected = 1
time.sleep(2)

#===================================================================================
# Generate mask for Circular window
#===================================================================================
if not os.path.exists('/run/shm/CMask.bmp'):
   pygame.init()
   bredColor =   pygame.Color(100,100,100)
   mwidth =200
   mheight = 200
   mcrop = 200
   windowSurfaceObj = pygame.display.set_mode((mwidth, mheight),0, 24)
   pygame.draw.circle(windowSurfaceObj, bredColor, (int(mcrop/2),int(mcrop/2)), int(mcrop/2),0)
   pygame.display.update()
   pygame.image.save(windowSurfaceObj, '/run/shm/CMask.bmp')
   pygame.display.quit()
mask = pygame.image.load('/run/shm/CMask.bmp')
  
x = int(width/2) - a
y = int(height/2) - b

pygame.init()
if fullscreen == 0:
   windowSurfaceObj = pygame.display.set_mode((800, 480), 0, 24)
else:
   windowSurfaceObj = pygame.display.set_mode((800, 480),pygame.NOFRAME, 24)
   
pygame.display.set_caption('Pi-AGL')

modes  = ['OFF','0','0','0','0','0','0','0','Night','0','0','Sports']
widths = [640, 800, 960, 1280, 1620, 1920, 2592, 3280]
scales = [1, 1.25, 1.5, 2, 2.531, 3, 4.047, 5.125]
scalex = int(scale / scales[zoom])
modes  = ['manual','normal','short','long']

global greyColor, redColor, greenColor, blueColor, dgryColor, lgryColor, blackColor, whiteColor, purpleColor, yellowColor
bredColor   = pygame.Color(255,   0,   0)
lgryColor   = pygame.Color(192, 192, 192)
blackColor  = pygame.Color(  0,   0,   0)
whiteColor  = pygame.Color(200, 200, 200)
greyColor   = pygame.Color(128, 128, 128)
dgryColor   = pygame.Color( 64,  64,  64)
greenColor  = pygame.Color(  0, 255,   0)
purpleColor = pygame.Color(255,   0, 255)
yellowColor = pygame.Color(255, 255,   0)
blueColor   = pygame.Color(  0,   0, 255)
redColor    = pygame.Color(200,   0,   0)

def button(col,row, bColor,x):
   colors = [greyColor, dgryColor, dgryColor, dgryColor, yellowColor]
   Color = colors[bColor]
   bx = x + (col * 80)
   by = row * 40
   pygame.draw.rect(windowSurfaceObj,Color,Rect(bx,by,79,40))
   pygame.draw.line(windowSurfaceObj,whiteColor,(bx,by),(bx+80,by))
   pygame.draw.line(windowSurfaceObj,greyColor,(bx+79,by),(bx+79,by+40))
   pygame.draw.line(windowSurfaceObj,whiteColor,(bx,by),(bx,by+39))
   pygame.draw.line(windowSurfaceObj,dgryColor,(bx,by+39),(bx+79,by+39))
   pygame.display.update(bx, by, 80, 40)
   return

def text(col,row,fColor,top,upd,msg,fsize,bcolor,x):
   colors =  [dgryColor, greenColor, yellowColor, redColor, greenColor, blueColor, whiteColor, greyColor, blackColor, purpleColor]
   Color  =  colors[fColor]
   bColor =  colors[bcolor]
   
   bx = x + (col * 80)
   by = row * 40
   if os.path.exists ('/usr/share/fonts/truetype/freefont/FreeSerif.ttf'): 
       fontObj =       pygame.font.Font('/usr/share/fonts/truetype/freefont/FreeSerif.ttf', int(fsize))
   else:
       fontObj =       pygame.font.Font(None, int(fsize))
   msgSurfaceObj = fontObj.render(msg, False, Color)
   msgRectobj =    msgSurfaceObj.get_rect()
   if top == 0:
       pygame.draw.rect(windowSurfaceObj,bColor,Rect(bx+1,by+1,70,20))
       msgRectobj.topleft = (bx + 5, by + 3)
   else:
       pygame.draw.rect(windowSurfaceObj,bColor,Rect(bx+25,by+18,51,21))
       msgRectobj.topleft = (bx + 25, by + 18)
       
   windowSurfaceObj.blit(msgSurfaceObj, msgRectobj)
   if upd == 1:
      pygame.display.update(bx, by, 80, 40)

# initialize the camera
if Pi_Cam == 1:
    # start Pi camera
    picam2 = Picamera2()
    picam2.configure(picam2.create_preview_configuration(main={"format": 'XRGB8888', "size": (640, 480)}))
    picam2.start()
else:
    import pygame.camera
    pygame.camera.init()
    if os.path.exists('/dev/video1') == True:
        cam = pygame.camera.Camera("/dev/video1", (width,height))
        dve = 1
    elif os.path.exists('/dev/video0') == True:
        cam = pygame.camera.Camera("/dev/video0", (width,height))
        dve = 0
    cam.start()


for c in range(0,2):
    for d in range(0,12):
        button(c,d,0,640)
if ser_connected == 1:
    for c in range(3,4):
        for d in range(9,11):
            button(c,d,0,0)
    text(3,9,2,0,1,"South North",14,7,0)
    text(3,10,2,0,1,"West    East",14,7,0)
    if focus_fitted:
        button(4,9,0,0)
        button(4,10,0,0)
        text(4,9,2,0,1,"- FOCUS +",14,7,0)
        text(4,10,2,0,1,"-Foc Speed+",13,7,0)
        text(4,10,2,1,1,str(focus_speed),13,7,0)

text(0,7,2,0,1,"Crop",14,7,640)
text(0,7,3,1,1,str(crop),18,7,640)
text(1,0,2,0,1,"Threshold",14,7,640)
if threshold > 0:
    text(1,0,3,1,1,str(threshold),18,7,640)
else:
   text(1,0,3,1,1,"Auto",18,7,640)
text(0,1,2,0,1,"Zoom",14,7,640)
text(0,1,3,1,1,str(zoom),18,7,640)
text(1,7,2,0,1,"mS/pixel",14,7,640)
text(1,7,3,1,1,str(scalex),18,7,640)
if Pi_Cam == 1:
    # setup camera parameters
    text(0,2,5,0,1,"FPS",14,7,640)
    text(0,2,3,1,1,str(fps),18,7,640)
    text(1,2,5,0,1,"Mode",14,7,640)
    text(1,2,3,1,1,modes[mode],18,7,640)
    text(1,1,5,0,1,"EV",14,7,640)
    text(1,1,3,1,1,str(ev),18,7,640)
    if mode == 0:
        picam2.set_controls({"AeEnable": False,"ExposureTime": speed})
    else:
        if mode == 1:
            picam2.set_controls({"AeEnable": True,"AeExposureMode": controls.AeExposureModeEnum.Normal})
        elif mode == 2:
            picam2.set_controls({"AeEnable": True,"AeExposureMode": controls.AeExposureModeEnum.Short})
        elif mode == 3:
            picam2.set_controls({"AeEnable": True,"AeExposureMode": controls.AeExposureModeEnum.Long})
    text(1,2,3,1,1,modes[mode],18,7,640)
    text(0,3,5,0,1,"Shutter mS",14,7,640)
    if mode == 0:
        text(0,3,3,1,1,str(int(speed/1000)),18,7,640)
    else:
        text(0,3,0,1,1,str(int(speed/1000)),18,7,640)
    time.sleep(1)
    if Pi_Cam == 3:
        if v3_f_mode == 0:
            picam2.set_controls({"AfMode": controls.AfModeEnum.Manual, "AfMetering" : controls.AfMeteringEnum.Windows,  "AfWindows" : [(int(vid_width* .33),int(vid_height*.33),int(vid_width * .66),int(vid_height*.66))]})
        elif v3_f_mode == 1:
            picam2.set_controls({"AfMode": controls.AfModeEnum.Auto, "AfMetering" : controls.AfMeteringEnum.Windows,  "AfWindows" : [(int(vid_width*.33),int(vid_height*.33),int(vid_width * .66),int(vid_height*.66))]})
            picam2.set_controls({"AfTrigger": controls.AfTriggerEnum.Start})
        elif v3_f_mode == 2:
            picam2.set_controls( {"AfMode" : controls.AfModeEnum.Continuous, "AfMetering" : controls.AfMeteringEnum.Windows,  "AfWindows" : [(int(vid_width*.33),int(vid_height*.33),int(vid_width * .66),int(vid_height*.66))] } )
            picam2.set_controls({"AfTrigger": controls.AfTriggerEnum.Start})
    picam2.set_controls({"Brightness": brightness/10})
    text(0,4,5,0,1,"Brightness",14,7,640)
    text(0,4,3,1,1,str(brightness),18,7,640)
    text(1,4,5,0,1,"Contrast",14,7,640)
    picam2.set_controls({"Contrast": contrast/10})
    text(1,4,3,1,1,str(contrast),18,7,640)
    picam2.set_controls({"ExposureValue": ev/10})
    picam2.set_controls({"AnalogueGain": Again})
    text(1,3,5,0,1,"Gain",14,7,640)
    text(1,3,3,1,1,str(Again),18,7,640)
    picam2.set_controls({"FrameRate": fps})
    text(0,2,3,1,1,str(fps),18,7,640)

else:
    # Philips Webcam initialisation
    rpistr = "v4l2-ctl -c gain=" + str(gain) + " -d " + str(dve)
    os.system (rpistr)
    rpistr = "v4l2-ctl -c gamma=" + str(gamma) + " -d " + str(dve)
    os.system(rpistr)
    rpistr = "v4l2-ctl -c white_balance_automatic=3" + " -d " + str(dve)
    os.system(rpistr)
    rpistr = "v4l2-ctl -c red_balance=" + str(red_balance) + " -d " + str(dve)
    os.system(rpistr)
    rpistr = "v4l2-ctl -c blue_balance=" + str(blue_balance) + " -d " + str(dve)
    os.system(rpistr)
    rpistr = "v4l2-ctl -c auto_contour=" + str(auto_contour) + " -d " + str(dve)
    os.system(rpistr)
    rpistr = "v4l2-ctl -c contour=" + str(contour) + " -d " + str(dve)
    os.system(rpistr)
    rpistr = "v4l2-ctl -c dynamic_noise_reduction=" + str(dnr) + " -d " + str(dve)
    os.system(rpistr)
    rpistr = "v4l2-ctl -c backlight_compensation=" + str(backlight) + " -d " + str(dve)
    os.system(rpistr)
    text(1,2,5,0,1,"Gamma",14,7,640)
    text(1,2,3,1,1,str(gamma),18,7,640)
    text(1,1,5,0,1,"Gain",14,7,640)
    text(1,1,3,1,1,str(gain),18,7,640)
    text(1,3,5,0,1,"Auto Gain",14,7,640)
    if Auto_Gain != 0:
        text(1,3,3,1,1,"ON",18,7,640)
    else:
        text(1,3,0,1,1,"off",18,7,640)
    path = "v4l2-ctl -c gain_automatic=" + str(Auto_Gain) + " -d " + str(dve)
    os.system(rpistr)
    text(0,3,5,0,1,"Exposure",14,7,640)
    text(0,3,3,1,1,str(exposure),18,7,640)
    path = "v4l2-ctl -c exposure=" + str(exposure) + " -d " + str(dve)
    os.system(rpistr)
    text(0,2,5,0,1,"Con Limit",14,7,640)
    text(0,2,3,1,1,str(conl),18,7,640)
    text(0,4,5,0,1,"Brightness",14,7,640)
    text(0,4,3,1,1,str(brightness),18,7,640)
    path = "v4l2-ctl -c brightness=" + str(brightness) + " -d " + str(dve)
    os.system (path)
    path = "v4l2-ctl -c contrast=" + str(contrast) + " -d " + str(dve)
    os.system (path)
    text(1,4,5,0,1,"Contrast",14,7,640)
    text(1,4,3,1,1,str(contrast),18,7,640)

    os.system (path)
text(0,5,2,0,1,"RA offset",14,7,640)
text(0,5,3,1,1,str(xo),18,7,640)
text(1,5,2,0,1,"DEC offset",14,7,640)
text(1,5,3,1,1,str(yo),18,7,640)
text(0,6,2,0,1,"Min'm Corr",14,7,640)
text(0,6,3,1,1,str(min_corr),18,7,640)
text(1,6,2,0,1,"Interval",14,7,640)
text(1,6,3,1,1,str(interval),18,7,640)
if Auto_G == 0:
    button(0,0,0,640)
    text(0,0,9,0,1,"AUTO",15,7,640)
    text(0,0,9,1,1,"GUIDE",15,7,640)
else:
    button(0,0,1,640)
    text(0,0,1,0,1,"AUTO",15,0,640)
    text(0,0,1,1,1,"GUIDE",15,0,640)
if preview == 1:
    button(0,11,1,640)
    text(0,11,1,0,1,"Preview",14,0,640)
    text(0,11,1,1,1,"Threshold",13,0,640)
else:
    button(0,11,0,640)
    text(0,11,0,0,1,"Preview",14,7,640)
    text(0,11,0,1,1,"Threshold",13,7,640)

if InvRA == 0:   
    text(0,8,0,0,1,"Invert RA",14,7,640)
else:
    text(0,8,1,0,1,"Invert RA",14,7,640)
if InvDEC == 0:
    text(1,8,0,0,1,"Invert DEC",14,7,640)
else:
    text(1,8,1,0,1,"Invert DEC",14,7,640)
text(0,9,1,0,1,"RA ON",14,7,640)
text(1,9,1,0,1,"DEC ON",14,7,640)
text(0,10,1,0,1,"NR",14,7,640)
text(0,10,3,1,1,str(noise),18,7,640)
text(1,10,1,0,1,"Binning",14,7,640)
if binn == 0:
    text(1,10,3,1,1,"off",18,7,640)
else:
    text(1,10,3,1,1,str(binn+1) + "x" + str(binn+1),18,7,640)
text(1,11,2,0,1,"  EXIT ",14,7,640)

w = widths[zoom]
h = int(w/1.7647)
x = int((w/2) - 320 + xo)
y = int((h/2) - 181 + yo)
dim = (w, h)
threshold2 = 0
ar6 = np.zeros((crop*2,crop*2), np.uint16)

def lx200(RAstr,DECstr):
   if ser_connected:
      ser.write(bytes(RAstr.encode('ascii')))
      time.sleep(0.1)
      ser.write(bytes(DECstr.encode('ascii')))
   return
   
capture = 0
xtotal  = 0
ytotal  = 0
while True:
    frames +=1
    capture +=1
    time.sleep(0.25)
    if Pi_Cam == 1:
        # GET AN IMAGE from Pi camera
        img = picam2.capture_array("main")
        image = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    else:
        img = cam.get_image()
        image = pygame.surfarray.array3d(img)
        image =  np.rot90(image, 1, (0,1))
    if threshold == 0:
        text(1,0,0,1,1,str(int(threshold2)),18,7,640)
    resized = cv2.resize(image, dim, interpolation = cv2.INTER_AREA)
    cropped = resized[y:y+362,x:x+640]
    crop2 = cropped[(0-b)-crop:(0-b)+crop,a-crop:a+crop]
    gray = cv2.cvtColor(crop2,cv2.COLOR_RGB2GRAY)
    if c_mask == 1:
        smask = pygame.transform.scale(mask, [crop*2, crop*2])
        img = pygame.surfarray.array3d(smask)
        new_img = img[:, :, 0]
        new_img[new_img > 50] = 1
        gray = gray * new_img
    if binn > 0:
        for x1 in range (binn , (crop*2)-binn):
            for y1 in range (binn , (crop*2)-binn):
                ar6[x1][y1] = np.sum(gray[x1-binn:x1+1,y1-binn:y1+1])
        if np.max(ar6) > 255:
            ar6[ar6 >= 255] = 255
        gray = ar6
    backtorgb = cv2.cvtColor(gray,cv2.COLOR_GRAY2RGB)
    if preview == 1:
        imageq = pygame.surfarray.make_surface(backtorgb)
        imageq = pygame.transform.rotate(imageq,90)
        imageq = pygame.transform.scale(imageq, [120,120])
    min_p = np.min(gray)
    max_p = np.max(gray)
    if threshold > 0:
        threshold2 = threshold
    else:
        threshold2 = ((max_p - min_p) + min_p) *.66
    gray[gray <  threshold2] = 0
    gray[gray >= threshold2] = 1
    ttot = np.sum(gray)
    if noise > 0:
        for x1 in range (noise , (crop*2)-noise):
            for y1 in range (noise , (crop*2)-noise):
                ar6[x1][y1] = np.sum(gray[x1-noise:x1,y1-noise:y1])
        cx = int(noise*noise)
        ar6[ar6 < cx] = 0
        ar6[ar6 >= cx] = 1
        gray = ar6
        ttot = np.sum(gray)
    if preview == 1:
        gray2 = gray[:] * 255
        backtorgb = cv2.cvtColor(gray2,cv2.COLOR_GRAY2RGB)
        backtorgb[:, :, 2:] = 0
        imagep = pygame.surfarray.make_surface(backtorgb)
        imagep = pygame.transform.rotate(imagep,90)
    column_sums = gray.sum(axis=0)
    row_sums = gray.sum(axis=1)
    acorrect = 0
    atot = 0
    while atot < int(ttot/2):
      atot += column_sums[acorrect]
      acorrect +=1
    bcorrect = 0
    btot = 0
    while btot < int(ttot/2):
      btot += row_sums[bcorrect]
      bcorrect +=1
    acorrect -= int(crop)
    bcorrect -= int(crop)
    xcorrect = acorrect
    ycorrect = bcorrect
    if InvRA == 1:
       xcorrect = 0 - xcorrect
    if InvDEC == 1:
       ycorrect = 0 - ycorrect
    xtotal += xcorrect
    ytotal += ycorrect
    update = 0
    RAstr  = ":Mge0000"
    DECstr = ":Mgn0000"
    if RAon == 1:
        text(0,9,1,1,1," ",16,7,640)
    if DECon == 1:
        text(1,9,1,1,1," ",16,7,640)
    if abs(xcorrect) > min_corr/scalex and ttot > 10 and (max_p - min_p) > conl and ttot < (crop * crop) and RAon == 1:
        if xcorrect < 0:
            RAstr = ":Mge" + ("0000" + str(int(abs(xcorrect) * scalex)))[-4:]
        else:
            RAstr = ":Mgw" + ("0000" + str(int(xcorrect * scalex)))[-4:]
        if Auto_G == 1:
            text(0,9,1,1,1,RAstr[3:8],16,7,640)
        else:
            text(0,9,9,1,1,RAstr[3:8],16,7,640)
        update = 1
  
    if abs(ycorrect) > min_corr/scalex  and ttot > 10 and (max_p - min_p) > conl and ttot < (crop * crop) and DECon == 1:
        if ycorrect < 0:
            DECstr = ":Mgn" + ("0000" + str(int(abs(ycorrect) * scalex)))[-4:]
        else:
            DECstr = ":Mgs" + ("0000" + str(int(ycorrect * scalex)))[-4:]
        if Auto_G == 1:
            text(1,9,1,1,1,DECstr[3:8],16,7,640)
        else:
            text(1,9,9,1,1,DECstr[3:8],16,7,640)
        update = 1
    RAstr  = ":Mge0000"
    DECstr = ":Mgn0000"
    if frames > interval and Auto_G == 1:
        if abs(xtotal/frames) > min_corr/scalex and RAon == 1 and ttot > 10 and (max_p - min_p) > conl and ttot < (crop * crop):
            if xtotal < 0:
                RAstr = ":Mge" + ("0000" + str(int(abs(xtotal/frames) * scalex)))[-4:]
            else:
                RAstr = ":Mgw" + ("0000" + str(int((xtotal/frames) * scalex)))[-4:]
        if abs(ytotal/frames) > min_corr/scalex and DECon == 1 and ttot > 10 and (max_p - min_p) > conl and ttot < (crop * crop):
            if ytotal < 0:
                DECstr = ":Mgn" + ("0000" + str(int(abs(ytotal/frames) * scalex)))[-4:]
            else:
                DECstr = ":Mgs" + ("0000" + str(int((ytotal/frames) * scalex)))[-4:]
        if RAstr  != ":Mge0000" or DECstr != ":Mgn0000":
            correct = RAstr+DECstr
            if ser_connected:
               lx200(RAstr,DECstr)
            time.sleep(0.35)
        xtotal = 0
        ytotal = 0
        frames = 0
    imagez = pygame.surfarray.make_surface(cropped)
    imagez = pygame.transform.rotate(imagez,90)
    windowSurfaceObj.blit(imagez, (0, 0))
    if preview == 1:
        imagep.set_colorkey(0, pygame.RLEACCEL)
        windowSurfaceObj.blit(imagep, (a-crop,b-crop))
        windowSurfaceObj.blit(imageq, (400,363))
    if DECon == 1:
        pygame.draw.rect(windowSurfaceObj, (200,200,200), Rect(a - crop,b - int(min_corr/scalex) ,crop*2,2*int(min_corr/scalex)), 1)
    if RAon == 1:
        pygame.draw.rect(windowSurfaceObj, (200,200,200), Rect(a  - int(min_corr/scalex),b - crop ,2*int(min_corr/scalex),crop*2), 1)
    if c_mask == 1:
        pygame.draw.circle(windowSurfaceObj,(0,255,0), (a,b),crop,2)
    else:
        pygame.draw.rect(windowSurfaceObj, (0,255,0), Rect(a  - crop,b - crop ,crop*2,crop*2), 2)
    if ttot > 10 and (max_p - min_p) > conl and ttot < (crop * crop):
        if Auto_G == 1:
            pygame.draw.rect(windowSurfaceObj, (255,0,0), Rect(a + acorrect-2,b - bcorrect-2,4,4), 1)
        else:
            pygame.draw.rect(windowSurfaceObj, (255,0,255), Rect(a + acorrect-2,b - bcorrect-2,4,4), 1)
    pygame.display.update()

    for event in pygame.event.get():
       if event.type == QUIT:
           pygame.quit()

       elif (event.type == MOUSEBUTTONUP):
           mousex, mousey = event.pos
           if mousex > crop and mousex < (640-crop) and mousey > crop and mousey < (362-crop):
               a = mousex
               b = mousey
           if mousex < 400 and mousey > 320 and ser_connected == 1:
               e = int((mousex)/40)
               f = int(mousey/40)
               g = (f*10) + e
               #print (g)
               if g == 97:
                   RAstr = "#:Mgn0250"
                   ser.write(bytes(RAstr.encode('ascii')))
                   time.sleep(.25)
               elif g == 96:
                   RAstr = "#:Mgs0250"
                   ser.write(bytes(RAstr.encode('ascii')))
                   time.sleep(.25)
               elif g == 99 and focus_fitted:
                   RAstr = "#:FP+00250"
                   ser.write(bytes(RAstr.encode('ascii')))
               elif g == 98 and focus_fitted:
                   RAstr = "#:FP-00250"
                   ser.write(bytes(RAstr.encode('ascii')))
               elif g == 107:
                   RAstr = "#:Mge0250"
                   ser.write(bytes(RAstr.encode('ascii')))
                   time.sleep(.25)
               elif g == 106:
                   RAstr = "#:Mgw0250"
                   ser.write(bytes(RAstr.encode('ascii')))
                   time.sleep(.25)
               elif g == 108 and focus_fitted:
                   focus_speed -=1
                   if focus_speed < 1:
                       focus_speed = 1
                   text(4,10,2,1,1,str(focus_speed),14,7,0)
                   RAstr = "#:F" + str(focus_speed)
                   ser.write(bytes(RAstr.encode('ascii')))
               elif g == 109 and focus_fitted:
                   focus_speed +=1
                   if focus_speed > 4:
                       focus_speed = 4
                   text(4,10,2,1,1,str(focus_speed),14,7,0)
                   RAstr = "#:F" + str(focus_speed)
                   ser.write(bytes(RAstr.encode('ascii')))

               # save config
               config[0]  = crop
               config[1]  = threshold
               config[2]  = scale 
               config[3]  = fps
               config[4]  = mode
               config[5]  = speed
               config[6]  = ISO
               config[7]  = brightness
               config[8]  = contrast
               config[9] = Auto_G
               config[10] = min_corr
               config[11] = interval
               config[12] = InvRA
               config[13] = InvDEC
               config[14] = preview
               config[15] = c_mask
               config[16] = fullscreen
               config[17] = ev
               config[18] = noise
               config[19] = binn
               config[20] = Auto_Gain
               config[21] = exposure
               config[22] = gain
               config[23] = gamma
               config[24] = red_balance
               config[25] = blue_balance
               config[26] = auto_contour
               config[27] = contour
               config[28] = dnr
               config[29] = backlight
               config[30] = conl


               with open('PiAGLconfig.txt', 'w') as f:
                   for item in config:
                       f.write("%s\n" % item)
               time.sleep(.1)
                       
           elif mousex > 640:
               e = int((mousex-640)/40)
               f = int(mousey/40)
               g = (f*4) + e
               #print (g)
               if g == 29:
                   crop +=1
                   crop = min(crop,180)
                   if a-crop < 1 or b-crop < 1 or a+crop > 640 or b+crop > 360:
                      crop -=1
                   ar6 = np.zeros((crop*2,crop*2), np.uint16)
                   text(0,7,3,1,1,str(crop),18,7,640)
               elif g == 28:
                   crop -=1
                   crop = max(crop,10)
                   ar6 = np.zeros((crop*2,crop*2), np.uint16)
                   text(0,7,3,1,1,str(crop),18,7,640)
               elif g == 3:
                   threshold +=1
                   threshold = min(threshold,255)
                   if threshold > 0:
                       text(1,0,3,1,1,str(threshold),18,7,640)
                   else:
                       text(1,0,3,1,1,"Auto",18,7,640)
               elif g == 2:
                   threshold -=1
                   threshold = max(threshold,0)
                   if threshold > 0:
                       text(1,0,3,1,1,str(threshold),18,7,640)
                   else:
                       text(1,0,3,1,1,"Auto",18,7,640)
               elif g == 5:
                   zoom +=1
                   if zoom < 7:
                       xo = (xo * (widths[zoom]/widths[zoom-1]))
                       yo = (yo * (widths[zoom]/widths[zoom-1]))
                       text(1,5,3,1,1,str(int(yo)),18,7,640)
                       text(0,5,3,1,1,str(int(xo)),18,7,640)
                       text(0,5,2,0,1,"RA offset",14,7,640)
                       text(1,5,2,0,1,"DEC offset",14,7,640)
                       text(0,1,3,1,1,str(zoom),18,7,640)
                       scalex = scale / scales[zoom]
                       text(1,7,3,1,1,str(int(scalex)),18,7,640)
                       w = widths[zoom]
                       h = int(w/1.7647)
                       x = int((w/2) - 320 + xo)
                       y = int((h/2) - 181 + yo)
                       dim = (w, h)
                   if zoom > 6:
                       zoom = 6
                  
                   
               elif g == 4:
                   zoom -=1
                   zoom = max(zoom,0)
                   xo = (xo * (widths[zoom]/widths[zoom+1]))
                   yo = (yo * (widths[zoom]/widths[zoom+1]))
                   if zoom == 0:
                      xo = 0
                      yo = 0
                      text(0,5,0,0,1,"RA offset",14,7,640)
                      text(1,5,0,0,1,"DEC offset",14,7,640)
                   text(0,5,3,1,1,str(int(xo)),18,7,640)
                   text(1,5,3,1,1,str(int(yo)),18,7,640)
                   text(0,1,3,1,1,str(zoom),18,7,640)
                   scalex = scale / scales[zoom]
                   text(1,7,3,1,1,str(int(scalex)),18,7,640)
                   w = widths[zoom]
                   h = int(w/1.7647)
                   x = int((w/2) - 320 + xo)
                   y = int((h/2) - 181 + yo)
                   dim = (w, h)
                   
               elif g == 31:
                   scale +=1
                   scalex = int(scale / scales[zoom])
                   scalex = min(scalex,255)
                   text(1,7,3,1,1,str(scalex),18,7,640)
               elif g == 30:
                   scale -=1
                   scalex = int(scale / scales[zoom])
                   scalex = max(scalex,0)
                   text(1,7,3,1,1,str(scalex),18,7,640)
               elif g == 7 and mode != 0 or (g == 7 and Pi_Cam == 0):
                   if Pi_Cam == 1:
                       ev +=1
                       ev = min(ev,12)
                       picam2.set_controls({"ExposureValue": ev/10})
                       text(1,1,3,1,1,str(ev),18,7,640)
                   else:
                       gain +=1
                       gain = min(gain,63)
                       path = "v4l2-ctl -c gain=" + str(gain) + " -d " + str(dve)
                       os.system (path)
                       text(1,1,3,1,1,str(gain),18,7,640)
               elif (g == 6 and mode != 0) or (g == 6 and Pi_Cam == 0):
                   if Pi_Cam == 1:
                       ev -=1
                       ev = max(ev,-12)
                       picam2.set_controls({"ExposureValue": ev/10})
                       text(1,1,3,1,1,str(ev),18,7,640)
                   else:
                       gain -=1
                       gain = max(gain,0)
                       path = "v4l2-ctl -c gain=" + str(gain) + " -d " + str(dve)
                       os.system (path)
                       text(1,1,3,1,1,str(gain),18,7,640)

               elif g == 9:
                   if Pi_Cam == 1:
                       fps +=1
                       fps = min(fps,40)
                       picam2.set_controls({"FrameRate": fps})
                       text(0,2,3,1,1,str(fps),18,7,640)
                   else:
                       conl +=1
                       conl = min(conl,255)
                       text(0,2,3,1,1,str(conl),18,7,640)
               elif g == 8:
                   if Pi_Cam == 1:
                       fps -=1
                       fps = max(fps,1)
                       picam2.set_controls({"FrameRate": fps})
                       text(0,2,3,1,1,str(fps),18,7,640)
                   else:
                       conl -=1
                       conl = max(conl,1)
                       text(0,2,3,1,1,str(conl),18,7,640)
               elif (g == 11 and Pi_Cam == 1) or (g == 10 and Pi_Cam == 1):
                 if Pi_Cam == 1:
                    mode += 1
                    if mode == 4:
                       mode = 0
                    if mode == 0:
                       picam2.set_controls({"AeEnable": False,"ExposureTime": speed})
                    else:
                       if mode == 1:
                           picam2.set_controls({"AeEnable": True,"AeExposureMode": controls.AeExposureModeEnum.Normal})
                       elif mode == 2:
                           picam2.set_controls({"AeEnable": True,"AeExposureMode": controls.AeExposureModeEnum.Short})
                       elif mode == 3:
                           picam2.set_controls({"AeEnable": True,"AeExposureMode": controls.AeExposureModeEnum.Long})
                    text(1,2,3,1,1,modes[mode],18,7,640)
                    text(0,3,5,0,1,"Shutter mS",14,7,640)
                    if mode == 0:
                      text(0,3,3,1,1,str(int(speed/1000)),18,7,640)
                    else:
                      text(0,3,0,1,1,str(int(speed/1000)),18,7,640)
               elif (g == 11 and Pi_Cam == 0):
                     gamma +=1
                     if gamma > 31:
                         gamma = 31
                     text(1,2,3,1,1,str(gamma),18,7,640)
                     rpistr = "v4l2-ctl -c gamma=" + str(gamma) + " -d " + str(dve)
                     os.system(rpistr)
               elif (g == 10 and Pi_Cam == 0):
                     gamma -=1
                     if gamma < 0:
                         gamma = 0
                     text(1,2,3,1,1,str(gamma),18,7,640)
                     rpistr = "v4l2-ctl -c gamma=" + str(gamma) + " -d " + str(dve)
                     os.system(rpistr)
               elif g == 13 and mode == 0:
                   if Pi_Cam == 1:
                       speed +=1000
                       speed = min(speed,6000000)
                       picam2.set_controls({"AeEnable": False,"ExposureTime": speed})
                       text(0,3,3,1,1,str(int(speed/1000)),18,7,640)
                       text(0,2,3,1,1,str(fps),18,7,640)
                   else:
                       exposure +=1
                       exposure = min(exposure,255)
                       text(0,3,3,1,1,str(exposure),18,7,640)
                       path = "v4l2-ctl -c exposure=" + str(exposure) + " -d " + str(dve)
                       os.system (path)
               elif g == 12 and mode == 0:
                   if Pi_Cam == 1:
                       speed -=1000
                       speed = max(speed,1000)
                       picam2.set_controls({"AeEnable": False,"ExposureTime": speed})
                       text(0,3,3,1,1,str(int(speed/1000)),18,7,640)
                       text(0,2,3,1,1,str(fps),18,7,640)
                   else:
                       exposure -=1
                       exposure = max(exposure,1)
                       text(0,3,3,1,1,str(exposure),18,7,640)
                       path = "v4l2-ctl -c exposure=" + str(exposure) + " -d " + str(dve)
                       os.system (path)
               elif g == 15 :
                 if Pi_Cam == 1:
                     Again += 1
                     Again = min(Again,64)
                     picam2.set_controls({"AnalogueGain": Again})
                     text(1,3,3,1,1,str(Again),18,7,640)
                 else:
                     Auto_Gain +=1
                     if Auto_Gain > 1:
                         Auto_Gain = 0
                     if Auto_Gain != 0:
                         text(1,3,3,1,1,"ON",18,7,640)
                     else:
                         text(1,3,0,1,1,"off",18,7,640)
                     rpistr = "v4l2-ctl -c gain_automatic=" + str(Auto_Gain) + " -d " + str(dve)
                     os.system(rpistr)
                     if Auto_Gain == 0:
                         path = "v4l2-ctl -c exposure=" + str(exposure) + " -d " + str(dve)
                         os.system (path)
                         path = "v4l2-ctl -c gain=" + str(gain) + " -d " + str(dve)
                         os.system (path)

               elif g == 14 :
                 if Pi_Cam == 1:
                     Again -= 1
                     Again = max(0,Again)
                     picam2.set_controls({"AnalogueGain": Again})
                     text(1,3,3,1,1,str(Again),18,7,640)
                 else:
                     Auto_Gain +=1
                     if Auto_Gain > 1:
                         Auto_Gain = 0
                     if Auto_Gain != 0:
                         text(1,3,3,1,1,"ON",18,7,640)
                     else:
                         text(1,3,0,1,1,"off",18,7,640)
                     rpistr = "v4l2-ctl -c gain_automatic=" + str(Auto_Gain) + " -d " + str(dve)
                     os.system(rpistr)
                     if Auto_Gain == 0:
                         path = "v4l2-ctl -c exposure=" + str(exposure) + " -d " + str(dve)
                         os.system (path)
                         path = "v4l2-ctl -c gain=" + str(gain) + " -d " + str(dve)
                         os.system (path)
                   

               elif g == 17:
                   brightness +=1
                   if Pi_Cam == 1:
                       brightness = min(brightness,100)
                   else:
                       brightness = min(brightness,127)
                   if Pi_Cam == 1:
                       picam2.set_controls({"Brightness": brightness/10})
                   else:
                       path = "v4l2-ctl -c brightness=" + str(brightness) + " -d " + str(dve)
                       os.system (path)
                   text(0,4,3,1,1,str(brightness),18,7,640)
               elif g == 16:
                   brightness -=1
                   brightness = max(brightness,0)
                   if Pi_Cam == 1:
                       picam2.set_controls({"Brightness": brightness/10})
                   else:
                       path = "v4l2-ctl -c brightness=" + str(brightness) + " -d " + str(dve)
                       os.system (path)
                   text(0,4,3,1,1,str(brightness),18,7,640)
               elif g == 19:
                   contrast +=1
                   if Pi_Cam == 1:
                       contrast = min(contrast,100)
                   else:
                       contrast = min(contrast,63)
                   if Pi_Cam == 1:
                       picam2.set_controls({"Contrast": contrast/10})
                   else:
                       path = "v4l2-ctl -c contrast=" + str(contrast) + " -d " + str(dve)
                       os.system (path)
                   text(1,4,3,1,1,str(contrast),18,7,640)
               elif g == 18:
                   contrast -=1
                   if Pi_Cam == 1:
                       contrast = max(contrast,-100)
                   else:
                       contrast = max(contrast,0)
                   if Pi_Cam == 1:
                       picam2.set_controls({"Contrast": contrast/10})
                   else:
                       path = "v4l2-ctl -c contrast=" + str(contrast) + " -d " + str(dve)
                       os.system (path)
                   text(1,4,3,1,1,str(contrast),18,7,640)
               elif g == 21:
                   xo +=1
                   if int((w/2) - 320 + xo) + 640 > w:
                       xo -=1
                   text(0,5,3,1,1,str(int(xo)),18,7,640)
                   x = int((w/2) - 320 + xo)
                   y = int((h/2) - 181 + yo)
               elif g == 20:
                   xo -=1
                   if int((w/2) - 320 + xo) <= 0:
                       xo +=1
                   text(0,5,3,1,1,str(int(xo)),18,7,640)
                   x = int((w/2) - 320 + xo)
                   y = int((h/2) - 181 + yo)
               elif g == 23:
                   yo +=1
                   if int((h/2) - 181 + yo) + 362 > h:
                       yo -=1
                   text(1,5,3,1,1,str(int(yo)),18,7,640)
                   x = int((w/2) - 320 + xo)
                   y = int((h/2) - 181 + yo)
               elif g == 22:
                   yo -=1
                   if int((h/2) - 181 + yo) <= 0:
                       yo +=1
                   text(1,5,3,1,1,str(int(yo)),18,7,640)
                   x = int((w/2) - 320 + xo)
                   y = int((h/2) - 181 + yo)
               elif g == 25:
                   min_corr +=50
                   min_corr = min(min_corr,1000)
                   text(0,6,3,1,1,str(min_corr),18,7,640)
               elif g == 24:
                   min_corr -=50
                   min_corr = max(min_corr,0)
                   text(0,6,3,1,1,str(min_corr),18,7,640)
               elif g == 27:
                   interval +=1
                   interval = min(interval,100)
                   text(1,6,3,1,1,str(interval),18,7,640)
               elif g == 26:
                   interval -=1
                   interval = max(interval,1)
                   text(1,6,3,1,1,str(interval),18,7,640)
               
               elif g == 0 or g == 1:
                   Auto_G +=1
                   if Auto_G > 1:
                       Auto_G = 0
                       button(0,0,0,640)
                       text(0,0,9,0,1,"AUTO",15,7,640)
                       text(0,0,9,1,1,"GUIDE",15,7,640)
                       start_ew = 0
                   else:
                       button(0,0,1,640)
                       text(0,0,1,0,1,"AUTO",15,0,640)
                       text(0,0,1,1,1,"GUIDE",15,0,640)
                       xtotal = 0
                       ytotal = 0
               elif g ==44 or g == 45:
                   preview +=1
                   if preview > 1:
                       preview = 0
                       button(0,11,0,640)
                       text(0,11,0,0,1,"Preview",14,7,640)
                       text(0,11,0,1,1,"Threshold",13,7,640)
                       pygame.draw.rect(windowSurfaceObj, (0,0,0), Rect(400,363,120,120), 0)
                   else:
                       button(0,11,1,640)
                       text(0,11,1,0,1,"Preview",14,0,640)
                       text(0,11,1,1,1,"Threshold",13,0,640)
               elif g == 32 or g == 33:
                   InvRA +=1
                   if InvRA > 1:
                       InvRA = 0
                       button(0,8,0,640)
                       text(0,8,0,0,1,"Invert RA",14,7,640)
                   else:
                       button(0,8,1,640)
                       text(0,8,1,0,1,"Invert RA",14,0,640)
               elif g == 34 or g == 35:
                   InvDEC +=1
                   if InvDEC > 1:
                       InvDEC = 0
                       button(1,8,0,640)
                       text(1,8,0,0,1,"Invert DEC",14,7,640)
                   else:
                       button(1,8,1,640)
                       text(1,8,1,0,1,"Invert DEC",14,0,640)
               elif g == 36 or g == 37:
                   RAon +=1
                   if RAon > 1:
                       RAon = 0
                       button(0,9,1,640)
                       text(0,9,9,0,1,"RA OFF",14,0,640)
                   else:
                       button(0,9,0,640)
                       text(0,9,1,0,1,"RA ON",14,7,640)
               elif g == 38 or g == 39:
                   DECon +=1
                   if DECon > 1:
                       DECon = 0
                       button(1,9,1,640)
                       text(1,9,9,0,1,"DEC OFF",14,0,640)
                   else:
                       button(1,9,0,640)
                       text(1,9,1,0,1,"DEC ON",14,7,640)
               elif g == 43:
                   binn +=1
                   binn = min(binn,3)
                   if binn == 0:
                       text(1,10,3,1,1,"off",18,7,640)
                   else:
                       text(1,10,3,1,1,str(binn+1) + "x" + str(binn+1),18,7,640)
               elif g == 42:
                   binn -=1
                   binn = max(binn,0)
                   if binn == 0:
                       text(1,10,3,1,1,"off",18,7,640)
                   else:
                       text(1,10,3,1,1,str(binn+1) + "x" + str(binn+1),18,7,640)
               elif g == 41:
                   noise +=1
                   noise = min(noise,3)
                   text(0,10,3,1,1,str(noise),18,7,640)
               elif g == 40:
                   noise -=1
                   noise = max(noise,0)
                   text(0,10,3,1,1,str(noise),18,7,640)
               elif g == 46 or g == 47:
                   pygame.quit()
                       
               # save config
               config[0]  = crop
               config[1]  = threshold
               config[2]  = scale 
               config[3]  = fps
               config[4]  = mode
               config[5]  = speed
               config[6]  = Again
               config[7]  = brightness
               config[8]  = contrast
               config[9] = Auto_G
               config[10] = min_corr
               config[11] = interval
               config[12] = InvRA
               config[13] = InvDEC
               config[14] = preview
               config[15] = c_mask
               config[16] = fullscreen
               config[17] = ev
               config[18] = noise
               config[19] = binn
               config[20] = Auto_Gain
               config[21] = exposure
               config[22] = gain
               config[23] = gamma
               config[24] = red_balance
               config[25] = blue_balance
               config[26] = auto_contour
               config[27] = contour
               config[28] = dnr
               config[29] = backlight
               config[30] = conl

               with open('PiAGLconfig.txt', 'w') as f:
                   for item in config:
                       f.write("%s\n" % item)

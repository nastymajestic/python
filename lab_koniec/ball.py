# parts of the code are based on https://www.pyimagesearch.com/2016/01/04/unifying-picamera-and-cv2-videocapture-into-a-single-class-with-opencv/
# before running the code install imutils for python3 (pip3 install imutils)

import time
from imutils.video import VideoStream
import serial
# from picamera.array import PiRGBArray
# from picamera import PiCamera
import numpy as np
import cv2
import math

def translate(value, oldMin, oldMax, newMin=-100, newMax=100):
    # Figure out how 'wide' each range is
    oldRange = oldMax - oldMin
    newRange = newMax - newMin
    NewValue = (((value - oldMin) * newRange) / oldRange) + newMin
    return int(NewValue)

def findCenterOfBlob(moment):
    blobCenter = tuple(-1, -1)    
    m01 = M['m01']
    m10 = M['m10']
    momentArea = M['m00']
	#if the area of the found object is not big enough, then it's just noise
    if momentArea > 10000:
        posX = (m10 / momentArea)
        posY = (m01 / momentArea)

        if posX >= 0 and posY >= 0:
            blobCenter = tuple(posX, posY)
    return blobCenter


usesPiCamera = True


# camera = PiCamera()
# camera.framerate = 60
cameraResolution = (640, 480)
# camera.resolution = cameraResolution

# # camera.awb_mode = 'tungsten'
# camera.vflip = camera.hflip = True
# camera.video_stabilization = True
# rawCapture = PiRGBArray(camera, size=cameraResolution)

# initialize the video stream and allow the cammera sensor to warmup
vs = VideoStream(usePiCamera=usesPiCamera, resolution=cameraResolution, framerate=60).start()
time.sleep(2.0)

#normalnie Hue, czyli baraw jest wyrazana jako kat pelny czyli 360 stopni
#w OpenCV dla HSV sa 3 bajty (po jednym na H, S, V), zredukowano przez miary katow koloru dwukrtonie (zakres bajtu to liczby 0-255)
#dlatego zakres H jest w wartosciach od 0-179


#nalezy wybrac zakres pasm kolorow poszukiwanego przez nas obiektu (okrag)
#H 170-179 sprobuj
#S 150-255 sprobuj
#V 60-255 sprobuj

colorLower = (0, 100, 50)
colorUpper = (20, 255, 255)
colorTolerance = 3
paused = False
roiSize = (16, 16) # roi size on the scaled down image (converted to HSV)


# # initialize serial communication
# ser = serial.Serial(port='/dev/ttyACM0', baudrate=57600, timeout=0.05)

while True:
# for cameraFrame in camera.capture_continuous(rawCapture, format="bgr", use_video_port=True):
    loopStart = time.time()
    if not paused:

        frame = vs.read()
        frame = cv2.flip(frame, flipCode=-1)
        
        height, width = frame.shape[0:2]
        scaleFactor = 4
        newWidth, newHeight = width//scaleFactor, height//scaleFactor

        kernel = (5,5)
        #moze kernel wiekszy (9,9) ?
        resizedColor = cv2.resize(frame, (newWidth, newHeight), interpolation=cv2.INTER_CUBIC)
        resizedColor_blurred = cv2.GaussianBlur(resizedColor, kernel, 0)

        # resizedHSV = cv2.cvtColor(resizedColor, cv2.COLOR_BGR2HSV)
        resizedHSV = cv2.cvtColor(resizedColor_blurred, cv2.COLOR_BGR2HSV)

        roi = resizedHSV[newHeight//2 - roiSize[0]//2 : newHeight //2 + roiSize[0]//2, newWidth//2 - roiSize[1]//2 : newWidth//2 + roiSize[1]//2, :]
        # roi = resizedHSV[10*newHeight//20 : 12*newHeight//20, 10*newWidth//20 : 12*newWidth // 20, :]
        
        colorLowerWithTolerance = (colorLower[0] - colorTolerance,) + colorLower[1:]
        colorUpperWithTolerance = (colorUpper[0] + colorTolerance,) + colorUpper[1:]

        mask = cv2.inRange(resizedHSV, colorLowerWithTolerance, colorUpperWithTolerance)
        cv2.erode(mask, None, iterations=5)
        cv2.dilate(mask, None, iterations=5)

        #cv2.CHAIN_APPROX_SIMPLE
        (_,contours, hierarchy) = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)

        boundingBoxes = []
        biggestObject_BoundingBox = None
        biggestObjectMiddle = None
        filteredContours = []
        minPointsInCountour = 50

        biggestObject_Circle = None
        circles = []
        if contours:
            # largestContour = max(contours, key=cv2.contourArea)
            # biggestObject_BoundingBox = cv2.boundingRect(largestContour)
            
            for i, contour in enumerate(contours):
                pointsInContour = len(contour)
                #odrzucamy kontury zawierajace malo elementow, interesuja nas duze obiekty
                if pointsInContour >= minPointsInCountour:
                    #area = cv2.contourArea(contour)
                    M = cv2.moments(contour)
                    n02 = M['nu02'] #okresla wariancje punktow obiektu w kierunku pionowym
                    n20 = M['nu20'] #okresla wariancje punktow obiektu w kierunku poziomym
                    m01 = M['m01']
                    m10 = M['m10']
                    momentArea = M['m00']
                    momentRadius = math.sqrt(momentArea / 3.141592)
                    maxMoment = max(n02, n20)
                    minMoment = min(n02, n20)
                    # if area > ((newWidth * newHeight)/256):
                    if momentRadius > 0 and momentArea > 0:
                        #bylo 0.8 i 2 z naszej wersji
                        if ((maxMoment / minMoment) > 0.75 and (maxMoment / minMoment) < 1.25):
                            posX = m10 / momentArea
                            posY = m01 / momentArea
                            if posX > 0 and posY > 0:
                                filteredContours.append(contour)
                                x, y, w, h = cv2.boundingRect(contour)
                                ((x, y), radius) = cv2.minEnclosingCircle(contour)
                                circles.append((x, y, radius)
                                boundingBoxes.append( (x, y, w, h) )

        else:
            pass

        upscaledColor = cv2.resize(resizedColor, (width, height), interpolation=cv2.INTER_NEAREST)
        # draw ROI on upscaled image
        xROI, yROI = width//2 - roiSize[1]//2 * scaleFactor, height//2 - roiSize[0]//2 * scaleFactor
        cv2.rectangle(upscaledColor, (xROI, yROI), (xROI + roiSize[0]*scaleFactor, yROI + roiSize[1]*scaleFactor), (0, 0, 0), thickness=3)
        if boundingBoxes:
            largestContour = max(filteredContours, key=cv2.contourArea)
            biggestObject_BoundingBox = cv2.boundingRect(largestContour)

        for boundingBox in boundingBoxes:
            x,y,w,h = boundingBox
            cv2.rectangle(resizedColor, (x, y), (x+w, y+h), (255, 255, 0), thickness=1)
            cv2.rectangle(upscaledColor, (x*scaleFactor, y*scaleFactor),
                        ((x+w)*scaleFactor, (y+h)*scaleFactor), (255, 255, 0), thickness=2)
        
        if biggestObject_BoundingBox:
            x, y, w, h = biggestObject_BoundingBox
            biggestObjectMiddle = ((x+ w//2)*scaleFactor, (y + h//2)*scaleFactor)
            cv2.rectangle(resizedColor, (x, y), (x+w, y+h), (0, 0, 255), thickness=2)
            cv2.rectangle(upscaledColor, (x*scaleFactor, y*scaleFactor),
                            ((x+w)*scaleFactor, (y+h)*scaleFactor), (0, 0, 255), thickness=3)
            cv2.circle(upscaledColor, biggestObjectMiddle, 2, (255, 0, 0), thickness=2)
            screenMiddle = width//2, height//2
            distanceVector = tuple(map(lambda x, y: x - y, biggestObjectMiddle, screenMiddle))
            # print("Vector: {}".format(distanceVector))
            scaled = (translate(distanceVector[0], -width//2, width//2), translate(distanceVector[1], -height//2, height//2) )
            # print("Vector scaled: {}".format(scaled))
            pitch = scaled[1] # up-down Y
            yaw = scaled[0] # left-right X
            cv2.line(upscaledColor, screenMiddle, biggestObjectMiddle, (0, 0, 255))
            packet = '<packet, {}, {}>'.format(yaw, pitch)
            # packetBytes = bytes(packet, 'utf-8')
            # ser.write(packetBytes)
            # print(ser.read_all())

        #wersja z minEnclosing circles
        #if circles:
         #   largestContour = max(filteredContours, key=cv2.contourArea)
          #  biggestObject_Circle = cv2.minEnclosingCircle(largestContour)
        #for circle in circles:
         #   x,y,r = circle
          #  objectCenter = x*scaleFactor, y*scaleFactor
           # cv2.circle(upscaledColor, objectCenter, r*scaleFactor, (255, 255, 0), thickness=2)
        #if biggestObject_Circle:
         #   x,y,radius = biggestObject_Circle
          #  objectCenter = x*scaleFactor, y*scaleFactor
           # scaledRadius = radius*scaleFactor
            #packet = '<packet, {}, {}, {}>'.format(objectCenter[0], objectCenter[1], scaledRadius)                                   
    
        cv2.imshow("video", upscaledColor)
        cv2.imshow("roi", roi)
        cv2.imshow("mask", mask)

        modTolerances = False

    # handle keys 
    key = cv2.waitKey(1) & 0xFF
    if key == ord('q'):
        break
    elif key == ord('a'):
        avg_h = 0
        avg_s = 0
        avg_v = 0
        i = 0
        for _, row in enumerate(roi):
            avg = np.average(row, 0)
            avg_h += avg[0]
            avg_s += avg[1]
            avg_v += avg[2]
            i+=1

        avg_h /= i
        avg_s /= i
        avg_v /= i
        print("HUE:{}, SAT:{}, VAL:{}".format(avg_h, avg_s, avg_v))
        colorLower = (max(0,avg_h), max(0, avg_s - 50), max(0,avg_v - 50))
        colorUpper = (min (255, avg_h), min(255, avg_s + 50), min(255, avg_v + 50))
    elif key == ord('z'):
        h = roi[:,:,0]
        s = roi[:,:,1]
        v = roi[:,:,2]
        colorLower = (int(np.min(h)), max(0, int(np.min(s)-20 )), max(0, int(np.min(v)-20)))
        colorUpper = (int(np.max(h)), min(255, int(np.max(s)+20)), min(255, int(np.max(v)+20)))
    elif key == ord('w'):
        colorTolerance = min(colorTolerance + 1, 50)
        print("New color range: {}".format(colorTolerance))
    elif key == ord('s'):
        colorTolerance = max(colorTolerance - 1, 0)
        print("New color range: {}".format(colorTolerance))
    elif key == ord('p'):
        paused = not paused
    elif key == ord('d'):
        # pause/unpause arduino camera movement
        ser.write(bytes('d', 'utf-8'))
    
    # rawCapture.truncate(0)
    loopEnd= time.time()
    print("loop execution took {:3.2f}ms".format((loopEnd - loopStart)*1000))
    
# cleanup
cv2.destroyAllWindows()
vs.stop()

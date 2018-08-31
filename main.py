import sys
import os
import picamera
import time
import RPi.GPIO as GPIO
from email.MIMEMultipart import MIMEMultipart
from email.MIMEText import MIMEText
from email.MIMEImage import MIMEImage
from email.MIMEBase import MIMEBase
from email import Encoders
import subprocess
import smtplib
import socket
import config
import pygame
import io
import random
import gphoto2 as gp
from config import *


## b/w
camera = picamera.PiCamera()
#camera.saturation = -100
camera.brightness = 50
camera.framerate = 10
camera.resolution = (2592, 1944)
camera.preview_alpha = 200
camera.vflip = True
camera.hflip = True
camera.flash_mode = 'on'

black = 0, 0, 0

pygame.init()
screen = pygame.display.set_mode((0,0), pygame.FULLSCREEN)
big_font = pygame.font.SysFont('freeserif', 50, bold=1)
small_font = pygame.font.SysFont('freeserif', 30, bold=1)
pretext_font = pygame.font.Font(None, 100)

GPIO.cleanup()
GPIO.setmode(GPIO.BCM)    
GPIO.setup(led_charge_pin,GPIO.OUT) # LED charge
GPIO.setup(led_torch_pin,GPIO.OUT)
GPIO.setup(button1_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP) # Big RED button
GPIO.output(led_charge_pin,True);
GPIO.output(led_torch_pin,False);

def drawText(font, textstr, clear_screen=False, color=(250, 10, 10),x=0,y=0):
    if clear_screen:
        screen.fill(black)
    pltText = font.render(textstr, 1, color)
    
    textpos = pltText.get_rect()
    if not x:
        textpos.centerx = screen.get_rect().centerx
    else:
        textpos.centerx = x
    if not y:    
        textpos.centery = screen.get_rect().centery
    else:
        textpos.centery = y

    screen.blit(pltText, textpos)

    pygame.display.update()

def randomImage(dir):
        files = [os.path.join(path, filename)
                for path, dirs, files in os.walk(dir)
                for filename in files]
	if files == []:
            return files
        else:
	    return random.choice(files)

def displayImage(file):
        print(file)
        if os.path.getsize(file) != 0 :
            screen.fill((0,0,0))
            image = pygame.image.load(file)
            image = pygame.transform.scale(image,(800,480))
            screen.blit(image,(0,0))
            pygame.display.flip()

def checkEvents():
        for event in pygame.event.get():
                if event.type == pygame.QUIT or ( event.type is pygame.KEYDOWN and event.key == pygame.K_ESCAPE ):
                        pygame.quit()
                        sys.exit()
                if (event.type is pygame.KEYDOWN and event.key == pygame.K_p) or (event.type == pygame.MOUSEBUTTONDOWN) :
                        return 1	

def preview(timeDelay, status='r', index=1):
    timeout = 1
    ticker = 0
    PRsize = (1312,976)
    clk = pygame.time.Clock()
    clk.tick()
    if (status == 'r'):
        ## Preview Loop
        camera.start_preview()
        GPIO.output(led_torch_pin,True)
        while (timeDelay):
            clk.tick()
            ticker+=clk.get_time()
            if (ticker > 2000):
                ticker = 0
                timeDelay=timeDelay - 1
            drawText(pretext_font, ":) SMILE NOW !! " + str(timeDelay), clear_screen=True, color=(255, 255, 255))
            drawText(small_font, 'photo ' + str(index) + ' of ' + str(total_pics), color=(255,255,255), y=15)
        GPIO.output(led_torch_pin,False)
        camera.stop_preview()
    
    ## Waiting Screen
    elif (status == 'w'):
        randomFile = randomImage(file_path)
        if randomFile != [] :
            displayImage(randomFile)
        else:
            screen.fill((255, 255, 255))
        drawText(big_font, "READY?", color=(0,255,0), y=50) 
        drawText(big_font, "Touch me", color=(255,0,0), y=200) 

def start_photobooth():
    ##for the first PIC
    preview(3,'r',1)

    #take the photos
    file_name=time.strftime("%d%m%Y_%H%M%S")
    for i, filename in enumerate(camera.capture_continuous(file_path + file_name + '-' + '{counter:02d}.jpg')):
        print(filename)

        if use_external_camera == 1:
            camera0 = gp.check_result(gp.gp_camera_new())
            gp.check_result(gp.gp_camera_init(camera0))
            gp.gp_camera_capture(camera0, gp.GP_CAPTURE_IMAGE)
            gp.gp_camera_exit(camera0)

        if i == total_pics-1:
            #GPIO.output(led1_pin,False);
            break
        preview(3,'r',i+2)

    #show photos
    for pNum in range (1,total_pics+1):
        displayImage(file_path + file_name + '-0' + str(pNum) + '.jpg')
        text = 'photo ' + str(pNum) + ' of ' + str(total_pics)
        drawText(small_font, text, clear_screen=False, color=(255,255,255), y=15)
        time.sleep(5)

## check internet connection
def is_connected():
    try:
    # see if we can resolve the host name -- tells us if there is
    # a DNS listening
        host = socket.gethostbyname(test_server)
    # connect to the host -- tells us if the host is actually
    # reachable
        s = socket.create_connection((host, 80), 2)
        return True
    except:
        pass
    return False

## Send Email with pic
def send_email():
    try:
        msg = MIMEMultipart()
        msg['Subject'] = "Photo Booth " + now
        msg['From'] = addr_from
        msg['To'] = addr_to
        file_to_upload = file_path_arch +"PB_"+now + ".jpg"
        print file_to_upload
        fp = open(file_to_upload, 'rb')
        part = MIMEBase('image', 'jpg')
        part.set_payload( fp.read() )
        Encoders.encode_base64(part)
        part.add_header('Content-Disposition', 'attachment; filename="%s"' % os.path.basename(file_to_upload))
        fp.close()
        msg.attach(part)
        server = smtplib.SMTP('smtp.gmail.com:587')
        server.starttls()
        server.login(user_name, password)
        server.sendmail(msg['From'], msg['To'], msg.as_string())
        server.quit()
        print "email sent"
    except ValueError:
        print "Oops. No internect connection. Upload later."
        try: #make a text file as a note to upload the .gif later
            file = open(file_path + now + "-FILENOTUPLOADED.txt",'w')   # Trying to create a new file or open one
            file.close()
        except:
            print('Something went wrong. Could not write file.')
            sys.exit(0) # quit Python

## send print script and create image
def printPic():
    cmd = ['sudo', './print.sh', now]
    pr = subprocess.Popen(cmd)
    pr.wait()


## Main Loop
while True:
    preview(1,'w')
    #GPIO.output(led1_pin,True);
    ##wait for button press 
    #GPIO.wait_for_edge(button1_pin, GPIO.FALLING)
    clk = pygame.time.Clock()
    clk.tick()
    ticker=0
    while (True):
         clk.tick()
         ticker+=clk.get_time()
         
         if checkEvents() == 1 :
             break

         for event in pygame.event.get():
             if event.type == pygame.QUIT:
                 print "QUIT event detected"
                 sys.exit()

             elif event.type == pygame.KEYDOWN:
                 # Quit the program on escape
                 if event.key == pygame.K_ESCAPE:
                     sys.exit()

         if (ticker > 5000):
             ticker = 0
             preview(1,'w')
   
    #GPIO.output(led1_pin,False);
    time.sleep(0.2) #debounce button press
    start_photobooth()
    #GPIO.output(led1_pin,True);
    

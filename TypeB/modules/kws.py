#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Example 1: GiGA Genie Keyword Spotting"""

from __future__ import print_function

import audioop
from ctypes import *
import RPi.GPIO as GPIO
import ktkws # KWS
import MicrophoneStream as MS
import tts
KWSID = ['기가지니', '지니야', '친구야', '자기야']
RATE = 16000
CHUNK = 512

GPIO.setmode(GPIO.BOARD)
GPIO.setwarnings(False)
GPIO.setup(29, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(31, GPIO.OUT)
btn_status = False

def callback(channel):  
	# print("falling edge detected from pin {}".format(channel))
	print("버튼 감지됨")
	global btn_status
	btn_status = True
	# print(btn_status)

GPIO.add_event_detect(29, GPIO.FALLING, callback=callback, bouncetime=1000)

ERROR_HANDLER_FUNC = CFUNCTYPE(None, c_char_p, c_int, c_char_p, c_int, c_char_p)
def py_error_handler(filename, line, function, err, fmt):
	dummy_var = 0
c_error_handler = ERROR_HANDLER_FUNC(py_error_handler)
asound = cdll.LoadLibrary('libasound.so')
asound.snd_lib_error_set_handler(c_error_handler)


def detect():
	global btn_status
	with MS.MicrophoneStream(RATE, CHUNK) as stream:
		audio_generator = stream.generator()

		for content in audio_generator:

			rc = ktkws.detect(content)
			rms = audioop.rms(content,2)
			#print('audio rms = %d' % (rms))

			if (btn_status == True):
				rc = 1
				btn_status = False	
			if (rc == 1):
				# MS.play_file("../data/sample_sound.wav") # 소리시러
				return 200

def call(key_word):
	rc = ktkws.init("../data/kwsmodel.pack")
	# print ('init rc = %d' % (rc))
	rc = ktkws.start()
	# print ('start rc = %d' % (rc))
	print ("KWS: 호출어 대기중")
	ktkws.set_keyword(KWSID.index(key_word))
	rc = detect()
	# print ('detect rc = %d' % (rc))
	# print ('\n\n호출어가 정상적으로 인식되었습니다.\n\n')
	ktkws.stop()
	return rc

def main():
	call("지니야")

if __name__ == '__main__':
	main()

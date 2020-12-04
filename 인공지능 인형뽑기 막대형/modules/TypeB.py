#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import print_function

""" AMK관련 라이브러리 """
import MicrophoneStream as MS # 음성출력
import kws # 음성호출
import tts # Text To Speech
import stt # Speech To Text
import time # time.sleep

""" 하드웨어 제어 및 시리얼 통신 """
import RPi.GPIO as GPIO # GPIO 제어(버튼, LED 제어)
import serial # 시리얼 통신
import re # 파싱
GPIO.setmode(GPIO.BOARD)
GPIO.setwarnings(False)
GPIO.setup(31, GPIO.OUT)
Serial = serial.Serial(
  port = '/dev/ttyACM0',
  baudrate = 9600,
)

""" 인공지능 관련 """
import cv2
import numpy as np
import json
import copy
with open ('data/data.json', 'r') as f:
  json_data = json.load(f)
capture = cv2.VideoCapture(0)
capture.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
capture.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

""" 기타 변수 설정 """
with open ('data/colordata.json', 'r') as f:
  colordata = json.load(f)
  color_to_korean = colordata['color_to_korean']
  color_to_english = colordata['color_to_english']
scan_position = [
  [34, 0, 4],
  [156, 0, 4],
  [264, 0, 4],
  [264, 155, 9],
  [156, 155, 4],
  [34, 155, 4]
]
hsv_data_list = np.arange(18).reshape(6, 3)
color_data_list = {} # 위치(0~6), 색상(영어 or '?')를 대응하여 저장
find_color_num_list = {} # 찾은 색상(영어), 개수를 대응하여 저장

""" 이미지 반환 함수 """
def get_image():
  ret, frame = capture.read()
  return frame

""" 색상 스캔 -> hsv_data_list에 저장 """
def get_hsv_data():
  global hsv_data_list
  hsv_data_list = np.arange(18).reshape(6, 3)
  i = 0
  Serial.write(bytes("G00 X{0}. Z{1}.;".format(scan_position[i][0], scan_position[i][1]).encode()))
  nexttime = time.time() + 2
  i = 1
  while True:
    image = get_image()
    cv2.imshow("debug", image)
    cv2.waitKey(1)
    if nexttime <= time.time():
      if i == 6:
        break
      changed_HSV = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
      hsv_data_list[i-1] = changed_HSV[240][320]
      Serial.write(bytes("G00 X{0}. Z{1}.;".format(scan_position[i][0], scan_position[i][1]).encode()))
      nexttime = time.time() + scan_position[i][2]
      i = i + 1
  Serial.write(bytes("G28;".encode()))
  time.sleep(14)
  print(hsv_data_list)

""" 색상 검출 -> color_data_list, find_color_num_list에 저장 """
def find_color_name():
  global hsv_data_list
  global color_data_list
  global find_color_num_list
  color_data_list = {}
  find_color_num_list = {}
  i = 0
  isfind = False
  for hsv in hsv_data_list:
    color_data_list[i] = ""
    for color_val in json_data:
      hsv_max = [0, 0, 0]
      hsv_min = [255, 255, 255]
      for color_num in json_data[color_val]:
        j = 0
        for color_type in json_data[color_val][color_num]:
          if hsv_max[j] <= json_data[color_val][color_num][color_type]:
            hsv_max[j] = json_data[color_val][color_num][color_type]
          if hsv_min[j] >= json_data[color_val][color_num][color_type]:
            hsv_min[j] = json_data[color_val][color_num][color_type]
          j = j + 1
      if hsv[0] >= hsv_min[0] and hsv[0] <= hsv_max[0] \
        and hsv[1] >= hsv_min[1] and hsv[1] <= hsv_max[1] \
        and hsv[2] >= hsv_min[2] and hsv[2] <= hsv_max[2] :
        color_data_list[i] = color_val
        isfind = True
        break
    if color_data_list[i] == "red2": # 적색은 어두운적색, 밝은적색이 존재함
      color_data_list[i] = "red"
    if color_data_list[i] == "": 
      color_data_list[i] = "?"
    else:
      find_color_num_list[color_data_list[i]] = 0
    i = i + 1
  if isfind:
    for pointer in color_data_list:
      if color_data_list[pointer] == "?": continue
      find_color_num_list[color_data_list[pointer]] = find_color_num_list[color_data_list[pointer]] + 1
  return isfind

""" 색상 데이터로 TTS 생성 """
def generate_tts_from_color():
  global color_data_list
  global find_color_num_list
  text = ""
  for key in find_color_num_list:
    text = text + "{0} {1}개, ".format(color_to_korean[key], find_color_num_list[key])
  text = text + "가 감지되었습니다. 어떤 색상을 선택할까요?"
  return text

""" STT로 선택한 색상을 뽑음 """
def get_ball_with_stt(colorname):
  global color_data_list
  final_key = 0
  if colorname == "red" and not color_data_list.has_key(colorname):
    colorKey = "red2"
  for key in color_data_list:
    if color_data_list[key] == colorname:
      final_key = key
      break
  Serial.write(bytes("G00 X{0}. Z{1}.;".format(scan_position[final_key][0], scan_position[final_key][1]+10).encode()))
  Serial.write(bytes("G01;".encode()))

""" 현재 위치 색상 반환 """
def get_hsv_data_now():
  global hsv_data_list
  hsv_data_list=[]
  nexttime = time.time() + 3
  while True:
    image = get_image()
    cv2.imshow("debug", image)
    cv2.waitKey(1)
    if nexttime <= time.time():
      changed_HSV = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
      center_HSV = changed_HSV[240][320]
      hsv_data_list = [center_HSV]
      break
  find_color_name()
  return center_HSV

""" 학습 데이터 저장 """
def add_hsv_code(color_name, hsv_code):
  global json_data
  hsv_code = [int(hsv_code[0]), int(hsv_code[1]), int(hsv_code[2])]
  if hsv_code[0] >= 100 and color_name == "red" : color_name = "red2" # 짙은 빨강
  i = 1
  if not color_name in json_data :
    json_data[color_name] = {}
  for color_num in json_data[color_name]: i = i + 1
  json_data[color_name][str(i)] = {
    'h' : hsv_code[0] - 10,
    's' : 0,
    'v' : 0  
  }
  json_data[color_name][str(i + 1)] = {
    'h' : hsv_code[0] + 10,
    's' : 255,
    'v' : 255 
  }
  jsonString = json.dumps(json_data, indent=4)
  with open ('data/data.json', 'w+') as f:
    f.write(jsonString)
  with open ('data/data.json', 'r') as f:
    json_data = json.load(f)

""" 음성인식 분류 """
def speech_read(mode):
  GPIO.output(31, GPIO.HIGH)
  readval = ""
  readval = stt.get_text_from_voice()
# 원점으로 이동해 -----
  if readval.find("원점") != -1: 
    print("원점이동")
    tts.getText2VoiceStream2("원점으로 이동합니다.")
    Serial.write(bytes("G28;".encode()))
# 가로 방향으로 ~ 만큼 이동해 -----
  elif readval.find("가로") != -1: 
    print("X축 이동")
    if re.findall("\d+", readval) :
      moveval = int(re.findall("\d+", readval)[0])
      tts.getText2VoiceStream2("가로축 방향 {0}으로 이동합니다.".format(moveval))
      Serial.write(bytes("G00 X{}.;".format(moveval).encode()))
# 세로 방향으로 ~ 만큼 이동해 -----
  elif readval.find("세로") != -1 or readval.find("새로") != -1: 
    print("Z축 이동")
    if re.findall("\d+", readval) :
      moveval = int(re.findall("\d+", readval)[0])
      tts.getText2VoiceStream2("세로축 방향 {0}으로 이동합니다.".format(moveval))
      Serial.write(bytes("G00 Z{}.;".format(moveval).encode()))
# 스틱 작동해 -----
  elif readval.find("스틱") != -1: 
    print("잡잡")
    tts.getText2VoiceStream2("스틱을 작동합니다.")
    Serial.write(bytes("G01;".encode()))
# 인공지능 물체 인식 시작 -----
  elif readval.find("인공지능") != -1: 
    tts.getText2VoiceStream2("인공지능 물체 인식을 시작합니다. 먼저 전체 물체 스캔을 시작합니다.")
    print("인공지능 작동")
    Serial.write(bytes("G28;".encode()))
    time.sleep(5)
    print("작동 시작")
    get_hsv_data()
    isfind = find_color_name()
    if not isfind:
      tts.getText2VoiceStream2("어떠한 공도 찾지 못하였습니다. 정상적으로 인식하지 못한 경우 학습을 진행해주시기 바랍니다.")
      return
    text = generate_tts_from_color()
    tts.getText2VoiceStream2(text)
    while True:
      readval = stt.get_text_from_voice()
      isbreak = False
      if readval.find("취소") != -1:
        tts.getText2VoiceStream2("취소합니다.")
        break
      else:
        for key, value in color_to_english.items():
          if readval.find(key) != -1 and value in find_color_num_list:
            get_ball_with_stt(value)
            isbreak = True
            break
      if isbreak:
        break
      else:
        tts.getText2VoiceStream2("이해하지 못했습니다. 다시 한번 말해주세요.")
    cv2.destroyAllWindows()
# 현재 위치의 물체 학습해줘 -----
  elif readval.find("학습") != -1: 
    tts.getText2VoiceStream2("현재 위치의 색상을 학습합니다. 카메라에 감지된 색상 코드를 읽는 중입니다.")
    hsv_data = get_hsv_data_now()
    cv2.destroyAllWindows()
    if color_data_list[0] != '?' :
      tts.getText2VoiceStream2("{0}이 감지되었습니다. 처음으로 돌아갑니다.".format(color_to_korean[color_data_list[0]]))
      return
    else:
      tts.getText2VoiceStream2("색상의 이름을 말해주세요.")
      while True:
        readval = stt.get_text_from_voice()
        isbreak = False
        if readval.find("취소") != -1:
          tts.getText2VoiceStream2("취소합니다.")
          break
        else:
          for key, value in color_to_english.items():
            if readval.find(key) != -1:
              tts.getText2VoiceStream2("{0}을 학습 데이터에 더합니다.".format(color_to_korean[value]))
              add_hsv_code(value, hsv_data)
              isbreak = True
              break
        if isbreak:
          break
        else:
          tts.getText2VoiceStream2("이해하지 못했습니다. 다시 한번 말해주세요.")
  else:
    tts.getText2VoiceStream2("이해하지 못했습니다.")

  GPIO.output(31, GPIO.LOW)

""" 호출 """
def call():
  recog = 500
  recog = kws.call('지니야')
  if recog == 200:
    tts.getText2VoiceStream2("네,")
    speech_read(1)

""" Main 함수 """
def main():
  while 1:
    call()
    cv2.destroyAllWindows()

""" 직접 코드 실행시 작동 """
if __name__ == '__main__':
  tts.getText2VoiceStream2("호출하기 위해 지니야 를 불러주세요.")
  main()

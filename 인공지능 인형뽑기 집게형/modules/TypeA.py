#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import print_function

""" AMK관련 라이브러리 """
import MicrophoneStream as MS # 음성출력
import kws # 음성호출
import tts # Text To Speech
import stt # Speech To 
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

coordinate_now = [0, 0] # 현재 기계좌표
coordinate_correction = [130, 25] # 2차 검출 시 화면 프레임에서 그래퍼까지의 상대좌표

""" 기타 변수 설정 """
with open ('data/colordata.json', 'r') as f:
  colordata = json.load(f)
  color_to_korean = colordata['color_to_korean']
  color_to_english = colordata['color_to_english']

""" 비율 계산 함수 """
def map(x,input_min,input_max,output_min,output_max):
  return (x-input_min)*(output_max-output_min)/(input_max-input_min)+output_min #map()함수 정의.

""" 사진 촬영, 그래퍼 걸리지 않는 크기로 잘라서 반환 """
def getimage():
  ret, frame = capture.read()
  asdf = cv2.rotate(frame[210:480, 300:640], cv2.ROTATE_90_COUNTERCLOCKWISE)
  return asdf

""" 전체 사진 촬영, 합성 """
def get_entire_image():
  i = 0
  imageall = list()
  nowtime = time.time() + 3
  while True:
    frame = getimage()
    cv2.imshow("VideoFrame", frame)
    cv2.waitKey(1)
    if nowtime <= time.time():
      if i == 0:
        image1 = getimage()[0:340][0:290] # 수정전 290
        Serial.write(bytes("G00 X140.;".encode()))
      elif i == 1:
        image2 = getimage()[0:340][0:315]
        Serial.write(bytes("G00 X280.;".encode()))
      elif i == 2:
        image3 = getimage()
        Serial.write(bytes("G00 Y180.;".encode()))
      elif i == 3:
        image4 = getimage()[0:340][117:340]
        Serial.write(bytes("G00 X140.;".encode()))
      elif i == 4:
        image5 = getimage()[0:340][92:340]
        Serial.write(bytes("G00 X0.;".encode()))
      elif i == 5:
        image6 = getimage()[0:340][67:340]
        Serial.write(bytes("G00 Y0.;".encode()))
      else:
        image16 = cv2.vconcat([image6, image1])
        image25 = cv2.vconcat([image5, image2])
        image34 = cv2.vconcat([image4, image3])
        image1625 = cv2.hconcat([image16, image25])
        imageall = cv2.hconcat([image1625, image34])
        cv2.imwrite('test4.jpg', imageall)
        time.sleep(2) # 이미지 쓰기가 완료될 때 까지 기다림
        break
      i = i + 1
      nowtime = time.time() + 5
  return imageall

""" 이미지에서 궁근물체 검출해 색상 찾는 함수 """
def object_detection(image):
  find = False
  find_color_list = {}
  # gray색상으로 변환, adaptiveThreashold
  height, width, channel = image.shape
  gray_frame = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
  img_thresh = cv2.adaptiveThreshold(
    gray_frame, 
    maxValue=255.0, 
    adaptiveMethod=cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
    thresholdType=cv2.THRESH_BINARY_INV, 
    blockSize=159, 
    C=9
    )
  # contours 검출
  contours, _= cv2.findContours(
    img_thresh, 
    cv2.RETR_LIST, 
    cv2.CHAIN_APPROX_SIMPLE
    )
  find = False
  # contour 하나씩 보면서 일정 크기 이상 물체 검출
  for contour in contours:
    x, y, w, h = cv2.boundingRect(contour)
    if w * h >= 9000 and w >= 90 and w <= 120 and h >= 90 and w <= 120: # 일정 크기 이상의 contour가 인식되었다면,
      # 센터 HSV코드 계산
      changed_HSV = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
      changed_HSV_DP = changed_HSV[int(y+h/2)][int(x+w/2)]
      isfind = False
      for color_val in json_data: # ex) color_val = "red"
        hsv_max = [0, 0, 0]
        hsv_min = [255, 255, 255]
        # 학습 데이터 중 최대, 최소 구함
        for color_num in json_data[color_val]: # ex) color_num = "1"
          i = 0
          for color_type in json_data[color_val][color_num]:  # ex) color_type = "H"
            if hsv_max[i] <= json_data[color_val][color_num][color_type]:
              hsv_max[i] = json_data[color_val][color_num][color_type]
            if hsv_min[i] >= json_data[color_val][color_num][color_type]:
              hsv_min[i] = json_data[color_val][color_num][color_type]
            i = i + 1
        # 계산끝
        if changed_HSV_DP[0] >= hsv_min[0] and changed_HSV_DP[0] <= hsv_max[0] \
        and changed_HSV_DP[1] >= hsv_min[1] and changed_HSV_DP[1] <= hsv_max[1] \
        and changed_HSV_DP[2] >= hsv_min[2] and changed_HSV_DP[2] <= hsv_max[2] :
          if not color_val in find_color_list : 
            find_color_list[color_val] = {
              'num' : 0,
              'location' : [],
              'hsv' : []
            }
          find_color_list[color_val]['num'] += 1
          find_color_list[color_val]['location'].append([int(x+w/2), height - int(y+h/2)])
          find_color_list[color_val]['hsv'].append([changed_HSV_DP[0], changed_HSV_DP[1], changed_HSV_DP[2]])
          isfind = True # 내부 처리('?' 태그)
          find = True # 외부 출력
          break
      if not isfind: # 아무런 색상을 찾지 못하였다면?
        if not '?' in find_color_list : 
          find_color_list['?'] = {
            'num' : 0,
            'location' : [],
            'hsv' : []
          }
        find_color_list['?']['num'] += 1
        find_color_list['?']['location'].append([int(x+w/2), height - int(y+h/2)])
        find_color_list['?']['hsv'].append([changed_HSV_DP[0], changed_HSV_DP[1], changed_HSV_DP[2]])
  return find_color_list, find

""" 찾은 객체 라벨 붙이는 함수 """
def labeling(image, find_color_list):
  findtext = ""
  height, width, channel = image.shape
  for color_val in find_color_list:
    i = 0
    for object_axis in find_color_list[color_val]['location']:
      changed_HSV = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
      changed_HSV_DP = changed_HSV[height - object_axis[1]][object_axis[0]]
      cv2.line(image, (object_axis[0], height - object_axis[1]), (object_axis[0], height - object_axis[1]), (255,0,0), 5)
      cv2.circle(image, (object_axis[0], height - object_axis[1]), 50, (255,0,0), 5)
      cv2.putText(image, "{0}".format(changed_HSV_DP), (object_axis[0], height - object_axis[1]+10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
      cv2.putText(image, "{0}".format(color_val), (object_axis[0], height - object_axis[1]-10), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
      i = i + 1
    if i != 0:
      findtext = findtext + color_to_korean[color_val]
      findtext = findtext + str(i) +"개, "
  if findtext != "":
    findtext = findtext + "가 감지되었습니다. 어떤 색상을 선택할까요?"
    result = True
  return image, findtext

""" 이미지상의 px 데이터를 mm데이터로 변환 """
def px_to_mm_and_go(pick_data_list, colorKey, calculateType):
  if colorKey == "red" and not pick_data_list.has_key(colorKey):
    colorKey = "red2"
  global coordinate_now
  location = [pick_data_list[colorKey]['location'][0][0], pick_data_list[colorKey]['location'][0][1]]
  if calculateType == 1:
    location[0] = int(map(location[0] - 135, 0, 710-135, 0, 280))
    location[1] = int(map(location[1] - 100, 0, 563-170, 0, 180))
    coordinate_now = location
    print("G00 X{0}. Y{1};".format(coordinate_now[0], coordinate_now[1]))
    Serial.write(bytes("G00 X{0}. Y{1};".format(coordinate_now[0], coordinate_now[1]).encode()))
  else:
    centerx_mm = int(location[0] / 12 * 10)
    centery_mm = int(location[1] / 17 * 10)
    coordinate_now[1] = coordinate_now[1] + centery_mm + coordinate_correction[1]
    if coordinate_correction[0]  - centerx_mm <= 0 : # 그랩에서 오른쪽에 있음
      coordinate_now[0] = coordinate_now[0] + abs(coordinate_correction[0] -centerx_mm)
    else:
      coordinate_now[0] = coordinate_now[0] - (coordinate_correction[0]  - centerx_mm)
    print("G00 X{0}. Y{1};".format(coordinate_now[0], coordinate_now[1]))
    Serial.write(bytes("G00 X{0}. Y{1};".format(coordinate_now[0], coordinate_now[1]).encode()))
    Serial.write(bytes("G01;".encode()))
    coordinate_now = [0, 0]
  return location

""" 임력된 음성 text를 영문 키로 반환하는 함수 """
def text_to_key(text):
  global color_to_english
  global color_to_korean
  if text == "취소":
    return "", "", 2 # 취소
  if text == "":
    return "", "", 0 # 찾지못함
  for key, value in color_to_english.items():
    if text.find(key) != -1:
      return value, color_to_korean[value], 1
  return "", "", 0 # 찾지못함
  
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
def speech_read():
  global coordinate_now
  GPIO.output(31, GPIO.HIGH)
  readval=""
  readval = stt.get_text_from_voice()
# 원점으로 이동해 -----
  if readval.find("원점") != -1: 
    tts.getText2VoiceStream2("원점으로 이동합니다.")
    Serial.write(bytes("G28;".encode()))
    coordinate_now = [0, 0]
# 가로 방향으로 ~ 만큼 이동해 -----
  elif readval.find("가로") != -1:
    tts.getText2VoiceStream2("X축 방향 {0}로 이동합니다.".format(int(re.findall("\d+", readval)[0])))
    if re.findall("\d+", readval) :
      moveval = int(re.findall("\d+", readval)[0])
      Serial.write(bytes("G00 X{}.;".format(moveval).encode()))
      coordinate_now[0] = moveval
# 세로 방향으로 ~ 만큼 이동해 -----
  elif readval.find("세로") != -1 or readval.find("새로") != -1: 
    tts.getText2VoiceStream2("Y축 방향 {0}로 이동합니다.".format(int(re.findall("\d+", readval)[0])))
    if re.findall("\d+", readval) :
      moveval = int(re.findall("\d+", readval)[0])
      Serial.write(bytes("G00 Y{}.;".format(moveval).encode()))
      coordinate_now[1] = moveval
# 물체 잡아 -----
  elif readval.find("물체") != -1 and readval.find("잡아") != -1: 
    tts.getText2VoiceStream2("잡을게요")
    Serial.write(bytes("G01;".encode()))
    coordinate_now = [0, 0]
# 현재 위치의 물체 학습해줘 -----
  elif readval.find("학습") != -1: 
    tts.getText2VoiceStream2("현재 위치의 색상을 학습합니다. 카메라에 감지된 색상 코드를 읽는 중입니다.")
    endtime = time.time() + 3
    finded_center = []
    finalfound = False # 알 수 없는 색상 발견여부
    colorfound = False # 알 수 있는 색상 발견여부
    while True:
      if endtime <= time.time():
        break
      image = getimage()
      find_color_list, isfind = object_detection(getimage())
      debugimage = copy.deepcopy(image)
      debugimage , _ = labeling(debugimage, find_color_list)
      if isfind: # 알 수 있는 색상이 감지된 경우
        colorfound = True
        finalkey = ""
        for key in find_color_list:
          finalkey = key
      if '?' in find_color_list:
        finded_center = find_color_list
        finalfound = True
      cv2.imshow("asdf", debugimage)
      cv2.waitKey(1)
    if finalfound and not colorfound:
      print (finded_center)
      tts.getText2VoiceStream2("X{0}, Y{1} 좌표에서 물체를 발견하였습니다. 색상의 이름을 말해주세요.".format(finded_center['?']['location'][0][0], finded_center['?']['location'][0][1]))
    elif colorfound:
      tts.getText2VoiceStream2("{0}이 발견되었습니다. 처음으로 돌아갑니다.".format(color_to_korean[finalkey]))
      return
    else:
      tts.getText2VoiceStream2("물체를 발견하지 못하였습니다. 처음으로 돌아갑니다.")
      return
    while True:
      inputcol = stt.get_text_from_voice()
      engkey, korkey, status = text_to_key(inputcol)
      print(engkey, korkey, status)
      if status == 0: # 찾지못함
        tts.getText2VoiceStream2("이해하지 못했습니다. 다시 한번 말해주세요.")
        continue
      elif status == 2: # 취소
        tts.getText2VoiceStream2("취소합니다.")
        return
      else: 
        tts.getText2VoiceStream2("{0}을 선택하셨습니다.".format(korkey))
        print(engkey, finded_center['?']['hsv'][0])
        add_hsv_code(engkey, finded_center['?']['hsv'][0])
        return
# 인공지능 물체인식 시작 -----
  elif readval.find("인공지능") != -1: 
    tts.getText2VoiceStream2("인공지능 작동을 시작합니다. 우선 전체 스캔을 시작합니다.")
    image = get_entire_image()
    find_color_list, isfind = object_detection(image)
    if isfind:
      _, ttsText = labeling(copy.deepcopy(image), find_color_list)
      tts.getText2VoiceStream2(ttsText) # TTS: 어떤 물체를 선택할까요?
      while True:
        inputcol = stt.get_text_from_voice()
        engkey, korkey, status = text_to_key(inputcol)
        if status == 0: # 찾지못함
          tts.getText2VoiceStream2("이해하지 못했습니다. 다시 한번 말해주세요.")
          continue
        elif status == 2: # 취소
          tts.getText2VoiceStream2("취소합니다.")
          return
        else: 
          if engkey in find_color_list:
            tts.getText2VoiceStream2("{0}을 선택하셨습니다.".format(korkey))
            break
          else:
            tts.getText2VoiceStream2("{0}은 인식되지 않은 색상입니다. 처음으로 돌아갑니다.".format(korkey))
            return
      px_to_mm_and_go(find_color_list, engkey, 1)
      tts.getText2VoiceStream2("X{0}, Y{1} 좌표로 이동한 후 최종 물체 인식을 시작합니다.".format(coordinate_now[0], coordinate_now[1]))
      endtime = time.time() + 10
      finded_center = []
      finalfound = False
      while True:
        if endtime <= time.time():
          break
        image = getimage()
        find_color_list, isfind = object_detection(image)
        if isfind:
          finalfound = True
          debugimage , _ = labeling(copy.deepcopy(image), find_color_list)
          cv2.imshow("debug", debugimage) # 디버그이미지 출력
          finded_center = find_color_list
        cv2.waitKey(1)
      print(finded_center)
      if finalfound:
        px_to_mm_and_go(finded_center, engkey, 2)
        tts.getText2VoiceStream2("최종 물체 인식에 성공하였습니다. 물체를 잡습니다.")
      else:
        tts.getText2VoiceStream2("최종 물체 인식에 실패하였습니다. 처음으로 돌아갑니다.")
        Serial.write(bytes("G28;".encode()))
        return
    else:
      tts.getText2VoiceStream2("어떠한 물체도 발견되지 않았습니다. 처음으로 돌아갑니다.")
      Serial.write(bytes("G28;".encode()))
      return
# 음성인식 결과 없음 -----
  else:
    tts.getText2VoiceStream2("이해하지 못했습니다.")
  GPIO.output(31, GPIO.LOW)

""" 호출 """
def call():
  recog = 500
  recog = kws.call('지니야')
  if recog == 200:
    tts.getText2VoiceStream2("네,")
    speech_read()

""" Main 함수 """
def main():
  while 1:
    call()
    cv2.destroyAllWindows()

""" 직접 코드 실행시 작동 """
if __name__ == '__main__':
  tts.getText2VoiceStream2("호출하기 위해 지니야 를 불러주세요.")
  main()
from __future__ import print_function
""" AMK관련 라이브러리 """
import MicrophoneStream as MS # 음성출력
import kws # 음성호출
import tts # Text To Speech
import stt # Speech To Text
import time # time.sleep

import RPi.GPIO as GPIO # GPIO 제어(버튼, LED 제어)
import re
import requests
import json
GPIO.setmode(GPIO.BOARD)
GPIO.setwarnings(False)
GPIO.setup(31, GPIO.OUT)

serverip = "http://localhost/api"
apikey = ""
cookies = {}

count_dic = {'첫': 1, '두': 2, '세': 3, '네': 4, '다섯': 5, '여섯': 6, '일곱': 7, '여덟': 8, '아홉': 9, '열': 10} # 파일 선택할 때 자연어 처리에 활용

""" File operations """
def Retrieve_all_files():
  headers = {
    "X-Api-Key" : apikey
  }
  resp = requests.get(serverip+"/files", headers = headers)
  if resp.status_code == 200:
    return True, resp.json()
  else:
    return False, {}

def Issue_a_file_command(filename): # select만 하고 출력할지 물어보고 출력함
  headers = {
    "X-Api-Key" : apikey
  }
  data = {
    "command" : "select",
    "print" : False
  }
  resp = requests.post(serverip+"/files/local/"+filename+".gcode", headers = headers, json = data)
  print(resp.text)
  if resp.status_code == 204:
    return 1
  elif "Printer is already printing, cannot select a new file" in resp.text : 
    return 2
  else:
    return 0

""" Job operations """
def Issue_a_job_command(command): # start, cancel, pause, resume
  headers = {
    "X-Api-Key" : apikey
  }
  if command == "start":
    data = {
      "command" : "start"
    }
  elif command == "cancel":
    data = {
      "command" : "cancel"
    }
  elif command == "pause":
    data = {
      "command" : "pause",
      "action" : "pause"
    }
  elif command == "resume":
    data = {
      "command" : "pause",
      "action" : "resume"
    }
    
  resp = requests.post(serverip+"/job", headers = headers, json = data)
  if resp.status_code == 204:
    return True
  else: 
    return False

def Retrieve_information_about_the_current_job():
  headers = {
    "X-Api-Key" : apikey
  }
  resp = requests.get(serverip+"/job", headers = headers)
  if resp.status_code == 200:
    return True, resp.json()
  else:
    return False, {}

""" Printer operations """
def Retrieve_the_current_printer_state():
  headers = {
    "X-Api-Key" : apikey
  }
  resp = requests.get(serverip+"/printer", headers = headers)
  if resp.status_code == 200:
    return True, resp.json()
  else:
    return False, {}

def Send_an_arbitrary_command_to_the_printer(command):
  # command example
  # ["M18", "M106 S0"]
  headers = {
    "X-Api-Key" : apikey
  }
  data = {
    "commands" : command
  }
  resp = requests.post(serverip+"/printer/command", headers = headers, json = data)
  return

def Issue_a_tool_command(temperature):
  headers = {
    "X-Api-Key" : apikey
  }
  data = {
    "command": "target",
    "targets": {
      "tool0": temperature
    }
  }
  resp = requests.post(serverip+"/printer/tool", headers = headers, json = data)
  return

def Issue_a_bed_command(temperature):
  headers = {
    "X-Api-Key" : apikey
  }
  data = {
    "command": "target",
    "target": temperature
  }
  resp = requests.post(serverip+"/printer/bed", headers = headers, json = data)
  return


""" 여기부터 API이용, 실제 기능 """
# 파일 이름, 소요 시간 알려주고 파일 선택하는 기능
def select_file_by_name(): # ~시간이 소요되는 ~, ~시간이 소요되는 ~
  status, data = Retrieve_all_files()
  filename_list = ["."]
  text = ""
  if not status:
    return
  for files in data['files']:
    filename_list.append(files['display'][:files['display'].find('.')])
    text = text + str(round(files['gcodeAnalysis']['estimatedPrintTime'] / 3600, 1)) + " 시간이 소요되는 " + files['display'][:files['display'].find('.')] + ", "
  text = text[:text.__len__()-2] + " 중 몇 번째 파일을 선택하시겠습니까?"
  print(filename_list.__len__())
  tts.getText2VoiceStream2(text)
  while True:
    readval = stt.get_text_from_voice()
    if readval.find("번째") != -1:
      for key, num in count_dic.items():
        if num > filename_list.__len__() - 1:
          break
        if readval.find(key) != -1:
          tts.getText2VoiceStream2("{0}파일을 선택합니다.".format(filename_list[num]))
          result = Issue_a_file_command(filename_list[num])
          if result == 0:
            tts.getText2VoiceStream2("알 수 없는 오류가 발생하였습니다. 처음으로 돌아갑니다.")
          return
    tts.getText2VoiceStream2("이해하지 못하였습니다. 다시 한번 말해주세요.")
  return

# 축, 절대좌표를 입력받아 해당 좌표로 이동하는 기능
def move_axis(axis, location): # axis는 대문자, location은 숫자 mm
  if axis == "H": 
    data=[
      "G28"
    ]
    Send_an_arbitrary_command_to_the_printer(data)
    return
  data=[
    "G90",
    "G1 {0}{1} F2000".format(axis, location)
  ]
  Send_an_arbitrary_command_to_the_printer(data)
  return

# 선택된 파일이 있는지 확인한 후 출력함. 선택된 파일이 없을 경우 에러메시지 출력
def chk_selected_and_print():
  status, data = Retrieve_information_about_the_current_job()
  if status:
    if data['job']['file']['name'] == None:
      tts.getText2VoiceStream2("출력을 위해 선택된 파일이 없습니다. 파일 선택 후 출력을 진행합니다.")
      select_file_by_name()
    tts.getText2VoiceStream2("선택된 파일을 출력합니다.")
    Issue_a_job_command("start")


""" 출력 """
# 노즐/히팅베드 온도 출력
def retrive_temperature():
  result, data = Retrieve_the_current_printer_state()
  if not result:
    tts.getText2VoiceStream2("알 수 없는 오류가 발생하였습니다. 나중에 다시 시도해주세요.")
    return
  tts.getText2VoiceStream2("노즐 온도는 {0}도, 히팅베드 온도는 {1}도 입니다.".format(data['temperature']['tool0']['actual'], data['temperature']['bed']['actual']))

def retrive_printing_status():
  status, data = Retrieve_information_about_the_current_job()
  if status:
    if data['job']['file']['name'] == None:
      tts.getText2VoiceStream2("프린터가 출력중이 아닙니다.")
      return
    tts.getText2VoiceStream2("{0} 파일을 출력중이며, {1}시간 후 종료될 예정입니다. 완료율은 {2}% 입니다.".format(data['job']['file']['name'][:data['job']['file']['name'].find('.')], round(data['progress']['printTimeLeft'] / 3600, 1), round(data['progress']['completion'], 1)))

""" 음성인식 분류 """
def speech_read():
  GPIO.output(31, GPIO.HIGH)
  GPIO.output(31, GPIO.LOW)
  readval = ""
  readval = stt.get_text_from_voice()
# 파일 선택 -----
  if readval.find("파일") != -1 and readval.find("선택") != -1: 
    select_file_by_name()
    return
  if readval.find("축") != -1 and readval.find("방향") != -1 and re.findall("\d+", readval).__len__() > 0:
# X축 방향으로 ~만큼 이동해 -----
    if readval.find("x") != -1 or readval.find("X") != -1: 
      move_axis('X', int(re.findall("\d+", readval)[0]))
      tts.getText2VoiceStream2("X축 방향 {0}로 이동합니다.".format(int(re.findall("\d+", readval)[0])))
      return
# Y축 방향으로 ~만큼 이동해 -----
    if readval.find("y") != -1 or readval.find("Y") != -1: 
      move_axis('Y', int(re.findall("\d+", readval)[0]))
      tts.getText2VoiceStream2("Y축 방향 {0}로 이동합니다.".format(int(re.findall("\d+", readval)[0])))
      return
# Z축 방향으로 ~만큼 이동해 -----
    if readval.find("z") != -1 or readval.find("Z") != -1: 
      move_axis('Z', int(re.findall("\d+", readval)[0]))
      tts.getText2VoiceStream2("Z축 방향 {0}로 이동합니다.".format(int(re.findall("\d+", readval)[0])))
      return
# 원점 복귀 -----
  if readval.find("원점") != -1: 
    move_axis('H', 123)
    tts.getText2VoiceStream2("원점으로 복귀합니다.")
    return
  if readval.find("알려줘") != -1:
# 현재 온도 알려줘 -----
    if readval.find("온도") != -1: 
      retrive_temperature()
      return
# 출력 현황 알려줘 -----
    if readval.find("출력") != -1: 
      retrive_printing_status()
      return

  if readval.find("설정해") != -1:
    if readval.find("온도") != -1 and re.findall("\d+", readval).__len__() > 0:
# 핫엔드 온도 ~도로 설정해줘 -----
      if readval.find("핫 &") != -1: 
        tts.getText2VoiceStream2("핫엔드 온도를 {0}도로 설정합니다.".format(int(re.findall("\d+", readval)[0])))
        Issue_a_tool_command(int(re.findall("\d+", readval)[0]))
        return
# 히팅베드 온도 ~도로 설정해줘 -----
      if readval.find("heating") != -1: 
        tts.getText2VoiceStream2("히팅베드 온도를 {0}도로 설정합니다.".format(int(re.findall("\d+", readval)[0])))
        Issue_a_bed_command(int(re.findall("\d+", readval)[0]))
        return
        
  if readval.find("출력") != -1:
# 출력 재시작해 -----
    if readval.find("재시작") != -1: 
      tts.getText2VoiceStream2("출력을 재시작 합니다.")
      Issue_a_job_command("resume")
      return
# 출력 시작해 -----
    if readval.find("시작") != -1: 
      tts.getText2VoiceStream2("출력을 시작합니다.")
      Issue_a_job_command("start")
      return
# 출력 일시중지해 -----
    if readval.find("일시") != -1:
      tts.getText2VoiceStream2("출력을 일시중지 합니다.")
      Issue_a_job_command("pause")
      return
# 출력 정지해 -----
    if readval.find("정지") != -1: 
      tts.getText2VoiceStream2("출력을 정지합니다.")
      Issue_a_job_command("stop")
      return
  else:
    tts.getText2VoiceStream2("이해하지 못했습니다.")

""" 호출 """
def call():
  recog = 500
  recog = kws.call('지니야')
  if recog == 200:
    speech_read()

""" Main 함수 """
def main():
  while 1:
    call()
  
""" 직접 코드 실행시 작동 """
if __name__ == "__main__":
  main()
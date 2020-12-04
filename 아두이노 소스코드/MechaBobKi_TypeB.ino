// 이펙터(DC모터) 세팅 ---------------
#define MOTOR_IN1_PIN 5
#define MOTOR_IN2_PIN 4
#define MOTOR_ENA_PIN 6

#define MOTOR_SPEED 255 // 0 ~ 255

#define MOTOR_LIMIT_F 47
#define MOTOR_LIMIT_R 45

// 스텝모터 세팅 ---------------
int axis_X = 0; // mm단위
int axis_Z = 0; // mm단위

#define X_STEP_PIN 54
#define X_DIR_PIN 55
#define X_ENABLE_PIN 38
#define X_DIR -1
#define X_MAX 280 // mm단위

#define Z_STEP_PIN 46
#define Z_DIR_PIN 48
#define Z_ENABLE_PIN 62
#define Z_DIR 1
#define Z_MAX 265

// 16T * 2 = 32mm(한바퀴당)
// 16분주 세팅, 16T 풀리 -> 1펄스당 0.1125도 -> 3200펄스 360도 -> 32mm 한바퀴 -> 1mm
// mm/s -> 1mm당 펄스수 -> 100
#define STEPMIN_X 100
#define STEPMIN_Z 400
// 펄스폭 조절, ms단위
#define SPEED_XZ_G00 50

// 조이스틱 세팅 ---------------
// 조이스틱 (좌우상하 이동)
#define Joystick_Right 14
#define Joystick_Left 15
#define Joystick_Up 18
#define Joystick_Down 19
// 조이스틱 옆 푸쉬버튼 (내려가는 버튼)
#define Pushbutton 32
// 리미트 스위치
#define Z_Reset_Pin 2
#define X_Reset_Pin 3
//#define Front_Reset_Pin 31

// 축, mm단위 절대좌표, 속도(펄스폭 조절)
/*
  X: X축
  Y: Y축
  Z: Z축
*/
void stepper(char axis, int position, int speed) {
  long movedistance_stepmm = ((long)position - ((axis == 'X') ? axis_X : axis_Z)) * ((axis == 'X') ? STEPMIN_X : STEPMIN_Z);
  digitalWrite((axis == 'X') ? X_DIR_PIN : Z_DIR_PIN, (((movedistance_stepmm * ((axis == 'X') ? X_DIR : Z_DIR)) > 0) ? HIGH : LOW)); // 방향 설정, 방향 반전
  int step_pin = (axis == 'X') ? X_STEP_PIN : Z_STEP_PIN;
  for (long i = 0; i < abs(movedistance_stepmm); i++) { // 발화
    digitalWrite(step_pin, HIGH);
    delayMicroseconds(speed);
    digitalWrite(step_pin, LOW);
    delayMicroseconds(speed);
  }
  ((axis == 'X') ? axis_X : axis_Z) = position; // 현재 상태 저장
}
void stepperOnce(int X, int Z) {

}

// 호밍
void homming() {
  // Serial.println("homming");
  digitalWrite(X_DIR_PIN, (X_DIR == 1) ? LOW : HIGH);
  digitalWrite(Z_DIR_PIN, (Z_DIR == 1) ? LOW : HIGH);
  int homming_X = HIGH, homming_Z = HIGH;
  //이펙터 호밍(뒤로 이동)
  while (true) {
    if (digitalRead(MOTOR_LIMIT_F) == 1) {
      digitalWrite(MOTOR_IN1_PIN, HIGH); //이펙터 후진
      digitalWrite(MOTOR_IN2_PIN, LOW);
    } else { //호밍이 완료 되었을 때
      digitalWrite(MOTOR_IN1_PIN, LOW);
      digitalWrite(MOTOR_IN2_PIN, LOW);
      break;
    }

  }
  // X, Z 동시호밍
  while (true) {
    int status_x = ! digitalRead(X_Reset_Pin);
    int status_z = ! digitalRead(Z_Reset_Pin);
    if (status_x) {
      homming_X = LOW;
      axis_X = 0;
    }
    if (status_z) {
      homming_Z = LOW;
      axis_Z = 0;
    }
    if (homming_Z == LOW && homming_X == LOW) break;
    digitalWrite(X_STEP_PIN, homming_X);
    digitalWrite(Z_STEP_PIN, homming_Z);
    delayMicroseconds(100);
    digitalWrite(X_STEP_PIN, LOW);
    digitalWrite(Z_STEP_PIN, LOW);
    delayMicroseconds(100);
  }
}

// 이펙터 작동
int action_flag = 0;
void grab() {
  delay(500);

  long time_end = millis() + 1500; //시간 시작
  while (true) {
    if (!digitalRead(MOTOR_LIMIT_R) || time_end <= millis())
      break;
    digitalWrite(MOTOR_IN1_PIN, LOW); //이펙터 전진
    digitalWrite(MOTOR_IN2_PIN, HIGH);
    delay(10);
  }
  digitalWrite(MOTOR_IN1_PIN, HIGH); //이펙터 정지
  digitalWrite(MOTOR_IN2_PIN, HIGH);
  delay(2000);
  while (true) {
    if (!digitalRead(MOTOR_LIMIT_F))
      break;
    digitalWrite(MOTOR_IN1_PIN, HIGH); //이펙터 후진
    digitalWrite(MOTOR_IN2_PIN, LOW);
    delay(10);
  }
  digitalWrite(MOTOR_IN1_PIN, HIGH); //이펙터 정지
  digitalWrite(MOTOR_IN2_PIN, HIGH);

  delay(1000);
  homming();

}

// 시리얼 데이터 입력 및 파싱
int readSerial() {
  char buff[100] = {0,};
  int i = 0;
  if (Serial.available()) {
    while (true) {
      while (!Serial.available()) {}; // 읽을 시리얼 데이터가 없는데 읽는것 방지
      buff[i++] = Serial.read();
      if (buff[i - 1] == 10 || buff[i - 1] == ';') break; // 개행문자 혹은 기호 ';'가 입력되면 브레이크
    }
  } else return 0;
  int gcode = -1;
  sscanf(buff, "G%d", &gcode);
  switch (gcode) {
    case 28: // G28 -> 호밍
      homming();
      break;
    case 1: // G01 -> Z 내리기
      grab();
      break;
    case 0: // G00 -> XY 조정
      int Xval = -1, Zval = -1;
      sscanf(buff, "G00 X%d. Z%d.", &Xval, &Zval);
      sscanf(buff, "G00 Z%d.", &Zval);
      if (Xval != -1) stepper('X', Xval, SPEED_XZ_G00);
      if (Zval != -1) stepper('Z', Zval, SPEED_XZ_G00);
      break;
    default: // 정의되지 않은 G코드 입력시
      break;
  }
  return 0;
}

int readSwitch() {
  // 조이스틱 신호 읽기
  int Joystick_Right_read = !digitalRead(Joystick_Right);
  int Joystick_Left_read = !digitalRead(Joystick_Left);
  int Joystick_Up_read = !digitalRead(Joystick_Up);
  int Joystick_Down_read = !digitalRead(Joystick_Down);
  int Pushbutton_read = !digitalRead(Pushbutton);

  int Right = Joystick_Right_read && axis_X != X_MAX;
  int Left = Joystick_Left_read && axis_X != 0;
  int Up = Joystick_Up_read && axis_Z != Z_MAX;
  int Down = Joystick_Down_read && axis_Z != 0;

  // 두 스위치가 눌려질 때 예외처리
  if (Right && Up) { // 우측상단
  } else if (Right && Down) { // 우측하단
  } else if (Left && Up) { // 좌측상단
  } else if (Left && Down) { // 좌측하단
  }
  else if (Right) {
    // Serial.println("Right");
    // Serial.println(axis_X);
    stepper('X', axis_X + 1, SPEED_XZ_G00);
  }
  else if (Left) {
    // Serial.println("Left");
    // Serial.println(axis_X);
    stepper('X', axis_X - 1, SPEED_XZ_G00);
  }
  else if (Up) {
    // Serial.println("Up");
    // Serial.println(axis_Z);
    stepper('Z', axis_Z + 1, SPEED_XZ_G00);
  }
  else if (Down) {
    // Serial.println("Down");
    // Serial.println(axis_Z);
    stepper('Z', axis_Z - 1, SPEED_XZ_G00);
  }
  if (Pushbutton_read) {
    grab();
  }
}

void setup() {
  Serial.begin(9600);
  // 스텝모터 STEP/DIRECTION/ENABLE 출력 설정
  pinMode(X_STEP_PIN, OUTPUT);
  pinMode(X_DIR_PIN, OUTPUT);
  pinMode(X_ENABLE_PIN, OUTPUT);
  pinMode(Z_STEP_PIN, OUTPUT);
  pinMode(Z_DIR_PIN, OUTPUT);
  pinMode(Z_ENABLE_PIN, OUTPUT);
  // 조이스틱, 아케이드버튼, 리셋스위치 입력 설정
  pinMode(Joystick_Right, INPUT_PULLUP);
  pinMode(Joystick_Left, INPUT_PULLUP);
  pinMode(Joystick_Up, INPUT_PULLUP);
  pinMode(Joystick_Down, INPUT_PULLUP);
  pinMode(Pushbutton, INPUT_PULLUP);
  pinMode(Z_Reset_Pin, INPUT_PULLUP);
  pinMode(X_Reset_Pin, INPUT_PULLUP);

  //이펙터 입출력 설정
  pinMode(MOTOR_LIMIT_F, INPUT_PULLUP);
  pinMode(MOTOR_LIMIT_R, INPUT_PULLUP);
  pinMode(MOTOR_IN1_PIN, OUTPUT);
  pinMode(MOTOR_IN2_PIN, OUTPUT);
  pinMode(MOTOR_ENA_PIN, OUTPUT);

  analogWrite(MOTOR_ENA_PIN, MOTOR_SPEED);

  // 스텝모터 ENABLE HIGH 설정 (HIGH: 모터 중지)
  digitalWrite(X_ENABLE_PIN, LOW);
  digitalWrite(Z_ENABLE_PIN, LOW);
  
  homming();
  Serial.println("OK!");
}

void loop() {
  readSerial();
  readSwitch();
}

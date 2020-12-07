// #include<Arduino.h>
#include<HardwareSerial.h>
#include<Servo.h>

// 서보모터 세팅 ---------------
int GripperPin = 2;
Servo Gripper;

// 스텝모터 세팅 ---------------
int axis_X = 0; // mm단위
int axis_Y = 0; // mm단위

#define X_STEP_PIN 54
#define X_DIR_PIN 55
#define X_ENABLE_PIN 38
#define X_DIR -1
#define X_MAX 280 // mm단위

#define Y_STEP_PIN 60
#define Y_DIR_PIN 61
#define Y_ENABLE_PIN 56
#define Y_DIR 1
#define Y_MAX 240 // mm단위

#define E_STEP_PIN 46
#define E_DIR_PIN 48
#define E_ENABLE_PIN 62
#define E_MIN_PIN 18
#define E_MAX_PIN 19
// 16T * 2 = 32mm(한바퀴당)
// 16분주 세팅, 16T 풀리 -> 1펄스당 0.1125도 -> 3200펄스 360도 -> 32mm 한바퀴 -> 1mm
// mm/s -> 1mm당 펄스수 -> 100
#define STEPMIN_X 100
#define STEPMIN_Y 100
// 펄스폭 조절, ms단위
#define SPEED_XY_G00 100
#define SPEED_E 300

// 조이스틱 세팅 ---------------
// 조이스틱 (좌우상하 이동)
#define Joystick_Right 4
#define Joystick_Left 5
#define Joystick_Up 11
#define Joystick_Down 6
// 조이스틱 옆 푸쉬버튼 (내려가는 버튼)
#define Pushbutton 57
// 리미트 스위치
#define Gripper_Reset_Pin 18
#define Left_Reset_Pin 3
#define Front_Reset_Pin 14

// 축, mm단위 절대좌표, 속도(펄스폭 조절)
/*
 * X: X축
 * Y: Y축
 * Z: Z축
 * E: 그랩/봉
*/
void stepper(char axis, int position, int speed) {
    if (((axis == 'X') ? X_MAX : Y_MAX) < position)
        return;
    long movedistance_stepmm = ((long)position - ((axis == 'X') ? axis_X : axis_Y)) * ((axis == 'X') ? STEPMIN_X : STEPMIN_Y);
    digitalWrite((axis == 'X') ? X_DIR_PIN : Y_DIR_PIN, (((movedistance_stepmm * ((axis == 'X') ? X_DIR : Y_DIR)) > 0) ? HIGH : LOW)); // 방향 설정, 방향 반전
    int step_pin = (axis == 'X') ? X_STEP_PIN : Y_STEP_PIN;
    for (long i = 0; i < abs(movedistance_stepmm); i++) { // 발화
        digitalWrite(step_pin, HIGH);
        delayMicroseconds(speed);
        digitalWrite(step_pin, LOW);
        delayMicroseconds(speed);
    }
    ((axis == 'X') ? axis_X : axis_Y) = position; // 현재 상태 저장
}
void stepperOnce(int X, int Y) {
    
}

int anti_floating(int pinnum) {
    int flag = 0;
    for(int i=0; i<10; i++) 
        if(!digitalRead(pinnum)) flag++;
    if(flag >= 9) return true;
    else return false;
}

// 호밍
void homming() {
    digitalWrite(X_DIR_PIN, (X_DIR == 1) ? LOW : HIGH);
    digitalWrite(Y_DIR_PIN, (Y_DIR == 1) ? LOW : HIGH);
    digitalWrite(E_DIR_PIN, HIGH);
    int homming_X = HIGH, homming_Y = HIGH;
    // 이펙터 호밍
    while(true) {
        int status_E = !digitalRead(Gripper_Reset_Pin);
        if(status_E) {
            if(anti_floating(Gripper_Reset_Pin)) {
                break;
            }
        }
        digitalWrite(E_STEP_PIN, HIGH);
        delayMicroseconds(SPEED_E);
        digitalWrite(E_STEP_PIN, LOW);
        delayMicroseconds(SPEED_E);
    }
    // X, Y 동시호밍
    while(true) {
        int status_x = !digitalRead(Left_Reset_Pin);
        int status_y = !digitalRead(Front_Reset_Pin);
        if (status_x) {
            if(anti_floating(Left_Reset_Pin)) {
                homming_X = LOW;
                axis_X = 0;
            }
        }
        if (status_y) {
            if(anti_floating(Front_Reset_Pin)) {
                homming_Y = LOW;
                axis_Y = 0;
            }
        }
        if (homming_Y == LOW && homming_X == LOW) break;
        digitalWrite(X_STEP_PIN, homming_X);
        digitalWrite(Y_STEP_PIN, homming_Y);
        delayMicroseconds(150);
        digitalWrite(X_STEP_PIN, LOW);
        digitalWrite(Y_STEP_PIN, LOW);
        delayMicroseconds(150);
    }
}

// 이펙터 작동
void grab() {
    Gripper.write(0);
    delay(500);
    digitalWrite(E_DIR_PIN, LOW);
    int homming_X = HIGH, homming_Y = HIGH;
    // 이펙터 하강
    for(int i=0; i<7500; i++) {
        digitalWrite(E_STEP_PIN, HIGH);
        delayMicroseconds(SPEED_E);
        digitalWrite(E_STEP_PIN, LOW);
        delayMicroseconds(SPEED_E);
    }
    Gripper.write(100); // 잡
    delay(1000);
    digitalWrite(E_DIR_PIN, HIGH);
    for(int i=0; i<7500; i++) {
        digitalWrite(E_STEP_PIN, HIGH);
        delayMicroseconds(SPEED_E);
        digitalWrite(E_STEP_PIN, LOW);
        delayMicroseconds(SPEED_E);
    }
    homming();
    Gripper.write(0); // 때
    delay(1000);
    Gripper.write(100); // 잡
    delay(1000);
    Gripper.write(0); // 때
    delay(1000);
    Gripper.write(100); // 잡
    delay(1000);
}

// 시리얼 데이터 입력 및 파싱
int readSerial() {
    char buff[100]={0,};
    int i=0;
    if(Serial.available()) {
        while(true) {
            while(!Serial.available()) {}; // 읽을 시리얼 데이터가 없는데 읽는것 방지
            buff[i++] = Serial.read();
            if(buff[i-1] == 10 || buff[i-1] == ';') break; // 개행문자 혹은 기호 ';'가 입력되면 브레이크
        }
    } else return 0;
    int gcode = -1;
    sscanf(buff, "G%d", &gcode);
    switch(gcode) {
        case 28: // G28 -> 호밍
            homming();
            break;
        case 1: // G01 -> Z 내리기
            grab();
            break;
        case 0: // G00 -> XY 조정
            int Xval = -1, Yval = -1;
            sscanf(buff, "G00 X%d. Y%d.", &Xval, &Yval);
            sscanf(buff, "G00 Y%d.", &Yval);
            if(Xval != -1) stepper('X', Xval, SPEED_XY_G00);
            if(Yval != -1) stepper('Y', Yval, SPEED_XY_G00);
            
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
    int Up = Joystick_Up_read && axis_Y != Y_MAX;
    int Down = Joystick_Down_read && axis_Y != 0;

    // 두 스위치가 눌려질 때 예외처리
    if(Right && Up) { //우측상단
    } else if (Right && Down) { //우측하단
    } else if (Left && Up) { //좌측상단
    } else if (Left && Down) { //좌측하단
    }
    else if(Right) stepper('X', axis_X + 1, SPEED_XY_G00);
    else if(Left) stepper('X', axis_X - 1, SPEED_XY_G00);
    else if(Up) stepper('Y', axis_Y + 1, SPEED_XY_G00);
    else if(Down) stepper('Y', axis_Y - 1, SPEED_XY_G00);
    if(Pushbutton_read) {
        grab();
    }
}

void setup() {
    Serial.begin(9600);
    // 스텝모터 STEP/DIRECTION/ENABLE 출력 설정
    pinMode(X_STEP_PIN, OUTPUT);
    pinMode(X_DIR_PIN, OUTPUT);
    pinMode(X_ENABLE_PIN, OUTPUT);
    pinMode(Y_STEP_PIN, OUTPUT);
    pinMode(Y_DIR_PIN, OUTPUT);
    pinMode(Y_ENABLE_PIN, OUTPUT);
    pinMode(E_STEP_PIN, OUTPUT);
    pinMode(E_DIR_PIN, OUTPUT);
    pinMode(E_ENABLE_PIN, OUTPUT);
    // 조이스틱, 아케이드버튼, 리셋스위치 입력 설정
    pinMode(Joystick_Right, INPUT_PULLUP);
    pinMode(Joystick_Left, INPUT_PULLUP);
    pinMode(Joystick_Up, INPUT_PULLUP);
    pinMode(Joystick_Down, INPUT_PULLUP);
    pinMode(Pushbutton, INPUT_PULLUP);
    pinMode(Gripper_Reset_Pin, INPUT_PULLUP);
    pinMode(Left_Reset_Pin, INPUT_PULLUP);
    pinMode(Front_Reset_Pin, INPUT_PULLUP);
    // 스텝모터 ENABLE HIGH 설정 (HIGH: 모터 중지)
    digitalWrite(X_ENABLE_PIN, LOW);
    digitalWrite(Y_ENABLE_PIN, LOW);
    digitalWrite(E_ENABLE_PIN, LOW);

    Gripper.attach(GripperPin);
    Gripper.write(100);

    homming();
    Serial.println("OK!");
}

void loop() {
    readSerial();
    readSwitch();
}
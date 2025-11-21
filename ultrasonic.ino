#include <Servo.h>

Servo myservo;              //servo 1
Servo myservo1;             //servo 2

const int trigPin = 9;      //sonic pins (trig)
const int echoPin = 10;     //sonic pins (echo)
int led = 8;                //led indicator
int pos = 0;                //servo position initialization

float duration, distance;   //pulse and calculated distance

bool handDetected = false;    //is the hand currently close?
bool readyToTrigger = true;   //prevents extra triggers
//bool servoState = false;      //false = 0, true = 90


void setup() {                
  pinMode(trigPin, OUTPUT);    //trigPin writes pulses
  pinMode(echoPin, INPUT);     //echoPin reads return pulse
  pinMode(led, OUTPUT);
  Serial.begin(9600);          //serial monitor baud rate

  myservo1.attach(6);          //servo on pin 6
  myservo.attach(7);           //servo on pin 7

  myservo.write(0);            //initialize servo positions
  myservo1.write(180);
}

void loop() {

  digitalWrite(trigPin, LOW);      //no pulse
  delayMicroseconds(2);            //wait 2us
  digitalWrite(trigPin, HIGH);     //send 10us pulse
  delayMicroseconds(10);           //wait 10us
  digitalWrite(trigPin, LOW);      //stop pulse

  duration = pulseIn(echoPin, HIGH, 30000); //measure echo return time
  float rawDist = (duration * 0.0343) / 2;  //convert time → cm

  if (rawDist == 0 || rawDist > 200) {      //if reaches edge of limit or way too close, returns 0,
//                                           so treat as far
    distance = 999;                //treat as FAR
  } else {
    distance = rawDist;            //valid reading
  }

  Serial.println(distance);        //print to serial monitor

  if (distance < 8 && !handDetected) {   //if close & no previous detection
    handDetected = true;                 //now hand is detected
  }

  if (distance > 12 && handDetected) {   //if hand was detected and now far
    handDetected = false;                //hand has left

    if (readyToTrigger) {                //only trigger once per entry/leave


      if (pos == 0) {                       //servoState false = at 0 degrees
        for (int i = pos; i <= 90; i += 3) {   //increment up to 90
          myservo.write(i);
          myservo1.write(180 - i);       //opposite direction for balance
          delay(30);
        }
        pos = 90;                        //update current pos
        // servoState = true;               //servo now at 90
        digitalWrite(led, LOW);          //turn led on
      }


      else {                                  //servoState true = at 90 degrees
        for (int i = pos; i >= 0; i -= 3) {   //decrement down to 0
          myservo.write(i);
          myservo1.write(180 - i);
          delay(30);
        }
        pos = 0;                         //update current pos
//        servoState = false;              //return to 0
        digitalWrite(led, HIGH);         //turn led off
      }

      readyToTrigger = false;            //block until fully cleared
    }
  }

  if (!handDetected && distance > 20) {  //far enough away
    readyToTrigger = true;               //allow next trigger
  }

  delay(50);                             
}
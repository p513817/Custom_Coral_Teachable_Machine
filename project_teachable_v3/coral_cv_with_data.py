#!/usr/bin/env python
#
# Copyright 2019 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import argparse
import sys
import os
import time

from abc import abstractmethod
from collections import deque, Counter
from functools import partial

os.environ['XDG_RUNTIME_DIR']='/run/user/1000'

from embedding import KNNEmbeddingEngine
from PIL import Image

import gstreamer

### Modify by Chun : import shutil & cv2
import shutil
import cv2
import threading

'''
File: coral_cv_with_data.py
Date: 109/12/02(Wed)
VERSION: 1.1
Author : Chun

INFO:
Modify Original Code to Save and Reload Data, and change PyGi to OpenCV.

Modify Items:
1. Modify TeachableMachineKNN_ByChun
2. Change PyGi to OpenCV in main()
3. Use Thread to Improve Delay of Streaming : ThreadCapture()
4. Modify TeachableMachine.visiual() to get_results()

'''

def detectPlatform():
  try:
    model_info = open("/sys/firmware/devicetree/base/model").read()
    if 'Raspberry Pi' in model_info:
      print("Detected Raspberry Pi.")
      return "raspberry"
    if 'MX8MQ' in model_info:
      print("Detected EdgeTPU dev board.")
      return "devboard"
    return "Unknown"
  except:
    print("Could not detect environment. Assuming generic Linux.")
    return "unknown"

class Log():

  def log_t(self, content, t=None, end='\n\n'):
    
      if t==None:
          print(f'\n{content}', end=end)
          return time.time()
      else:
          t_cost = time.time()-t
          print('{} ({:.5f}s)'.format(content, t_cost))
          return t_cost

class UI(object):
  """Abstract UI class. Subclassed by specific board implementations."""
  def __init__(self):
    self._button_state = [False for _ in self._buttons]
    current_time = time.time()
    self._button_state_last_change = [current_time for _ in self._buttons]
    self._debounce_interval = 0.1 # seconds

  def setOnlyLED(self, index):
    for i in range(len(self._LEDs)): self.setLED(i, False)
    if index is not None: self.setLED(index, True)

  def isButtonPressed(self, index):
    buttons = self.getButtonState()
    return buttons[index]

  def setLED(self, index, state):
    raise NotImplementedError()

  def getButtonState(self):
    raise NotImplementedError()

  def getDebouncedButtonState(self):
    t = time.time()
    for i,new in enumerate(self.getButtonState()):
      if not new:
        self._button_state[i] = False
        continue
      old = self._button_state[i]
      if ((t-self._button_state_last_change[i]) >
             self._debounce_interval) and not old:
        self._button_state[i] = True
      else:
        self._button_state[i] = False
      self._button_state_last_change[i] = t
    return self._button_state

  def testButtons(self):
    while True:
      for i in range(5):
        self.setLED(i, self.isButtonPressed(i))
      print('Buttons: ', ' '.join([str(i) for i,v in
          enumerate(self.getButtonState()) if v]))
      time.sleep(0.01)

  def wiggleLEDs(self, reps=3):
    for i in range(reps):
      for i in range(5):
        self.setLED(i, True)
        time.sleep(0.05)
        self.setLED(i, False)


class UI_Keyboard(UI):
  def __init__(self):
    global keyinput
    import keyinput

    # Layout of GPIOs for Raspberry demo
    self._buttons = ['q', '1' , '2' , '3', '4']
    self._LEDs = [None]*5
    super(UI_Keyboard, self).__init__()

  def setLED(self, index, state):
    pass

  def getButtonState(self):
    pressed_chars = set()
    while True:
      char = keyinput.get_char()
      if not char : break
      pressed_chars.add(char)

    state = [b in pressed_chars for b in self._buttons]
    return state


class UI_Raspberry(UI):
  def __init__(self):
    # Only for RPi3: set GPIOs to pulldown
    global rpigpio
    import RPi.GPIO as rpigpio
    rpigpio.setmode(rpigpio.BCM)

    # Layout of GPIOs for Raspberry demo
    self._buttons = [26 , 4 , 27 , 5, 13]
    self._LEDs = [21, 17, 22, 6, 19]

    # Initialize them all
    for pin in self._buttons:
      rpigpio.setup(pin, rpigpio.IN, pull_up_down=rpigpio.PUD_DOWN)
    for pin in self._LEDs:
      rpigpio.setwarnings(False)
      rpigpio.setup(pin, rpigpio.OUT)
    super(UI_Raspberry, self).__init__()

  def setLED(self, index, state):
    return rpigpio.output(self._LEDs[index],
           rpigpio.LOW if state else rpigpio.HIGH)

  def getButtonState(self):
    return [rpigpio.input(button) for button in self._buttons]


class UI_EdgeTpuDevBoard(UI):
  def __init__(self):
    global GPIO, PWM
    from periphery import GPIO, PWM, GPIOError
    def initPWM(pin):
      pwm = PWM(pin, 0)
      pwm.frequency = 1e3
      pwm.duty_cycle = 0
      pwm.enable()
      return pwm
    try:
      self._LEDs = [GPIO(86, "out"),
                    initPWM(1),
                    initPWM(0),
                    GPIO(140, "out"),
                    initPWM(2)]
      self._buttons = [GPIO(141, "in"),
                       GPIO(8, "in"),
                       GPIO(7, "in"),
                       GPIO(138, "in"),
                       GPIO(6, "in")]
    except GPIOError as e:
      print("Unable to access GPIO pins. Did you run with sudo ?")
      sys.exit(1)

    super(UI_EdgeTpuDevBoard, self).__init__()

  def __del__(self):
    if hasattr(self, "_LEDs"):
      for x in self._LEDs or [] + self._buttons or []: x.close()

  def setLED(self, index, state):
    """Abstracts away mix of GPIO and PWM LEDs."""
    if isinstance(self._LEDs[index], GPIO): self._LEDs[index].write(not state)
    else: self._LEDs[index].duty_cycle = 0.0 if state else 1.0

  def getButtonState(self):
    return [button.read() for button in self._buttons]

class TeachableMachine(object):
  """Abstract TeachableMachine class. Subclassed by specific method implementations."""
  @abstractmethod
  def __init__(self, model_path, ui):
    assert os.path.isfile(model_path), 'Model file %s not found'%model_path
    self._ui = ui
    self._start_time = time.time()
    self._frame_times = deque(maxlen=40)

  # 信心指數、類別
  def get_results(self, classification):
    self._frame_times.append(time.time())
    fps = len(self._frame_times)/float(self._frame_times[-1] - self._frame_times[0] + 0.001)
    # Print/Display results
    self._ui.setOnlyLED(classification)
    classes = ['--', 'One', 'Two', 'Three', 'Four']
    status = 'FPS: %.1f | Nums: %d | Class: %5s'%(
            fps, self._engine.exampleCount(),
            classes[classification or 0])
    return status, classes[classification or 0]

  def classify(self):
    raise NotImplementedError()

### Modify by Chun
class TeachableMachineKNN_ByChun(TeachableMachine, Log):
  def __init__(self, model_path, ui, KNN=3, data_path='data'):
    TeachableMachine.__init__(self, model_path, ui)
    self._buffer = deque(maxlen = 4)
    self._engine = KNNEmbeddingEngine(model_path, KNN)
    
    self.cls_nums = KNN+1
    self.data_path = data_path
    self.trg_folder = []    # trg_folder = './data/{Class}'
    self.img_nums = [0, 0, 0, 0]    # img_nums = [ x, x, x, x], count each class's images
    self.check_dir()
    
    if sum(self.img_nums) != 0:
      t_reload = self.log_t('Reload Data', end=' ... ')
      self.reload_data()
      self.log_t('Done.', t_reload)
    
  
  def check_dir(self):
    
    t_check = self.log_t('Check Files', end=' ... ')
    for cls in range(1, self.cls_nums+1):  # Classes from 1 to 4
      self.trg_folder.append(os.path.join(self.data_path, str(cls)))
      
      # Check Directory is existed or not 
      if os.path.exists(self.trg_folder[cls-1]) is False:
        os.makedirs(self.trg_folder[cls-1])
        self.img_nums[cls-1] = 0
      else:
        self.img_nums[cls-1] = len(os.listdir(self.trg_folder[cls-1]))
    self.log_t('Done.', t_check)
    self.log_t(f'Files:{sum(self.img_nums)}')
    
  def clear_dir(self):
    shutil.rmtree(self.data_path) 
    self.check_dir()
    self.log_t('Clear')
    
  def reload_data(self):

    for cls in range(1, self.cls_nums+1):  # 1 ~ 4
      if self.img_nums[cls-1] != 0 :
        for idx in range(0, self.img_nums[cls-1]):
          img = Image.open(os.path.join(self.trg_folder[cls-1], f'{idx}.jpg'))
          emb = self._engine.DetectWithImage(img)
          self._buffer.append(self._engine.kNNEmbedding(emb))
          classification = Counter(self._buffer).most_common(1)[0][0]
          self._engine.addEmbedding(emb, cls)     
    
  def classify(self, img, infer=True, add_data=True):

    if infer:    
      # Classify current image and determine
      emb = self._engine.DetectWithImage(img)
      self._buffer.append(self._engine.kNNEmbedding(emb))
      classification = Counter(self._buffer).most_common(1)[0][0]
      # Interpret user button presses (if any)
      if add_data:
        debounced_buttons = self._ui.getDebouncedButtonState()
        for i, b in enumerate(debounced_buttons):
          if not b: continue
          if i == 0:
            self._engine.clear() # Hitting button 0 resets
            ### Modify by Chun : clear data folder
            self.clear_dir()   
          else :
            self._engine.addEmbedding(emb, i) # otherwise the button # is the class
            ### Modify by Chun : Save Image & Label
            save_path = os.path.join(self.trg_folder[i-1], f'{str(self.img_nums[i-1])}.jpg')
            img.save(save_path)
            self.img_nums[i-1] += 1
          
        # Hitting exactly all 4 class buttons simultaneously quits the program.
        if sum(filter(lambda x:x, debounced_buttons[1:])) == 4 and not debounced_buttons[0]:
          self.clean_shutdown = True
          return True # return True to shut down pipeline
      
      return self.get_results(classification)   ### Modify by Chun : log of results
### End of Modify

### Modify by Chun
class ThreadCapture(Log):
    
  def __init__(self, knn):
    self.frame = []
    self.status = False
    self.isStop = False
    self.knn = knn
    self.cap = cv2.VideoCapture(0)
    self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 480)
    
  def start(self):
    self.log_t('Start Video Stream')
    threading.Thread(target=self.current_frame, daemon=True, args=()).start()

  def stop(self):
    self.isStop = True
    
  def get_frame(self):
    return self.frame
  
  def crop_frame(self):
    h = self.frame.shape[0]
    w = self.frame.shape[1]
    cut = int((w-h)/2)
    self.frame = self.frame[0:h, cut:w-cut]
  
  def current_frame(self):
    while(not self.isStop):
      self.status, self.frame = self.cap.read()
      self.crop_frame()
    self.cap.release()

  def run_knn(self):
    img_resize = cv2.resize(self.frame, (224, 224))
    img = cv2.cvtColor(img_resize, cv2.COLOR_BGR2RGB)
    img_pil = Image.fromarray(img)
    return self.knn.classify(img_pil)
### End of Modify

def main(args):
    parser = argparse.ArgumentParser()
    parser.add_argument('--model', help='File path of Tflite model.',
                        default='models/mobilenet_quant_v1_224_headless_edgetpu.tflite')
    parser.add_argument('--testui', dest='testui', action='store_true',
                        help='Run test of UI. Ctrl-C to abort.')
    parser.add_argument('--keyboard', dest='keyboard', action='store_true',
                        help='Run test of UI. Ctrl-C to abort.')
    parser.add_argument('--method', dest='method',
                        help='method for transfer learning, support knn or imprinting',
                        default='knn',
                        choices=['knn', 'imprinting'])
    parser.add_argument('--outputmodel', help='File path of output Tflite model, only for imprinting method.',
                        default='output.tflite')
    parser.add_argument('--keepclasses', dest='keepclasses', action='store_true',
                        help='Whether to keep base model classes, only for imprinting method.')
    parser.add_argument('-d', '--data', default='data', help="Data's Path.")
    
    args = parser.parse_args()

    # The UI differs a little depending on the system because the GPIOs
    # are a little bit different.
    log = Log()
    log.log_t('Initialize UI.')
    platform = detectPlatform()
    if args.keyboard:
      ui = UI_Keyboard()
    else:
      if platform == 'raspberry': ui = UI_Raspberry()
      elif platform == 'devboard': ui = UI_EdgeTpuDevBoard()
      else:
        print('No GPIOs detected - falling back to Keyboard input')
        ui = UI_Keyboard()

    ui.wiggleLEDs()
    
    if args.testui:
        ui.testButtons()
        return

    t_model = log.log_t('Initialize Model')
    if args.method == 'knn':
      #teachable = TeachableMachineKNN(args.model, ui)
      teachable = TeachableMachineKNN_ByChun(args.model, ui, data_path=args.data)
    else:
      teachable = TeachableMachineImprinting(args.model, ui, args.outputmodel, args.keepclasses)

    log.log_t('Initial Model Finish.', t_model)
    #print('Start Pipeline.')
    #result = gstreamer.run_pipeline(teachable.classify)
    
    ### Modify by Chun
    cam = ThreadCapture(teachable)
    cam.start()
    time.sleep(1)
    
    while(True):
        
      I = cam.get_frame()
      info, cls = cam.run_knn()
      
      cv2.putText(I, info, (10,40), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0,0,255), 1, cv2.LINE_AA)
      cv2.imshow('Test', I)
      
      if cv2.waitKey(1)==ord('q'):
        cv2.destroyAllWindows()
        cam.stop()
        ui.wiggleLEDs(4)
        break
    log.log_t('End.')
    ### End of Modify

if __name__ == '__main__':
    sys.exit(main(sys.argv))



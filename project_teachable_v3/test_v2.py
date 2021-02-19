import cv2
import tkinter
from tkinter import *
import os, time
import PIL
from PIL import Image, ImageTk
import threading
import time
from coral_cv_with_data import detectPlatform, UI_Keyboard, UI_Raspberry, UI_EdgeTpuDevBoard, TeachableMachineKNN_ByChun
import argparse

class Image_Process():

    def crop(self, image):
        h, w, _ = image.shape
        cut = int((w-h)/2)
        return image[0:h, cut: int(w-cut)]
    
    def resize(self, image, resize=(224)):
        return cv2.resize(image, (resize,resize) )
    
    def cv2pil(self, image):
        f_rgb= cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        return Image.fromarray(f_rgb)

    def pil2tk(self, image):
        return ImageTk.PhotoImage(image)

class Log():

    def log_t(self, content, t=None, end='\n\n'):

        if t==None:
            print(f'\n{content}', end=end)
            return time.time()
        else:
            t_cost = time.time()-t
            print('{} ({:.5f}s)'.format(content, t_cost))
            return t_cost

""" WS2812 需要 thread 讀值"""
class WS2812():
    def __init__(self):
        self.isStop = False
        self.t_start = 0
        self.exec_time = 0
        self.status = False
    
    def start(self):
        threading.Thread(target=self.do_something, daemon=True, args=()).start()
    
    def do_something(self):
        while not self.isStop :
            self.status = True
            if self.exec_time == 0 : 
                self.t_start = time.time()
                self.exec_time = time.time() - self.t_start
            else:
                self.exec_time = time.time() - self.t_start
            print(self.exec_time)

    def get_time(self):
        return self.exec_time
    
    def get_status(self):
        return self.status

    def stop(self):
        self.status = False
        self.isStop=True

class MyVideoCapture(Image_Process, Log):
    
    def __init__(self, video_source):
    
        #將原本Webcam影像畫面大小設定為320X240
        self.vid = cv2.VideoCapture(video_source)
        self.vid.set(cv2.CAP_PROP_FRAME_WIDTH,320)
        self.vid.set(cv2.CAP_PROP_FRAME_HEIGHT,240)
        
        if not self.vid.isOpened():
            raise ValueError("Unable to open video source", video_source)
    
    def get_cap(self):
        return self.vid

    def get_frame(self):
        if self.vid.isOpened():
            ret, frame = self.vid.read()
            if ret:
                frame = self.resize( self.crop(frame))
                return (ret, frame)
            else:
                return (ret, None)
        else:
            return (ret, None)

    # 釋放影像資源
    def __del__(self):
        if self.vid.isOpened():
            self.vid.release()

class App_Setup():

    def __init__(self, win_title, mode=2):

        super().__init__()

        # 定義基本參數
        self.mode = mode
        self.img_size = 480
        self.pad, self.sticky = 3, "nsew"
        self.wpad = self.pad * 2
        self.h_item = 2
        self.isStart = False

        # format for items and fonts
        self.size = 'm'
        self.f_blocks = {'s':25, 'm':30, 'l':40, 'xl':45}
        self.f_fonts = {'s':('Arial', 15),  'm':('Arial', 20),  'l':('Arial', 30), 'xl':('Arial', 35)}

        # 控制 KNN
        self.ls_knn = ['KNN 0', 'KNN 1', 'BOTH']
        self.knn_0 = False
        self.knn_1 = False
        self.add_data = True

        # # 設定 KNN 畫面大小
        # knn_items_row, knn_items_col = 2, 2 
        # w_knn = ( self.img_size * 2 ) + ( self.wpad * knn_items_row ) + ( self.wpad * 4 )
        # h_knn = ( self.img_size * 1 ) + ( self.f_blocks[self.size] * ( knn_items_col - 1 ) ) + ( self.wpad * knn_items_col ) + ( self.wpad * 4 )

        # # 設定 按鈕區域 畫面大小
        # ctrl_items_row , ctrl_items_col = 2, 5
        # h_ctrl = ( self.f_blocks[self.size] * ctrl_items_col ) + ( self.wpad * ctrl_items_col )
        
        # # 取得最終視窗大小
        # w_main , h_main = w_knn , ( h_knn + h_ctrl )

        # 開啟新的視窗並進行設定
        self.window = tkinter.Tk()          # 開啟視窗
        self.window.title(win_title)        # 視窗標題

        # 設定全螢幕
        self.window.attributes('-zoomed', True)  
        self.fullScreenState = False
        self.window.bind("<F11>", self.toggleFullScreen)
        self.window.bind("<Escape>", self.quitFullScreen)

        # 設定區域分別為 標題區域、TM-KNN區域、控制區域
        self.frame_knn = self.new_frame(win=self.window, row=0, col=0)        
        self.frame_ctrl = self.new_frame(win=self.window, row=1, col=0) 
        self.frame_info = self.new_frame(win=self.window, row=0, col=1, rowspan=2)     

        # 設定KNN畫面位置
        self.cvs_0 = self.new_cvs(self.frame_knn, 0, 0)
        self.cvs_1 = self.new_cvs(self.frame_knn, 0, 1)
        self.lbl_knn_0 = self.new_lbl(self.frame_knn, self.ls_knn[0], 1, 0, bg='#BEBEBE', fg='#FF0000', f_font=('Arial', 20, 'bold'))
        self.lbl_knn_1 = self.new_lbl(self.frame_knn, self.ls_knn[1], 1, 1, bg='#BEBEBE', fg='#FF0000', f_font=('Arial', 20, 'bold'))

        # 設定INFO
        self.lbl_action = self.new_lbl(self.frame_info, '選擇動作', 0, 0, columnspan=2)
        self.bt_detect, self.bt_detect_text = self.new_bt(self.frame_info, 'DETECT', 1, 0, columnspan=2, fg='green')
        self.bt_close, self.bt_close_text = self.new_bt(self.frame_info, 'CLOSE', 2, 0, columnspan=2, fg='red')

        self.new_lbl(self.frame_info, '選擇模型', 3, 0, columnspan=2)
        self.bt_knn_0, self.bt_knn_0_text = self.new_bt(self.frame_info, self.ls_knn[0], 4, 0)
        self.bt_knn_1, self.bt_knn_1_text = self.new_bt(self.frame_info, self.ls_knn[1], 4, 1)

        self.cls_text_default = ['CLASS 1', 'CLASS 2', 'CLASS 3', 'CLASS 4']
        self.lbl_cls_t1 = self.new_lbl(self.frame_info, self.cls_text_default[0], 5, 0, f_font=self.f_fonts['s'], h=1)
        self.lbl_cls_t2 = self.new_lbl(self.frame_info, self.cls_text_default[1], 6, 0, f_font=self.f_fonts['s'], h=1)
        self.lbl_cls_t3 = self.new_lbl(self.frame_info, self.cls_text_default[2], 7, 0, f_font=self.f_fonts['s'], h=1)
        self.lbl_cls_t4 = self.new_lbl(self.frame_info, self.cls_text_default[3], 8, 0, f_font=self.f_fonts['s'], h=1)
        self.lbl_cls_1, self.lbl_cls_1_text = self.new_lbl_var(self.frame_info, '', 5, 1, f_font=self.f_fonts['s'], h=1)
        self.lbl_cls_2, self.lbl_cls_2_text = self.new_lbl_var(self.frame_info, '', 6, 1, f_font=self.f_fonts['s'], h=1)
        self.lbl_cls_3, self.lbl_cls_3_text = self.new_lbl_var(self.frame_info, '', 7, 1, f_font=self.f_fonts['s'], h=1)
        self.lbl_cls_4, self.lbl_cls_4_text = self.new_lbl_var(self.frame_info, '', 8, 1, f_font=self.f_fonts['s'], h=1)

        self.lbl_cls_text = [self.lbl_cls_t1, self.lbl_cls_t2, self.lbl_cls_t3, self.lbl_cls_t4]

        self.new_lbl(self.frame_info, '計時器(s)', 9, 0, f_font=self.f_fonts['s'])
        self.lbl_timer, self.lbl_timer_text = self.new_lbl_var(self.frame_info, self.timer_format(), 9, 1 , f_font=self.f_fonts['s'])
        
        # 控制區域的標籤與按鈕 : text是可變動的按鈕文字變數 使用.set()來更改
        self.bt_text_var = ['自動控制','自動顯示', '自動控制', '開啟裝置', '自動控制']
        self.lbl_fence = self.new_lbl(self.frame_ctrl, '汽車柵欄', 0, 0)
        self.bt_fence, self.bt_fence_text = self.new_bt(self.frame_ctrl, self.bt_text_var[0], 1, 0)

        self.lbl_aporn = self.new_lbl(self.frame_ctrl, '停機坪', 0, 1)
        self.bt_aporn, self.bt_aporn_text = self.new_bt(self.frame_ctrl, self.bt_text_var[1], 1, 1)

        self.lbl_spin = self.new_lbl(self.frame_ctrl, '旋轉車盤', 0, 2)
        self.bt_spin, self.bt_spin_text = self.new_bt(self.frame_ctrl, self.bt_text_var[2], 1, 2)

        self.lbl_RFID = self.new_lbl(self.frame_ctrl, 'RFID', 0, 3)
        self.bt_RFID, self.bt_RFID_text = self.new_bt(self.frame_ctrl, self.bt_text_var[3], 1, 3)

        self.lbl_locker = self.new_lbl(self.frame_ctrl, '四旋翼鎖', 0, 4)
        self.bt_locker, self.bt_locker_text = self.new_bt(self.frame_ctrl, self.bt_text_var[4], 1, 4)

        # 設定標籤清單
        self.bt_list = [self.bt_fence, self.bt_aporn, self.bt_spin, self.bt_RFID, self.bt_locker]
        self.bt_text_list = [self.bt_fence_text, self.bt_aporn_text, self.bt_spin_text, self.bt_RFID_text, self.bt_locker_text]        
        
        # 設定按鈕事件額外宣告的寫法，
        # 提供兩種，一種是副函式的另一種是直接給予物件數值 
        # lambda 後面執行階段不能有等號，前面參數可以有等號指定參數名稱，詳情請上網搜尋
        self.bt_knn_0['command'] = lambda : self.bt_knn_0_event()
        self.bt_knn_1['command'] = lambda : self.bt_knn_1_event()
        self.bt_close['command'] = self.window.destroy
        
        # 讓其保持平均分布
        for bt in range(5):
            Grid.columnconfigure(self.frame_ctrl, bt, weight=1)

    """
    設計 UI 所需要的副函式
    如有需求請自行增加
    """
    def new_frame(self, win, row, col, columnspan=1, rowspan=1):
        f = Frame(win, highlightbackground="gray", highlightthickness=2)
        f.grid(row=row, column=col, padx=self.pad, pady=self.pad, sticky=self.sticky, columnspan=columnspan, rowspan=rowspan)
        return f

    def new_cvs(self, frame, row, col):
        cvs = Canvas(frame, width = self.img_size, height = self.img_size)
        cvs.grid(row=row, column=col, padx=self.pad, pady=self.pad, sticky=self.sticky)
        return cvs

    def new_lbl(self, frame, text, row, col, columnspan=1, rowspan=1, bg='#d9d9d9', fg='black', f_font='', h=0):
        f_font = self.f_fonts[self.size] if f_font=='' else f_font
        h= self.h_item if h is 0 else h
        lbl = Label(frame, text=text, font=f_font, height=h, bg=bg, fg=fg)
        lbl.grid(row=row, column=col, columnspan=columnspan, rowspan=rowspan ,padx=self.pad, pady=self.pad, sticky=self.sticky)

        return lbl
    
    def new_bt(self, frame, text ,row, col, columnspan=1, rowspan=1 ,bg='#d9d9d9', fg='black'):
        str_var = StringVar()
        str_var.set(text)
        bt = Button(frame, textvariable=str_var , font= self.f_fonts[self.size], height=self.h_item, bg=bg, fg=fg)
        bt.grid(row=row, column=col, columnspan=columnspan, rowspan=rowspan, padx=self.pad, pady=self.pad, sticky=self.sticky)
        return bt, str_var

    def new_lbl_var(self, frame, text, row, col, columnspan=1, rowspan=1, bg='#d9d9d9', fg='black', f_font='', h=0):
        f_font = self.f_fonts[self.size] if f_font=='' else f_font
        h= self.h_item if h is 0 else h
        str_var = StringVar()
        str_var.set(text)
        lbl = Label(frame, textvariable=str_var, font=f_font, height=self.h_item, bg=bg, fg=fg)
        lbl.grid(row=row, column=col, columnspan=columnspan, rowspan=rowspan ,padx=self.pad, pady=self.pad, sticky=self.sticky)
        return lbl, str_var

    def timer_format(self, sec_0=0, sec_1=0, setup=False):
        
        format = f"{sec_0:0.1f} , {sec_1:0.1f}"
        
        if setup:
            self.lbl_timer_text.set(format)
        else:
            return format

    """
    一些基礎的事件可以宣告在這裡
    """

    def bt_knn_0_event(self):
        
        self.knn_0 = not self.knn_0
        
        if self.knn_0:
            self.bt_knn_0['bg'] = 'green'
            self.bt_knn_0['fg'] = 'white'
        else:
            self.bt_knn_0['bg'] = '#d9d9d9'
            self.bt_knn_0['fg'] = 'black'

    def bt_knn_1_event(self):
        
        self.knn_1 = not self.knn_1

        if self.knn_1:
            self.bt_knn_1['bg'] = 'green'
            self.bt_knn_1['fg'] = 'white'
        else:
            self.bt_knn_1['bg'] = '#d9d9d9'
            self.bt_knn_1['fg'] = 'black'

    def check_knn(self):
        
        if self.knn_0 and self.knn_1 : 
            self.add_data = False
        else:
            self.add_data = True

    def other_event(self):
        self.bt_fence['command'] = lambda : self.lbl_fence.config(bg='yellow')
        self.bt_aporn['command'] = lambda : self.random_color(self.lbl_aporn)
        self.bt_spin['command'] = lambda : self.random_color(self.lbl_spin)
        self.bt_RFID['command'] = lambda : self.random_color(self.lbl_RFID)
        self.bt_locker['command'] = lambda : self.random_color(self.lbl_locker)

    def random_color(self, label):
        import random
        r,g,b = int(random.random()*255), int(random.random()*255), int(random.random()*255)
        fg_color = 'white' if sum([r,g,b]) < (255*3*3/5) else 'black'
        bg_color = f'#{r:02x}{g:02x}{b:02x}'
        label['bg']=bg_color
        label['fg']=fg_color

    def toggleFullScreen(self, event):
        self.fullScreenState = not self.fullScreenState
        self.window.attributes("-zoomed", self.fullScreenState)

    def quitFullScreen(self, event):
        self.fullScreenState = False
        self.window.attributes("-zoomed", self.fullScreenState)

##### APP #####
# 建議:主要執行程式的地方
class App(App_Setup, Image_Process, Log):

    def __init__(self, win_title, knn, data_path, dev_0 = 0, dev_1 = 2, mode=2):
        
        t_init = self.log_t('Initialize', end=' ... ')

        # 繼承 App_Setup 的 init
        # 由於 Setup 的部分太多，會影響程式閱讀，所以用繼承的方式去寫
        super().__init__(win_title, mode)       
        
        self.knn = knn      # Teachable Machine via KNN
        self.delay = 15     # 10毫秒更新一次 
        
        # 辨識 & 辨識按鈕事件
        self.isDetect = False
        self.bt_detect['command'] = lambda : self.bt_detect_event()

        # KNN 類別相關 : 如果沒有的話記得打 '--'
        self.classes = ['--', 'One', 'Two', 'Three', 'Four']
        self.ur_cls_0 = ['--', 'Chun', 'Other', 'Water', 'Wallet']
        self.ur_cls_1 = ['--', 'One', 'Two', 'Three', 'Four']
        
        # KNN 相關
        self.info_0, self.cls_0 = '', '--'
        self.info_1, self.cls_1 = '', '--'
        self.status_0, self.frame_0 = 0, []
        self.status_1, self.frame_1 = 0, []
        # Timer的參數
        self.t_clock_0 = False
        self.t_clock_1 = False
        self.t_start_0 , self.t_start_1 = 0, 0
        self.t_end_0, self.t_end_1 = 5, 5
        self.timer_nums = 0

        # 資料及相關
        self.data_path = data_path      # data1, data2
        self.data_1, self.data_2 = [0, 0, 0, 0], [0, 0, 0, 0]
        self.check_once = False
        self.check_test = 0
        
        # 紀錄時間並顯示
        self.log_t('Done.', t_init)

        # 實例化相機 並啟動Thread
        self.cap_0 = MyVideoCapture(dev_0)
        self.cap_1 = MyVideoCapture(dev_1)
        threading.Thread(target=self.tm, daemon=True, args=()).start()
        
        # 宣告 WS2812 給 t_WS2812 : 這邊設定成 按下按鈕才執行Thread
        self.t_WS2812 = WS2812()

        # 執行 update的程式並重複執行
        self.update()
        self.window.mainloop()

    def update(self):
        
        # 取得相機畫面
        self.knn_event()

        # 如果按下 Detect 則會顯示辨識結果
        self.show_info( self.isDetect )

        # 透過辨識結果而啟動的副函式
        self.knn_example()

        # 計時器
        self.timer_event()

        # 當按下 aporn 的時候 WS2812 的 Thread 會執行
        self.ws2812_event()

        self.window.after(self.delay, self.update)

    # 測試程式 將會放在 detect 按鈕上
    def start_timer(self, clock_idx=0):
        
        if clock_idx == 0:
            if self.t_clock_0 == False:
                self.t_start_0 = time.time()
                self.t_clock_0 = True
            else: 
                pass

        if clock_idx == 1:
            if self.t_clock_1 == False:
                self.t_start_1 = time.time()
                self.t_clock_1 = True
            else: 
                pass
                
    # 透過 timer_clock 來控制
    def timer_event(self):

        t_0 = 0
        t_1 = 0

        # 如果 計時器開啟
        if self.t_clock_0:
            # 如果開啟計時器 {limit} 秒內則執行 ...
            if time.time() - self.t_start_0 <= self.t_end_0 :
                self.bt_fence['bg'] = 'red'
                t_0 = (time.time() - self.t_start_0)
            # 如果 大於 limit 則執行 ... 記得要將 timer_clock 關掉
            else:
                t_0 =0
                self.bt_fence['bg']='#d9d9d9'
                self.bt_fence['fg']='black'
                self.t_clock_0 = False

        # 如果 計時器開啟
        if self.t_clock_1:
            
            if time.time() - self.t_start_1 <= self.t_end_1 :
                self.bt_RFID['bg'] = 'yellow'
                t_1 = (time.time() - self.t_start_1)
            else:
                t_1 = 0
                self.bt_RFID['bg']='#d9d9d9'
                self.bt_RFID['fg']='black'
                self.t_clock_1 = False
        
        # 設定 Timer 標籤 App_setup 裡面
        self.timer_format(t_0, t_1, setup=True)

    def knn_example(self):

        if self.isDetect and self.knn_0 :
            # 如果辨識到 Chun 的話
            if self.classes.index(self.cls_0) == self.ur_cls_0.index('Chun'):
                # 開啟計時器
                self.start_timer(0)

        if self.isDetect and self.knn_1 :
            # 如果辨識到第三個類別
            if self.classes.index(self.cls_1) == 3:

                self.start_timer(1)

    # 後來新增的事件 : detect按鈕事件
    def bt_detect_event(self):

        self.isDetect = not self.isDetect
        
        if self.isDetect:
            self.bt_detect['bg']='green'
            self.bt_detect['fg']='white'
        else:
            self.bt_detect['bg']='#d9d9d9'
            self.bt_detect['fg']='green'

        # 可以連動其他事件
        #self.other_event() 

    def show_info(self, isDetect):  # show =

        if isDetect:
            self.lbl_knn_0['text'] = f'{self.classes.index(self.cls_0)} : {self.ur_cls_0[self.classes.index(self.cls_0)]}' if self.knn_0 else self.ls_knn[0]
            self.lbl_knn_1['text'] = f'{self.classes.index(self.cls_1)} : {self.ur_cls_1[self.classes.index(self.cls_1)]}' if self.knn_1 else self.ls_knn[1]
        else:
            self.lbl_knn_0['text'] = self.ls_knn[0]
            self.lbl_knn_1['text'] = self.ls_knn[1]        

    # KNN 事件 用於 讀取相機並顯示在畫布上
    # 控制選項為 knn_0 、 knn_1
    def knn_event(self):
        if self.knn_0:                
            self.status_0, self.frame_0 = self.cap_0.get_frame()
            self.photo_0 = PIL.ImageTk.PhotoImage(image = self.cv2pil( self.resize(self.frame_0, self.img_size)))
            self.cvs_0.create_image(0, 0, image = self.photo_0, anchor="nw")  
        else:
            self.cvs_0.delete('all')

        if self.knn_1:
            self.status_1, self.frame_1 = self.cap_1.get_frame()
            self.photo_1 = PIL.ImageTk.PhotoImage(image = self.cv2pil( self.resize(self.frame_1, self.img_size)))
            self.cvs_1.create_image(0, 0, image = self.photo_1, anchor="nw")
        else:
            self.cvs_1.delete('all')

    def ws2812_event(self):
        
        if self.t_WS2812.get_status():
            self.bt_aporn_text.set(f'{self.t_WS2812.get_time():.3f}s')
        else:
            self.bt_aporn_text.set('自動顯示')
            self.bt_aporn['command'] = lambda : self.t_WS2812.start()

    # 確認檔案數量
    def check_file(self):
        cls_labels = [self.lbl_cls_1_text, self.lbl_cls_2_text, self.lbl_cls_3_text, self.lbl_cls_4_text]
        ls_data = [self.data_1, self.data_2]
        ls_cls = [self.ur_cls_0, self.ur_cls_1]

        self.trg, self.count = -1, 0
        self.check_test += 1
        
        def set_param(target):

            self.trg = target
            self.count = self.count + 1

        if self.knn_0:  set_param(0)
        if self.knn_1:  set_param(1)
        if self.knn_0 and self.knn_1 :  set_param(2)

        if self.count < 2:
            self.check_once = False

        if self.trg >= 0:
            if not self.check_once:
                for idx in range(2):
                    for cls in range(4):
                        trg_path = os.path.join(self.data_path[idx], str(cls+1))
                        ls_data[idx][cls] = len(os.listdir(trg_path))     
                        
                        if self.trg == 2 :                        
                            cls_labels[cls].set(f'{ls_data[0][cls]:02}  ,  {ls_data[1][cls]:02}')
                            self.lbl_cls_text[cls]['text'] = self.cls_text_default[cls]
                            # 由於 兩個都打開的狀況下 是讀法增加檔案的，
                            self.check_once = True
                        else:
                            self.lbl_cls_text[cls]['text'] = ls_cls[self.trg][cls+1]
                            cls_labels[cls].set(f'{ls_data[self.trg][cls]:02}')
        else:
            self.check_test = 0
            for cls in range(4):
                self.lbl_cls_text[cls]['text'] = self.cls_text_default[cls]
            for lbl in cls_labels:
                lbl.set('__')

    def tm(self):
        while(True):
            self.check_file()
            self.check_knn()
            if self.status_0 and self.knn_0:
                self.info_0, self.cls_0 = self.knn[0].classify( img=self.cv2pil(self.resize(self.frame_0)), infer=self.knn_0, add_data=self.add_data) # if return status, prop, cls

            if self.status_1 and self.knn_1:
                self.info_1, self.cls_1 = self.knn[1].classify( img=self.cv2pil(self.resize(self.frame_1)), infer=self.knn_1, add_data=self.add_data)
    
    def __del__(self):
        self.t_WS2812.stop()
        self.log_t('QUIT')

if __name__ == "__main__":
    
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
    parser.add_argument('-d1', '--data1', default='data1', help="Data's Path.")
    parser.add_argument('-d2', '--data2', default='data2', help="Data2's Path.")
    parser.add_argument('-c', '--camera', default=2, help="if you have two camera and two dataset than choose 2, data path is target to 'data2'.")                        
    args = parser.parse_args()

    # The UI differs a little depending on the system because the GPIOs
    # are a little bit different.
    Log().log_t('Initialize UI.')
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

    data_path = [args.data1, args.data2]
    teachables = []

    for i in range(int(args.camera)):   # default = 2
        if args.method == 'knn':
            teachables.append(TeachableMachineKNN_ByChun(args.model, ui, data_path=data_path[i]))
        else:
            teachable = TeachableMachineImprinting(args.model, ui, args.outputmodel, args.keepclasses)

    # tm = [ tm_1, tm_2]
    App("test", knn=teachables, dev_0=0, dev_1=2, mode=args.camera, data_path=data_path)


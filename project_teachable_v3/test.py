import cv2
import tkinter
from tkinter import *
import os, time
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
    
    def resize(self, image, resize=(224, 224)):
        return cv2.resize(image, resize)
    
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
        self.img_size = 400
        self.pad, self.sticky = 1, "nsew"
        self.wpad = self.pad * 2
        self.h_item = 2
        self.isStart = False

        # format for items and fonts
        self.size = 'm'
        self.f_blocks = {'s':25, 'm':30, 'l':40, 'xl':45}
        self.f_fonts = {'s':('Arial', 10),  'm':('Arial', 15),  'l':('Arial', 20), 'xl':('Arial', 30)}

        
        # 設定 KNN 畫面大小
        knn_items_row, knn_items_col = 2, 2 
        w_knn = ( self.img_size * 2 ) + ( self.wpad * knn_items_row ) + ( self.wpad * 4 )
        h_knn = ( self.img_size * 1 ) + ( self.f_blocks[self.size] * ( knn_items_col - 1 ) ) + ( self.wpad * knn_items_col ) + ( self.wpad * 4 )
        
        # 設定 標題以及開關
        title_items_row, title_items_col = 1, 5 # title 佔3個 另外兩個放按鈕
        h_title = ( self.f_blocks['xl'] * title_items_row ) + ( self.wpad * title_items_row )

        # 設定 按鈕區域 畫面大小
        ctrl_items_row , ctrl_items_col = 2, 5
        h_ctrl = ( self.f_blocks[self.size] * ctrl_items_col ) + ( self.wpad * ctrl_items_col )
        
        # 取得最終視窗大小
        w_main , h_main = w_knn , ( h_knn + h_ctrl + h_title )
    
        # 開啟新的視窗並進行設定
        self.window = tkinter.Tk()          # 開啟視窗
        self.window.title(win_title)        # 視窗標題
        self.window.geometry('{w}x{h}'.format(w=w_main, h=h_main))     # 設定介面視窗像素大小
        self.window.resizable(False, False) # 不可改變大小

        # 設定區域分別為 標題區域、TM-KNN區域、控制區域
        self.frame_title = self.new_frame(win=self.window, w=w_main, h=h_title, row=0, col=0)
        self.frame_knn = self.new_frame(win=self.window, w=w_main, h=h_knn, row=1, col=0)        
        self.frame_ctrl = self.new_frame(win=self.window, w=w_main, h=h_ctrl, row=2, col=0)      

        # 設定標題內容
        self.lbl_title = self.new_lbl(self.frame_title, '樟樹國際實中', 0, 0, columnspan=3, bg='white', f_size='l')
        self.bt_start, self.bt_start_text = self.new_bt(self.frame_title, 'START', 0, 3, fg='green')
        self.bt_quit, self.bt_quit_text = self.new_bt(self.frame_title, 'QUIT', 0, 4, fg='red')
        # 讓其保持平均分布
        [ Grid.columnconfigure(self.frame_title, item, weight=1) for item in range(5) ]

        # 設定KNN畫面位置
        self.cvs_0 = self.new_cvs(self.frame_knn, 0, 0)
        self.cvs_1 = self.new_cvs(self.frame_knn, 0, 1)
        self.lbl_knn_0 = self.new_lbl(self.frame_knn, 'KNN 1', 1, 0, bg='grey')
        self.lbl_knn_1 = self.new_lbl(self.frame_knn, 'KNN 2', 1, 1, bg='grey')

        # 控制區域的標籤與按鈕 : text是可變動的按鈕文字變數 使用.set()來更改
        self.lbl_fence = self.new_lbl(self.frame_ctrl, '汽車柵欄', 0, 0)
        self.bt_fence, self.bt_fence_text = self.new_bt(self.frame_ctrl, '自動控制', 1, 0)

        self.lbl_aporn = self.new_lbl(self.frame_ctrl, '停機坪', 0, 1)
        self.bt_aporn, self.bt_aporn_text = self.new_bt(self.frame_ctrl, '自動顯示', 1, 1)

        self.lbl_spin = self.new_lbl(self.frame_ctrl, '旋轉車盤', 0, 2)
        self.bt_spin, self.bt_spin_text = self.new_bt(self.frame_ctrl, '自動控制', 1, 2)

        self.lbl_RFID = self.new_lbl(self.frame_ctrl, 'RFID', 0, 3)
        self.bt_RFID, self.bt_RFID_text = self.new_bt(self.frame_ctrl, '開啟裝置', 1, 3)

        self.lbl_locker = self.new_lbl(self.frame_ctrl, '四旋翼鎖', 0, 4)
        self.bt_locker, self.bt_locker_text = self.new_bt(self.frame_ctrl, '自動控制', 1, 4)
        
        # 設定按鈕事件額外宣告的寫法，
        # 提供兩種，一種是副函式的另一種是直接給予物件數值 
        # lambda 後面執行階段不能有等號，前面參數可以有等號指定參數名稱，詳情請上網搜尋
        self.bt_start['command'] = lambda : self.start_stream(self.bt_start_text)
        self.bt_quit['command'] = lambda : self.quit_app()
        self.bt_fence['command'] = lambda : self.lbl_fence.config(bg='yellow')
        self.bt_aporn['command'] = lambda : self.random_color(self.lbl_aporn)
        self.bt_spin['command'] = lambda : self.random_color(self.lbl_spin)
        self.bt_RFID['command'] = lambda : self.random_color(self.lbl_RFID)
        self.bt_locker['command'] = lambda : self.random_color(self.lbl_locker)

        # 讓其保持平均分布
        for bt in range(5):
            Grid.columnconfigure(self.frame_ctrl, bt, weight=1)

    def new_frame(self, win, w, h, row, col):
        f = Frame(win, width=w, height=h)
        f.grid(row=row, column=col, padx=self.pad, pady=self.pad, sticky=self.sticky)
        return f

    def new_cvs(self, frame, row, col):
        cvs = Canvas(frame, width = self.img_size, height = self.img_size)
        cvs.grid(row=row, column=col, padx=self.pad, pady=self.pad, sticky=self.sticky)
        return cvs

    def new_lbl(self, frame, text, row, col, columnspan=1, rowspan=1, bg='#d9d9d9', fg='black', f_size=''):
        lbl = Label(frame, text=text, font=self.f_fonts[self.size if f_size=='' else f_size], height=self.h_item)
        lbl.grid(row=row, column=col, columnspan=columnspan, rowspan=rowspan ,padx=self.pad, pady=self.pad, sticky=self.sticky)
        lbl['bg']=bg
        lbl['fg']=fg
        return lbl
    
    def new_bt(self, frame, text ,row, col ,bg='#d9d9d9', fg='black'):
        str_var = StringVar()
        str_var.set(text)
        bt = Button(frame, textvariable=str_var , font= self.f_fonts[self.size], height=self.h_item)
        bt.grid(row=row, column=col, padx=self.pad, pady=self.pad, sticky=self.sticky)
        return bt, str_var

    def random_color(self, label):
        import random
        r,g,b = int(random.random()*255), int(random.random()*255), int(random.random()*255)
        fg_color = 'white' if sum([r,g,b]) < (255*3*3/5) else 'black'
        bg_color = f'#{r:02x}{g:02x}{b:02x}'
        label['bg']=bg_color
        label['fg']=fg_color
    
    def start_stream(self, bt_text):
        if self.isStart is not True:
            self.isStart = True

            bt_text.set('PAUSE')
        else:
            self.isStart = False
            bt_text.set('START')

    def quit_app(self):
        self.window.destroy()

##### APP #####
class App(App_Setup, Image_Process, Log):

    def __init__(self, win_title, knn, dev_0 = 0, dev_1 = 2, mode=2):
        
        t_init = self.log_t('Initialize', end=' ... ')

        # 繼承 App_Setup 的 init
        # 由於 Setup 的部分太多，會影響程式閱讀，所以用繼承的方式去寫
        super().__init__(win_title, mode)       
        
        self.knn = knn      # Teachable Machine via KNN
        self.delay = 10     # 10毫秒更新一次 
        # 紀錄時間並顯示
        self.log_t('Done.', t_init)

        # 實例化相機
        self.cap_0 = MyVideoCapture(dev_0)  
        if self.mode==2:   
            self.cap_1 = MyVideoCapture(dev_1)

        # 宣告 WS2812 給 t_WS2812
        self.t_WS2812 = WS2812()
    
        # 執行 update的程式並重複執行
        self.update()
        self.window.mainloop()
    
    def update(self):
        # 如果按下開始按鈕則開始進行
        if self.isStart:
            
            status_0, frame_0 = self.cap_0.get_frame()

            # 進行 knn 的即時辨識，會獲得一組字串，欲修改內容請到 coral_cv_with_data.get_result() 中修改
            info = self.knn[0].classify( self.cv2pil( self.resize( frame_0) ))

            # 原本是使用 put Text 到圖片上，改用 label的方式
            # cv2.putText(frame_0, info, (5, 10), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (0,0,255), 1, cv2.LINE_AA)
            self.lbl_knn_0['text'] = info
            
            # 轉換成 tkinter可以讀的資料型態
            self.photo_0 = self.pil2tk( self.cv2pil( self.resize(frame_0, (self.img_size, self.img_size) ) ) )
            # 將圖片畫上畫布
            self.cvs_0.create_image(0, 0, image = self.photo_0, anchor="nw")

            # 如果有兩個camera則將第二個畫上
            if self.mode==2 :

                status_1, frame_1 = self.cap_1.get_frame()
                info = self.knn[1].classify(self.cv2pil( self.resize(frame_1)))
                self.lbl_knn_1['text'] = info
                self.photo_1 = self.pil2tk( self.cv2pil( self.resize(frame_1, (self.img_size, self.img_size) ) ))
                self.cvs_1.create_image(0, 0, image = self.photo_1, anchor="nw")

            # 當按下 aporn 的時候 WS2812 的 Thread 會執行
            if self.t_WS2812.get_status():
                self.bt_aporn_text.set(f'{self.t_WS2812.get_time():.3f}s')
            else:
                self.bt_aporn_text.set('自動顯示')
                self.bt_aporn['command'] = lambda : self.t_WS2812.start()


        self.window.after( self.delay, self.update)

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
    Log = Log()
    Log.log_t('Initialize UI.')
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

    for i in range(int(args.camera)):
        if args.method == 'knn':
            teachables.append(TeachableMachineKNN_ByChun(args.model, ui, data_path=data_path[i]))
        else:
            teachable = TeachableMachineImprinting(args.model, ui, args.outputmodel, args.keepclasses)

    App("test", knn=teachables, dev_0=0, dev_1=2, mode=args.camera)


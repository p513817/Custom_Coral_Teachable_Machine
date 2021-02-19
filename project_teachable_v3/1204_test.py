import cv2
import tkinter
import os, time
from PIL import Image, ImageTk
import threading
import time

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
        

##### Coral_Knn_VideoCapture #####
class KNN_Capture(Image_Process, Log):

    def __init__(self, dev=0):
        self.frame = []
        self.status = False
        self.isStop = False
        self.cap = cv2.VideoCapture(dev)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    
    def start(self):
        
        self.thread = threading.Thread(target=self.current_frame, daemon=True, args=()).start()
        
    def stop(self):
        self.isStop = True

    def get_frame(self):
        return (self.status, self.frame)

    def current_frame(self):
        while(self.isStop == False):
            self.status, self.frame = self.cap.read()
            self.frame = self.crop(self.frame)
        self.cap.release()
    
    def __del__(self):
        self.stop()

##### End of Coral_Knn_VideoCapture #####

##### APP #####
class App(Image_Process, Log):

    def __init__(self, win_title, dev_0 = 0 , dev_1 = 1):
        
        t_init = self.log_t('Initialize', end=' ... ')
        # 定義視窗的大小寬度
        self.pad, self.img_size = 5, 480

        main_h = str((self.img_size * 1) + (self.pad * 3))
        main_w = str((self.img_size * 2) + (self.pad * 3))

        self.window = tkinter.Tk()          # 開啟視窗
        self.window.title(win_title)        # 視窗標題
        self.window.geometry('{w}x{h}'.format(w=main_w, h=main_h))     # 設定介面視窗像素大小 480 x 480 , 邊框都是5的話
        self.window.resizable(False, False) # 不可改變大小

        self.frame_main = tkinter.Frame(self.window, width=main_w, height=main_h)        # 定義 畫格
        self.frame_main.grid(row=0, column=0)    # 定義 位置

        self.canvas_0 = tkinter.Canvas(self.frame_main, width = self.img_size, height = self.img_size)        # 定義畫布並且放在 main 畫格上
        self.canvas_0.grid(row=1, column=0)           # 設定在畫布的哪個位置

        self.canvas_1 = tkinter.Canvas(self.frame_main, width = self.img_size, height = self.img_size)        # 定義畫布並且放在 main 畫格上
        self.canvas_1.grid(row=1, column=1)           # 設定在畫布的哪個位置

        self.log_t('Done.', t_init)
        
        self.t_stream = self.log_t('Start Stream')

        self.cap_0 = KNN_Capture(dev_0)
        self.cap_0.start()
        time.sleep(1)
        self.cap_1 = KNN_Capture(dev_1)
        self.cap_1.start()  
        time.sleep(1)
        
        self.delay = 10     # 10毫秒更新一次        
        self.update()
        self.window.mainloop()
    
    def update(self):

        status_0, frame_0 = self.cap_0.get_frame()
        status_1, frame_1 = self.cap_1.get_frame()
        
        if status_0:
            self.photo_0 = self.pil2tk( self.cv2pil( frame_0))
            self.canvas_0.create_image(self.pad, self.pad, image = self.photo_0, anchor="nw")

        if status_1:
            self.photo_1 = self.pil2tk( self.cv2pil( frame_1))
            self.canvas_1.create_image(self.pad, self.pad, image = self.photo_1, anchor="nw")

        self.window.after( self.delay, self.update)

    def __del__(self):
        self.log_t('QUIT', self.t_stream)
        self.cap_0.stop()
        self.cap_1.stop()

if __name__ == "__main__":
    App('測試')

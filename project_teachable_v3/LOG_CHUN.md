# Modify Source Project

Item | Description
-----|-----
Date |109/12/02
Author| 張嘉鈞 Chia-Chun, Chang

---

## - coral_with_data.py

原本的版本是無法儲存拍的照片
將其修改成能夠儲存照片
並在下一次啟動的時候自動讀取
按下按鈕0即可清除buffer以及data資料夾

## - coral_cv_with_data.py

將原本的PyGi串流方式改為OpenCV
提供一個Thread來執行Infer的部分


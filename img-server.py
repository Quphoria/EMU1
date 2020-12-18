# import socket programming library 
import socket 

from PIL import Image
import numpy as np
import hashlib, io

import time

image_path = "web\\images\\"
url = "https://emu-1.quphoria.co.uk/"

# import thread module 
from _thread import *
import threading 

charset = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ +-*/<=>()[]{}#$_?|^&!~,.:\n"
def emu_1_string(s):
    s = s.upper()
    enc = b""
    for c in s:
        if c in charset:
            enc += bytes([charset.index(c)])
    return enc + bytes([0b111111])
  
# thread function 
def threaded(c): 
    try:
        while True: 
    
            # data received from client
            data = b""
            while len(data) < 63*64:
                data += c.recv(4096) 
            pixels = np.zeros((63, 64, 3), dtype=np.uint8)
            i = 0
            j = 0
            for i in range(64):
                for j in range(63):
                    color = data[j + 63*i]
                    lookup = [0, 85, 170, 255]
                    r = lookup[(color >> 4) & 0b11]
                    g = lookup[(color & 0b1111) >> 2]
                    b = lookup[color & 0b11]
                    pixels[j, i] = [r, g, b]
            img = Image.fromarray(pixels, 'RGB')
            
            m = hashlib.md5()
            with io.BytesIO() as memf:
                img.save(memf, 'PNG')
                data = memf.getvalue()
                m.update(data)
                h = m.hexdigest()[:8]
                img.save(image_path + h + ".png")
                print("Saved:", image_path + h + ".png")
                
                msg = "\n\nUploaded to " + url + h + "\n"
                c.send(emu_1_string(msg))
                time.sleep(0.5)
            break
        # connection closed 
        c.close() 
    except Exception as ex:
        print("Error: ", ex)
        try:
            c.close()
        except:
            pass
  
  
def Main(): 
    host = "" 
  
    # reverse a port on your computer 
    # in our case it is 12345 but it 
    # can be anything 
    port = 1337
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM) 
    s.bind((host, port)) 
    print("socket binded to port", port) 
  
    # put the socket into listening mode 
    s.listen(5) 
    print("socket is listening") 
  
    # a forever loop until client wants to exit 
    while True: 
  
        # establish connection with client 
        c, addr = s.accept() 
  
        # lock acquired by client 
        print('Connected to :', addr[0], ':', addr[1]) 
  
        # Start a new thread and return its identifier 
        start_new_thread(threaded, (c,)) 
    s.close() 
  
  
if __name__ == '__main__': 
    Main() 
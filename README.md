# EMU-1.0 Emulator
### This is my work for the 2020 X-MAS CTF EMU-1.0 EMULATOR
This is written in python3, it requires pygame and msvcrt  

msvcrt is used for non-blocking input()  
I have not yet rewrote this for linux

---

It contains different versions, for the differerent design stages of the CTF's Emulation category

The best version is **emu_1.0_gamebreak.py**,  
it is configured to use **paint.rom** and connect to the paint server:  
https://emu-1.quphoria.co.uk

To run it without connecting to a server,

uncomment `server_address = None` at the top of the file


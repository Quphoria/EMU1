import time
import msvcrt
import sys
import socket
import pygame as pg

# server_address = ("challs.xmas.htsp.ro", 5100)
server_address = ("emu-1.quphoria.co.uk", 1337)
# server_address = ("localhost", 1337)
# server_address = None

halted = False

class Tape:
    def __init__(self, filename):
        base64 = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/"
        self.rom = []
        with open(filename, "r") as romfile:
            for c in romfile.read():
                if c != "\n":
                    self.rom.append(base64.index(c))
        self.pointer = 0
        self.length = len(self.rom)
        print("ROM Length:", hex(self.length))
    
    def read(self, offset = 0):
        addr = (self.pointer + offset) % self.length
        return self.rom[addr]

    def get_instruction(self):
        osr = self.read()
        self.forward()
        a = self.read()
        self.forward()
        b = self.read()
        self.forward()
        c = self.read()
        self.forward()
        return (osr, a, b, c)

    def forward(self, amount=1):
        self.pointer = (self.pointer + amount) % self.length
        # print(hex(self.pointer))

    def backward(self, amount=1):
        self.forward(-amount)

    def jumpLabel(self, a, b, c, cond_flag):
        opc = self.read() - 1
        op = opc % 21
        condition = opc // 21

        if condition == 1 and not cond_flag:
            return False
        elif condition == 2 and cond_flag:
            return False
        if not op == 0o17:
            return False

        l_a = self.read(1)
        l_b = self.read(2)
        l_c = self.read(3)

        d = a == l_a and b == l_b and c == l_c
        
        return d

    def jumpUp(self, a, b, c, cond_flag):
        while not self.jumpLabel(a, b, c, cond_flag):
            self.forward(-4)
        # print("jumped to", hex(self.pointer))
    def jumpDown(self, a, b, c, cond_flag):
        while not self.jumpLabel(a, b, c, cond_flag):
            self.backward(-4)
        # print("jumped to", hex(self.pointer))


class Memory:
    def __init__(self):
        self.ram = [0] * 64

    def write(self, i, value):
        # if (i == 2):
        #     print("Write", value, "into", i)
        if i > 0:
            self.ram[i] = value
        # if (i == 1):
        #     print(self.ram[i])
        d = 1

    def read(self, i):
        return self.ram[i]

class ALU:
    def __init__(self):
        self.resetFlags()
    def resetFlags(self):
        self.O = False # Overflow
        self.Z = False # Zero
        self.C = False # Carry
        self.S = False # Sign
    
    def Add(self, a, b):
        self.resetFlags()
        c = a + b
        same_sign = a & (1<<5) == b & (1<<5)
        if same_sign and c & (1<<5) != a & (1<<5):
            self.O = True
        if c & (1<<6):
            self.C = True
        c &= 0b111111

        if c == 0:
            self.Z = True
        if c & (1<<5):
            self.S = True
        return c

    def Sub(self, a, b):
        self.resetFlags()
        c = a - b
        if c < 0:
            self.C = True  
        diff_sign = a & (1<<5) != b & (1<<5)
        if diff_sign and c & (1<<5) != a & (1<<5):
            self.O = True
        c &= 0b111111
        if c == 0:
            self.Z = True
        if c & (1<<5):
            self.S = True
        return c
    def Bitwise(self, c):
        self.resetFlags()
        if c == 0:
            self.Z = True
        if c & (1<<5):
            self.S = True
        return c

    def Or(self, a, b):
        return self.Bitwise(a | b)

    def Xor(self, a, b):
        return self.Bitwise(a ^ b)

    def And(self, a, b):
        return self.Bitwise(a & b)

    def LShiftL(self, a, n):
        self.resetFlags()
        c = a << n
        if c & (1<<6):
            self.C = True
        c = c % (1<<6)
        if c == 0:
            self.Z = True
        if c & (1<<5):
            self.S = True
        return c

    def LShiftR(self, a, n):
        return self.Bitwise(a >> n)

    def AShiftR(self, a, n):
        c = a >> n
        if a & (1<<5):
            c += 0b111111 << (6 - n)
        return self.Bitwise(c)
    
    def Rotate(self, a, n):
        c = a << n
        c += a >> (6 - n)
        return self.Bitwise(c)

    def Mult(self, a, b, n):
        self.resetFlags()
        c = a * b
        d = c >> n
        #self.S = c & (1<<15)
        d &= 0b111111
        if d & (1<<5):
            self.S = True
        self.Z = d == 0
        return d

    def SMulti(self, a, b, n):
        self.resetFlags()
        if a & (1<<5):
            a = -a & 0b11111
        else :
            a = a & 0b11111
        if b & (1<<5):
            b = -b & 0b11111
        else:
            b = b & 0b11111
        c = a * b
        if c < 0:
            c + (1 << 32)

        d = c >> n
        if c & (1<<12):
            d += 0b111111111111 << (12 - n)
        d &= 0b111111
        if d & (1<<5):
            self.S = True
        self.Z = d == 0
        return d

charset = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ +-*/<=>()[]{}#$_?|^&!~,.:\n"
serial_buffer = []

def serial_print(x, tape, ram, alu, cond_flag):
    if charset[x] == "H":
        save_state(tape, ram, alu, cond_flag)
    print(charset[x], end="", flush=True)

partial_flag = ""
n = 0

def flag_brute():
    global n
    flag = partial_flag
    while len(flag) < (40 - 23):
        flag += charset[n]
    n += 1
    return flag

def to_charset_array(s):
    a = []
    for n in s:
        a.append(charset.index(n))
    return a

def incoming():
    global serial_buffer
    while msvcrt.kbhit():
        c = msvcrt.getch().decode().upper()
        if c == "\r":
            c = "\n"
            # break
        if debug_input:
            print("[" + c + "]", end="", flush=True)
        else:
            print(c, end="", flush=True)
        if not c in charset:
            if c == "%":
                message = "S{" + flag_brute() + "}\n"
                print(message, end="", flush=True)
                serial_buffer = serial_buffer + to_charset_array(message)
            else:
                serial_buffer.append(63)
        else:
            serial_buffer.append(charset.index(c))
    return min(63, len(serial_buffer))

def serial_read():
    if incoming() == 0:
        return -1
    return serial_buffer.pop(0)

clock_initial = time.time() * 100
def get_clock():
    #print("Clock")
    now = time.time() * 100
    return round(now - clock_initial) % 4096

def get_clock_lo():
    
    return get_clock() & 0b111111

def get_clock_hi():
    return get_clock() >> 6

class NetworkCard:
    def __init__(self, address, mode="client"):
        self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.address = address
        self.mode = mode
        self.socks = []
        self.buffers = []
        self.i = 0
        self.marked_i = -1

    def connect(self):
        if self.mode == "client":
            self.s.connect(self.address)
            self.s.setblocking(False)
            self.socks.append(self.s)
            self.buffers.append([])
        elif self.mode == "server":
            host = "localhost"
            self.s.bind((host, self.address[1]))
            self.s.setblocking(False)
            self.s.listen()
            print("BOUND:", (host, self.address[1]))
            print("LISTENING..")
        else:
            print("Unknown Mode:", self.mode)
            
    def accept(self):
        if (self.mode == "server"):
            try:
                (clientsocket, address) = self.s.accept()
                clientsocket.setblocking(False)
                self.socks.append(clientsocket)
                print("ACCEPTED:", address)
                self.buffers.append([])
            except BlockingIOError:
                pass

    def wait_accept(self):
        while len(self.socks) == 0:
            self.accept()

    def send(self, x):
        if debug_net:
            print("Send:",x)
        self.socks[self.i].send(bytes([x]))

    def incoming(self):
        try:
            data = self.socks[self.i].recv(100)
        except BlockingIOError:
            data = bytes()
        while len(data) > 0:
            c = data[0]
            data = data[1:]
            if debug_net:
                print("RECV:",min(63, c))
            self.buffers[self.i].append(min(63, c))
        return min(63, len(self.buffers[self.i]))

    def incoming_safe(self):
        while len(self.socks) > 0:
            return self.incoming()
            try:
                return self.incoming()
            except Exception as ex:
                print("NET_ERROR:", ex)
                if self.i == self.marked_i:
                    self.marked_i -= 1
                self.i = self.i % len(self.socks)
                del self.socks[self.i]
                del self.buffers[self.i]
        return 0

    def read(self):
        self.accept()
        if self.incoming_safe() == 0:
            return -1
        return self.buffers[self.i].pop(0)

    def set_marker(self):
        self.marked_i = self.i

    def cycle_connection(self):
        self.accept()
        passed_marked = False
        reached_connection = False
        self.i = self.i + 1
        while not reached_connection:
            if len(self.socks) == 0:
                return 0
            self.i = self.i % len(self.socks)
            try:
                self.incoming()
                reached_connection = True
            except:
                if self.i == self.marked_i:
                    passed_marked = True
                    self.marked_i -= 1
                del self.socks[self.i]
                del self.buffers[self.i]
        if passed_marked:
            return 1
        return 0

class ExternalMemory:
    def __init__(self):
        self.address = 0
        self.mem = []
        for i in range(0x1 << 18):
            self.mem.append(0)
    
    def set_addr_hi(self, addr):
        a = self.address & 0b111111111111
        self.address = a + (addr << 12)
    
    def set_addr_mid(self, addr):
        a = self.address & 0b111111000000111111
        self.address = a + (addr << 6)

    def set_addr_lo(self, addr):
        a = self.address & 0b111111111111000000
        self.address = a + addr
    
    def read(self):
        d = self.mem[self.address]
        self.address = (self.address + 1) % (1 << 18)
        return d
    
    def write(self, d):
        self.mem[self.address] = d
        self.address = (self.address + 1) % (1 << 18)

class GPU:
    def __init__(self):
        self.w = 64 # width
        self.h = 64 # height
        self.s = 8 # scale
        pg.display.init()
        self.display = pg.display.set_mode((self.w*self.s, self.h*self.s), flags=0, depth=24)
        self.screen = pg.Surface((self.w, self.h), flags=0, depth=24)
        pg.transform.scale(self.screen, (self.w*self.s, self.h*self.s), self.display)
        self.x = 0
        self.y = 0
        self.screen_clear()

    def update(self):
        pg.transform.scale(self.screen, (self.w*self.s, self.h*self.s), self.display)
        pg.display.update()
        # print("Screen Update")

    def screen_clear(self):
        self.screen.fill((0,0,0))
        self.update()

    def set_x(self, value):
        self.x = value

    def set_y(self, value):
        self.y = value

    def draw(self, color):
        lookup = [0, 85, 170, 255]
        r = lookup[color >> 4]
        g = lookup[(color & 0b1111) >> 2]
        b = lookup[color & 0b11]
        c = (r, g, b)
        # print(c)
        pg.draw.rect(self.screen, c, pg.Rect(self.x,self.y,1,1))
        self.update()

class DPAD:
    def __init__(self):
        self.keys = 0
        print("----   CONTROLS    ----")
        print("WASD  X:COMMA  Y:PERIOD")
        print("-----------------------")

    def get_keys(self):
        return self.keys

    def event(self, event):
        if event.type == pg.QUIT:
            pg.quit()
            sys.exit()
        if event.type == pg.KEYDOWN or event.type == pg.KEYUP:
            bitmask = 0b000000
            if event.key == pg.K_COMMA:
                bitmask = 0b100000
            elif event.key == pg.K_PERIOD:
                bitmask = 0b10000
            elif event.key == pg.K_w:
                bitmask = 0b1000
            elif event.key == pg.K_s:
                bitmask = 0b100
            elif event.key == pg.K_a:
                bitmask = 0b10
            elif event.key == pg.K_d:
                bitmask = 0b1
            if event.type == pg.KEYDOWN:
                self.keys |= bitmask
            elif event.type == pg.KEYUP:
                self.keys &= 0b111111 ^ bitmask

class IODevice:
    def __init__(self, address=None, net_mode="client"):
        if (address != None):
            self.net = NetworkCard(address, net_mode)
            self.net.connect()
        self.mem = ExternalMemory()
        self.gpu = GPU()
            #self.net.wait_accept()
        self.dpad = DPAD()

    def update(self):
        self.gpu.update()

    def event(self, event):
        self.dpad.event(event)

    def read_write(self, id, value, tape, ram, alu, cond_flag):
        if id == 0:
            return incoming()
        elif id == 1:
            return serial_read()
        elif id == 2:
            serial_print(value, tape, ram, alu, cond_flag)
        elif id == 3:
            return get_clock_lo()
        elif id == 4:
            return get_clock_hi()
        elif id == 0o10:
            return self.net.incoming_safe()
        elif id == 0o11:
            return self.net.read()
        elif id == 0o12:
            self.net.send(value)
        elif id == 0o13:
            if value == 1:
                self.net.set_marker()
            elif value == 2:
                return self.net.cycle_connection()
        elif id == 0o20:
            self.mem.set_addr_hi(value)
        elif id == 0o21:
            self.mem.set_addr_mid(value)
        elif id == 0o22:
            self.mem.set_addr_lo(value)
        elif id == 0o23:
            return self.mem.read()
        elif id == 0o24:
            self.mem.write(value)
        elif id == 0o25:
            self.gpu.set_x(value)
        elif id == 0o26:
            self.gpu.set_y(value)
        elif id == 0o27:
            self.gpu.draw(value)
        elif id == 0o30:
            return self.dpad.get_keys()
        return 0

def save_state(tape, ram, alu, cond_flag):
    return
    print("SAVE:")
    print("TAPE:", tape.pointer - 4)
    print("RAM:", ram.ram)
    print("Overflow", alu.O)
    print("Carry", alu.C)
    print("Zero", alu.Z)
    print("Sign", alu.S)
    print("Cond", cond_flag)
    print("END_SAVE")

def load_state(tape, ram, alu):
    tape.pointer = 736
    ram.ram = [0, 17, 48, 23, 15, 23, 15, 0, 0, 0, 0, 60, 4, 0, 6, 0, 40, 49, 62, 14, 32, 20, 61, 28, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 23, 13, 0, 0, 0, 0, 0, 0, 0, 0, 0, 2]
    ram.ram = [0, 17, 48, 23, 15, 23, 15, 0, 0, 0, 0, 60, 4, 0, 6, 0, 40, 49, 62, 14, 32, 20, 61, 28, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 23, 13, 0, 0, 0, 0, 0, 0, 0, 0, 0, 2]
    alu.O = False
    alu.C = False
    alu.Z = False
    alu.S = False
    return False

debug = False
debug_input = False
debug_net = False

if __name__ == "__main__":
    #tape = Tape("mandelflag.rom")
    tape = Tape("paint1.rom")
    ram = Memory()
    alu = ALU()
    dev = IODevice(server_address)
    cond_flag = False # Conditional Flag
    #cond_flag = load_state(tape, ram, alu) # Load from saved state
    while not halted:
        # Handle pygame events
        for event in pg.event.get():
            dev.event(event)
        # incoming()
        opc, a, b, c = tape.get_instruction()
        if opc == 0:
            halted = True
            break
        opc -= 1
        op = opc % 21
        condition = opc // 21

        if condition == 1 and not cond_flag:
            continue
        elif condition == 2 and cond_flag:
            continue
        
        if op == 0o0:
            if debug:
                print("Add", ram.read(b), "with", ram.read(c), "into", a)
            ram.write(a, alu.Add(ram.read(b), ram.read(c)))
        elif op == 0o1:
            if debug:
                print("Add", ram.read(b), "with immediate", c, "into", a)
            ram.write(a, alu.Add(ram.read(b), c))
        elif op == 0o2:
            if debug:
                print("Sub", ram.read(b), "with", ram.read(c), "into", a)
            ram.write(a, alu.Sub(ram.read(b), ram.read(c)))
        elif op == 0o3: 
            
            cc = a % 0o10
            m = a // 0o10
            if m == 0:
                alu.Sub(ram.read(b), ram.read(c))
                if debug:
                    print("Cmp", ram.read(b), "with", ram.read(c))
            elif m == 1:
                alu.Sub(ram.read(c), ram.read(b))
                if debug:
                    print("Cmp", ram.read(c), "with", ram.read(b))
            elif m == 2:
                alu.Sub(ram.read(b), c)
                if debug:
                    print("Cmp", ram.read(b), "with immediate", c)
            elif m == 3:
                alu.Sub(b, ram.read(c))
                if debug:
                    print("Cmp immediate", b, "with", ram.read(c))

            if cc == 0:
                cond_flag = True
            elif cc == 1:
                cond_flag = False
            elif cc == 2:
                cond_flag = alu.Z
            elif cc == 3:
                cond_flag = not alu.Z
            elif cc == 4:
                cond_flag = alu.S ^ alu.O
            elif cc == 5:
                cond_flag = (not alu.S ^ alu.O) and not alu.Z
            elif cc == 6:
                cond_flag = alu.C
            elif cc == 7:
                cond_flag = not (alu.C or alu.Z)
        elif op == 0o4:
            if debug:
                print("Or", ram.read(b), "with", ram.read(c), "into", a)
            ram.write(a, alu.Or(ram.read(b), ram.read(c)))
        elif op == 0o5:
            if debug:
                print("Or", ram.read(b), "with immediate", c, "into", a)
            ram.write(a, alu.Or(ram.read(b), c))
        elif op == 0o6:
            if debug:
                print("Xor", ram.read(b), "with", ram.read(c), "into", a)
            ram.write(a, alu.Xor(ram.read(b), ram.read(c)))
        elif op == 0o7:
            if debug:
                print("Xor", ram.read(b), "with immediate", c, "into", a)
            ram.write(a, alu.Xor(ram.read(b), c))
        elif op == 0o10:
            if debug:
                print("And", ram.read(b), "with", ram.read(c), "into", a)
            ram.write(a, alu.And(ram.read(b), ram.read(c)))
        elif op == 0o11:
            if debug:
                print("And", ram.read(b), "with immediate", c, "into", a)
            ram.write(a, alu.And(ram.read(b), c))
        elif op == 0o12:
            ib = c % 0o10
            c = c // 0o10
            if c == 0:
                if debug:
                    print("LShiftL", ram.read(b), "with immediate", c, "into", a)
                ram.write(a, alu.LShiftL(ram.read(b), ib))
            elif c == 1:
                if debug:
                    print("LShiftR", ram.read(b), "with immediate", c, "into", a)
                ram.write(a, alu.LShiftR(ram.read(b), ib))
            elif c == 2:
                if debug:
                    print("AShiftR", ram.read(b), "with immediate", ib, "into", a)
                ram.write(a, alu.AShiftR(ram.read(b), ib))
            elif c == 3:
                ram.write(a, alu.Rotate(ram.read(b), ib))
        elif op == 0o13:
            if debug:
                print("LShiftL", ram.read(b), "with", ram.read(c), "into", a)
            ram.write(a, alu.LShiftL(ram.read(b), ram.read(c)))
        elif op == 0o14:
            if debug:
                print("LShiftR", ram.read(b), "with", ram.read(c), "into", a)
            ram.write(a, alu.LShiftR(ram.read(b), ram.read(c)))
        elif op == 0o15:
            if debug:
                print("LD", ram.read(b), "+", c, "into", a)
            addr = (ram.read(b) + c) % 64
            ram.write(a, ram.read(addr))
        elif op == 0o16:
            if debug:
                print("LD", a, "into", ram.read(b), "+", c)
            addr = (ram.read(b) + c) % 64
            ram.write(addr, ram.read(a))
        elif op == 0o17:
            if debug:
                print("Jump Label")
            pass # Jump label
        elif op == 0o20:
            if debug:
                print("Jump up to", a, b, ram.read(c))
            tape.jumpUp(a, b, ram.read(c), cond_flag)
        elif op == 0o21:
            if debug:
                print("Jump down to", a, b, ram.read(c))
            tape.jumpDown(a, b, ram.read(c), cond_flag)
        elif op == 0o22:
            x = dev.read_write(b, ram.read(c), tape, ram, alu, cond_flag)
            ram.write(a, x)
            if debug:
                print("I/O write", ram.read(c), "into", b, "read", x, oct(x))
        elif op == 0o23:
            pr = c % 0o20
            if c < 0o20:
                ram.write(a, alu.Mult(ram.read(a), ram.read(b), pr))
                if debug:
                    print("Mult", a, "with", b, "shift", pr,"into", a)
            else:
                ram.write(a, alu.SMult(ram.read(a), ram.read(b), pr))
                if debug:
                    print("SMult", a, "with", b, "shift", pr,"into", a)
        elif op == 0o24: # op == 20
            #halted = True
            print("OP 20")
            #break
    print("HALTED.")
    while True:
        for event in pg.event.get():
            dev.event(event)
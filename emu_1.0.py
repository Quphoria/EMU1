import time
import msvcrt
import sys

passwd = ""
if len(sys.argv) > 1:
    passwd = sys.argv[1].replace("s", " ").replace("l", "\n")

# print(passwd)
# print(len(passwd))

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
        if c > 0b111111:
            self.O = True
            self.C = True
        c = c % (1<<6)

        if c == 0:
            self.Z = True
        if c & (1<<5):
            self.S = True
        return c

    def Sub(self, a, b):
        self.resetFlags()
        c = a - b
        if c < 0:
            self.O = True
            self.C = True
        c = c % (1<<6)
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
        self.S = c & (1<<15)
        self.Z = c == 0
        return d & 0b111111

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
            self.S = True
        self.Z = c == 0
        return d & 0b111111

charset = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ +-*/<=>()[]{}#$_?|^&!~,.:\n"
serial_buffer = []

for l in passwd:
    serial_buffer.append(charset.index(l))

def serial_print(x, tape, ram, alu, cond_flag):
    if (charset[x] == "H"):
        save_state(tape, ram, alu, cond_flag)
    print(charset[x], end="", flush=True)

def incoming():
    while msvcrt.kbhit():
        c = msvcrt.getch().decode().upper()
        if (c == "\r"):
            c = "\n"
            # break
        print("[" + c + "]", end="", flush=True)
        serial_buffer.append(charset.index(c))
    return min(63, len(serial_buffer))

def serial_read():
    if incoming() == 0:
        return -1
    return serial_buffer.pop(0)

clock_initial = time.time() * 100
def get_clock():
    #print("Clock")
    return round(time.time() - clock_initial) % 4096

def get_clock_lo():
    return get_clock() & 0b111111

def get_clock_hi():
    return get_clock() >> 6

class IODevice():
    def read(self, id):
        if id == 0:
            return incoming()
        elif id == 1:
            return serial_read()
        elif id == 3:
            return get_clock_lo()
        elif id == 4:
            return get_clock_hi()
        return 0

    def write(self, id, value, tape, ram, alu, cond_flag):
        if id == 2:
            serial_print(value, tape, ram, alu, cond_flag)

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

if __name__ == "__main__":
    tape = Tape("mandelflag.rom")
    ram = Memory()
    alu = ALU()
    dev = IODevice()
    cond_flag = False # Conditional Flag
    cond_flag = load_state(tape, ram, alu) # Load from saved state
    while not halted:
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
            x = dev.read(b)
            if debug:
                print("I/O write", ram.read(c), "into", b, "read", x, oct(x))
            dev.write(b, ram.read(c), tape, ram, alu, cond_flag)
            ram.write(a, x)
            if b == 1:
                print("READ")
        elif op == 0o23:
            pr = c % 0o20
            if c < 0o20:
                ram.write(a, alu.Mult(ram.read(a), b, pr))
                if debug:
                    print("Mult", a, "with", b, "shift", pr,"into", a)
            else:
                ram.write(a, alu.SMult(ram.read(a), b, pr))
                if debug:
                    print("SMult", a, "with", b, "shift", pr,"into", a)
        elif op == 0o24: # op == 20
            #halted = True
            print("OP 20")
            #break
    print("HALTED.")
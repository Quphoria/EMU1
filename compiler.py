data = []
with open("paint_bin.txt") as f:
    data = f.readlines()

base64 = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/"

binary = ""
for line in data:
    line = line.split(" ")
    if len(line) >= 4:
        a = line[0][:3]
        b = line[1][:3]
        c = line[2][:3]
        d = line[3][:3]
        a = base64[int(a, 8)]
        b = base64[int(b, 8)]
        c = base64[int(c, 8)]
        d = base64[int(d, 8)]
        binary += a + b + c + d

print("PROGRAM COMPILED")
print("SIZE:", len(binary))

with open("paint.rom", "w") as f:
    f.write(binary)
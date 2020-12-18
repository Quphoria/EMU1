base64 = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/"
charset = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ +-*/<=>()[]{}#$_?|^&!~,.:\n"
enc_pass = "kkKVcdOWKOSXVWiSQkVdYWkLmYOVhYdLcRRkdKkb"

instructions = """Yk
Vk
oK
tV
Lc
bd
XO
nW
iK
dO
OS
jX
rV
JW
Ii
RS
SQ
kk
vV
Ud
sY
QW
Pk
WL
mm
wY
aO
xV
lh
uY
gd
ZL
pc
TR
hR
fk
cd
KK
qk
eb"""

instructions = instructions.split("\n")
d = {}
for i in instructions:
    d[base64.index(i[0])] = base64.index(i[1])
d = dict(sorted(d.items()))

dec_pass = "["
for ch in d.items():
    dec_pass += charset[ch[1]]
print(dec_pass + "]")

pswd = "YMASI MIGHT BE BETTER THAN X-MAS LOLOLOL"
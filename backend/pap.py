import bcrypt

hashed = "$2b$12$S4nigkn1Ca1Sq6joQ5M4juyOvFnBG9sCvcvX3sDXVjoAhXKTP6M6W"
password = "Huawei@2025"  # the password you tried
print(bcrypt.checkpw(password.encode(), hashed.encode()))

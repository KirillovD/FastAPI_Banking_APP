import bcrypt


def hash_password(password: str) -> str:
    #convert into bytes
    pwd_bytes = password.encode('utf-8')

    #creating the salt
    salt = bcrypt.gensalt()

    #hashing the pass
    hashed_password = bcrypt.hashpw(password=pwd_bytes, salt=salt)

    # returned after decoding
    return hashed_password.decode('utf-8')


def verify_password(plain_password: str, hashed_password: str) -> bool:
    #convert them both into bytes
    password_byte_enc = plain_password.encode('utf-8')
    hashed_password_byte_enc = hashed_password.encode('utf-8')

    # compare
    return bcrypt.checkpw(password_byte_enc, hashed_password_byte_enc)
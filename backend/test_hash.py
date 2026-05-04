from passlib.context import CryptContext
import traceback
try:
    pwd_context = CryptContext(schemes=['bcrypt'], deprecated='auto')
    hash = pwd_context.hash('Testpassword1!')
    print(hash)
except Exception as e:
    traceback.print_exc()

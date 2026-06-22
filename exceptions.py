#this file is for all HTTPPerceptions

from fastapi import HTTPException, status

class AccountInsufficientFundsException(HTTPException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail= "Transaction declined: Insufficient funds"

        )

class AccountNotFoundException(HTTPException):
    def __init__(self, detail: str = "Invalid transfer details"):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail= detail

        )

class UserNotFoundException(HTTPException):
    def __init__(self, detail: str = "User not found"):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail= detail

        )

class TokenException(HTTPException):
    def __init__(self, detail: str = "Token expired or invalid"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail= detail

        )
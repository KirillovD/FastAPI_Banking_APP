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

class NotAdmin(HTTPException):
    def __init__(self, detail: str = "User does no have admin rights"):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail= detail

        )

class IbanGenError(HTTPException):
    def __init__(self, detail: str = "Something went wrong, please refresh the page and try again"):
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail= detail

        )
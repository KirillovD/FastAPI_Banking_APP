#this file is for all HTTPPerceptions

from fastapi import HTTPException, status

class InsufficientFunds(HTTPException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail= "Transaction declined: Insufficient funds"

        )

class AccountNotFound(HTTPException):
    def __init__(self, detail: str = "Invalid transfer details"):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail= detail

        )

class UserNotFound(HTTPException):
    def __init__(self, detail: str = "User not found"):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail= detail

        )


class UserAlreadyExists(HTTPException):
    def __init__(self, detail: str = "User with this email already exists"):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
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

class NotYourAccount(HTTPException):
    def __init__(self, detail: str = "You don't have access to this account"):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail= detail
        )


class NotYourCard(HTTPException):
    def __init__(self, detail: str = "You don't have access to this card"):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail= detail
        )

class CardNotFound(HTTPException):
    def __init__(self, detail: str = "Card not found"):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail= detail

        )
class MinPaymentNotReached(HTTPException):
    def __init__(self, detail: str = "Your payment is smaller than the minimal amount"):
        super().__init__(
            status_code=status.HTTP_400_NOT_FOUND,
            detail= detail

        )

class CvvMissing(HTTPException):
    def __init__(self, detail: str = "There is no CVV send"):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail= detail

        )

class PinMissing(HTTPException):
    def __init__(self, detail: str = "There is no PIN send"):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail= detail

        )

class PinCodeIncorrect(HTTPException):
    def __init__(self, detail: str = "The pin code you entered is incorrect"):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail= detail
        )

class CvvCodeIncorrect(HTTPException):
    def __init__(self, detail: str = "The cvv code you entered is incorrect"):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail= detail
        )




class GraceNoInterest(HTTPException):
    def __init__(self, detail: str = "Can't add aquired interest to the balance: Grace period is active"):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail= detail
        )
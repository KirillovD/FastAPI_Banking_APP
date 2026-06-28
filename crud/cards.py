from sqlalchemy.orm import Session
import models,schemas
import utils


def create_credit_card(user_id : int, card_type_and_pin : schemas.CreateCard, db : Session ):

    credit_card_info = utils.generate_card_info(card_type_and_pin.card_type, card_type_and_pin.pin_code)

    new_credit_card = models.CreditCard(owner_id = user_id,
                                        credit_card_number = credit_card_info["card_number"],
                                        expiry_date = credit_card_info["expiry_date"],
                                        pin_code_hashed = credit_card_info["hashed_pin_code"],
                                        CVV_encrypted = credit_card_info["encrypted_security_code"])

    db.add(new_credit_card)
    db.commit()
    db.refresh(new_credit_card)

    return new_credit_card


def create_debit_card(acc_id : int, card_type_and_pin : schemas.CreateCard, db : Session ):

    debit_card_info = utils.generate_card_info(card_type_and_pin.card_type, card_type_and_pin.pin_code)

    new_debit_card = models.DebitCard( linked_acc_id = acc_id,
                                        debit_card_number = debit_card_info["card_number"],
                                        expiry_date = debit_card_info["expiry_date"],
                                        pin_code_hashed = debit_card_info["hashed_pin_code"],
                                        CVV_encrypted = debit_card_info["encrypted_security_code"])

    db.add(new_debit_card)
    db.commit()
    db.refresh(new_debit_card)

    return new_debit_card
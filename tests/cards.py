
from schemas import DebitCardResponse, CreditCardResponse, CardSecretResponse
from tests.conftest import create_account, create_credit_card, create_debit_card, create_user_and_login


def test_create_credit_card(client, auth_headers):

    credit_card = client.post("/cards/credit",
                              json = { "pin_code" : 1234,
                                       "card_type" : "mastercard"},
                              headers = auth_headers)

    assert credit_card.status_code == 200

    data = credit_card.json()
    assert "pin_code" not in data

    validated_card = CreditCardResponse(**data)



def test_create_debit_card(client, auth_headers):

    account = create_account(client,
                             auth_headers,
                             "Checking",
                             1000)

    acc_id = account["id"]

    debit_card = client.post(f"/cards/debit/{acc_id}",
                              json={"pin_code": 1234,
                                    "card_type": "maestro"},
                              headers=auth_headers)

    assert debit_card.status_code == 200

    data = debit_card.json()
    assert "pin_code" not in data

    validated_card = DebitCardResponse(**data)

    assert validated_card.linked_acc_id == account["id"]



def test_create_debit_card_idor(client, auth_headers):

    account_a = create_account(client,
                             auth_headers,
                             "Checking",
                             1000)

    acc_id_a = account_a["id"]


    header_b = create_user_and_login(client, "mary@example.com","Mary")

    debit_card = client.post(f"/cards/debit/{acc_id_a}",
                              json={"pin_code": 1234,
                                    "card_type": "maestro"},
                              headers=header_b)


    assert debit_card.status_code in [403, 404]


def test_get_credit_card(client,auth_headers):

    credit_card = create_credit_card(client,auth_headers)
    card_id = credit_card["id"]

    response = client.get(f"/cards/credit/{card_id}",
                          headers=auth_headers)
    data = response.json()
    assert "pin_code" not in data

    validated_card = CreditCardResponse(**data)


def test_get_credit_card_idor(client,auth_headers):

    credit_card_a = create_credit_card(client,auth_headers)
    card_id_a = credit_card_a["id"]


    header_b = create_user_and_login(client, "mary@example.com","Mary")

    response = client.get(f"/cards/credit/{card_id_a}",
                          headers=header_b)

    assert response.status_code in [403, 404]


def test_get_debit_card(client,auth_headers):
    account = create_account(client,auth_headers,
                             "Checking", 1000)

    debit_card = create_debit_card(client,auth_headers,account["id"])

    card_id = debit_card["id"]

    response = client.get(f"/cards/debit/{card_id}",
                          headers=auth_headers)

    data = response.json()
    assert "pin_code" not in data

    validated_card = DebitCardResponse(**data)


def test_get_debit_card_idor(client,auth_headers):

    acc_a = create_account(client, auth_headers,
                          "Checking", 1000)

    debit_card_a = create_debit_card(client,auth_headers,acc_a["id"])

    card_id_a = debit_card_a["id"]

    header_b = create_user_and_login(client, "mary@example.com","Mary")

    response = client.get(f"/cards/debit/{card_id_a}",
                          headers=header_b)

    assert response.status_code in [403, 404]


def test_get_credit_card_cvv(client,auth_headers):

    credit_card = create_credit_card(client,auth_headers)
    card_id = credit_card["id"]

    response = client.get(f"/cards/credit/{card_id}/cvv",
                          headers=auth_headers)

    assert response.status_code == 200
    data = response.json()

    validated_card = CardSecretResponse(**data)


def test_get_credit_card_cvv_idor(client,auth_headers):

    credit_card = create_credit_card(client,auth_headers)
    card_id = credit_card["id"]

    header_b = create_user_and_login(client, "mary@example.com","Mary")


    response = client.get(f"/cards/credit/{card_id}/cvv",
                          headers=header_b)

    assert response.status_code in [403, 404]


def test_get_debit_card_cvv(client, auth_headers):

    account = create_account(client, auth_headers,
                             "Checking", 1000)

    debit_card = create_debit_card(client,auth_headers,account["id"])

    card_id = debit_card["id"]

    response = client.get(f"/cards/debit/{card_id}/cvv",
                          headers=auth_headers)

    assert response.status_code == 200
    data = response.json()

    validated_card = CardSecretResponse(**data)


def test_get_debit_card_cvv_idor(client, auth_headers):

    account_a = create_account(client, auth_headers,
                             "Checking", 1000)

    debit_card_a = create_debit_card(client,auth_headers,account_a["id"])

    card_id_a = debit_card_a["id"]

    header_b = create_user_and_login(client, "mary@example.com","Mary")


    response = client.get(f"/cards/debit/{card_id_a}/cvv",
                          headers=header_b)

    assert response.status_code in [403, 404]



from decimal import Decimal

from conftest import create_user_and_login,create_account
from schemas.transactions import TransactionResponse, CashOperationsResponse


def test_transfer_money_success(client,auth_headers):

    #create users with accounts
    sender_headers = auth_headers
    sender_user_account = create_account(client,sender_headers,
                                        "checking",500)

    recipient_headers = create_user_and_login(client,"bob@example.com","Bob")

    recipient_user_account = create_account(client, recipient_headers,
                                            "checking",1000)

    #creating transaction
    response = client.post(f"/transactions/{sender_user_account["id"]}",
                           json={
                                 "recipient_iban": recipient_user_account["iban"],
                                 "sender_iban" : sender_user_account["iban"],
                                 "recipient_name": "Bob Test",
                                 "sender_account_id":sender_user_account["id"],
                                 "amount" : 200,
                                 "description" : "Rewe sagt danke"

                                },
                                headers = sender_headers
                           )
    print(response.json())
    assert  response.status_code == 200

    #check if response matches the scheme
    data = response.json()
    print(data)
    correct_transaction = TransactionResponse(**data)
    #check the categorizer
    assert  data["category"] == "groceries"


    #check refreshed balances for both users
    sender_refreshed_acc = client.get(f"/accounts/{sender_user_account["id"]}",
                                headers = sender_headers)

    assert sender_refreshed_acc.status_code == 200
    sender_acc_data = sender_refreshed_acc.json()
    assert sender_acc_data["balance"] == 300



    recipient_refreshed_acc = client.get(f"/accounts/{recipient_user_account["id"]}",
                                headers = recipient_headers)

    assert recipient_refreshed_acc.status_code == 200
    recipient_acc_data = recipient_refreshed_acc.json()
    assert recipient_acc_data["balance"] == 1200


def test_transfer_money_success_idor(client,auth_headers):

    #create users with accounts
    sender_headers = auth_headers
    sender_user_account = create_account(client,sender_headers,
                                        "checking",500)

    recipient_headers = create_user_and_login(client,"bob@example.com","Bob")

    recipient_user_account = create_account(client, recipient_headers,
                                            "checking",1000)

    #creating transaction from NOT authorized acc
    response = client.post("/transactions/10",
                           json={
                                 "recipient_iban": recipient_user_account["iban"],
                                 "recipient_name":"Bob Test",
                                 "source_account_id":sender_user_account["id"],
                                 "amount" : 200,
                                 "description" : "Rewe sagt danke"

                                },
                                headers = sender_headers
                           )
    assert response.status_code in [403, 404]


def test_deposit_cash_success(client,auth_headers):

    #create users with accounts
    sender_headers = auth_headers
    sender_user_account = create_account(client,sender_headers,
                                        "checking",500)


    response = client.post(f"/transactions/{sender_user_account["id"]}/deposit",
                           json={ "amount" : 100.0 },
                                headers = sender_headers
                           )

    assert response.status_code == 200
    data = response.json()
    valid_response = CashOperationsResponse(**data)

    sender_refreshed_acc = client.get(f"/accounts/{sender_user_account["id"]}",
                                headers = sender_headers)

    assert sender_refreshed_acc.status_code == 200
    sender_acc_data = sender_refreshed_acc.json()
    assert Decimal(sender_acc_data["balance"]) == Decimal("600")


def test_withdraw_cash_success(client, auth_headers):
    # create users with accounts
    sender_headers = auth_headers
    sender_user_account = create_account(client, sender_headers,
                                         "checking", 500)

    response = client.post(f"/transactions/{sender_user_account["id"]}/withdraw",
                           json={"amount": 100.0},
                           headers=sender_headers
                           )

    assert response.status_code == 200
    data = response.json()
    valid_response = CashOperationsResponse(**data)

    sender_refreshed_acc = client.get(f"/accounts/{sender_user_account["id"]}",
                                      headers=sender_headers)

    assert sender_refreshed_acc.status_code == 200
    sender_acc_data = sender_refreshed_acc.json()
    print(sender_acc_data)
    assert Decimal(sender_acc_data["balance"]) == Decimal("400")


def test_deposit_cash_idor(client,auth_headers):

    #create users with accounts
    sender_headers = auth_headers
    sender_user_account = create_account(client,sender_headers,
                                        "checking",500)

    wrong_headers = create_user_and_login(client,"bob@example.com","Bob")

    wrong_user_account = create_account(client, wrong_headers,
                                            "checking",1000)

    response = client.post(f"/transactions/{wrong_user_account["id"]}/deposit",
                           json={ "amount" : 100.0 },
                                headers = sender_headers
                           )

    assert response.status_code in [403, 404]



def test_withdraw_cash_idor(client, auth_headers):
    # create users with accounts
    sender_headers = auth_headers
    sender_user_account = create_account(client, sender_headers,
                                         "checking", 500)

    wrong_headers = create_user_and_login(client,"bob@example.com","Bob")

    wrong_user_account = create_account(client, wrong_headers,
                                            "checking",1000)

    response = client.post(f"/transactions/{wrong_user_account["id"]}/withdraw",
                           json={"amount": 100.0},
                           headers=sender_headers
                           )

    assert response.status_code in [403, 404]

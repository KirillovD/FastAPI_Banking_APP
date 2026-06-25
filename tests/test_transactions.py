from urllib import response

from conftest import create_user_and_login,create_account


def test_transfer_money_success(client,auth_headers):

    sender_headers = auth_headers
    sender_user_account = create_account(client,sender_headers,
                                        "Checking",500)

    recipient_headers = create_user_and_login(client,"bob@example.com","Bob")

    recipient_user_account = create_account(client, recipient_headers,
                                            "Checking",1000)

    response = client.post("/transactions/",
                           json={
                                 "recipient_acc_id": recipient_user_account["acc_id"],
                                 "recipient_name":"Bob",
                                 "source_account_id":sender_user_account["acc_id"],
                                 "transfer_amount" : 200
                                },
                                headers=auth_headers
                           )
    print(sender_headers,sender_user_account)
    assert response.status_code == 200
    data = response.json()
    assert data == {"Message": "Transfer successful!", "Amount": 200}



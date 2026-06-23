from pygments.lexers import data


def test_create_account(client, auth_headers):

    response = client.post("/accounts/",
                           json={"acc_type"  :"Savings",
                                 "acc_balance" : 1000},
                           headers=auth_headers
                           )

    assert response.status_code == 200
    data = response.json()
    assert data["acc_type"] == "Savings"
    assert data["acc_balance"] == 1000

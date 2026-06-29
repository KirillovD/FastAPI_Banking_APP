

#test function for account creation
#we use auth_headers to create and login user first
def test_create_account(client, auth_headers):

    #create savings account using token data from auth_headers
    response = client.post("/accounts/",
                           json={"type"  :"Savings",
                                 "balance" : 1000},
                           headers=auth_headers
                           )

    assert response.status_code == 200

    data = response.json()

    #see AccountResponse in schemas.py for details
    assert data["type"] == "Savings"
    assert data["balance"] == 1000
    assert "owner_id" in data
    assert "id" in data
    assert  "overdraft_limit" in data


def test_get_all_accounts(client, auth_headers):

    #we only create one account per request
    #create the first one as savings
    #use auth_headers to create and login the user and get the token
    create_savings_account = client.post("/accounts/",
                           json={"type"  :"Savings",
                                 "balance" : 1000},
                           headers=auth_headers
                           )

    assert create_savings_account.status_code == 200

    #Response should match AccountResponse in schemas.py
    create_checking_account = client.post("/accounts/",
                           json={"type"  :"Checking",
                                 "balance" : 50000},
                           headers=auth_headers
                           )

    assert create_checking_account.status_code == 200


    #now we can make get request for all accounts
    #we use user_id from the token from auth_header login to find them
    get_accounts = client.get("/accounts/",
                           headers=auth_headers
                          )

    assert get_accounts.status_code == 200

    data = get_accounts.json()

    #we get returned a list of accounts
    #as stated in the response_model in router/accounts/get
    #check the type and length
    assert isinstance(data, list)
    assert len(data) == 2

    #Response should match AccountResponse in schemas.py
    assert data[0]["type"] == "Savings"
    assert data[0]["balance"] == 1000
    assert "owner_id" in data[0]
    assert "id" in data[0]
    assert  "overdraft_limit" in data[0]

    #Response should match AccountResponse in schemas.py
    assert data[1]["type"] == "Checking"
    assert data[1]["balance"] == 50000
    assert "owner_id" in data[1]
    assert "id" in data[1]
    assert  "overdraft_limit" in data[1]


#no accounts created, will the list be empty?
def test_get_accounts_empty(client,auth_headers):
    get_accounts = client.get("/accounts/",
                              headers=auth_headers
                              )

    assert get_accounts.status_code == 200

    data = get_accounts.json()

    #we should get an empty list, no accounts created
    assert isinstance(data, list)
    assert len(data) == 0


def test_create_account_without_token(client):

    create_savings_account = client.post("/accounts/",
                           json={"type"  :"Savings",
                                 "balance" : 1000}
                           )

    #401 for not authorized, not logged in
    assert create_savings_account.status_code == 401


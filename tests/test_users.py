

def test_create_user(client):
    # create the user in the testing client
    response = client.post("/users/",
                           json={
                               "first_name" : "John",
                               "last_name" : "Test",
                               "email" : "john@example.com",
                               "password" : "securepassword123"
                           }
                 )
    #check if we get a right response code
    assert response.status_code == 200

    #time to analyze the data
    data = response.json()
    assert data["email"] == "john@example.com"
    assert data["first_name"] == "John"
    assert "user_id" in data
    #we do not want to return password in any instance
    assert "password" not in data


def test_login_user(client):

    #we have to create a new user first
    #our db only exists in the RAM during one test
    create = client.post("/users/",
                           json={
                               "first_name": "John",
                               "last_name": "Test",
                               "email": "john@example.com",
                               "password": "securepassword123"
                           }
                           )
    assert create.status_code == 200

    #now try to log in with the data from created user
    login = client.post("/auth/",
                           data={"username" : "john@example.com",
                                 "password": "securepassword123"})
    #check if the status code is correct
    assert login.status_code == 200
    #time to check the response data
    data = login.json()
    assert data["access_token"]
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert "password" not in data

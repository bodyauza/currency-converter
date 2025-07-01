# Currency Converter

<p align="center">
  <img src="https://raw.githubusercontent.com/fastapi-users/fastapi-users/master/logo.svg?sanitize=true" alt="FastAPI Users">
</p>

<p align="center">
    <em>Ready-to-use and customizable users management for <a href="https://fastapi.tiangolo.com/">FastAPI</a></em>
</p>

[![PyPI version](https://badge.fury.io/py/fastapi-users.svg)](https://badge.fury.io/py/fastapi-users)

---

**Documentation**: <a href="https://fastapi-users.github.io/fastapi-users/" target="_blank">https://fastapi-users.github.io/fastapi-users/</a>

**Source Code**: <a href="https://github.com/fastapi-users/fastapi-users" target="_blank">https://github.com/fastapi-users/fastapi-users</a>

---

## Screenshots

### Home Page

![Home Page](https://github.com/bodyauza/currency-converter/raw/master/home_page.png)

### Swagger UI

![Swagger1](https://github.com/bodyauza/currency-converter/raw/master/swagger1.png)

## Technological Stack

### Backend


### Build Tools


### Database
- **PostgreSQL**: 17.5


### Testing Tools


### Frontend
- **HTML5**, **CSS3**, **JavaScript**
- ****: 

## Authentication Process

1. **Login and Password Request**  
   The client sends a request to the server with an object containing the user's login and password.

2. **Token Generation**  
   If the entered password is correct, the server generates access and refresh tokens and returns them to the client.

3. **Using the Access Token**  
   The client uses the received access token to interact with the API. All subsequent requests to protected routes must
   include this token in the authorization header.

4. **Access Token Renewal**  
   The access token has a validity period, usually 5 minutes. When the validity of this token expires, the client sends
   the refresh token to the server and receives a new access token. This process is repeated until the refresh token
   expires.

5. **Extending the Refresh Token**  
   The refresh token is issued for 30 days. Approximately 1-5 days before the expiration of the refresh token, the
   client sends a request with valid refresh token to obtain a new pair of tokens.

## Local development

1.

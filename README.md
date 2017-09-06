# Contacts IVR

This is a python (Twisted) web-app, designed to give you phone call access to your Google Contacts address book. i.e. in the event of a flat battery or lost phone, you can call a Twilio number from another phone, authenticate with your own phone number and a pin, and then retrieve numbers from your address book or have a contact's details texted to the number you are dialling from.

## Requirements
* A [Twilio](https://www.twilio.com/) account and number
* A Google Account with contacts
* A [Google Developer Console](https://console.developers.google.com/apis) Project

## Configuration variables
You can set the application configuration in environment variables or in a .env file
in the root directory of the application.

| Name | Required | Default |
| ---- | --------- | ------- |
| TWILIO_AUTH_TOKEN | Yes | - |
| GOOGLE_API_CLIENT_ID | Yes | - |
| GOOGLE_API_CLIENT_SECRET | Yes | - |
| PORT | No | 5080 |
| IP_ADDRESS | No | 0.0.0.0 |
| HOST | Yes | |
| USE_ASTERISK | No | False |
| ASTERISK_HTTP_USER | No | - |
| ASTERISK_HTTP_PASSWORD | No | - |
| USER_FIRST_NAME | No | User |
| USER_LAST_NAME | No | - |
| USER_PHONE_NUMBER | Yes | - |
| USER_PIN_NUMBER | Yes | - |

## Installation

** In the configuration details below HOST refers to the publicly accessible URL of your running instance of this application. e.g. if the application is running at ivr.example.com and accessible on the default port 5080 via http, the HOST variable will be http://ivr.example.com:5080**

There are two options for running the contacts-ivr server:
1. Deploy to Docker using the provided Dockerfile
2. Checkout the project to your deployment location, install the requirements.txt with pip and run server.py

Configuration:
1. Create a Twilio account, with a phone number.
  * Set the incoming call webhook in Twilio to POST to HOST/twilio/handleinboundcall
  * Set the call status changes webhook in Twilio to POST to HOST/twilio/inboundcallcomplete
  * Copy your Twilio Account Auth Token and set in the contacts-ivr TWILIO_AUTH_TOKEN configuration variable.
2. Create a Google Developers Console project.
 * In the Developer Console grant the project access to the Google Contacts API.
 * In the Developer Console create 'OAuth Client ID' credentials with 'Web application' application type and specify HOST/google/auth_return as an authorised redirect URI.
 * After creating the credentials copy the Client ID and Client Secret from the Developer Console and set in the contacts-ivr GOOGLE_API_CLIENT_ID and GOOGLE_API_CLIENT_SECRET configuration variables.
3. Set the contacts-ivr HOST configuration variable.
4. Set the contacts-ivr USER_PHONE_NUMBER configuration variable to your phone number, which you will use for authentication when calling the service.
5. Set the contacts-ivr USER_PIN_NUMBER configuration variable to the PIN number you want to use for authentication when calling the service.
6. Run the service by starting the Docker container or running server.py
7. The Google authentication URL will be printed to stdout by the application, get this from the Docker logs or terminal and open in a browser. Sign in with Google and grant your Developer Console project access to your contacts. You should then be redirected back to HOST/google/auth_return and a message will be displayed showing you the number of contacts successfully synced from your account.

## Using the service

** All input via the phone keypad must be completed by pressing the # key**

1. To use the service dial your Twilio number.
2. When prompted enter your phone number (as configured above in USER_PHONE_NUMBER), followed by the # key.
3. When prompted enter your pin number (as configured above in USER_PIN_NUMBER), followed by the # key.
4. If entered correctly you will be prompted to enter the name of a contact.
5. To search for a contact press the keys that match the characters of their name you wish to search for. e.g. to search for Alex, press 2 for A, 5 for L, 3 for E and 9 for X, followed by the # key.
6. The application will list matching contacts, and you can select a particular match by clicking the relevant number followed by the # key.
7. Having selected a contact their phone numbers will be read out on the phone. You can also press 0 followed by the # key to have the contacts numbers sent via a text message to the number you are calling from.

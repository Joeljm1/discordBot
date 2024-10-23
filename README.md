# Bot Setup Instructions

This document outlines the steps to set up the bot using `pipenv` for package management and virtual environment handling.

## Prerequisites

Ensure you have Python and `pip` installed on your system.

## Installation Steps

1. **Install Pipenv**  
   If `pipenv` is not already installed, you can install it using the following command:

   pip install pipenv
2. **Create a Virtual Environment**
Open your terminal and run the following command to create a virtual environment:

   pipenv shell<br>
3. **Install Required Packages**
Use the command below to download the necessary packages specified in your Pipfile:

   pipenv install<br>
4. **Create secret.py File**
Create a file named secret.py and store your bot token in a variable called token.
For example:
   token = "tokenId here"<br>

5. **Create secret.key File**
Create a file named secret.key and store your Fernet key in it, which will be used for encryption.<br>

6. **Run the Bot**
Finally, execute the bot by running the following command:

   python bot.py
## How to run 
1. use command "/login username password" where username and password are the users lms username and password
2. if you want to change the login credentials just use the /login command and enter new username and password
3. Now use command  /startLMS to start the bot to analyse your lms calender for changes
4. The bot will notify u through dm when u have recieved a new assignemnt or any other work
   


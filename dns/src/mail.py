import smtplib
from email.message import EmailMessage
from os import environ

message = EmailMessage()
message.set_content('Testing SMTP')
message['Subject'] = 'Testing email'
message['From'] = environ["SMTP_USERNAME"]
message['To'] = environ["MAINTAINER_EMAIL"]

mailer = smtplib.SMTP_SSL(host=environ["SMTP_HOST"], port=environ["SMTP_PORT"])
mailer.login(user=environ["SMTP_USERNAME"], password=environ["SMTP_PASSWORD"])
mailer.send_message(msg=message)

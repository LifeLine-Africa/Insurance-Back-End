import smtplib

try:
    with smtplib.SMTP_SSL('smtp.gmail.com', 465, timeout=30) as server:
        server.login('SMTP_USERNAME', 'SMTP_PASSWORD')
        print("SMTP SSL connection successful")
except Exception as e:
    print(f"SMTP SSL connection failed: {str(e)}")
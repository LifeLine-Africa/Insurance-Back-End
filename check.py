import smtplib

try:
    with smtplib.SMTP_SSL('smtp.gmail.com', 465, timeout=30) as server:
        server.login('J.chukwuony@alustudent.com', 'ljol rjet wgyg fgbe')
        print("SMTP SSL connection successful")
except Exception as e:
    print(f"SMTP SSL connection failed: {str(e)}")
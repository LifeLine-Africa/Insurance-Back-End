from PIL import Image
from io import BytesIO
import base64

# Open and convert image to base64
with Image.open("Logo.png") as img:
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    img_base64 = base64.b64encode(buffer.getvalue()).decode()

# Save base64 string to a text file
with open("logo_base64.txt", "w") as f:
    f.write(img_base64)

print("✅ logo_base64.txt has been created successfully!")
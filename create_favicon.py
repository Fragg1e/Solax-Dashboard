from PIL import Image, ImageDraw
import os

# Create a 32x32 image with a transparent background
img = Image.new("RGBA", (32, 32), (0, 0, 0, 0))
draw = ImageDraw.Draw(img)

# Draw a simple sun icon
# Outer circle (sun)
draw.ellipse([4, 4, 28, 28], fill="#FFD700")  # Gold color
# Inner circle (face)
draw.ellipse([8, 8, 24, 24], fill="#FFA500")  # Orange color

# Save as ICO
if not os.path.exists("static/img"):
    os.makedirs("static/img")
img.save("static/img/favicon.ico", format="ICO")

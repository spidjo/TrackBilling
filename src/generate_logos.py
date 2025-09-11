from PIL import Image, ImageDraw, ImageFont
import os

# Create output directory
os.makedirs('logos', exist_ok=True)

# Generate Alpha logo
alpha_img = Image.new('RGB', (200, 200), 'white')
draw = ImageDraw.Draw(alpha_img)
draw.polygon([(100, 50), (50, 150), (150, 150)], fill='blue')
draw.rectangle([(85, 150), (115, 180)], fill='blue')
alpha_img.save('assets/alpha.png')

# Generate Beta logo
beta_img = Image.new('RGB', (200, 200), 'white')
draw = ImageDraw.Draw(beta_img)
draw.ellipse([(50, 50), (150, 150)], outline='green', width=10)
draw.ellipse([(50, 100), (150, 200)], outline='green', width=10)
beta_img.save('assets/beta.png')

# Generate Gamma logo
gamma_img = Image.new('RGB', (200, 200), 'white')
draw = ImageDraw.Draw(gamma_img)
draw.arc([(50, 50), (150, 150)], 270, 90, fill='red', width=10)
draw.line([(100, 50), (100, 150)], fill='red', width=10)
gamma_img.save('assets/gamma.png')

print("Logos generated in 'assets' directory")
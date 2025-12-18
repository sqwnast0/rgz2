from PIL import Image, ImageDraw, ImageFont
import os

# Создаем иконку 32x32
size = 32
img = Image.new('RGBA', (size, size), (52, 152, 219, 255))  # Синий фон
draw = ImageDraw.Draw(img)

# Рисуем простой склад
# Здание
draw.rectangle([8, 10, 24, 22], fill=(44, 62, 80, 255), outline=(255, 255, 255, 255))
# Дверь
draw.rectangle([13, 12, 19, 18], fill=(255, 255, 255, 255))
# Крыша
draw.polygon([8, 10, 16, 5, 24, 10], fill=(231, 76, 60, 255))

# Создаем папки если их нет
os.makedirs('static/favicon', exist_ok=True)

# Сохраняем как ICO (для простоты сохраняем как PNG и переименовываем)
img.save('static/favicon/favicon.ico', format='ICO', sizes=[(32, 32)])
print("✅ Favicon создан в static/favicon/favicon.ico")
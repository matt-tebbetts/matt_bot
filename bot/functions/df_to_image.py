import pandas as pd
from PIL import Image, ImageDraw, ImageFont
from bot.connections.config import FONT_PATH
from bot.functions.admin import direct_path_finder
import platform
import os
# returns the image filepath
def df_to_image(df, 
                                 img_filepath='files/images/leaderboard.png', 
                                 img_title="Today's Mini", 
                                 img_subtitle="Leaderboard",
                                 left_aligned_columns=['Game', 'Name', 'Player', 'Genre'],
                                 right_aligned_columns=['Rank', 'Time', 'Score','Points', 'Wins',
                                                        'Top 3', 'Top 5', 'Played', 'Games', 
                                                        'Scores Added', 'Avg', '1st', '2nd', '3rd', '4th', '5th']):

    # Ensure the image filepath uses the proper absolute path
    if not os.path.isabs(img_filepath):
        # Convert relative path to absolute using direct_path_finder
        # Split the relative path into components
        path_parts = img_filepath.split('/')
        img_filepath = direct_path_finder(*path_parts)
    
    # Ensure the directory exists
    os.makedirs(os.path.dirname(img_filepath), exist_ok=True)

    # Set colors
    header_bg_color = '#4a4e53'
    row_bg_color = '#2c2f33'
    text_color = 'white'
    title_color = 'white'
    subtitle_color = '#a0a0a0'  # Color for the subtitle
    border_color = '#a0a0a0'
    padding = 8

    # Determine the font path based on the operating system
    if platform.system() == 'Windows':
        font_path = 'C:/Windows/Fonts/arial.ttf'
    elif platform.system() == 'Darwin':  # macOS
        font_path = '/Library/Fonts/Arial.ttf'
    else:  # linux on remote
        font_path = '/usr/share/fonts/truetype/ARIAL.TTF'  # Using uppercase as it was working before

    font_size = 18
    font = ImageFont.truetype(FONT_PATH, font_size)

    # Temporary image and draw object for calculating column widths
    temp_img = Image.new('RGB', (1, 1))
    temp_draw = ImageDraw.Draw(temp_img)
    
    # calculate row height
    row_height = font.getbbox('A')[3] + 2 * padding

    # old col widths calculation
    #col_widths = [max(temp_draw.textlength(str(max(df[col].tolist() + [col], key=lambda x: len(str(x)))), font) for col in df.columns) + 2 * padding for col in df.columns]

    # new col widths calculation    
    col_widths = [max(temp_draw.textlength(str(x), font) for x in df[col].tolist() + [col]) + 2 * padding for col in df.columns]
    
    # Create a new image
    img_width = sum(col_widths)
    img_height = (len(df) + 2) * row_height + row_height  # Add an extra row for the title
    img = Image.new('RGB', (int(img_width), int(img_height)), row_bg_color)
    draw = ImageDraw.Draw(img)

    # Draw title
    title_width = draw.textlength(img_title, font)
    title_height = font.getbbox('A')[1]
    draw.text(((img_width - title_width) // 2, padding), img_title, font=font, fill=title_color)

    # Draw subtitle with word wrapping
    max_subtitle_width = img_width - 2 * padding  # Leave some padding on both sides
    words = img_subtitle.split()
    lines = []
    current_line = []
    
    for word in words:
        test_line = ' '.join(current_line + [word])
        if draw.textlength(test_line, font) <= max_subtitle_width:
            current_line.append(word)
        else:
            if current_line:
                lines.append(' '.join(current_line))
            current_line = [word]
    if current_line:
        lines.append(' '.join(current_line))
    
    # Draw each line of the subtitle
    subtitle_y = padding + title_height + row_height
    for line in lines:
        line_width = draw.textlength(line, font)
        draw.text(((img_width - line_width) // 2, subtitle_y), line, font=font, fill=subtitle_color)
        subtitle_y += font.getbbox('A')[3]  # Move down by line height

    # Draw header
    x, y = 0, subtitle_y + padding  # Adjust y position based on wrapped subtitle
    for col, width in zip(df.columns, col_widths):
        draw.rectangle([x, y, x + width, y + row_height], fill=header_bg_color)
        text_x = x + padding  # Left-align by default
        if col not in left_aligned_columns:
            text_x = x + width - temp_draw.textlength(str(col), font) - padding  # Right-align if not in left_aligned_columns
        draw.text((text_x, y + padding), col, font=font, fill=text_color)
        x += width

    # Draw rows
    y += row_height
    for _, row in df.iterrows():
        x = 0
        for col, width in zip(df.columns, col_widths):
            # Draw cell borders
            draw.rectangle([x, y, x + width, y + row_height], outline=border_color)

            # Text alignment
            text_value = str(row[col])
            text_width = draw.textlength(text_value, font)
            text_x = x + padding  # Left-align by default
            if col not in left_aligned_columns:
                text_x = x + width - text_width - padding  # Right-align if not in left_aligned_columns

            draw.text((text_x, y + padding), text_value, font=font, fill=text_color)
            x += width
        y += row_height

    img.save(img_filepath)
    
    return img_filepath
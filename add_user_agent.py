#!/usr/bin/env python

import re

# Define the User-Agent header we want to add
user_agent_line = "                    self.send_header('User-Agent', 'DiscordBot (https://github.com/ltfschoen/opengov-bot, 1.0)')"

# Path to the verify_endpoint.py file
file_path = '/Users/luke/code/clones/github/ltfschoen/opengov-bot/verify_endpoint.py'

# Read the file content
with open(file_path, 'r') as file:
    content = file.read()

# Pattern to match response code sections that need the User-Agent header
# Look for send_header('Content-Type'...) followed by end_headers() without User-Agent in between
pattern = r"(self\.send_header\('Content-Type'[^)]+\))\n([^U]+?)(self\.end_headers\(\))"

# Function to add the User-Agent header after Content-Type
def add_user_agent(match):
    content_type_header = match.group(1)
    middle_text = match.group(2)
    end_headers = match.group(3)
    
    # Check if User-Agent is already present
    if "User-Agent" in middle_text:
        return match.group(0)
    
    # Calculate the indentation level
    indentation = ""
    for char in content_type_header:
        if char == ' ':
            indentation += ' '
        else:
            break
    
    # Create User-Agent header with correct indentation
    user_agent = indentation + "self.send_header('User-Agent', 'DiscordBot (https://github.com/ltfschoen/opengov-bot, 1.0)')"
    
    return f"{content_type_header}\n{user_agent}\n{middle_text}{end_headers}"

# Apply the substitution
modified_content = re.sub(pattern, add_user_agent, content, flags=re.DOTALL)

# Write the modified content back to the file
with open(file_path, 'w') as file:
    file.write(modified_content)

print("User-Agent header added to all necessary response sections in verify_endpoint.py")

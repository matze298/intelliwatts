#!/usr/bin/env bash
set -euo pipefail

# Ensure the static directory exists for serving assets
mkdir -p app/static

# Check if npm is available and ask user to install if not
if ! command -v npm >/dev/null 2>&1; then
  # Ask user if npm shall be installed 
  read -p "npm not found. Would you like to install it now? (y/N): " -n 1 -r
  echo
  if [[ $REPLY =~ ^[Yy]$ ]]; then
    curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.4/install.sh | bash
    source ~/.bashrc
    nvm install --lts
  else
    # Exit with info
    echo "npm is required to build Tailwind CSS. Please install npm and try again."
    exit 1
  fi
fi

echo "Building initial Tailwind CSS for Retro theme..."
# Iterate over all available styles in ./app/static
for style_file in ./app/static/style-*.css; do
  # Extract the theme name (e.g., 'retro' from 'style-retro.css')
  theme_name=$(basename "$style_file" .css | sed 's/style-//')
  echo "Building Tailwind CSS for $theme_name theme..."
  npx @tailwindcss/cli -i "$style_file" -o "./app/static/tailwind-$theme_name.css"
done

echo "CSS themes built successfully ✔"
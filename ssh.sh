#!/usr/bin/env bash

# Display help message if --help is provided
if [[ "$1" == "--help" ]]; then
  echo -e "Usage: $0 <your_email@example.com>\n"
  echo "Generates an SSH key using id_ed25519 with no passphrase."
  echo "Attempts to copy the public key to the clipboard."
  echo "Ensure you have disk encryption enabled for security. (You do have it enabled already, right? 🤨)"
  exit 0
fi

# Retrieve the Git email
git_email=$(git config --get user.email)

# Check if the Git email is set
if [ -z "$git_email" ]; then
  echo -e "Git email not found. Please set your Git email using:\n"
  echo "git config --global user.email \"your_email@example.com\""
  exit 1
fi

# Generate a new SSH key
ssh-keygen -t ed25519 -C "$git_email" -f ~/.ssh/id_ed25519 -N ""

# Set permissions for the private key
chmod 600 ~/.ssh/id_ed25519

# Display the public key
public_key=$(cat ~/.ssh/id_ed25519.pub)
echo "Your new SSH public key is:"

# Try to copy to clipboard
if command -v xclip &> /dev/null; then
    echo "$public_key" | xclip -selection clipboard
    echo "Public key copied to clipboard."
elif command -v pbcopy &> /dev/null; then
    echo "$public_key" | pbcopy
    echo "Public key copied to clipboard."
else
    echo "$public_key"
    echo "Clipboard command not found. Displaying public key instead."
fi

# Add the SSH key as a signing key for Git
git config --global user.signingkey "$(cat ~/.ssh/id_ed25519)"
echo "SSH key added as the signing key for Git."

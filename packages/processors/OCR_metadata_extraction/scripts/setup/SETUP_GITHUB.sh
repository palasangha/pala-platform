#!/bin/bash
# GitHub Setup Script for GVPOCR
# Run this script to install GitHub CLI and push your code

echo "=== Installing GitHub CLI ==="
curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg | sudo dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg
sudo chmod go+r /usr/share/keyrings/githubcli-archive-keyring.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | sudo tee /etc/apt/sources.list.d/github-cli.list > /dev/null
sudo apt update
sudo apt install gh -y

echo ""
echo "=== GitHub CLI installed successfully! ==="
echo ""
echo "Now let's authenticate and create your repository..."
echo ""

# Authenticate with GitHub
gh auth login

echo ""
echo "=== Creating GitHub repository and pushing code ==="
echo ""

# Create repository and push
gh repo create gvpocr --public --source=. --remote=origin --push --description "Enterprise OCR Application with Flask backend, React frontend, and Google Cloud Vision API integration"

echo ""
echo "=== Done! ==="
echo "Your code has been pushed to GitHub!"
echo ""
echo "View your repository:"
gh repo view --web

<!-- START doctoc generated TOC please keep comment here to allow auto update -->
<!-- DON'T EDIT THIS SECTION, INSTEAD RE-RUN doctoc TO UPDATE -->
**Table of Contents**  *generated with [DocToc](https://github.com/thlorenz/doctoc)*

- [MoneyManager Installation Guide](#moneymanager-installation-guide)
  - [Installation Steps](#installation-steps)
  - [Fill in the config](#fill-in-the-config)
  - [Running the Project for Development](#running-the-project-for-development)
  - [Development Notes](#development-notes)

<!-- END doctoc generated TOC please keep comment here to allow auto update -->

# MoneyManager Installation Guide

Welcome to the **MoneyManagerV2** project! This guide will help you set up the environment and install dependencies to get started.

## Installation Steps

1. **Clone the Repository**

Begin by cloning the repository to your local machine:

```bash
git clone https://github.com/your-username/MoneyManagerV2.git
cd MoneyManagerV2
```

1. **Install Package Manager for Python**

Install `uv`:

```bash
pip install uv
```

Create a virtual environment:

```bash
uv venv
```

Activate the virtual environment:

```bash
source .venv/bin/activate
```

> [!NOTE]
> If you are using fish shell (like me), you can activate the virtual environment using:
> ```bash
> source .venv/bin/activate.fish
> ```
>  You can deactivate the virtual environment using:
> ```bash
> deactivate
> ```


## Fill in the config

Before running the application, you need to set up the necessary configurations in the config.py file. Follow these steps:

- **Create a bot and get its token:** Set up a bot using the Telegram Bot API, and obtain the API token required to integrate the bot with the application.
- **Create a Gmail account and get the app password:** Generate an app-specific password for Gmail to enable email functionality securely.
- **Set up a MongoDB database and get the connection token:** Create a MongoDB cluster or database, and retrieve the connection string/token for the database.

Ensure you replace the placeholder values in config.py with the actual credentials and tokens for these services.

## Running the Project for Development

1. **Install tmux**

If you don't have tmux installed, you can install it using:

```bash
sudo apt install tmux # For Ubuntu
brew install tmux # For MacOS
sudo pacman -S tmux # For Arch Linux
```

Run the development script:

```
scripts/dev.sh
```

It should open a new tmux session with the application running in the first window and the bot running in the second window.

## Development Notes

Please install pre-commit hooks to ensure code quality and consistency:

```bash
uv run pre-commit install
```

To run the tests:

```bash
uv run pytest
```

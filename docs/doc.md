<!-- START doctoc generated TOC please keep comment here to allow auto update -->
<!-- DON'T EDIT THIS SECTION, INSTEAD RE-RUN doctoc TO UPDATE -->
**Table of Contents**  *generated with [DocToc](https://github.com/thlorenz/doctoc)*

- [Money Manager Telegram Bot Documentation](#money-manager-telegram-bot-documentation)
  - [Overview](#overview)
  - [Private Chat](#private-chat)
    - [/start](#start)
    - [/menu](#menu)
    - [/login](#login)
    - [/signup](#signup)
    - [/expenses_add](#expenses_add)
    - [/expenses_view](#expenses_view)
    - [/expenses_delete](#expenses_delete)
    - [/categories_view](#categories_view)
    - [/categories_add](#categories_add)
    - [/categories_delete](#categories_delete)
    - [/analytics](#analytics)
    - [/exports](#exports)
  - [Group Chat](#group-chat)
    - [/menu](#menu-1)
    - [/bill_split](#bill_split)
    - [/bill_split_status](#bill_split_status)
    - [/bill_split_proceed](#bill_split_proceed)
    - [/cancel](#cancel)
  - [Notes](#notes)

<!-- END doctoc generated TOC please keep comment here to allow auto update -->


# Money Manager Telegram Bot Documentation

This documentation provides detailed information about the commands available in the Money Manager Telegram Bot.

## Overview
The Money Manager Bot is designed to assist users with managing their personal finances, including tracking expenses, managing categories, and generating analytics. Each command in the bot has a specific purpose, inputs, outputs, and associated notes.

---

## Private Chat

### /start
**Functionality:** Initiates the bot and displays a welcome message along with available commands.
**Inputs:** None.
**Outputs:** A message displaying available commands.
**Notes:** Requires no authentication. Ideal for first-time users.

### /menu
**Functionality:** Displays a list of all available commands grouped by categories.
**Inputs:** None.
**Outputs:** A categorized command menu.
**Notes:** Users should be logged in to access personalized commands.

---

### /login
**Functionality:** Starts the login process for existing users.
**Inputs:** Username and password (via messages).
**Outputs:** Login confirmation or error message.
**Notes:** Users must have a valid account.

### /signup
**Functionality:** Starts the signup process for new users.
**Inputs:** Username and password (via messages).
**Outputs:** Account creation confirmation or error message.
**Notes:** Users must choose a unique username.

---

### /expenses_add
**Functionality:** Begins the process to add a new expense.
**Inputs:** Amount, description, category, currency, and date (optional).
**Outputs:** Confirmation of successful expense addition or an error message.
**Notes:** Requires authentication. Sends an alert if the expense makes user go over budget in category.

### /expenses_view
**Functionality:** Displays a paginated list of all expenses.
**Inputs:** Page number (optional).
**Outputs:** A formatted list of expenses with pagination controls.
**Notes:** Users can navigate through multiple pages using inline buttons.

### /expenses_delete
**Functionality:** Initiates the process to delete an expense.
**Inputs:** Selected expense to delete.
**Outputs:** Confirmation of successful deletion or error message.
**Notes:** Requires user confirmation.

---

### /categories_view
**Functionality:** Displays a list of all expense categories.
**Inputs:** None.
**Outputs:** A formatted list of categories with their budgets.
**Notes:** Categories are shown with pagination.

### /categories_add
**Functionality:** Begins the process to add a new category.
**Inputs:** Category name and monthly budget.
**Outputs:** Confirmation of successful category addition or error message.
**Notes:** Budgets are set in the default currency.

### /categories_delete
**Functionality:** Initiates the deletion of a category.
**Inputs:** Selected category to delete.
**Outputs:** Confirmation of deletion or error message.
**Notes:** Users must confirm before deletion.

---

### /analytics
**Functionality:** Provides options to view various analytics, such as bar charts and pie charts.
**Inputs:** Selected chart type (via buttons).
**Outputs:** Displays a chart or an error message.
**Notes:** Data for the charts is fetched from the user’s account.

### /exports
**Functionality:** Allows users to export their data in various formats.
**Inputs:** Date range (optional) and file format (CSV, PDF, Excel).
**Outputs:** File download or email confirmation.
**Notes:** Users can export data for specific date ranges.

---

## Group Chat

### /menu
**Functionality:** Displays a list of all available commands grouped by categories.
**Inputs:** None.
**Outputs:** A categorized command menu.
**Notes:** Users should be logged in to access personalized commands.

### /bill_split
**Functionality:** Initiates the process to split a bill among group members.
**Inputs:** Total bill amount, number of members, and their names.
**Outputs:** Individual share amounts for each member, the states of confirmations, the result of the bill split.
**Notes:** Requires user authentication.

### /bill_split_status
**Functionality:** Displays the current status of the bill split.
**Inputs:** None.
**Outputs:** Current status of the bill split.
**Notes:** Does not require user authentication.

### /bill_split_proceed
**Functionality:** Proceeds with the bill split manually.
**Inputs:** None.
**Outputs:** Confirmation of the bill split or an error message.
**Notes:** Requires user confirmation.

### /cancel
**Functionality:** Cancels the group bill split transaction.
**Inputs:** None.
**Outputs:** Confirmation of the cancellation or an error message.
**Notes:** Requires user confirmation.

---

## Notes
- All commands that modify data require user authentication.
- Commands are designed with user interaction in mind, providing inline buttons where applicable.
- Data integrity and privacy are ensured via secure APIs.

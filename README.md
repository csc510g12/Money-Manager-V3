<!-- START doctoc generated TOC please keep comment here to allow auto update -->
<!-- DON'T EDIT THIS SECTION, INSTEAD RE-RUN doctoc TO UPDATE -->
**Table of Contents**  *generated with [DocToc](https://github.com/thlorenz/doctoc)*

- [Money Manager](#money-manager)
  - [👥 Functionality](#-functionality)
  - [👨‍💻 Developer Friendly](#%E2%80%8D-developer-friendly)
  - [🛠️ Installation and Dev](#-installation-and-dev)
  - [👨‍💻 Screenshots of Functionalities](#%E2%80%8D-screenshots-of-functionalities)
  - [🤝 Contributing](#-contributing)
  - [📜 Code of Conduct](#-code-of-conduct)
  - [🔦 Support](#-support)

<!-- END doctoc generated TOC please keep comment here to allow auto update -->

# Money Manager

<div align="center">
  <img src="docs/logo/logo.png" alt="Project Logo" width="300"/>
  <img src="http://ForTheBadge.com/images/badges/built-with-love.svg">
</div>
A REST API application for managing expenses. Build your own automation—be it a Telegram bot 🤖, Discord bot, or your own app 📱! Now includes WebAPI and a telegram bot.

![license](https://img.shields.io/github/license/csc510g12/project2?style=plastic&) [![DOI](https://zenodo.org/badge/928521002.svg)](https://doi.org/10.5281/zenodo.14927596)

📽️ Introducing Money Manager

- [Introduction animation](./introduction.mp4)
- [New features in V3](https://drive.google.com/file/d/1nqmDwzc6p4Lfe2XhXx-rge31Epu6TpOF/view?usp=sharing)

✅ Quality

[![Pre-commit](https://github.com/csc510g12/project2/actions/workflows/pre-commit.yml/badge.svg)](https://github.com/csc510g12/project2/actions/workflows/pre-commit.yml) [![Pytest](https://github.com/csc510g12/project2/actions/workflows/pytest.yml/badge.svg)](https://github.com/csc510g12/project2/actions/workflows/pytest.yml) [![codecov](https://codecov.io/gh/csc510g12/Money-Manager-V3/graph/badge.svg?token=HxVOHc7Prp)](https://codecov.io/gh/csc510g12/project2) [![badge_total_tests](https://img.shields.io/badge/tests-218-blue?style=plastic&logo=pytest&logoColor=white)](https://github.com/csc510g12/project2/tree/main/tests)


Code coverage graph:

![CodeCovGraph](https://codecov.io/gh/csc510g12/Money-Manager-V3/graphs/icicle.svg?token=HxVOHc7Prp)

📊 Stats

![pr_open](https://img.shields.io/github/issues-pr/csc510g12/project2?style=plastic&) ![pr_close](https://img.shields.io/github/issues-pr-closed/csc510g12/project2?style=plastic&) ![issue_open](https://img.shields.io/github/issues/csc510g12/project2.svg?style=plastic&) ![issue_close](https://img.shields.io/github/issues-closed/csc510g12/project2.svg?style=plastic&)
![commits_since_last_project](https://img.shields.io/github/commits-since/csc510g12/project2/0.1.0.svg?style=plastic&) ![repo_size](https://img.shields.io/github/repo-size/csc510g12/project2?style=plastic&) ![forks](https://img.shields.io/github/forks/csc510g12/project2?style=plastic&) ![stars](https://img.shields.io/github/stars/csc510g12/project2?style=plastic&)

🛠️ Tools & Technologies

[![Python](https://img.shields.io/badge/python%203.12-3670A0?logo=python&logoColor=ffdd54)](https://www.python.org/downloads/release/python-3121/) [![MongoDB](https://img.shields.io/badge/MongoDB-%234ea94b.svg?logo=mongodb&logoColor=white)](https://www.mongodb.com/) [![FastAPI](https://img.shields.io/badge/FastAPI-009485.svg?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/) [![Docker](https://img.shields.io/badge/Docker-2496ED?logo=docker&logoColor=fff)](https://www.docker.com/) [![GitHub](https://img.shields.io/badge/github-%23121011.svg?logo=github&logoColor=white)](https://github.com/) [![GitHub Actions](https://img.shields.io/badge/github%20actions-%232671E5.svg?logo=githubactions&logoColor=white)](https://github.com/features/actions) [![Linux](https://img.shields.io/badge/Linux-FCC624?logo=linux&logoColor=black)](https://www.linux.org/) [![Telegram](https://img.shields.io/badge/Telegram-2CA5E0?logo=telegram&logoColor=white)](https://telegram.org/) [![ChatGPT](https://img.shields.io/badge/ChatGPT-74aa9c?logo=openai&logoColor=white)](https://chatgpt.com/) [![Visual Studio Code](https://img.shields.io/badge/Visual%20Studio%20Code-0078d7.svg?logo=visual-studio-code&logoColor=white)](https://code.visualstudio.com/)

---

## 👥 Functionality

- **Expense Tracking**: Add, update, and delete expenses. Track expenses by category, date, and account.
- **Authentication**: Secure access to your data using token-based authentication.
- **RESTful API**: Access and interact with your financial data programmatically via a FastAPI-powered API.
- **Data Visualization**: View your expenses over time with customizable charts, including:
  - Monthly and weekly spending trends
  - Categorical expense breakdowns
- **Multiple Accounts**: Manage multiple accounts like spending and saving.

## 👨‍💻 Developer Friendly

- **Modular Configuration**: Simplify setup with a sample_config.py file that supports environment variables for secure, customizable settings like database URIs, API ports, and bot tokens—just rename and update, or export values directly from your environment!
- **Stable Release(master) Branch**: We have Pre-commit running as github workflows which allows only the tested, formatted, linted, checked, code to push to the release branches
- **Comprehensive Test Suite**: With over 150 testcases in unit test suite, developer can easily extend and follow Test Driven Development.
- **>95% Code coverage**: Well, almost all the lines of the code is covered in the unit test suite. Extend without worrying about what'll break the current functionality.
- **Testing Suite**: Comprehensive tests to ensure stability and reliability across key functionality.

## 🛠️ Installation and Dev

Refer to [INSTALL](INSTALL.md) for the guidance and follow the steps.

## 👨‍💻 Screenshots of Functionalities

| What                   | Screenshot                                                                                                                    | What                  | Screenshot                                                                                                                    | What                    | Screenshot                                                                                                                    |
| ---------------------- | ----------------------------------------------------------------------------------------------------------------------------- | --------------------- | ----------------------------------------------------------------------------------------------------------------------------- | ----------------------- | ----------------------------------------------------------------------------------------------------------------------------- |
| **Sign Up**            | <img src="https://github.com/user-attachments/assets/76c7867b-81ae-4be3-a73a-9e08e0cda8b3" alt="Sign Up" width="200"></br>    | **Login**             | <img src="https://github.com/user-attachments/assets/94daf731-9ce0-4ef6-8797-54ede9ac9713" alt="Login" width="200"></br>      | **Add Expenses**        | <img src="https://github.com/user-attachments/assets/38206a69-68f9-4b1f-b25b-c6853ab90894" alt="Expenses" width="200"></br>   |
| **Different Currency** | <img src="https://github.com/user-attachments/assets/816367c0-e145-4334-af23-97614b9cb1bd" alt="Expenses" width="200"></br>   | **Multiple Accounts** | <img src="https://github.com/user-attachments/assets/716f301f-dee6-4fbf-a890-25d0edf1994b" alt="Expenses" width="200"></br>   | **View Expenses**       | <img src="https://github.com/user-attachments/assets/b54b9329-d2de-4386-8b4c-7c2437b3273e" alt="Expenses" width="200"></br>   |
| **Update Expenses**    | <img src="https://github.com/user-attachments/assets/4ad39895-8f66-4e1c-9c3f-8c67c0b735bf" alt="Expenses" width="200"></br>   | **Delete Expenses**   | <img src="https://github.com/user-attachments/assets/6e981ef7-a094-4c1b-835e-3114776c985f" alt="Expenses" width="200"></br>   | **Delete All Expenses** | <img src="https://github.com/user-attachments/assets/a1962ccb-81c9-45c9-9edf-6f57acb7e632" alt="Expenses" width="200"></br>   |
| **Add Categories**     | <img src="https://github.com/user-attachments/assets/ca18b4a7-bbfc-4b79-8c31-aad577fa15bf" alt="Categories" width="200"></br> | **View Categories**   | <img src="https://github.com/user-attachments/assets/1273770e-83f2-4c0f-9109-58cdb3c4f987" alt="Categories" width="200"></br> | **Update Categories**   | <img src="https://github.com/user-attachments/assets/73d693fc-8967-4bf6-9052-1b3018cdfc64" alt="Categories" width="200"></br> |
| **Delete Categories**  | <img src="https://github.com/user-attachments/assets/7a4feab0-d8d5-49be-97ce-d291cbc12fb0" alt="Categories" width="200"></br> | **Add Accounts**      | <img src="https://github.com/user-attachments/assets/c6bdb2d8-0bd3-45f6-b237-be0dd4b2e8f8" alt="Accounts" width="200"></br>   | **View Accounts**       | <img src="https://github.com/user-attachments/assets/f86b08cb-aae0-4e1c-9076-67274587f288" alt="Accounts" width="200"></br>   |
| **Update Accounts**    | <img src="https://github.com/user-attachments/assets/294f0b80-7883-4c93-9967-c37a16a4cddf" alt="Accounts" width="200"></br>   | **Delete Accounts**   | <img src="https://github.com/user-attachments/assets/18870a19-eb0e-4cdd-84ff-cbd1b4cccfab" alt="Accounts" width="200"></br>   | **Analytics**           | <img src="https://github.com/user-attachments/assets/c30c1c10-b4c5-4947-affe-88a59f608839" alt="Analytics" width="200"></br>  |
| **Export Range**       | <img src="https://github.com/user-attachments/assets/e80f74ce-9417-4403-8c4a-fc1d3c3338b8" alt="Exports" width="200"></br>    | **Export Format**     | <img src="https://github.com/user-attachments/assets/35f20478-429e-4100-b163-558ab11e91f0" alt="Exports" width="200"></br>    |**Group Level Commands** | <img src="https://github.com/user-attachments/assets/c0f189f9-c0b0-4716-9bea-0072545a7423" alt="Group Level Commands" width="200"></br> |
| **Issue Group Bill Split**              | <img src="https://github.com/user-attachments/assets/e02ffaa4-6e7d-4501-9656-80d1cc435ea6" alt="Cancel" width="200"></br> | **Group Level transaction Status** | <img src="https://github.com/user-attachments/assets/b02f10d8-de27-4fe5-a202-7e1858b3befb" alt="Group Level transaction Status" width="200"></br> | **Group Transfer** | <img src="https://github.com/user-attachments/assets/47403736-4330-4da3-a004-3aac3c63f21a" alt="Transfer" width="200"></br> |
| **Cancel Group Level Transaction** | <img src="https://github.com/user-attachments/assets/0d974e6a-e5d5-4881-9b4c-34ed2ef38e31" alt="Cancel" width="200"></br> | **Budget Alert** | <img src="https://github.com/user-attachments/assets/d8f7b514-512c-464a-bc80-551c897a623c" alt="Budget Alert" width="200"></br> | **Transfer Between Accounts** | <img src="https://github.com/user-attachments/assets/bec18a00-f19d-4e05-b5ee-b9df85f28dfb" alt="Transfer Between Accounts" width="200"></br> |

## 🔮 Future Features

- **Transaction Roll Back**: Allow users to roll back transactions incase of misinputs.
- **Shared Group Account**: Allow users in a group to create a shared bank account and keep track of group funds.
- **Recurring Expenses**: Allow users to set up recurring expenses.
- **Expense Remdiners**: Will notify users of upcoming payments and deadlines.
- **Reports**: Generate customized reports about spending habits.
- **AI-driven Insights**: Use AI to analyze spending reports and generate personalized tips.

## 🤝 Contributing

Thank you for your interest in contributing to MoneyManager! Your contributions are greatly appreciated, and this guide will help you get started. For full details on contributing, please refer to the [CONTRIBUTING.md](CONTRIBUTING.md) file, which provides comprehensive instructions and guidelines.

## 📜 Code of Conduct

Please note that we have a [Code of Conduct](CODE_OF_CONDUCT.md) that all contributors are expected to uphold. This ensures that our community remains welcoming and inclusive for everyone.

## 🔦 Support

If you have any questions or need assistance, please feel free to reach out. You can contact us via email at `mmv3 @ 550w . host` (remove spaces) or through our [GitHub Discussions](https://github.com/csc510g12/project2/discussions).

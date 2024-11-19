import logging

import helper
from matplotlib import pyplot as plt
from telebot import types


def run(message, bot):
    markup = types.ReplyKeyboardMarkup(one_time_keyboard=True)
    options = helper.getIncomeOrExpense()
    markup.row_width = 2
    for c in options.values():
        markup.add(c)
    msg = bot.reply_to(message, "Select Income or Expense", reply_markup=markup)
    bot.register_next_step_handler(msg, post_type_selection, bot)


def post_type_selection(message, bot):
    try:
        helper.read_json()
        chat_id = message.chat.id
        selectedType = message.text
        user_history = helper.getUserHistory(chat_id, selectedType)
        print(user_history)
        message = "Alright. I just created a pdf of your " + selectedType + " history!"
        bot.send_message(chat_id, message)
        fig = plt.figure()
        ax = fig.add_subplot(1, 1, 1)
        top = 0.8
        if user_history is None or (len(user_history) == 0):
            plt.text(
                0.1,
                top,
                "No record found!",
                horizontalalignment="left",
                verticalalignment="center",
                transform=ax.transAxes,
                fontsize=20,
            )
        for rec in user_history:
            date, category, amount = rec.split(",")
            date, time = date.split(" ")
            print(date, category, amount)
            if selectedType == "Income":
                rec_str = f"{amount}$ {category} income on {date} at {time}"
            else:
                rec_str = f"{amount}$ {category} expense on {date} at {time}"
            plt.text(
                0,
                top,
                rec_str,
                horizontalalignment="left",
                verticalalignment="center",
                transform=ax.transAxes,
                fontsize=14,
                bbox=dict(facecolor="red", alpha=0.3),
            )
            top -= 0.15
        plt.axis("off")
        plt.savefig("history.pdf")
        plt.close()
        bot.send_document(chat_id, open("history.pdf", "rb"))
    except Exception as e:
        logging.exception(str(e))
        bot.reply_to(message, "Oops!" + str(e))

from twitch import TwitchClient
import telegram
from telegram.ext import Updater, CommandHandler, Job
import shelve
import logging
import settings
from requests.exceptions import HTTPError

# Глобальные переменные
db = shelve.open("database.db")
twitch = TwitchClient(client_id=settings.twitch_client_id)

# команды
def commStart(bot, update):
    update.message.reply_text("Используй /help для справки")

def commAdd(bot, update, args):
    chat_id = update["message"]["chat"]["id"]

    try:
        username = args[0]
    except IndexError:
        update.message.reply_text("Используй /add <username>")
        return

    try:
        userid = twitch.users.translate_usernames_to_ids(username)[0]["id"]
    except IndexError:
        update.message.reply_text('Пользователь {0} не найден на Twitch'.format(username))
        return
    except HTTPError:
        update.message.reply_text('Временные проблемы с Twitch... попробуйте позже.')
        return

    listChatIds = db.get(userid, [username])
    if chat_id in listChatIds:
        bot.send_message(chat_id=chat_id,
                text='Пользователь  <a href="https://www.twitch.tv/{0}">{0}</a> уже добавлен'.format(username),
                parse_mode=telegram.ParseMode.HTML)
        return

    listChatIds.append(chat_id)
    db[userid] = listChatIds

    bot.send_message(chat_id=chat_id,
            text='Пользователь  <a href="https://www.twitch.tv/{0}">{0}</a> успешно добавлен'.format(username),
            parse_mode=telegram.ParseMode.HTML)

def commDel(bot, update, args):
    chat_id = update["message"]["chat"]["id"]

    try:
        username = args[0]
    except KeyError:
        update.message.reply_text("Используй /del <username>")
        return

    for userid in db.keys():
        if username == db[userid][0]:
            if chat_id in db[userid]:
                listChatIds = db[userid]
                listChatIds.remove(chat_id)
                if len(listChatIds) == 1:
                    del db[userid]
                else:
                    db[userid] = listChatIds

                bot.send_message(chat_id=chat_id,
                        text='Пользователь  <a href="https://www.twitch.tv/{0}">{0}</a> успешно удален'.format(username),
                        parse_mode=telegram.ParseMode.HTML)
                return
            else:
                update.message.reply_text('Пользователь {0} не найден'.format(username))
                return

    update.message.reply_text('Пользователь {0} не найден'.format(username))

def commList(bot, update):
    chat_id = update["message"]["chat"]["id"]

    streamers = []
    for userid in db.keys():
        if chat_id in db[userid]:
            streamers.append(db[userid][0])

    if not streamers:
        update.message.reply_text('Вы ни на кого не подписаны. Добавьте стримеров командой /add <username>')
        return

    tmpStr = "Вы подписаны на:\n"
    for streamer in streamers:
            tmpStr += '• <a href="https://www.twitch.tv/{0}">{0}</a>\n'.format(streamer)

    bot.send_message(chat_id=chat_id,
            text=tmpStr,
            parse_mode=telegram.ParseMode.HTML)

def commHelp(bot, update):
    update.message.reply_text('Справка по боту:\n'
                              '/add <username> - добавляет стримера в мониторинг\n'
                              '/del <username> - удаляет стримера из мониторинга\n'
                              '/list - показывает список стримеров')

# периодически запускаемые задачи
def jobCheckTwitch(bot, job):
    print("Job")


def main():
    if ( settings.telegram["logged"] ):
        logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    updater = Updater(settings.telegram["access_token"])

    dp = updater.dispatcher
    dp.add_handler(CommandHandler("start", commStart))
    dp.add_handler(CommandHandler("add", commAdd, pass_args=True))
    dp.add_handler(CommandHandler("del", commDel, pass_args=True))
    dp.add_handler(CommandHandler("list", commList))
    dp.add_handler(CommandHandler("help", commHelp))

    job = updater.job_queue
    job.run_repeating(jobCheckTwitch, settings.telegram["time_update"])

    updater.start_polling()

    updater.idle()

if __name__ == '__main__':
    main()

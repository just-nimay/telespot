#!/usr/bin/env python3

# Импорт необходимых библиотек
from aiogram import Bot, types
from aiogram.dispatcher import Dispatcher
from aiogram.utils import executor

from pytube import YouTube

from urllib import request as rq
import re
import shutil
import os
import zipfile
import math
import numpy as np

# Получение значения переменной 
# TOKEN из файла config
from config import TOKEN

# Получение доступа к функции валидатора
# из файла validators.py
from validators import PlaylistURIValidator

# Получение доступа к функциям из файла helper.py
from helper import get_info, add_metadata, \
    get_ydl_opts, check_existing_tracks


# Создаем экземпляр класса Bot и передаем ему
# обязательное значение token
# а так же parse_mode=types.ParseMode.HTML
# для форматирования текста как в HTML
bot = Bot(token=TOKEN, parse_mode=types.ParseMode.HTML)
# Dispatcher нужен для упрощения исползования
# фильтров при регистрации обработчиков
dp = Dispatcher(bot)

# Обработчик команды /start
@dp.message_handler(commands=['start'])
async def process_start_command(message: types.Message):
    await message.reply("Привет!\nОтправь мне ссылку на плейлист в Spotify и я отрправлю тебе архив этого плейлиста!")

# Обработчик команды /help
@dp.message_handler(commands=['help'])
async def process_help_command(message: types.Message):
    await message.reply("Просто отправь мне ссылку на плейлист!")

# Обработчик получающий ввод от пользователя.
# В функции get_message аргумент message 
# хранит в себе сообщение отправителя,
# то есть пользователя
@dp.message_handler()
async def get_message(message: types.Message):
    # Проверка на валидность текста, введенного пользователем
    valid = PlaylistURIValidator()
    check = valid.validate(message.text)
    # Если ссылка имеет значение False, то
    if check is False:
        # Отправка пользователю сообщение о невалидности ссылки
        await bot.send_message(
            message.from_user.id,
            "<b>Ссылка невалидна!</b>\nОтправь валидную ссылку (например: spotify:playlist:<i>id</i> или https://open.spotify.com/playlist/<i>id</i>)")
        return
    # Получение информации об альбоме, пути, в который
    # будут загружаться треки и получение списка треков
    pl_details, path, tracks = get_info(message.text)
    
    # Названия альбома присваивается переменной pl_name
    pl_name = pl_details['pl_name']
    # Получение треков из информации об альбоме
    tracks = pl_details['pl_tracks']
    
    # Проверка на существование трека в папке загрузок
    existing_tracks = check_existing_tracks(pl_details, path, unexist=True)
    
    # Отрпавка пользователю сообщения в котором отображается
    # прогресс загрузки треков
    progress_message = await bot.send_message(
        message.from_user.id,
        f'Загружено {len(existing_tracks)}/{len(tracks)} треков из <b>{pl_name}</b>'
    )
    
    # Это сообщение будет изменятся и показывать трек,
    # который в настоящий момент загружается
    download_message = await bot.send_message(message.from_user.id, 'Загрузка...')

    # С помощью цикла проходимся по всем трекам альбома
    for track in tracks:
        # Если трек уже существует,
        # то мы переходим к следующему треку
        if track in existing_tracks:
            continue

        # Получение названия трека
        file_name = track['file_name']
        # Получение обложки трека
        album_art = track['album_art']

        # Изменение сообщения, отображающего
        # трек, который в настоящий момент загружается
        await download_message.edit_text(f'Загрузка {file_name} \n{album_art}')
        
        # Создание ссылки поиска текущего трека в YouTube 
        url_track = f"https://www.youtube.com/results?search_query={track['uri']}"
        
        # Получение данных страницы поиска
        html = rq.urlopen(url_track)
        video_ids = re.findall(r"watch\?v=(\S{11})", html.read().decode())
         
        # Если есть результаты, то 
        if video_ids:
            # Получение ссылки на первый ролик в поиске
            url = "https://www.youtube.com/watch?v=" + video_ids[0]
            
            # Получение ролика трека
            video = YouTube(url)

            # Фильтруем ролик, чтобы получить
            # только аудио дорожку
            audio = video.streams.filter(only_audio=True).first()

            # Скачивание трека в папку загрузок
            out_file = audio.download(output_path=path)
            #base, ext = os.path.splitext(out_file)
            # Создание нового имени скачаного файла
            # с расширением .mp3
            new_file = path + "/" + file_name + '.mp3'

            # Переименование скачаного файла
            os.rename(out_file, new_file)

            # Попытка добавления метаданных
            try:
                # Если ушпешно, то у аудиофала
                # будут метаданные
                add_metadata(file_name, track, path)
            # Если неуспешно, то продолжить
            except AttributeError as e:
                pass

        # Получение треков, которые уже загружены
        existing_tracks = check_existing_tracks(pl_details, path, unexist=True)

        # Изменение сообщения о прогрессе загрузки треков
        try:
            await progress_message.edit_text(
                f'Загружено {len(existing_tracks)}/{len(tracks)} треков из <b>{pl_name}</b>'
            )
        except Exception as e:
            pass
    # После того, как цилк прошел по всем трекам,
    # Пользователю отправляется сообщение об окончании загрузки
    # и начале создания архива с треками
    archiving = await download_message.edit_text(
        f'Загрузка альбома <b>{pl_name}</b>  завершена!\nНачинаю архивацию...'
    )
    
    # Создание архива
    shutil.make_archive(pl_name, 'zip', f'{path}')

    # Изменение сообщения об сосоянии создания архива
    await archiving.edit_text(
        f'Архивация архива <b>{pl_name}</b> завершена!\nОтправляю архив'
    )
    # Попытка отрпавки архива пользователю 
    try:
        archive = open(f'{pl_name}.zip', 'rb')
        await bot.send_document(message.from_user.id, archive)
    # Ошибка вызывается если архив больше 50 мб
    # потому что телеграмм может отправлять файлы только
    # меньше 50 мб
    # В таком случае нужно разбить архив на несколько частей:
    except Exception as e:
        # Узнаем вес архива
        zp = zipfile.ZipFile(f'{pl_name}.zip')
        size = sum([zinfo.file_size for zinfo in zp.filelist])
        # Вес архива в килобайтах
        zip_kb = float(size) / 1000
        # Вес архива в мегабайтах  
        zip_mg = float(zip_kb) / 1024
        # Удаление большого архива
        os.remove(f'{pl_name}.zip')
        
        # Вывод в термилал вес большого архива
        print("zip_mg:", zip_mg)
        # Подсчет количества архивов меньше 50 мб
        cout_of_achives = math.ceil(zip_mg / 50)
        # Вывод количесва архивов
        print('cout_of_achives:', cout_of_achives)
        
        # Отпрака пользователю сообщения в котором
        # сообщается что альбом будет отправлен в
        # нескольких архивах
        await bot.send_message(message.from_user.id, f'Архив получился больше <b>50 МБ</b>, так что разбиваю его на {cout_of_achives} архива(ов)')

        # Получение списка существующих архивов
        existing_tracks = check_existing_tracks(pl_details, path, unexist=True)
        # Разделение существующих треков на кол-во частей архивов
        split_tracks = np.array_split(existing_tracks, cout_of_achives)
        
        # Проход цыклом по разделенным трекам
        for i in range(0, len(split_tracks)):
            print('===========================')
            print(i)
            # Создание архива в котором будет только часть треков
            with zipfile.ZipFile(f'{pl_name}-{i + 1}.zip', 'w') as zipF:
                for track in split_tracks[i]:
                    file_name = track['file_name']
                    zipF.write(f'{path}/{file_name}.mp3', compress_type=zipfile.ZIP_DEFLATED)
            # Отправка архива
            await bot.send_document(message.from_user.id, open(f'{pl_name}-{i+1}.zip', 'rb'))
            # Удаление арива 
            os.remove(f'{pl_name}-{i + 1}.zip')


        


    # Удаление папки с треками
    shutil.rmtree(path, ignore_errors=False)
    

# Если этот файл запускается пользователем,
# а не через другой файл, то
if __name__ == '__main__':
    # Запуск бота
    executor.start_polling(dp)
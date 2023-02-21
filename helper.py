#!/usr/bin/env python3

# Импорт необходимых библиотек
import os
from urllib import request as rq

from urllib.parse import quote

import eyed3
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials

# Импорт переменных из файла cofig.py
from config import CLIENT_ID, CLIENT_SECRET, USER_ID

# Путь к папке, в которую будут
# загружаться треки
download_base_path = "./downloads"

# Авторизация API Spotify
auth_manager = SpotifyClientCredentials(
    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET
)
sp = spotipy.Spotify(auth_manager=auth_manager)

# Функция с параметрами для загрузки
# Треков с YouTube
def get_ydl_opts(path):
    # Возращает словарь параметров
    return {
        "format": "bestaudio/best",
        "outtmpl": f"{path}/%(id)s.%(ext)s",
        "ignoreerrors": True,
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "320",
            }
        ],
    }

# Функция получения альбома пользователя,
# которая возращает детали (составляющие) альбома
def get_user_playlists(sp, user_id):
    return [
        {"value": pl.get("uri"), "name": pl.get("name")}
        for pl in sp.user_playlists(user_id).get("items")
    ]

# Функция, которая преобразует строку,
# проганяя через фильтр
def normalize_str(string):
    return string.translate(str.maketrans('\\/:*?"<>|', "__       "))

# Функция, которая поулчает данные об альбоме
def get_playlist_details(sp, pl_uri):
    offset = 0
    # В переменной fields хранятся параметры
    # которые нам нужно получить
    fields = "items.track.track_number,items.track.name,items.track.artists.name,items.track.album.name,items.track.album.release_date,total,items.track.album.images"
    # Получение параметров
    pl_name = sp.playlist(pl_uri)["name"]
    pl_items = sp.playlist_items(
        pl_uri,
        offset=offset,
        fields=fields,
        additional_types=["track"],
    )["items"]
    
    # Получение списка треков
    pl_tracks = []
    while len(pl_items) > 0:
        # Перебор элементов альбома
        for item in pl_items:
            # Если элемент является треком, то
            if item["track"]:
                # Получение названия трека
                track_name = normalize_str(item["track"]["name"])
                # Поулчение имени исполнителя
                artist_name = normalize_str(
                    item["track"]["artists"][0]["name"]
                )

                # добавление в список треков значение
                pl_tracks.append(
                    {   # Ссылка на трек
                        "uri": quote(
                            f'{track_name.replace(" ", "+")}+{artist_name.replace(" ", "+")}'
                        ),
                        # Имя файла трека
                        "file_name": f"{artist_name} - {track_name}",
                        # Название трека
                        "track_name": track_name,
                        # Имя исполнителя
                        "artist_name": artist_name,
                        # Название альбома
                        "album_name": normalize_str(
                            item["track"]["album"]["name"]
                        ),
                        # Дата релиза альбома
                        "album_date": item["track"]["album"]["release_date"],
                        # Порядковый номер трека
                        "track_number": item["track"]["track_number"],
                        # Обложка альбома
                        "album_art": item["track"]["album"]["images"][0]["url"],
                    }
                )

        offset = offset + len(pl_items)
        pl_items = sp.playlist_items(
            pl_uri,
            offset=offset,
            fields=fields,
            additional_types=["track"],
        )["items"]
    # Возращение словоря с данными об альбоме
    return {"pl_name": pl_name, "pl_tracks": pl_tracks}

# Функция, которая создает папку загрузки треков
def create_download_directory(dir_name):
    # Путь папки
    path = f"{download_base_path}/{dir_name}"
    # Если папка уже существует, то
    if os.path.exists(path):
        # Возрашение пути к папке загрузок
        return path
    # Если папки нет, то попробовать
    try:
        # Создание папки по пути
        os.makedirs(path)
        # Возращение пути к папке загрузок
        return path
    # При возникновении ошибки
    # при создании папки
    except OSError:
        # Отправить сообщение в консоль
        print("Creation of the download directory failed")

# Функция проверки треков на их существование
# Параметр unexist имеет значение по умолчанию False
def check_existing_tracks(playlist, path, unexist=False):
    # Получение пути папки загрузок
    existing_tracks = os.listdir(path)
    # Если параметр unexist имеет значение True, то
    if unexist is True:
        # Создание списка с существующими треками
        # через генератор
        tracks = [
            track
            for track in playlist["pl_tracks"]
            if f"{track['file_name']}.mp3" in existing_tracks
        ]
        # Возращение списка сущесвтующих треков
        return tracks
    # Если параметр unexist имеет значение False
    # Создание списка с несуществующими треками
    # через генератор
    tracks = [
        track
        for track in playlist["pl_tracks"]
        if f"{track['file_name']}.mp3" not in existing_tracks
    ]
    # Возращение списка существуюших треков
    return tracks

# Функция добавления метаданных к медиафайлу
def add_metadata(track_name, metadata, path):
    # Составление пути до полученного трека
    audio_path = f'{path}/{track_name}.mp3'
    # Чтение аудиофайла
    audio = eyed3.load(audio_path)
    # Если тегов небыло, то
    if not audio.tag:
        # Иницилизируем тэги
        audio.initTag()
    # Создание тэга названия трека
    audio.tag.title = metadata["track_name"]
    # Создание тэга названия альбома трека
    audio.tag.album = metadata["album_name"]
    # Создание тэга имени исполнителя
    audio.tag.artist = metadata["artist_name"]
    # Создание тэга выпуска альбома
    audio.tag.release_date = metadata["album_date"]
    # Создание тэга номера трека
    audio.tag.track_num = metadata["track_number"]
    # Добавление обложки трека
    album_art = rq.urlopen(metadata["album_art"]).read()
    audio.tag.images.set(3, album_art, "image/jpeg")
    # Сохранение созданных тэгов
    audio.tag.save()

# Функция получения данных 
# об альбоме
# о пути папки загрузок
# о треках
def get_info(pl_uri):
    # Получение данных об плейлисте
    # с помощью вызова функции get_playlist_details
    pl_details = get_playlist_details(sp, pl_uri)
    # Создание папки загрузок 
    # с помощью вызова функции create_download_directory
    path = create_download_directory(pl_details["pl_name"])
    # Получение информации о треках
    # с помощью вызова функции check_existing_tracks
    tracks = check_existing_tracks(pl_details, path)
    # Возращение данных
    return pl_details, path, tracks

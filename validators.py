#!/usr/bin/env python3

# Импорт необходимых библиотек
import regex
from prompt_toolkit.validation import ValidationError, Validator

# Класс в котором хранится функция валидации ссылки
class PlaylistURIValidator(Validator):
    # функция валидации ссылки
    def validate(self, document):
        # Если параметр document имеет значение back, то
        if document == "back":
            # Возразение False
            return False
        # Проверка ссылки на валидность
        uriCheck = regex.match("^(spotify:playlist:)([a-zA-Z0-9]+)(.*)$", document)
        urlCheck = regex.match("^(https:\/\/open.spotify.com\/playlist\/)([a-zA-Z0-9]+)(.*)$", document)
        # Если ссылка не прошла валидность, то
        if not (uriCheck or urlCheck):
            # Возращение False
            return False
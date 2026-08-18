def bbox_filter(stations, lat, lon, delta=0.5):
    """Фильтрация списка станций (id, name, lat, lon, ...) по прямоугольнику.

    Оставлено как утилита для случаев, когда станции уже загружены в
    память целиком (например, во время сборки БД). Для запросов
    пользователей в самом боте используйте
    services.stations_db.get_stations_near — она фильтрует на уровне
    SQL и не требует загрузки всей таблицы станций в память.
    """
    return [
        s for s in stations
        if abs(s[2] - lat) < delta and abs(s[3] - lon) < delta
    ]
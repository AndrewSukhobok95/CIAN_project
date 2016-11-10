# -*- coding: utf-8 -*-

# Sukhobok Andrey

import requests
import re
from bs4 import BeautifulSoup
import pandas as pd
import time

# ПОДРОБНОЕ ОПИСАНИЕ КОДА В ФАЙЛЕ ipynb

# Страница ЦИАНа по которой будем ходить - собирать квартиры
# p = число - номер страницы (поставим туда {}, чтоб подставлять туда разные страницы)
district = 'http://www.cian.ru/cat.php?deal_type=sale&district%5B0%5D=13&district%5B1%5D=14&district%5B2%5D=15&\
district%5B3%5D=16&district%5B4%5D=17&district%5B5%5D=18&district%5B6%5D=19&district%5B7%5D=20&district%5B8%5D=21\
&district%5B9%5D=22&engine_version=2&offer_type=flat&p={}&room1=1&room2=1&room3=1&room4=1&room5=1&room6=1'



# Функция для сбора квартир с одной страницы циана
def page_grabber(page):
    flats_links = [] # список с ссылками с одной страницы поиска
    p = len(page)
    for i in range(p):
        flats_links.append(page[i].attrs['href']) # один элемент - ссылка (то есть атрибут href тега div)
    return(flats_links)

links = [] # Список, который заполним всеми квартирами

for i in range(1,31):
    # Получаем нужную страницу
    search_page = requests.get(district.format(i))
    search_page = search_page.text
    search_page = BeautifulSoup(search_page, 'lxml')
    
    # Внутри нужной страницы добираемся до таблицы с квартирами
    flats = search_page.html.body.findAll('div', id='content')
    flats = flats[0].findAll('div', attrs = {'class':'serp-list'})
    
    # В этой переменной будет лежать нужный кусок страницы (в каждой итерации новая страница)
    flats_cian = flats[0].findAll('div',\
              attrs = {'ng-class':"{'serp-item_removed': offer.remove.state, 'serp-item_popup-opened': isPopupOpen}"})
    
    # Берем ссылки с текущей страницы и кладем в наш общий список ссылок
    links = links + page_grabber(flats_cian)
    
    # Каждую итерацию проверяем, что все нормально работает 
    print('The page number {} wroks well\nIts requests.ok is {}'.format(i, requests.get(district.format(i)).ok))




# Функции для сбора данных по одной квартире


# Сбор количества комнат
def room_grabber(table):
    room = table.findAll('div', class_='object_descr_title')
    try:
        room = re.findall(r'.?-комн. кв.' ,str(room[0]))[0]
    except:
        if re.findall(r'многокомн' ,str(room[0]))[0] == 'многокомн':
            room = [6]
    return(int(room[0]))


# Цена
def price_grabber(table):
    '''
    Будем возвращать цену списком. Судя по всему ЦИАН предоставил нам скрытый тег, в котором лежит цена в удобном для нас
    виде - на всякий случай будем собирать цену в двух вариантах (можно будет проверить + если один вариант отпал - другой будет доступен).
    В качестве нулевых значений возьмем NaN
    '''
    price = table.findAll('div', class_='object_descr_price_box')
    
    p1 = np.nan
    p2 = np.nan
    
    try:
        p1 = price[0].findAll('div')[0].string.strip()
        p1 = int(p1[:-5].replace(' ', ''))
    except:
        pass
    
    try:
        p2 = price[0].findAll('div')[1].string.strip()
        p2 = float(p2.replace(',', '.'))
    except:
        pass
    
    return([p1,p2])


# Расстояние до метро в минутах + Способ передвижения (как добраться до метро)
def metro(table):
    try:
        # Нужный кусок html
        metro = table.findAll('div', class_='object_descr_metro')
        metro = metro[0].findAll('span', class_='object_item_metro_comment')[0].string

        # Минуты
        metrdist = int(re.findall(r'\d+', metro)[0])

        # Walk
        walk = metro.replace(' ', '')
        walk = walk.replace('\n', '')
        walk = re.findall(r'мин\..+', walk)[0][4:]
        if walk == 'пешком':
            walk = 1
        elif walk == []:
            walk = np.nan
        else:
            walk = 0
    except:
        metrdist = np.nan
        walk = np.nan
        
    return({'metrdist': metrdist, 'walk': walk})


# Материал стен: кирпичный/монолит/жб
def brick_grabber(flat_page):
    
    # Ищем на странице нужный кусок html кода
    house_table = flat_page.findAll('div', class_='offer_container object_descr cleared')
    house_table = house_table[0].findAll('div', class_='bti__inner')
    
    # Проверка на случай, если искомая секция вобще отсутствует на странице данной квартиры
    if house_table == []:
        brick = np.nan
    else:
        # Углубляемся в нужный кусок html кода
        first_table = house_table[0].findAll('tbody')[0]
        first_table_tr = first_table.findAll('tr') # Собрали все tr, то есть все секции первой малой таблицы

        #Ищем нужный th с информацией о материале
        for i in range(1,len(first_table_tr)):
            try:
                brick_str = re.findall(r'Материалы стен', str(first_table_tr[i].th))[0]
                if brick_str == 'Материалы стен':
                    # Ищем один из нужных нам флажков - кирпич, монолит или варианты ж/б
                    brick = re.findall(r'кирпич|монолит|ж??б|желез.+бетон', str(first_table_tr[i].td))
            except:
                pass

        # Проверяем результат регулярного выражения
        if len(brick) == 0:
            brick = 0
        else:
            brick = 1
        
    return(brick)


# Расстояние от центра в км.

# Собираем координаты квартиры из гуголовской карты
def getCoords(flat_page):
    coords = flat_page.find('div', attrs={'class':'map_info_button_extend'}).contents[1]
    coords = re.split('&amp|center=|%2C', str(coords))
    coords_list = []
    for item in coords:
        if item[0].isdigit():
            coords_list.append(item)
    lat = float(coords_list[0])
    lon = float(coords_list[1])
    return lat, lon

# house_coords = getCoords(flat_page)
def dist_grabber(house_coords):
    null_coords = (55.755831, 37.617673)
    
    # Радиус Земли
    R = 6371
    
    # Широта (latitude):
    lat1 = house_coords[0]
    lat2 = null_coords[0]

    # Долгота (longtude):
    lon1 = house_coords[1]
    lon2 = null_coords[1]
    
    d = np.arccos(
    np.sin(lat1)*np.sin(lat2) + np.cos(lat1)*np.cos(lat2)*np.cos(lat1-lat2)
    )
    L = d*R
    return(L)


# Общая площадь квартиры, кв. м. + Площадь кухни, кв. м. + Жилая площадь квартиры, кв. м.
def sp_grabber(inner_table, sp_pl = ['Общая площадь', 'Площадь кухни', 'Жилая площадь']):
    
    # Теперь тут лежит внутренняя таблица (список td)
    table_td = inner_table.findAll('tr')
    
    # Список, куда будем класть наши значения искомых площадей
    sp_list = []
    
    # Перебираем три метста
    for s in sp_pl:
        
        # Поиск нужной цифры
        for i in range(1,len(table_td)):
            try:
                sp_str = re.findall(r'{}'.format(s) ,table_td[i].th.string)[0] # В качестве s ставим искмую сейчас площадь
                if sp_str == '{}'.format(s):
                    sp = re.findall(r'\d+\,?\d+\xa0м', str(table_td[i].td))

                    # Надстройка на случай, если графа с площадью пуста
                    if sp == []:
                        sp = np.nan
                        sp_list.append(sp) # Добавим в список значение так же, если нужной информации нет
                        break

                    sp = sp[0].replace(',', '.')
                    sp = float(re.findall(r'\d+\.?\d+', sp)[0])
                    
                    # Добавим в список значение очередной площади
                    sp_list.append(sp)
            except:
                pass
    
    # Словарь, в котором подпишем цифры удобным названием переменных
    sp_dist = {}
    sp_dist['totsp'] = sp_list[0]
    sp_dist['kitsp'] = sp_list[1]
    sp_dist['livesp'] = sp_list[2]
    
    # Вернем словарь со всеми нужными значениями
    return(sp_dist)


# Номер этажа, на котором расположена квартира + Всего этажей в доме
def floor_grabber(inner_table):
    
    # Теперь тут лежит внутренняя таблица (список td)
    table_td = inner_table.findAll('tr')
    
    # Вытаскиваем этажи
    for i in range(1,len(table_td)):
        try:
            th = re.findall(r'Этаж' ,table_td[i].th.string)[0]
            if th == 'Этаж':
                floor_td = table_td[i].td # тег со всей информацией об этажах
                floor_td = re.findall(r'\d+', str(floor_td)) # Теперь в переенной лежит список
                # Одно число - только этаж квартиры, Два - еще суммарное количество этажей, Пустой - этой информции нет
        except:
            pass
    
    # Определяем какую информацию дать на выход
    if len(floor_td) == 0:
        floor = np.nan
        nfloor = np.nan
    elif len(floor_td) == 1:
        floor = int(floor_td[0])
        nfloor = np.nan
    else:
        floor = int(floor_td[0])
        nfloor = int(floor_td[1])

    return({'floor':floor, 'n_floor':nfloor})


# Балкон
def bal_grabber(inner_table):
    
    # Теперь тут лежит внутренняя таблица (список td)
    table_td = inner_table.findAll('tr')
    
    #Ищем нужный th с общей площадью квартиры
    for i in range(1,len(table_td)):
        # Положим сюда строку "Балкон" и поней будем искать нужный th
        # (на случай, если кол-во параметров может отличаться в разных квартирах)
        try:
            bal_str = re.findall(r'Балкон' ,table_td[i].th.string)[0]
            if bal_str == 'Балкон':
                bal = re.findall(r'i>\d+|есть', str(table_td[i].td))# Найдем кусок с метрами
                # Если балконов нет, то реулярное выражение ничего не найдет и вернет пустой список
                if bal == []:
                    bal = 0
                else:
                    bal = 1
        except:
            pass
        
    return(bal)


# Телефон
def tel_grabber(inner_table):
    
    # Теперь тут лежит внутренняя таблица (список td)
    table_td = inner_table.findAll('tr')
    
    # На некоторых страницах отстутствует графа "Телефон", поэтому введем проверку на наличие этой строки с помощью индикатора
    th_count = 0
    
    # Смотрим на td в поисках графы "Телефон"
    for i in range(1,len(table_td)):
        try:
            # Накручиваем значение индикатора
            th_count = th_count + 1
            
            th = re.findall(r'Телефон' ,table_td[i].th.string)[0]
            
            if th == 'Телефон':
                th_count = 0
                
                tel = table_td[i].td.string
                
                # Проверка на текст в нужном куске html кода
                if tel == 'да':
                    tel = 1
                else:
                    tel = 0
        except:
            pass
    
    # Проверка индикатора
    if th_count == len(table_td)-1:
        tel = 0
    
    return(tel)


# Рынок (первичный / вторичный)
def new_grabber(inner_table):
    
    # Теперь тут лежит внутренняя таблица (список td)
    table_td = inner_table.findAll('tr')
    
    # Идем по всем td в поисках графы 'Тип дома'
    for i in range(1,len(table_td)):
        try:
            new_str = re.findall(r'Тип дома' ,table_td[i].th.string)[0]
            if new_str == 'Тип дома':
                new = re.findall(r'вторич', str(table_td[i].td))
                
                # Проверка на наличия корня "вторич" в данной графе таблице
                if new == []:
                    new = 1
                else:
                    new = 0
        except:
            pass
        
    return(new)


# Словарь, в который сложим квартиры
flats_dict = {}
N = 0

for l in links:
    
    # Это будет номер квартиры
    N = N + 1
    
    # Соберем все, что написано выше, вместе
    flat_page = requests.get(l)
    flat_page = flat_page.text
    flat_page = BeautifulSoup(flat_page, 'lxml')
    inf_table = flat_page.findAll('table', class_ = 'object_descr_tab')
    inf_table = inf_table[0]
    inner_table = inf_table.findAll('table', class_ = 'object_descr_props flat sale')
    inner_table = inner_table[0]
    
    house_coords = getCoords(flat_page)
    
    flats_dict[N] = {
        'Rooms': room_grabber(inf_table),
        'Price': price_grabber(inf_table)[0],
        'Price_duplicate': price_grabber(inf_table)[1],
        'Totsp': sp_grabber(inner_table, sp_pl = ['Общая площадь', 'Площадь кухни', 'Жилая площадь'])['totsp'],
        'Livesp': sp_grabber(inner_table, sp_pl = ['Общая площадь', 'Площадь кухни', 'Жилая площадь'])['kitsp'],
        'Kitsp': sp_grabber(inner_table, sp_pl = ['Общая площадь', 'Площадь кухни', 'Жилая площадь'])['livesp'],
        'Dist': dist_grabber(house_coords),
        'Metrdist': metro(inf_table)['metrdist'],
        'Walk': metro(inf_table)['walk'],
        'Brick': brick_grabber(flat_page),
        'Tel': tel_grabber(inner_table),
        'Bal': bal_grabber(inner_table),
        'Floor': floor_grabber(inner_table)['floor'],
        'Nfloors': floor_grabber(inner_table)['n_floor'],
        'New': new_grabber(inner_table),
        'Link': l
    }
    
    print('Page {} is working well'.format(N))


# Наши квартиры в DataFrame
df_flats = pd.DataFrame(flats_dict).T

# Выведем результат парсинга:
print(df_flats.describe())
for c in df_flats.columns:
    print(c, len(df_flats[c][df_flats[c].isnull()]))

# Выведем готовый csv файл
df_flats.to_csv('flats_from_CIAN.csv')

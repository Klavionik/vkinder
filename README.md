# Курсовая работа VKinder

## Нетология, модуль "Продвинутый Python", февраль 2020 г.

### Описание

"Tinder-like" консольная утилита. Принимает имя пользователя ВКонтакте
или его screen name и находит для него наиболее подходящие "пары"
среди других пользователей ВКонтакте, основываясь на схожести профилей.
Информация о найденных парах (имя, ссылка на профиль, ссылки на самые популярные фото) выводится в консоль либо экспортируется в JSON-файл.

### Установка

`$ git clone https://github.com/Klavionik/vkinder.git`  
`$ cd vkinder`  
`$ pip install .`

### Как оно работает?

Совершенно банальнейшим образом сравнивая информацию из профилей ВКонтакте. Сравниваются (по убыванию веса) жизненные взгляды, интересы, количество общих групп, количество общих друзей, разница в возрасте. Результат не самый точный, потому что далеко не все в принципе заполняют свои профили. И даже те, кто это делает - делают это по-разному, даже если имеют в виду одно и то же.

Если профиль пользователя заполнен не полностью, программа попросит заполнить его перед тем, как продолжить работу.

Информация о пользователях и их парах сохраняется в БД SQLite.
Вес для критериев сравнения можно настроить в `vkinder/resources/config.ini`, секция `[Match Settings]`.

Результат поиска можно сохранить в JSON-файл или просто выводить в консоль (см. опции запуска).

### Использование

- Опции запуска  
  `$ vkinder --help`

- Настройки приложения  
  `$ vkinder run --help`

- Старт приложения  
  `$ vkinder run`

- Добавление нового пользователя

  ```
  >>> u
  Let's find somebody's fortune! Enter their ID or screenname below.
  We'll need to acquire some information.
  >>> dm

  Favorite movies?

  >>> Побег из Шоушенка, Зеленая миля, Звездные Войны

  Favorite TV shows?

  >>> Клиника, Lost

  Favorite books?

  >>> Чехов, Достоевский, Толстой

  Favorite games (PC or console)?

  >>> StarCraft

  Political views?
  ...
  4 – Liberal
  ...

  >>> 4

  ...

  User Дмитрий Медведев loaded from the API
  User Дмитрий Медведев set as the current user.
  ```

- Установка текущего пользователя из сохраненных ранее

  ```
  >>> u
  Let's find somebody's fortune! Enter their ID or screenname below.
  We'll need to acquire some information.
  >>> vadim.shuvalov

  User Вадим Шувалов loaded from the database.
  User Вадим Шувалов set as the current user.

  ```

- Поиск пар для текущего пользователя

  ```
  >>> f

  Please, wait a minute while we're collecting data...

  Sorting out data: 100%||
  Fetching profiles: 100%||
  Building matches: 100%||

  643 matches found and saved.
  ```

- Вывод найденных пар для текущего пользователя

  ```
  >>> n

  Галина Лёшина https://vk.com/id305829479 Total score: 29
  Best photos:
  ...

  Елена Родина https://vk.com/id157020531 Total score: 23
  Best photos:
  ...

  Валентина Конакова https://vk.com/id158383063 Total score: 21
  Best photos:
  ...

  Irina Sytaya https://vk.com/id398236971 Total score: 12
  Best photos:
  ...
  ```

- Удаление информации о пользователе из БД

  ```
  >>> d
  Enter user id to delete their profile from the database.
  >>> 377553209
  User with ID 377553209 and all the corresponding matches have been deleted.

  ```

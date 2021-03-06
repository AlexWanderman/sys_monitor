from socket import AF_INET, SOCK_STREAM, socket
from threading import Thread
from time import sleep

import psutil


class Spectator:
    '''Класс сборшик данных о системе

    Получает запрос о том, какие данные считать и возвращает сообщение в виде
    str для отправки на сервер.

    '''
    def get_data(self, tp):
        if tp == 'cpu':  # -> str
            prc = int(psutil.cpu_percent())

            return f'type:cpu prc:{prc}'

        elif tp == 'ram':  # -> str
            ram = psutil.virtual_memory()

            ttl = ram.total
            avl = ram.available
            prc = int(ram.percent)

            return f'type:ram ttl:{ttl} avl:{avl} prc:{prc}'

        elif tp == 'swp':  # -> str
            swp = psutil.swap_memory()

            ttl = swp.total
            free = swp.free
            prc = int(swp.percent)

            return f'type:swp ttl:{ttl} free:{free} prc:{prc}'

        elif tp == 'dsk':  # -> list
            drives = psutil.disk_partitions(all=False)
            paths = [x.mountpoint for x in drives if x.opts == 'rw,fixed']
            result = []

            for p in paths:
                dsk = psutil.disk_usage(p)

                ltr = p[0].lower()
                ttl = dsk.total
                free = dsk.free
                prc = int(dsk.percent)

                t = f'type:dsk ltr:{ltr} ttl:{ttl} free:{free} prc:{prc}'
                result.append(t)

            return result  # ['...', '...', '...', ...]

        else:
            raise TypeError('Неправильно указан запрошенный тип')


class Client:
    '''Класс клиента

    ip -> str (IP адрес сервера);
    port -> int (Порт сервера);
    name -> str (Имя учетной записи);
    key -> str (Ключ учетной записи).

    Клиент аутентифицируется на сервере, при удачной аутентификации собирает
    данные о загруженности системы и отправляет на сервер через определенный
    интервал времени.

    '''
    def __init__(self, ip, port, name, key):
        self.address = ip
        self.port = port
        self.name = name
        self.key = key

        self.msg_size = 64
        self.client_socket = None
        self.spectator = Spectator()

        # Период отправки данных по параметрам
        self.cpu_timer = 6
        self.ram_timer = 6
        self.swp_timer = 12
        self.dsk_timer = 30

        # Запуск клиентов
        self.client()

    def client(self):
        # Настройка соединения
        self.client_socket = socket(AF_INET, SOCK_STREAM)
        self.client_socket.connect((self.address, self.port))

        # Аутентификация
        login = f'name:{self.name} key:{self.key}'
        self.client_socket.send(login.encode())
        respr = self.client_socket.recv(self.msg_size)

        if respr.decode() != '+':
            print('Аутентификация не пройдена')
            self.client_socket.close()
            return

        print('Аутентификация пройдена')

        # Запуск потоков, для отправки данных по параметрам
        Thread(target=self.monitor, args=('cpu', self.cpu_timer)).start()
        Thread(target=self.monitor, args=('ram', self.ram_timer)).start()
        Thread(target=self.monitor, args=('swp', self.swp_timer)).start()
        Thread(target=self.li_monitor, args=('dsk', self.dsk_timer)).start()

    def monitor(self, tp, period):
        while True:
            data = self.spectator.get_data(tp)

            # Исключение если сервер не получит запрос или не вернет ответ
            self.client_socket.send(data.encode())
            respr = self.client_socket.recv(self.msg_size).decode()

            if respr == '-':
                print(f'- Ошибка: {data}')

            elif respr == '+':
                print(f'+ Запись: {data}')

            else:
                print(f'~ Ответ: {respr}')

            sleep(period)

    def li_monitor(self, tp, period):
        while True:
            data = self.spectator.get_data(tp)

            for n in data:
                # Исключение если сервер не получит запрос или не вернет ответ
                self.client_socket.send(n.encode())
                respr = self.client_socket.recv(self.msg_size).decode()

                if respr == '-':
                    print(f'- Ошибка: {n}')

                elif respr == '+':
                    print(f'+ Запись: {n}')

                else:
                    print(f'~ Ответ: {respr}')

                sleep(2)

            sleep(period)


if __name__ == "__main__":
    ip = input('server address: ')
    port = int(input('server port: '))
    name = input('name: ')
    key = input('key: ')
    client = Client(ip, port, name, key)

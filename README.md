# Лабораторная работа №3. Размещение секретов в хранилище
## Цель работы
Получить навыки размещения секретов в хранилище и взаимодействия с ним.
## Ход работы
Для реализации хранилища секретов был использован Ansible. Был добавлен файл с секретам в зашифрованном виде, который выглядит следующим образом:

```
$ANSIBLE_VAULT;1.1;AES256
37643436616530313461373139303632393936363939653665636436356365666435633231363761
6163643236396362346362306531326165633936653431330a313863316465396361346462653464
36383661653831336565353363613333396539373763323962396366373238396438633835363662
3361613438346232320a643230393435613163343739373862333162333964356536343230626234
62383631633162313437663937333961636236663436376231656138386537353139646565656563
30623333303764366337353338313932653035623333316130396561363238633961616662366133
34643031326133393831353864376431633665306231366563353965616362333531333330373863
61333861333862393565
```

Был создан файл setup.yml для запуска Ansible Playbook, который принимает файл с паролем от Ansible для расшифровки vault.yml и создания файла .env, который потом используется Docker'ом для создания переменных окружения.

```
- name: Set up PostgreSQL credentials
  hosts: localhost
  tasks:
    - name: Load PostgreSQL credentials from vault
      ansible.builtin.include_vars:
        file: vault.yml
        name: db_creds

    - name: Create .env file for Docker
      ansible.builtin.copy:
        dest: .env
        content: |
          POSTGRES_USER={{ db_creds.postgres_user }}
          POSTGRES_PASSWORD={{ db_creds.postgres_password }}
          POSTGRES_DB={{ db_creds.postgres_db }}
        mode: '0644'
```

В docker-compose.yml были использованы переменные, которые были расшифрованы из Ansible.

```
version: '3.8'
services:
   web:
      depends_on:
         - postgres
      build: .
      command: bash -c "python src/preprocess.py && python src/train.py && python src/predict.py -m RAND_FOREST -t func && coverage run src/unit_tests/test_preprocess.py && coverage run -a src/unit_tests/test_training.py && coverage report -m"
      environment:
         - POSTGRES_USER=${POSTGRES_USER}
         - POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
         - POSTGRES_DB=${POSTGRES_DB}
      ports:
         - 8000:8000
      image: synphase/big_data_lab_3:latest
   postgres:
      image: postgres:latest
      container_name: postgres
      environment:
         - POSTGRES_USER=${POSTGRES_USER}
         - POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
         - POSTGRES_DB=${POSTGRES_DB}
      ports:
         - "5432:5432"
      volumes:
         - pgdata:/var/lib/postgresql/data
      restart: on-failure

volumes:
   pgdata:
```
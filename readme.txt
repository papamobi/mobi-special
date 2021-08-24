# Сначала получаем bot token. Пусть будет XXXX
#

# Установка
export BOT_TOKEN=XXXX
git clone https://github.com/em92/mobi-special.git
cd mobi-special
python3 -m venv venv --prompt mobi-special
echo "export BOT_TOKEN=$BOT_TOKEN" >> venv/bin/activate
source venv/bin/activate
python3 -m pip install -r requirements.txt

# из примера создаем конфиг файл
cp config.sample.ini config.ini
# далее редактируем config.ini. Самостоятельно
# nano config.ini

# Запуск (если выполнять сразу после установки, то первые два шага пропустить)
cd mobi-special
source venv/bin/activate
./main.py

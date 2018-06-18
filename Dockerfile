FROM python:3.6

# Install docpress
RUN curl -sL https://deb.nodesource.com/setup_8.x | bash - && \
    apt-get install -y nodejs
RUN npm install -g docpress

# Install Git
RUN apt-get install -y git
COPY credentials.sh /credentials.sh
RUN git config --global credential.helper '/bin/bash /credentials.sh'

# Install Python deps
COPY requirements.txt /requirements.txt
RUN pip install -r /requirements.txt

WORKDIR /code
COPY . /code

EXPOSE 80

CMD ["python", "-u", "main.py"]
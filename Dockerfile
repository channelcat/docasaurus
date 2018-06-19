FROM python:3.6

# Install Git
RUN apt-get install -y git
COPY credentials.sh /credentials.sh
RUN git config --global credential.helper '/bin/bash /credentials.sh'

# Install docpress
RUN curl -sL https://deb.nodesource.com/setup_8.x | bash - && \
    apt-get install -y nodejs

# Install stable docpress
#RUN npm install -g docpress
# Install custom docpress
RUN mkdir /docpress
RUN git clone http://github.com/docpress/docpress.git /docpress/docpress
RUN git clone https://github.com/channelcat/docpress-base.git /docpress/docpress-base
RUN git clone http://github.com/docpress/docpress-core.git /docpress/docpress-core
RUN cd /docpress/docpress-core && npm i && npm link
RUN cd /docpress/docpress-base && npm i && npm link && npm link docpress-core
RUN cd /docpress/docpress && npm i && npm link && npm link docpress-base && npm link docpress-core

# Install Python deps
COPY requirements.txt /requirements.txt
RUN pip install -r /requirements.txt

WORKDIR /code
COPY . /code

EXPOSE 80

CMD ["gunicorn", "--bind", "0.0.0.0:80", "--workers", "10", "--timeout", "600", "main:app"]
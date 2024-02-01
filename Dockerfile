FROM python:3.11

ENV MAIN_HOME /main

WORKDIR $MAIN_HOME

COPY . .


EXPOSE 3000

ENTRYPOINT ["python", "main.py"]
# syntax=docker/dockerfile:1

FROM python:3.8

WORKDIR /src
ADD requirements.txt /src/requirements.txt
RUN pip install -r requirements.txt
ADD . /src

CMD [ "ipython", "eda/run_nbsafety.py"]
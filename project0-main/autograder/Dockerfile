FROM gradescope/autograder-base:latest as build1

RUN apt update \
    && apt install -y libssl-dev \
    && adduser student --no-create-home --disabled-password --gecos "" \
    && apt install -y tmux

FROM gradescope/autograder-base:latest as build2
RUN apt update && apt install -y libssl-dev
COPY src /src
RUN cd /src && make && rm -rf Makefile *.c *.h

FROM build1
COPY --from=build2 /src /autograder/source/src
COPY autograder/run_autograder /autograder
COPY autograder /autograder/source
RUN pip install -r /autograder/source/requirements.txt

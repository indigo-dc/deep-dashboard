FROM ubuntu:20.04
LABEL maintainer="Alvaro Lopez Garcia <aloga@ifca.unican.es>"
LABEL description="DEEP Dashboard container"

RUN apt-get update \
    && apt-get upgrade -y \
    && DEBIAN_FRONTEND="noninteractive" apt-get install -y --no-install-recommends --no-install-suggests \
        ca-certificates \
        gettext \
        git \
        memcached \
        nginx \
        supervisor \
        python3-netifaces \
        python3-setuptools \
        python3-pip \
        python3-wheel \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* 

RUN ln -sf /dev/stdout /var/log/nginx/access.log \
    && ln -sf /dev/stderr /var/log/nginx/error.log \
    && mkdir /docker-entrypoint.d

RUN groupadd memcached \
    && useradd -r -g memcached -s /sbin/nologin -M -d /var/run/memcached memcached \
    && mkdir /var/log/memcached

WORKDIR /srv

RUN git clone https://gitlab.ifca.es/deep/deep-dashboard  -b  devel
RUN pip3 install deep-dashboard/ 

RUN mkdir /etc/deep-dashboard/ \
    && mkdir /srv/deep-dashboard-runtime \ 
    && chown www-data /srv/deep-dashboard-runtime

COPY dashboard-docker.conf /etc/deep-dashboard/dashboard-docker.conf
COPY supervisor.conf.d/* /etc/supervisor/conf.d/

ENV NGINX_ENTRYPOINT_WORKER_PROCESSES_AUTOTUNE=1
COPY docker-entrypoint.d/* /docker-entrypoint.d/
COPY docker-entrypoint.sh /
RUN chmod 755 /docker-entrypoint.sh

ENTRYPOINT ["/docker-entrypoint.sh"]

EXPOSE 80

CMD ["supervisord"]

FROM ubuntu:20.04
LABEL maintainer="Alvaro Lopez Garcia <aloga@ifca.unican.es>"
LABEL description="DEEP Dashboard container"

WORKDIR /srv

RUN apt-get update \
    && apt-get upgrade -y \
    && fetch_deps='gcc libc-dev curl' \
    && DEBIAN_FRONTEND="noninteractive" apt-get install -y --no-install-recommends --no-install-suggests \
        $fetch_deps \
        git \
        python3-netifaces \
        python3-setuptools \
        python3-pip \
        python3-wheel \
        tini \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* \
    && curl -o /tmp/su-exec.c https://raw.githubusercontent.com/ncopa/su-exec/master/su-exec.c \
    && gcc -Wall /tmp/su-exec.c -o/usr/local/bin/su-exec \
    && chown root:root /usr/local/bin/su-exec \
    && chmod 0755 /usr/local/bin/su-exec \
    && rm /tmp/su-exec.c \
    && apt-get purge -y --auto-remove $fetch_deps

RUN pip3 install "deep-dashboard>=0.9.3"

RUN mkdir /etc/deep-dashboard/

COPY dashboard-docker.conf /etc/deep-dashboard/dashboard-docker.conf

COPY docker-entrypoint.sh /
RUN chmod 755 /docker-entrypoint.sh
ENTRYPOINT ["tini", "--", "/docker-entrypoint.sh"] 

CMD ["/usr/local/bin/deep-dashboard", "--listen-path", "/srv/deep-dashboard-runtime/dashboard_${HOSTNAME}.sock", "--config-dir", "/etc/deep-dashboard/"]

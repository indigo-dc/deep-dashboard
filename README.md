# DEEP dashboard

<img src="https://marketplace.deep-hybrid-datacloud.eu/images/logo-deep.png" width=200 alt="DEEP-Hybrid-DataCloud logo"/>

Welcome to the DEEP Dashboard, a web user interface to interact with the
[DEEP Platform](https://deep-hybrid-datacloud.eu/the-platform/) resources.

This is still work in progress, under very heavy development.

# Configuration

Please check the sample configuration file that is distributed with the
dashboard. You must pass one to the dashboard, otherwise it will refuse to
start.

## Minimal configuration

The minimal set of options that you must configure in order to run the
dashboard is the following:

    [iam]
    base_url = <IAM endpoint>
    client_id = <OpenID Connect Client ID>
    client_secret = <OpenID Connect Client Secret>

    [orchestrator]
    url = <orchestrator_url>

As you can see, you need to create an OpenID Connect Client in an IAM instance,
then add it to the configuration file. Assuming that you are using the DEEP
production infrastructure, the endpoints can be configured as follows:

    [iam]
    base_url = "https://iam.deep-hybrid-datacloud.eu"
    client_id = <OpenID Connect Client ID>
    client_secret = <OpenID Connect Client Secret>

    [orchestrator]
    url = "https://deep-paas.cloud.ba.infn.it/orchestrator"

The dashboard assumes that it has read and write permissions to the runtime
directory that is configured in the `runtime_dir` configuration option. By
defaul this is set to `/var/run/deep-dashboard/`.

# Running the dashboard

The simplest way is to use the Docker compose with the compose file that is
provided.

First of all, you would need to define a `docker/.env` file, containing
the aforementioned minimal configuration. Validate the docker-compose file 
with:

    docker-compose -f docker/docker-compose.yml config


Then you can build the containers needed, and start the Docker compose with:

    make docker-compose-build
    make docker-compose-run

If you wish to use a different environment file, you can do so, indicating it
with the `COMPOSE_LOCAL_ENV` environment variable:

    COMPOSE_LOCAL_ENV=foo.env make (...)

Or, directly with Docker compose:

    docker-compose -f docker/docker-compose.yml build
    docker-compose -f docker/docker-compose.yml --compatibility up --force-recreate

# Acknowledgements

This software has been developed within the DEEP-Hybrid-DataCloud (Designing
and Enabling E-infrastructures for intensive Processing in a Hybrid DataCloud)
project that has received funding from the European Union's Horizon 2020
research and innovation programme under grant agreement No 777435.

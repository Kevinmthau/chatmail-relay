import io

from chatmaild.config import Config
from pyinfra.operations import apt, files, systemd

from cmdeploy.basedeploy import (
    Deployer,
    get_resource,
)


class NginxDeployer(Deployer):
    def __init__(self, config):
        self.config = config

    def install(self):
        #
        # If we allow nginx to start up on install, it will grab port
        # 80, which then will block acmetool from listening on the port.
        # That in turn prevents getting certificates, which then causes
        # an error when we try to start nginx on the custom config
        # that leaves port 80 open but also requires certificates to
        # be present.  To avoid getting into that interlocking mess,
        # we use policy-rc.d to prevent nginx from starting up when it
        # is installed.
        #
        # This approach allows us to avoid performing any explicit
        # systemd operations during the install stage (as opposed to
        # allowing it to start and then forcing it to stop), which allows
        # the install stage to run in non-systemd environments like a
        # container image build.
        #
        # For documentation about policy-rc.d, see:
        # https://people.debian.org/~hmh/invokerc.d-policyrc.d-specification.txt
        #
        files.put(
            src=get_resource("policy-rc.d"),
            dest="/usr/sbin/policy-rc.d",
            user="root",
            group="root",
            mode="755",
        )

        apt.packages(
            name="Install nginx",
            packages=["nginx", "libnginx-mod-stream"],
        )

        files.file("/usr/sbin/policy-rc.d", present=False)

    def configure(self):
        self.need_restart = _configure_nginx(self.config)

    def activate(self):
        systemd.service(
            name="Start and enable nginx",
            service="nginx.service",
            running=True,
            enabled=True,
            restarted=self.need_restart,
        )
        self.need_restart = False


def _configure_nginx(config: Config, debug: bool = False) -> bool:
    """Configures nginx HTTP server."""
    need_restart = False
    admin_create_enabled = bool(
        config.admin_create_user and config.admin_create_password_hash
    )

    main_config = files.template(
        src=get_resource("nginx/nginx.conf.j2"),
        dest="/etc/nginx/nginx.conf",
        user="root",
        group="root",
        mode="644",
        config={"domain_name": config.mail_domain},
        admin_create_enabled=admin_create_enabled,
        disable_ipv6=config.disable_ipv6,
    )
    need_restart |= main_config.changed

    autoconfig = files.template(
        src=get_resource("nginx/autoconfig.xml.j2"),
        dest="/var/www/html/.well-known/autoconfig/mail/config-v1.1.xml",
        user="root",
        group="root",
        mode="644",
        config={"domain_name": config.mail_domain},
    )
    need_restart |= autoconfig.changed

    mta_sts_config = files.template(
        src=get_resource("nginx/mta-sts.txt.j2"),
        dest="/var/www/html/.well-known/mta-sts.txt",
        user="root",
        group="root",
        mode="644",
        config={"domain_name": config.mail_domain},
    )
    need_restart |= mta_sts_config.changed

    # install CGI newemail script
    #
    cgi_dir = "/usr/lib/cgi-bin"
    files.directory(
        name=f"Ensure {cgi_dir} exists",
        path=cgi_dir,
        user="root",
        group="root",
    )

    files.put(
        name="Upload cgi newemail.py script",
        src=get_resource("newemail.py", pkg="chatmaild").open("rb"),
        dest=f"{cgi_dir}/newemail.py",
        user="root",
        group="root",
        mode="755",
    )

    files.put(
        name="Upload cgi admin-create.py script",
        src=get_resource("admin_create.py", pkg="chatmaild").open("rb"),
        dest=f"{cgi_dir}/admin-create.py",
        user="root",
        group="root",
        mode="755",
    )

    if admin_create_enabled:
        # admin-create CGI runs under fcgiwrap as www-data, but must create mailbox
        # directories and password files as vmail to match service ownership.
        apt.packages(name="Install sudo (admin-create helper)", packages=["sudo"])
        sudoers = files.put(
            name="Install sudoers rule for admin-create helper",
            src=io.BytesIO(
                b"www-data ALL=(vmail) NOPASSWD: /usr/local/lib/chatmaild/venv/bin/chatmail-admin-create-helper\n"
            ),
            dest="/etc/sudoers.d/chatmail-admin-create",
            user="root",
            group="root",
            mode="440",
        )
        need_restart |= sudoers.changed

        htpasswd_content = (
            f"{config.admin_create_user}:{config.admin_create_password_hash}\n".encode()
        )
        admin_auth = files.put(
            name="Upload nginx admin auth file",
            src=io.BytesIO(htpasswd_content),
            dest="/etc/nginx/chatmail-admin.htpasswd",
            user="root",
            group="www-data",
            mode="640",
        )
        need_restart |= admin_auth.changed
    else:
        sudoers_removed = files.file(
            name="Remove sudoers rule when admin endpoint is disabled",
            path="/etc/sudoers.d/chatmail-admin-create",
            present=False,
        )
        need_restart |= sudoers_removed.changed

        admin_auth_removed = files.file(
            name="Remove nginx admin auth file when admin endpoint is disabled",
            path="/etc/nginx/chatmail-admin.htpasswd",
            present=False,
        )
        need_restart |= admin_auth_removed.changed

    return need_restart

"""Installs and configures rspamd for local Postfix milter scanning."""

from pyinfra.operations import apt, files, systemd

from cmdeploy.basedeploy import Deployer, get_resource


class RspamdDeployer(Deployer):
    def install(self):
        apt.packages(
            name="Install rspamd",
            packages=["rspamd"],
        )

    def configure(self):
        need_restart = False

        files.directory(
            name="Ensure rspamd local.d exists",
            path="/etc/rspamd/local.d",
            user="root",
            group="root",
            mode="755",
            present=True,
        )

        proxy_conf = files.put(
            name="Configure rspamd milter worker",
            src=get_resource("rspamd/worker-proxy.inc"),
            dest="/etc/rspamd/local.d/worker-proxy.inc",
            user="root",
            group="root",
            mode="644",
        )
        need_restart |= proxy_conf.changed

        actions_conf = files.put(
            name="Configure rspamd actions",
            src=get_resource("rspamd/actions.conf"),
            dest="/etc/rspamd/local.d/actions.conf",
            user="root",
            group="root",
            mode="644",
        )
        need_restart |= actions_conf.changed

        self.need_restart = need_restart

    def activate(self):
        systemd.service(
            name="Start and enable rspamd",
            service="rspamd.service",
            running=True,
            enabled=True,
            restarted=self.need_restart,
        )
        self.need_restart = False


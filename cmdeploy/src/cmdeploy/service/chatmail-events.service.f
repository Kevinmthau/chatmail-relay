[Unit]
Description=Relay-mediated chatmail event stream service

[Service]
ExecStart={execpath} 127.0.0.1:3350 {config_path}
Restart=always
RestartSec=30
User=vmail

[Install]
WantedBy=multi-user.target

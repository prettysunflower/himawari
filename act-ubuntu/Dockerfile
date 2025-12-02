FROM docker.io/gitea/runner-images:ubuntu-latest

# Add kubectl and dependencies for infra

RUN curl -fsSL https://pkgs.k8s.io/core:/stable:/v1.33/deb/Release.key | gpg --dearmor -o /etc/apt/keyrings/kubernetes-apt-keyring.gpg
RUN chmod 644 /etc/apt/keyrings/kubernetes-apt-keyring.gpg
RUN echo 'deb [signed-by=/etc/apt/keyrings/kubernetes-apt-keyring.gpg] https://pkgs.k8s.io/core:/stable:/v1.33/deb/ /' | tee /etc/apt/sources.list.d/kubernetes.list
RUN chmod 644 /etc/apt/sources.list.d/kubernetes.list
RUN apt-get update
RUN apt install -y kubectl fd-find php-cli unzip

# Add Rust toolchains

RUN curl https://sh.rustup.rs -sSf | sh -s -- -y 
ENV PATH="$PATH:/root/.cargo/bin"
RUN rustup toolchain install beta
RUN rustup toolchain install nightly 

# Add DNSControl and SOPS (infra)

RUN curl -LO https://github.com/StackExchange/dnscontrol/releases/download/v4.27.1/dnscontrol-4.27.1.amd64.deb
RUN curl -LO https://github.com/getsops/sops/releases/download/v3.11.0/sops_3.11.0_amd64.deb
RUN apt install -y ./sops_3.11.0_amd64.deb ./dnscontrol-4.27.1.amd64.deb
RUN rm ./sops_3.11.0_amd64.deb ./dnscontrol-4.27.1.amd64.deb

# Add composer
# https://getcomposer.org/doc/faqs/how-to-install-composer-programmatically.md

RUN <<EOF
EXPECTED_CHECKSUM="$(php -r 'copy("https://composer.github.io/installer.sig", "php://stdout");')"
php -r "copy('https://getcomposer.org/installer', 'composer-setup.php');"
ACTUAL_CHECKSUM="$(php -r "echo hash_file('sha384', 'composer-setup.php');")"

if [ "$EXPECTED_CHECKSUM" != "$ACTUAL_CHECKSUM" ]
then
    >&2 echo 'ERROR: Invalid installer checksum'
    rm composer-setup.php
    exit 1
fi

php composer-setup.php --quiet
RESULT=$?
rm composer-setup.php
exit $RESULT
EOF
RUN mv composer.phar /usr/local/bin/composer
